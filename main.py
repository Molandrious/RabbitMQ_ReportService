import asyncio
import json
from datetime import (
    datetime,
    timezone
)
from functools import wraps
from pathlib import Path
from time import (
    perf_counter
)
from typing import Any

import aio_pika
from aio_pika import (
    connect
)
from aio_pika.abc import AbstractIncomingMessage
from loguru import logger

from config import (
    LOG_PATH,
    RABBITMQ_QUEUE_KEY,
    RABBITMQ_URL,
    RESOURCES_PATH
)


def measure_time(func):
    """
    Decorator for measuring the execution time of an asynchronous function.

    :param func: Asynchronous function to be measured.
    :return: Dictionary with the execution time (duration) and result of the function.
    """

    @wraps(func)
    async def wrapper(*args, **kwargs) -> dict[str, Any]:
        start_time = perf_counter()
        result = await func(*args, **kwargs)
        duration = perf_counter() - start_time
        return {"duration": duration, "result": result}

    return wrapper


class PhoneReportService:
    """
    Initializes the PhoneReportService instance.

    :param url: RabbitMQ URL.
    :param queue_key: Queue key for RabbitMQ.
    :param data_path: Path to the data file.
    :param max_one_time_requests: Maximum number of one-time requests (default: 10).
    """

    def __init__(self, url: str, queue_key: str, data_path: Path, max_one_time_requests: int = 10):
        raw_data = self._load_data_from_file(path=data_path)
        self.data = self._format_data(data=raw_data)

        self._url = url
        self._queue_key = queue_key
        self._max_one_time_requests = max_one_time_requests

        self._connection = None
        self._channel = None

    async def _handle_request(self, request: dict) -> dict:
        """
        Handles the incoming request.

        :param request: Request dictionary containing "phones" key.
        :return: Dictionary containing the data and total duration.
        """

        result = await self._get_report_for_phone(data=self.data, phone_numbers=request["phones"])
        report = {
            "data": result["result"],
            "total_duration": result["duration"],
        }
        return report

    async def _callback(self, message: AbstractIncomingMessage) -> Any:
        """
        Callback function to handle incoming RabbitMQ messages.

        :param message: Incoming RabbitMQ message.
        :return: Any.
        """
        logger.info(f"Received message {message.correlation_id} with body {str(message.body)}")
        async with message.process():
            received_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")

            request = json.loads(message.body)
            try:
                report = await self._handle_request(request=request)
                status = "Complete"
            except Exception as e:  # TODO: handle exceptions
                logger.exception(e)
                status = "Error"

            response = {
                "correlation_id": message.correlation_id,
                "status": status,
                "task_received": received_at,
                "from": "report_generator_service",
                "to": "client",
            }

            response.update(report)

            await self._channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(response).encode(),
                    correlation_id=message.correlation_id,
                    reply_to=message.reply_to
                ),
                routing_key=message.reply_to
            )
            logger.success(f"Sent response for message {message.correlation_id}")

    async def _connect(self):
        """
        Asynchronously establishes a connection with RabbitMQ and subscribes to the queue.
        """

        logger.info(f"Connecting to RabbitMQ: '{self._url}'")
        self._connection = await connect(self._url)
        logger.success(f"Connected to RabbitMQ")

        async with self._connection as connection:
            self._channel = await connection.channel()

            await self._channel.set_qos(prefetch_count=self._max_one_time_requests)
            self.queue = await self._channel.declare_queue(self._queue_key, durable=True)
            await self.queue.consume(callback=self._callback)

            logger.info("Waiting for messages. To exit press CTRL+C")
            await asyncio.Future()

    @staticmethod
    @measure_time
    async def _get_report_for_phone(data: dict[int, list], phone_numbers: list[int]) -> list[dict]:
        """
        Generates a detailed report for each provided phone number.

        The report includes:
        - Total call attempts
        - Duration categories (below 10 seconds, between 10-30 seconds, and above 30 seconds)
        - Minimum call price based on duration
        - Maximum call price based on duration
        - Average call duration
        - Total price for all calls exceeding 15 seconds in price

        :param data: A dictionary with phone numbers as keys and their respective data as values.
        :param phone_numbers: A list of phone numbers for which the report should be generated.
        :return: A list of dictionaries, each representing a detailed report for a phone number.
        """
        reports = []
        for number in phone_numbers:
            number_data = data.get(number, [])

            durations = []
            cnt_10_sec = 0
            cnt_10_30_sec = 0
            cnt_30_sec = 0
            sum_price_att_over_15 = 0

            if number_data:
                first_record = number_data[0] if number_data else None
                min_price_att = max_price_att = (first_record['end_date'] - first_record['start_date']) / 100
                cnt_all_attempts = len(number_data)
            else:
                min_price_att = max_price_att = 0
                cnt_all_attempts = 0

            for item in number_data:
                duration = (item['end_date'] - item['start_date']) / 1000
                durations.append(duration)
                price = duration * 10

                if price < min_price_att:
                    min_price_att = price

                if price > max_price_att:
                    max_price_att = price

                if duration >= 15:
                    sum_price_att_over_15 += price

                if duration < 10:
                    cnt_10_sec += 1
                elif 10 <= duration < 30:
                    cnt_10_30_sec += 1
                else:
                    cnt_30_sec += 1

            cnt_att_dur = {
                "10_sec": cnt_10_sec,
                "10_30_sec": cnt_10_30_sec,
                "30_sec": cnt_30_sec
            }

            avg_dur_att = sum(durations) / len(durations) if durations else 0

            number_report = {
                "phone": number,
                "cnt_all_attempts": cnt_all_attempts,
                "cnt_att_dur": cnt_att_dur,
                "min_price_att": min_price_att,
                "max_price_att": max_price_att,
                "avg_dur_att": avg_dur_att,
                "sum_price_att_over_15": sum_price_att_over_15,
            }

            reports.append(number_report)

        return reports

    @staticmethod
    def _load_data_from_file(path: Path) -> list[dict]:
        """
        Loads data from a given file path.

        :param path: Path to the file.
        :return: List of dictionaries containing the data.
        """
        logger.info(f"Reading data from file {path.as_uri()}")

        with path.open('r') as file:
            data = json.load(file)

        logger.success(f"Data from file {path.as_uri()} loaded")
        return data

    @staticmethod
    def _format_data(data: list[dict]) -> dict[int, list[dict]]:
        """
        Formats the raw data into a structured format.

        :param data: List of dictionaries containing raw data.
        :return: Dictionary with phone numbers as keys and their respective data as values.
        """
        logger.info("Formatting initial data")

        formatted_data = {}
        for item in data:
            phone = item.pop('phone')
            if phone not in formatted_data:
                formatted_data[phone] = []

            formatted_data[phone].append(item)

        logger.success("Data formatted")
        return formatted_data

    def run(self):
        asyncio.run(self._connect())


def run_service():
    LOG_PATH.mkdir(parents=True, exist_ok=True)
    current_date = datetime.utcnow().strftime("%d%m%Y")
    logger.add(LOG_PATH.joinpath(f"{current_date}.log"))

    data_file_path = RESOURCES_PATH.joinpath("data.json")
    service = PhoneReportService(url=RABBITMQ_URL, queue_key=RABBITMQ_QUEUE_KEY, data_path=data_file_path)

    service.run()


if __name__ == "__main__":
    run_service()
