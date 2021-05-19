import pytest
from click.testing import CliRunner
from PIL import UnidentifiedImageError
from redis import Redis

from app.app import redis_connection
from tests.conftest import fake_redis_connection
from worker.worker import check_name, cleanup_queue, main_loop

runner = CliRunner()
r = fake_redis_connection()


def test_upload_img(client):
    response = client.post('/tasks', files={'file': open('tests/square.png', 'rb')})
    assert response.status_code == 201
    assert response.json() == {'id': 1}


def test_upload_bad_aspect_ratio_img(client):
    response = client.post('/tasks', files={'file': open('tests/not_square.png', 'rb')})
    assert response.status_code == 400
    assert response.json() == {'error': 'image must be square'}


def test_get_task_status_waiting(client):
    client.post('/tasks', files={'file': open('tests/square.png', 'rb')})
    response = client.get('/tasks/1')
    assert response.status_code == 200
    assert response.json() == {'status': 'WAITING'}


def test_get_resized_image_32(client):
    client.post('/tasks', files={'file': open('tests/square.png', 'rb')})
    main_loop('testing')
    response = client.get('/tasks/1?size=32')
    assert response.status_code == 200
    assert response.content.startswith(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x03\x00\x00'
    )


def test_cleanup_queue(client):
    client.post('/tasks', files={'file': open('tests/square.png', 'rb')})
    r.brpoplpush('default', 'testing')
    cleanup_queue('testing')
    response = client.get('/tasks/1?size=32')
    assert response.status_code == 200
    assert response.content.startswith(
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00 \x08\x03\x00\x00'
    )


def test_get_image_before_processing_complete(client):
    client.post('/tasks', files={'file': open('tests/square.png', 'rb')})
    response = client.get('/tasks/10?size=32')
    assert response.status_code == 404
    assert response.json() == {'error': 'image not found'}


def test_check_name_false():
    name = 'bad_name'
    r.lpush('worker_names', name)
    assert check_name(name) is False


def test_check_name_true():
    name = 'good_name'
    assert check_name(name)


def test_cleanup_queue_exc():
    r.lpush('test_q', 10)
    r.set('10_original', 'not_bytes')
    with pytest.raises(UnidentifiedImageError) as e:
        cleanup_queue('test_q')
    assert 'cannot identify image file' in str(e.value)


def test_redis_connection():
    assert isinstance(redis_connection(), Redis)
