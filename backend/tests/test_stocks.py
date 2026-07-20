from collections import Counter
from collections.abc import Callable
from datetime import date

import httpx
from fastapi.testclient import TestClient

from backend.app.main import create_app


QUOTE_PAYLOAD = {
    'symbol': 'AAPL',
    'name': 'Apple Inc',
    'timestamp': 1_720_000_000,
    'open': '211.00000',
    'high': '214.20000',
    'low': '210.10000',
    'close': '213.49000',
    'volume': '75000000',
    'previous_close': '212.24000',
    'change': '1.25000',
    'percent_change': '0.58900',
    'fifty_two_week': {
        'high': '237.49000',
        'low': '164.08000',
    },
}

HISTORY_PAYLOAD = {
    'meta': {
        'symbol': 'AAPL',
        'interval': '1day',
    },
    'values': [
        {
            'datetime': '2024-07-04',
            'open': '214.00000',
            'high': '216.00000',
            'low': '212.50000',
            'close': '215.50000',
            'volume': '82000000',
        },
        {
            'datetime': '2024-07-03',
            'open': '211.00000',
            'high': '214.20000',
            'low': '210.10000',
            'close': '213.49000',
            'volume': '75000000',
        },
    ],
    'status': 'ok',
}

PROVIDER_UNAVAILABLE_DETAIL = {
    'detail': {
        'code': 'provider_unavailable',
        'message': 'Stock data is temporarily unavailable.',
    }
}


def test_company_name_search() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_authentication(request)
        assert request.url.path == '/symbol_search'
        assert request.url.params['symbol'] == 'Apple Inc'
        assert request.url.params['outputsize'] == '10'
        data = [
            {
                'symbol': f'AAPL{i}',
                'instrument_name': 'Apple Inc',
                'instrument_type': 'Common Stock',
            }
            for i in range(12)
        ]
        return httpx.Response(200, json={'data': data, 'status': 'ok'})

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


def test_ticker_search_and_empty_results() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params['symbol'] == 'AAPL':
            return httpx.Response(
                200,
                json={
                    'data': [
                        {
                            'symbol': 'AAPL',
                            'instrument_name': 'Apple Inc',
                            'instrument_type': 'Common Stock',
                        }
                    ],
                    'status': 'ok',
                },
            )
        return httpx.Response(200, json={'data': [], 'status': 'ok'})

    with _client(handler) as client:
        ticker_response = client.get('/api/stocks/search?q=AAPL')
        empty_response = client.get('/api/stocks/search?q=not-a-company')

    assert ticker_response.status_code == 200
    assert ticker_response.json()['results'][0]['symbol'] == 'AAPL'
    assert empty_response.status_code == 200
    assert empty_response.json() == {'results': []}


def test_search_provider_not_found_is_an_empty_result() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={'code': 404, 'message': 'provider detail', 'status': 'error'},
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/search?q=unlisted-company')

    assert response.status_code == 200
    assert response.json() == {'results': []}


def test_blank_search_input_returns_422_without_provider_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError('Twelve Data must not be called for a blank search.')

    with _client(handler) as client:
        response = client.get('/api/stocks/search', params={'q': '   '})

    assert response.status_code == 422


def test_successful_quote_retrieval() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_authentication(request)
        assert request.url.path == '/quote'
        assert request.url.params['symbol'] == 'AAPL'
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
        'week52_high': 237.49,
        'week52_low': 164.08,
        'volume': 75000000,
        'timestamp': 1_720_000_000,
    }


def test_lowercase_ticker_is_normalized() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params['symbol'] == 'MSFT'
        return httpx.Response(200, json={**QUOTE_PAYLOAD, 'symbol': 'MSFT'})

    with _client(handler) as client:
        response = client.get('/api/stocks/%20msft%20/quote')

    assert response.status_code == 200
    assert response.json()['symbol'] == 'MSFT'


def test_unknown_ticker_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={'code': 404, 'message': 'provider detail', 'status': 'error'},
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/UNKNOWN/quote')

    assert response.status_code == 404
    assert response.json() == {
        'detail': {
            'code': 'stock_not_found',
            'message': 'No quote data was found for symbol UNKNOWN.',
        }
    }


def test_provider_rate_limit_returns_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={'code': 429, 'message': 'provider detail', 'status': 'error'},
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 429
    assert response.json()['detail']['code'] == 'provider_rate_limit'


def test_provider_timeout_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout('timed out', request=request)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_provider_500_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={'status': 'error', 'code': 500})

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_malformed_quote_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={**QUOTE_PAYLOAD, 'close': 'not-a-number'})

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/quote')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_history_defaults_to_one_year_and_orders_records() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_authentication(request)
        assert request.url.path == '/time_series'
        assert request.url.params['symbol'] == 'AAPL'
        assert request.url.params['interval'] == '1day'
        assert 'outputsize' not in request.url.params
        start = date.fromisoformat(request.url.params['start_date'])
        end = date.fromisoformat(request.url.params['end_date'])
        assert (end - start).days == 365
        return httpx.Response(200, json=HISTORY_PAYLOAD)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history')

    assert response.status_code == 200
    assert response.json() == {
        'symbol': 'AAPL',
        'range': '1Y',
        'records': [
            {
                'timestamp': 1_719_964_800,
                'date': '2024-07-03',
                'open': 211.0,
                'high': 214.2,
                'low': 210.1,
                'close': 213.49,
                'volume': 75_000_000.0,
            },
            {
                'timestamp': 1_720_051_200,
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
        start = date.fromisoformat(request.url.params['start_date'])
        end = date.fromisoformat(request.url.params['end_date'])
        assert (end - start).days == 7
        return httpx.Response(200, json=HISTORY_PAYLOAD)

    with _client(handler) as client:
        response = client.get('/api/stocks/%20msft%20/history?range=1W')

    assert response.status_code == 200
    assert response.json()['symbol'] == 'MSFT'
    assert response.json()['range'] == '1W'


def test_history_rejects_unsupported_range_without_provider_call() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError('Twelve Data must not be called for an invalid range.')

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history?range=5Y')

    assert response.status_code == 422


def test_history_not_found_returns_404() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={'code': 404, 'message': 'provider detail', 'status': 'error'},
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/UNKNOWN/history?range=1M')

    assert response.status_code == 404
    assert response.json()['detail']['code'] == 'stock_not_found'


def test_history_rate_limit_returns_429() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={'status': 'error', 'code': 429})

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history?range=3M')

    assert response.status_code == 429


def test_history_timeout_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout('timed out', request=request)

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history?range=6M')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_history_malformed_response_returns_502() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={**HISTORY_PAYLOAD, 'values': [{'datetime': '2024-07-03'}]},
        )

    with _client(handler) as client:
        response = client.get('/api/stocks/AAPL/history')

    assert response.status_code == 502
    assert response.json() == PROVIDER_UNAVAILABLE_DETAIL


def test_successful_responses_are_cached() -> None:
    calls: Counter[str] = Counter()

    def handler(request: httpx.Request) -> httpx.Response:
        calls[request.url.path] += 1
        if request.url.path == '/symbol_search':
            return httpx.Response(200, json={'data': [], 'status': 'ok'})
        if request.url.path == '/quote':
            return httpx.Response(200, json=QUOTE_PAYLOAD)
        if request.url.path == '/time_series':
            return httpx.Response(200, json=HISTORY_PAYLOAD)
        raise AssertionError('Unexpected provider path.')

    with _client(handler) as client:
        for _ in range(2):
            assert client.get('/api/stocks/search?q=AAPL').status_code == 200
            assert client.get('/api/stocks/AAPL/quote').status_code == 200
            assert client.get('/api/stocks/AAPL/history').status_code == 200

    assert calls == Counter(
        {
            '/symbol_search': 1,
            '/quote': 1,
            '/time_series': 1,
        }
    )


def _assert_authentication(request: httpx.Request) -> None:
    assert request.headers['authorization'] == 'apikey test-api-key'
    assert 'apikey' not in request.url.params


def _client(
    handler: Callable[[httpx.Request], httpx.Response],
) -> TestClient:
    return TestClient(create_app(transport=httpx.MockTransport(handler)))
