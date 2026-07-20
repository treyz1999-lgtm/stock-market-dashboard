'''Twelve Data integration, normalization, errors, and in-memory caching.'''

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from time import monotonic
from typing import Any, Generic, TypeVar

import httpx

from backend.app.schemas.stocks import (
    HistoricalPrice,
    HistoryRange,
    StockQuote,
    StockSearchResult,
)


logger = logging.getLogger(__name__)

HISTORY_RANGE_DAYS: dict[HistoryRange, int] = {
    '1W': 7,
    '1M': 30,
    '3M': 90,
    '6M': 180,
    '1Y': 365,
}

SEARCH_CACHE_TTL_SECONDS = 300
QUOTE_CACHE_TTL_SECONDS = 30
HISTORY_CACHE_TTL_SECONDS = 600

T = TypeVar('T')


class StockNotFoundError(Exception):
    '''Indicate that the provider has no data for the requested symbol.'''


class ProviderRateLimitError(Exception):
    '''Indicate that Twelve Data rejected a request due to rate limits.'''


class ProviderUnavailableError(Exception):
    '''Indicate a timeout, connection failure, or invalid provider response.'''


@dataclass(slots=True)
class _CacheEntry(Generic[T]):
    '''Store a normalized cached value and its monotonic expiry time.'''

    value: T
    expires_at: float


class _TTLCache(Generic[T]):
    '''Provide a small process-local time-to-live cache.'''

    def __init__(self, ttl_seconds: int, clock: Callable[[], float]) -> None:
        self._ttl_seconds = ttl_seconds
        self._clock = clock
        self._entries: dict[object, _CacheEntry[T]] = {}

    def get(self, key: object) -> T | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= self._clock():
            self._entries.pop(key, None)
            return None
        return entry.value

    def set(self, key: object, value: T) -> None:
        self._entries[key] = _CacheEntry(
            value=value,
            expires_at=self._clock() + self._ttl_seconds,
        )


class TwelveDataProvider:
    '''Fetch and normalize stock data from Twelve Data.'''

    def __init__(
        self,
        client: httpx.AsyncClient,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        self._client = client
        self._search_cache = _TTLCache[list[StockSearchResult]](
            SEARCH_CACHE_TTL_SECONDS,
            clock,
        )
        self._quote_cache = _TTLCache[StockQuote](QUOTE_CACHE_TTL_SECONDS, clock)
        self._history_cache = _TTLCache[list[HistoricalPrice]](
            HISTORY_CACHE_TTL_SECONDS,
            clock,
        )

    async def search(self, query: str) -> list[StockSearchResult]:
        '''Return up to ten normalized symbol matches, cached for five minutes.'''

        cache_key = query.casefold()
        cached = self._search_cache.get(cache_key)
        if cached is not None:
            return cached

        try:
            payload = await self._get_json(
                '/symbol_search',
                operation='symbol search',
                params={'symbol': query, 'outputsize': 10},
            )
        except StockNotFoundError:
            results: list[StockSearchResult] = []
            self._search_cache.set(cache_key, results)
            return results
        if not isinstance(payload, dict) or not isinstance(payload.get('data'), list):
            self._log_malformed('symbol search')
            raise ProviderUnavailableError

        results = []
        for item in payload['data']:
            if not isinstance(item, dict):
                continue
            symbol = self._as_text(item.get('symbol')).upper()
            if not symbol:
                continue
            results.append(
                StockSearchResult(
                    symbol=symbol,
                    display_symbol=symbol,
                    name=self._as_text(item.get('instrument_name')),
                    type=self._as_text(item.get('instrument_type')),
                )
            )
            if len(results) == 10:
                break

        self._search_cache.set(cache_key, results)
        return results

    async def quote(self, symbol: str) -> StockQuote:
        '''Return a normalized current quote, cached for thirty seconds.'''

        cached = self._quote_cache.get(symbol)
        if cached is not None:
            return cached

        payload = await self._get_json(
            '/quote',
            operation='stock quote',
            params={'symbol': symbol},
            bad_request_is_not_found=True,
        )
        if not isinstance(payload, dict):
            self._log_malformed('stock quote')
            raise ProviderUnavailableError

        fifty_two_week = payload.get('fifty_two_week')
        if not isinstance(fifty_two_week, dict):
            self._log_malformed('stock quote')
            raise ProviderUnavailableError

        try:
            quote = StockQuote(
                symbol=symbol,
                current_price=self._parse_float(payload.get('close')),
                change=self._parse_float(payload.get('change')),
                percent_change=self._parse_float(payload.get('percent_change')),
                open=self._parse_float(payload.get('open')),
                high=self._parse_float(payload.get('high')),
                low=self._parse_float(payload.get('low')),
                previous_close=self._parse_float(payload.get('previous_close')),
                week52_high=self._parse_float(fifty_two_week.get('high')),
                week52_low=self._parse_float(fifty_two_week.get('low')),
                volume=self._parse_int(payload.get('volume')),
                timestamp=self._parse_int(payload.get('timestamp')),
            )
        except (TypeError, ValueError):
            self._log_malformed('stock quote')
            raise ProviderUnavailableError from None
        if quote.current_price <= 0 or quote.timestamp <= 0:
            self._log_malformed('stock quote')
            raise ProviderUnavailableError

        self._quote_cache.set(symbol, quote)
        return quote

    async def history(
        self,
        symbol: str,
        history_range: HistoryRange,
    ) -> list[HistoricalPrice]:
        '''Return oldest-first daily OHLCV records, cached for ten minutes.'''

        cache_key = (symbol, history_range)
        cached = self._history_cache.get(cache_key)
        if cached is not None:
            return cached

        end_date = datetime.now(UTC).date()
        start_date = end_date - timedelta(days=HISTORY_RANGE_DAYS[history_range])
        payload = await self._get_json(
            '/time_series',
            operation='stock history',
            params={
                'symbol': symbol,
                'interval': '1day',
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
            },
            bad_request_is_not_found=True,
        )
        if not isinstance(payload, dict) or not isinstance(payload.get('values'), list):
            self._log_malformed('stock history')
            raise ProviderUnavailableError
        if not payload['values']:
            raise StockNotFoundError

        records: list[HistoricalPrice] = []
        try:
            for item in payload['values']:
                if not isinstance(item, dict):
                    raise ValueError
                record_date = self._parse_date(item.get('datetime'))
                records.append(
                    HistoricalPrice(
                        timestamp=int(
                            datetime.combine(record_date, time.min, UTC).timestamp()
                        ),
                        date=record_date,
                        open=self._parse_float(item.get('open')),
                        high=self._parse_float(item.get('high')),
                        low=self._parse_float(item.get('low')),
                        close=self._parse_float(item.get('close')),
                        volume=self._parse_float(item.get('volume')),
                    )
                )
        except (TypeError, ValueError):
            self._log_malformed('stock history')
            raise ProviderUnavailableError from None

        records.sort(key=lambda record: record.timestamp)
        self._history_cache.set(cache_key, records)
        return records

    async def _get_json(
        self,
        path: str,
        *,
        operation: str,
        params: dict[str, str | int],
        bad_request_is_not_found: bool = False,
    ) -> Any:
        try:
            response = await self._client.get(path, params=params)
        except httpx.TimeoutException:
            logger.warning('Twelve Data %s request timed out.', operation)
            raise ProviderUnavailableError from None
        except httpx.RequestError:
            logger.warning('Twelve Data %s connection failed.', operation)
            raise ProviderUnavailableError from None

        if response.status_code == 429:
            logger.warning('Twelve Data rate limit reached during %s.', operation)
            raise ProviderRateLimitError

        try:
            payload = response.json()
        except ValueError:
            self._log_malformed(operation)
            raise ProviderUnavailableError from None

        if response.is_error:
            self._raise_provider_error(
                operation,
                response.status_code,
                bad_request_is_not_found,
            )
        if isinstance(payload, dict) and payload.get('status') == 'error':
            self._raise_provider_error(
                operation,
                self._error_code(payload.get('code')),
                bad_request_is_not_found,
            )
        return payload

    @staticmethod
    def _raise_provider_error(
        operation: str,
        code: int,
        bad_request_is_not_found: bool,
    ) -> None:
        if code == 429:
            logger.warning('Twelve Data rate limit reached during %s.', operation)
            raise ProviderRateLimitError
        if code == 404 or (code == 400 and bad_request_is_not_found):
            raise StockNotFoundError
        logger.warning(
            'Twelve Data %s returned provider error code %s.',
            operation,
            code,
        )
        raise ProviderUnavailableError

    @staticmethod
    def _error_code(value: object) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _as_text(value: object) -> str:
        return value if isinstance(value, str) else ''

    @staticmethod
    def _parse_float(value: object) -> float:
        number = float(value)
        if not math.isfinite(number):
            raise ValueError
        return number

    @classmethod
    def _parse_int(cls, value: object) -> int:
        number = cls._parse_float(value)
        if not number.is_integer():
            raise ValueError
        return int(number)

    @staticmethod
    def _parse_date(value: object) -> date:
        if not isinstance(value, str):
            raise TypeError
        return date.fromisoformat(value[:10])

    @staticmethod
    def _log_malformed(operation: str) -> None:
        logger.warning('Twelve Data %s returned malformed data.', operation)
