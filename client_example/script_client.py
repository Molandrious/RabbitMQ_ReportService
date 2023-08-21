import asyncio
import json
import uuid
from pathlib import Path

from aio_pika import (
    connect,
    DeliveryMode,
    Message
)
from aio_pika.abc import AbstractIncomingMessage
from envparse import Env
from loguru import logger

env = Env()
env.read_envfile()

RABBITMQ_URL = env.str(
    "RABBITMQ_URL",
    default="amqp://guest:guest@localhost:5673/"
)
RABBITMQ_QUEUE_KEY = env.str(
    "RABBITMQ_QUEUE_KEY",
    default="ReportServiceQueue"
)


class ReportServiceClient:
    def __init__(self, url: str, queue_key: str):
        self.url = url
        self.queue_key = queue_key
        self.loop = asyncio.get_event_loop()
        self.connection = None
        self.channel = None
        self.callback_queue = None
        self.futures = {}

    async def connect(self):
        self.connection = await connect(url=self.url)
        self.channel = await self.connection.channel()
        self.callback_queue = await self.channel.declare_queue("", exclusive=True)
        await self.callback_queue.consume(self._on_response)

    async def _on_response(self, message: AbstractIncomingMessage):
        corr_id = message.correlation_id
        future = self.futures.get(corr_id)
        if future:
            future.set_result(message.body)

    async def send_message(self, task_data: dict):
        corr_id = str(uuid.uuid4())
        future = self.loop.create_future()
        self.futures[corr_id] = future

        serialized_data = json.dumps(task_data)

        message = Message(
            body=serialized_data.encode(),
            correlation_id=corr_id,
            reply_to=self.callback_queue.name,
            delivery_mode=DeliveryMode.PERSISTENT
        )

        await self.channel.default_exchange.publish(message=message, routing_key=self.queue_key)

        return await future

    async def close(self):
        logger.info("Closing connection")
        await self.connection.close()

    async def send_message_and_wait_for_response(self, sample_data: dict):
        logger.info(f"Sending message with data: {sample_data}")
        response = await self.send_message(sample_data)
        logger.success(f"Received: {response}")


async def main():
    requests_path = Path("example_requests.json")
    sample_requests = json.load(requests_path.open("r"))  # load sample requests

    # sample_requests = [
    #     {'phones': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
    #     {'phones': [171, 181, 182, 176, 183, 180, 198, 90, 32, 161]},
    #     {'phones': [67, 116, 125, 107, 187, 140, 0, 33, 114, 78]},
    # ]

    client = ReportServiceClient(url=RABBITMQ_URL, queue_key=RABBITMQ_QUEUE_KEY)
    await client.connect()

    tasks = [client.send_message_and_wait_for_response(sample_data) for sample_data in sample_requests]

    logger.info("Waiting for responses")
    await asyncio.gather(*tasks)

    logger.success("Got responses for all sent messages")
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
