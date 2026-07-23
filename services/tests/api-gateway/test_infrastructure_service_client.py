import pytest
from unittest.mock import MagicMock
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


class TestRequestHeaders:
    def test_defaults_to_json_content_type(self):
        assert ServiceClient._build_request_headers(None) == {'Content-Type': 'application/json'}

    def test_propagates_whitelisted_headers_in_title_case(self):
        headers = ServiceClient._build_request_headers({
            'Authorization': 'Bearer token',
            'x-user-id': 'user-1',
            'X-Correlation-Id': 'corr-1',
            'Cookie': 'secret',
        })
        assert headers['Authorization'] == 'Bearer token'
        assert headers['X-User-Id'] == 'user-1'
        assert headers['X-Correlation-Id'] == 'corr-1'
        assert 'Cookie' not in headers


class TestRequestBranches:
    def _client_with_session(self, base_url=''):
        client = ServiceClient(base_url)
        client._session = MagicMock()
        return client

    def test_success_parses_json_body(self):
        client = self._client_with_session('http://svc:8000')
        response = MagicMock(text='{"ok": true}', status_code=200)
        response.json.return_value = {"ok": True}
        client._session.request.return_value = response
        data, status = client.request('GET', '/things')
        assert (data, status) == ({"ok": True}, 200)
        assert client._session.request.call_args.kwargs['url'] == 'http://svc:8000/things'

    def test_empty_body_returns_empty_dict(self):
        client = self._client_with_session()
        response = MagicMock(text='', status_code=204)
        client._session.request.return_value = response
        data, status = client.request('DELETE', 'http://svc:8000/things/1')
        assert (data, status) == ({}, 204)

    def test_unexpected_error_returns_502(self):
        client = self._client_with_session()
        client._session.request.side_effect = RuntimeError("boom")
        data, status = client.request('GET', 'http://svc:8000/things')
        assert status == 502
        assert data == {"error": "Internal gateway error"}
