import logging
import math
from datetime import UTC, datetime, timedelta
from typing import Any

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


class StockNotFoundError(Exception):
    pass


class ProviderRateLimitError(Exception):
    pass


class ProviderUnavailableError(Exception):
    pass


class FinnhubProvider:
    def __init__(self, client: httpx.AsyncClient, api_key: str) -> None:
        self._client = client
        self._api_key = api_key

    async def search(self, query: str) -> list[StockSearchResult]:
        payload = await self._get_json(
            '/search',
            operation='symbol search',
            params={'q': query, 'exchange': 'US'},
        )
        if not isinstance(payload, dict) or not isinstance(payload.get('result'), list):
            self._log_malformed('symbol search')
            raise ProviderUnavailableError

        results: list[StockSearchResult] = []
        for item in payload['result']:
            if not isinstance(item, dict):
                continue
            results.append(
                StockSearchResult(
                    symbol=self._as_text(item.get('symbol')),
                    display_symbol=self._as_text(item.get('displaySymbol')),
                    name=self._as_text(item.get('description')),
                    type=self._as_text(item.get('type')),
                )
            )
            if len(results) == 10:
                break
        return results

    async def quote(self, symbol: str) -> StockQuote:
        payload = await self._get_json(
            '/quote',
            operation='stock quote',
            params={'symbol': symbol},
        )
        if not isinstance(payload, dict):
            self._log_malformed('stock quote')
            raise ProviderUnavailableError

        required_fields = ('c', 'd', 'dp', 'h', 'l', 'o', 'pc', 't')
        if not payload or any(field not in payload for field in required_fields):
            raise StockNotFoundError
        if not all(self._is_number(payload[field]) for field in required_fields):
            self._log_malformed('stock quote')
            raise ProviderUnavailableError
        if payload['c'] <= 0 or payload['t'] <= 0:
            raise StockNotFoundError

        return StockQuote(
            symbol=symbol,
            current_price=payload['c'],
            change=payload['d'],
            percent_change=payload['dp'],
            high=payload['h'],
            low=payload['l'],
            open=payload['o'],
            previous_close=payload['pc'],
            timestamp=int(payload['t']),
        )

    async def history(
        self,
        symbol: str,
        history_range: HistoryRange,
    ) -> list[HistoricalPrice]:
        end = datetime.now(UTC)
        start = end - timedelta(days=HISTORY_RANGE_DAYS[history_range])
        payload = await self._get_json(
            '/stock/candle',
            operation='stock history',
            params={
                'symbol': symbol,
                'resolution': 'D',
                'from': int(start.timestamp()),
                'to': int(end.timestamp()),
            },
        )
        if not isinstance(payload, dict):
            self._log_malformed('stock history')
            raise ProviderUnavailableError
        if payload.get('s') == 'no_data':
            raise StockNotFoundError
        if payload.get('s') != 'ok':
            self._log_malformed('stock history')
            raise ProviderUnavailableError

        field_names = ('t', 'o', 'h', 'l', 'c', 'v')
        arrays = [payload.get(field) for field in field_names]
        if not all(isinstance(values, list) for values in arrays):
            self._log_malformed('stock history')
            raise ProviderUnavailableError
        lengths = {len(values) for values in arrays}
        if lengths == {0}:
            raise StockNotFoundError
        if len(lengths) != 1:
            self._log_malformed('stock history')
            raise ProviderUnavailableError

        records: list[HistoricalPrice] = []
        for timestamp, open_price, high, low, close, volume in zip(*arrays):
            values = (timestamp, open_price, high, low, close, volume)
            if not all(self._is_number(value) for value in values) or timestamp <= 0:
                self._log_malformed('stock history')
                raise ProviderUnavailableError
            normalized_timestamp = int(timestamp)
            records.append(
                HistoricalPrice(
                    timestamp=normalized_timestamp,
                    date=datetime.fromtimestamp(normalized_timestamp, UTC).date(),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )

        return sorted(records, key=lambda record: record.timestamp)

    async def _get_json(
        self,
        path: str,
        *,
        operation: str,
        params: dict[str, str | int],
    ) -> Any:
        request_params = {**params, 'token': self._api_key}
        try:
            response = await self._client.get(path, params=request_params)
        except httpx.TimeoutException:
            logger.warning('Finnhub %s request timed out.', operation)
            raise ProviderUnavailableError from None
        except httpx.RequestError:
            logger.warning('Finnhub %s connection failed.', operation)
            raise ProviderUnavailableError from None

        if response.status_code == 429:
            logger.warning('Finnhub rate limit reached during %s.', operation)
            raise ProviderRateLimitError
        if response.is_error:
            logger.warning(
                'Finnhub %s returned HTTP status %s.',
                operation,
                response.status_code,
            )
            raise ProviderUnavailableError

        try:
            return response.json()
        except ValueError:
            self._log_malformed(operation)
            raise ProviderUnavailableError from None

    @staticmethod
    def _as_text(value: object) -> str:
        return value if isinstance(value, str) else ''

    @staticmethod
    def _is_number(value: object) -> bool:
        return (
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
        )

    @staticmethod
    def _log_malformed(operation: str) -> None:
        logger.warning('Finnhub %s returned malformed data.', operation)
