from collections.abc import Callable

import httpx
from fastapi.testclient import TestClient

from backend.app.main import create_app


QUOTE_PAYLOAD = {
    'c': 213.49,
    'd': 1.25,
    'dp': 0.589,
    'h': 214.2,
    'l': 210.1,
    'o': 211.0,
    'pc': 212.24,
    't': 1_720_000_000,
}

HISTORY_PAYLOAD = {
    's': 'ok',
    't': [1_720_086_400, 1_720_000_000],
    'o': [214.0, 211.0],
    'h': [216.0, 214.2],
    'l': [212.5, 210.1],
    'c': [215.5, 213.49],
    'v': [82_000_000, 75_000_000],
}

PROVIDER_UNAVAILABLE_DETAIL = {
    'detail': {
        'code': 'provider_unavailable',
        'message': 'Stock data is temporarily unavailable.',
    }
}


def test_company_name_search() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/api/v1/search'
        assert request.url.params['q'] == 'Apple Inc'
        assert request.url.params['exchange'] == 'US'
        assert request.url.params.get('token')
        results = [
            {
                'symbol': f'AAPL{i}',
                'displaySymbol': f'AAPL{i}',
                'description': 'Apple Inc',
                'type': 'Common Stock',
            }
            for i in range(12)
        ]
        return httpx.Response(200, json={'count': 12, 'result': results})

    with _client(handler) as client:
        response = client.get('/api/stocks/search', params={'q': '  Apple Inc  '})

    assert response.status_code == 200
    assert len(response.json()['results']) == 10
    assert response.json()['results'][0] == {
        'symbol': 'AAPL0',
        'display_symbol': 'AAPL0',
        'name': 'Apple Inc',
        'type': 'Common Stock',
    }


def test_ticker_search() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params['q'] == 'AAPL'
        return httpx.Response(
            200,
            json={
                'result': [
                    {
                        'symbol': 'AAPL',
                        'displaySymbol': 'AAPL',
                        'description': 'Apple Inc',
                        'type': 'Common Stock',
                    }
                ]
            },
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/search?q=AAPL')

    assert response.status_code == 200
    assert response.json()['results'][0]['symbol'] == 'AAPL'


def test_empty_search_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'count': 0, 'result': []})

    with _client(handler) as client:
        response = client.get('/api/stocks/search?q=not-a-company')

    assert response.status_code == 200
    assert response.json() == {'results': []}


def test_blank_search_input() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError('Finnhub must not be called for a blank search.')

    with _client(handler) as client:
        response = client.get('/api/stocks/search', params={'q': '   '})

    assert response.status_code == 422


def test_successful_quote_retrieval() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/api/v1/quote'
        assert request.url.params['symbol'] == 'AAPL'
        assert request.url.params.get('token')
        return httpx.Response(200, json=QUOTE_PAYLOAD)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 200
    assert response.json() == {
        'symbol': 'AAPL',
        'current_price': 213.49,
        'change': 1.25,
        'percent_change': 0.589,
        'high': 214.2,
        'low': 210.1,
        'open': 211.0,
        'previous_close': 212.24,
        'timestamp': 1_720_000_000,
    }


def test_lowercase_ticker_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params['symbol'] == 'MSFT'
        return httpx.Response(200, json=QUOTE_PAYLOAD)

    with _client(handler) as client:
        response = client.get('/api/stocks/%20msft%20/quote')

    assert response.status_code == 200
    assert response.json()['symbol'] == 'MSFT'


def test_unknown_ticker_with_missing_fields_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'c': 0})

    with _client(handler) as client:
        response = client.get('/api/stocks/UNKNOWN/quote')

    assert response.status_code == 404
    assert response.json() == {
        'detail': {
            'code': 'stock_not_found',
            'message': 'No quote data was found for symbol UNKNOWN.',
        }
    }


def test_empty_quote_response_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    with _client(handler) as client:
        response = client.get('/api/stocks/NONE/quote')

    assert response.status_code == 404


def test_zero_timestamp_quote_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={**QUOTE_PAYLOAD, 't': 0})

    with _client(handler) as client:
        response = client.get('/api/stocks/OLD/quote')

    assert response.status_code == 404


def test_finnhub_rate_limit_returns_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={'error': 'not returned to client'})

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 429
    assert response.json() == {
        'detail': {
            'code': 'provider_rate_limit',
            'message': (
                'The stock data provider request limit was reached. '
                'Try again shortly.'
            ),
        }
    }


def test_finnhub_timeout_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout('timed out', request=request)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_finnhub_500_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={'token': 'must not be returned'})

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_history_defaults_to_one_year_and_orders_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == '/api/v1/stock/candle'
        assert request.url.params['symbol'] == 'AAPL'
        assert request.url.params['resolution'] == 'D'
        start = int(request.url.params['from'])
        end = int(request.url.params['to'])
        assert end - start == 365 * 24 * 60 * 60
        assert request.url.params.get('token')
        return httpx.Response(200, json=HISTORY_PAYLOAD)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history')

    assert response.status_code == 200
    assert response.json() == {
        'symbol': 'AAPL',
        'range': '1Y',
        'records': [
            {
                'timestamp': 1_720_000_000,
                'date': '2024-07-03',
                'open': 211.0,
                'high': 214.2,
                'low': 210.1,
                'close': 213.49,
                'volume': 75_000_000.0,
            },
            {
                'timestamp': 1_720_086_400,
                'date': '2024-07-04',
                'open': 214.0,
                'high': 216.0,
                'low': 212.5,
                'close': 215.5,
                'volume': 82_000_000.0,
            },
        ],
    }


def test_history_range_and_lowercase_symbol_are_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params['symbol'] == 'MSFT'
        start = int(request.url.params['from'])
        end = int(request.url.params['to'])
        assert end - start == 7 * 24 * 60 * 60
        return httpx.Response(200, json=HISTORY_PAYLOAD)

    with _client(handler) as client:
        response = client.get('/api/stocks/%20msft%20/history?range=1W')

    assert response.status_code == 200
    assert response.json()['symbol'] == 'MSFT'
    assert response.json()['range'] == '1W'


def test_history_rejects_unsupported_range() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError('Finnhub must not be called for an invalid range.')

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history?range=5Y')

    assert response.status_code == 422


def test_history_no_data_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={'s': 'no_data'})

    with _client(handler) as client:
        response = client.get('/api/stocks/UNKNOWN/history?range=1M')

    assert response.status_code == 404
    assert response.json() == {
        'detail': {
            'code': 'stock_not_found',
            'message': 'No historical data was found for symbol UNKNOWN.',
        }
    }


def test_history_rate_limit_returns_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history?range=3M')

    assert response.status_code == 429
    assert response.json()['detail']['code'] == 'provider_rate_limit'


def test_history_timeout_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout('timed out', request=request)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history?range=6M')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_history_500_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_history_malformed_arrays_return_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={**HISTORY_PAYLOAD, 'c': [213.49]},
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> TestClient:
    transport = httpx.MockTransport(handler)
    return TestClient(create_app(transport=transport))
