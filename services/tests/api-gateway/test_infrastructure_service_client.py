import pytest
from infrastructure.service_client import ServiceClient


class TestServiceClient:
    def test_init_stores_base_url(self):
        client = ServiceClient('http://test:8000')
        assert client._base_url == 'http://test:8000'

    def test_init_strips_trailing_slash(self):
        client = ServiceClient('http://test:8000/')
        assert client._base_url == 'http://test:8000'

    def test_request_returns_error_on_timeout(self):
        client = ServiceClient('http://192.0.2.1:1', 0.01)
        result, status = client.request('GET', '/test')
        assert status == 504
