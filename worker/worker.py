import base64
import logging
import os
import sys
from io import BytesIO

import click
from PIL import Image, UnidentifiedImageError

from app.app import redis_connection
from tests.conftest import fake_redis_connection

if os.environ.get('TESTING'):
    r = fake_redis_connection()
else:
    r = redis_connection()

logger = logging.getLogger(__name__)


def process_exception(task: str, e: Exception) -> None:
    r.rpoplpush('failed_tasks', task)
    r.set(task + '_status', 'FAILED')
    raise e


@click.command()
@click.argument('name', type=str)
def start(name: str) -> None:
    if not check_name(name):
        sys.exit()
    cleanup_queue(name)
    while True:
        main_loop(name)


def check_name(name: str) -> bool:
    if name.encode() in r.lrange('worker_names', 0, -1):
        logger.error('Name already taken, cant start')
        return False
    r.lpush('worker_names', name)
    return True


def resize_image(file: bytes, task_id: str) -> None:
    im = Image.open(BytesIO(base64.b64decode(file)))
    resized_64 = im.resize((64, 64))
    resized_32 = im.resize((32, 32))
    img_byte_arr_64 = BytesIO()
    img_byte_arr_32 = BytesIO()
    resized_64.save(img_byte_arr_64, format='PNG')
    img_base64_64 = base64.b64encode(img_byte_arr_64.getvalue())
    resized_32.save(img_byte_arr_32, format='PNG')
    img_base64_32 = base64.b64encode(img_byte_arr_32.getvalue())
    r.mset(
        {
            task_id + '_64': img_base64_64,
            task_id + '_32': img_base64_32,
            task_id + '_status': 'DONE',
        }
    )


def cleanup_queue(queue: str) -> None:
    while r.llen(queue):
        task = (r.lindex(queue, -1)).decode()
        file = r.get(task + '_original')
        try:
            resize_image(file, task)
        except (UnidentifiedImageError, TypeError) as e:
            process_exception(task, e)
        else:
            r.lpop(queue)


def main_loop(queue: str) -> None:
    task = (r.brpoplpush('default', queue)).decode()
    file = r.get(task + '_original')
    logger.info('%s: Working on task %s', queue, task)
    r.set(task + '_status', 'IN_PROGRESS')
    try:
        resize_image(file, task)
    except (UnidentifiedImageError, TypeError) as e:
        process_exception(task, e)
    else:
        r.lpop(queue)


if __name__ == '__main__':
    start()  # pylint: disable=no-value-for-parameter
