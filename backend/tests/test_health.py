import httpx
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_route() -> None:
    with _client() as client:
        response = client.get('/api/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok'}


def test_local_react_origin_is_allowed() -> None:
    with _client() as client:
        response = client.options(
            '/api/health',
            headers={
                'Origin': 'http://localhost:5173',
                'Access-Control-Request-Method': 'GET',
            },
        )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == (
        'http://localhost:5173'
    )


def test_deployed_vercel_origin_is_allowed() -> None:
    origin = 'https://stock-market-dashboard-self.vercel.app'

    with _client() as client:
        response = client.options(
            '/api/health',
            headers={
                'Origin': origin,
                'Access-Control-Request-Method': 'GET',
            },
        )

    assert response.status_code == 200
    assert response.headers['access-control-allow-origin'] == origin


def test_unconfigured_origin_is_not_allowed() -> None:
    origin = 'http://localhost:3000'

    with _client() as client:
        response = client.options(
            '/api/health',
            headers={
                'Origin': origin,
                'Access-Control-Request-Method': 'GET',
            },
        )

    assert response.status_code == 400
    assert 'access-control-allow-origin' not in response.headers


def _client() -> TestClient:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError('The health route must not call Twelve Data.')

    return TestClient(create_app(transport=httpx.MockTransport(handler)))
