import os
import psycopg2
import sys

from time import time, sleep
from typing import Union


HOST = os.getenv('POSTGRES_HOST')
PORT = os.getenv('POSTGRES_PORT')
USER = os.getenv('POSTGRES_USER')
PASS = os.getenv('POSTGRES_PASSWORD')
DATABASE = os.getenv('POSTGRES_DATABASE')

MAX_TRIES = int(os.getenv('WAIT_FOR_POSTGRES_MAX_TRIES', 10))
SLEEP_BETWEEN = int(os.getenv('WAIT_FOR_POSTGRES_SLEEP_BETWEEN', 2))


def _check_connection() -> Union[bool, Exception]:
    try:
        psycopg2.connect(
            host=HOST,
            port=PORT,
            user=USER,
            password=PASS,
            database=DATABASE,
            connect_timeout=SLEEP_BETWEEN
        )
    except Exception as e:  # noqa
        return e

    return True


print(f'1/{MAX_TRIES}: Attempting to connect to postgresql host "{HOST}:{PORT}" and database "{DATABASE}"')

for i in range(MAX_TRIES):
    def log(message: str):
        print(f'{i + 1}/{MAX_TRIES}: {message}')

    start = time()
    result = _check_connection()

    if result is True:
        log(f'Successfully connected to postgresql host "{HOST}:{PORT}" and database "{DATABASE}"')
        sys.exit(0)

    end = time() - start
    if end < SLEEP_BETWEEN:
        sleep(SLEEP_BETWEEN - end)

    if i + 1 >= MAX_TRIES:
        log(f'Error connecting to postgresql after {MAX_TRIES} attempts')
        sys.exit(1)

    log(f'Error connecting: {str(result).strip()}')
