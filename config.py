from pathlib import Path

from envparse import Env

ROOT_PATH = Path(__file__).parent
RESOURCES_PATH = ROOT_PATH.joinpath("resources")
LOG_PATH = ROOT_PATH.joinpath("logs")

env = Env()
env.read_envfile()

RABBITMQ_URL = env.str(
    "RABBITMQ_URL",
    default="amqp://guest:guest@localhost:5672/"
)
RABBITMQ_QUEUE_KEY = env.str(
    "RABBITMQ_QUEUE_KEY",
    default="ReportGeneratorQueue"
)
