import pytest
from fakeredis import FakeRedis, FakeServer
from fastapi.testclient import TestClient

from app.app import app, redis_connection

server = FakeServer()


def fake_redis_connection():
    r = FakeRedis(server=server, encoding='utf-8')
    return r


app.dependency_overrides[redis_connection] = fake_redis_connection


@pytest.fixture()
def client():
    c = TestClient(app)
    return c
