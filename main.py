from datetime import (
    datetime
)

from loguru import logger

from config import (
    LOG_PATH,
    RABBITMQ_QUEUE_KEY,
    RABBITMQ_URL,
    RESOURCES_PATH
)
from src.report_service import PhoneReportService


def run_service():
    LOG_PATH.mkdir(parents=True, exist_ok=True)
    logger.add(LOG_PATH.joinpath(f"{datetime.utcnow().strftime('%d%m%Y')}.log"))

    data_file_path = RESOURCES_PATH.joinpath("data.json")
    service = PhoneReportService(url=RABBITMQ_URL, queue_key=RABBITMQ_QUEUE_KEY, data_path=data_file_path)

    service.run()


if __name__ == "__main__":
    run_service()
