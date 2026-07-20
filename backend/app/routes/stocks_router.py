from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from backend.app.schemas.stocks import (
    HistoryRange,
    StockHistoryResponse,
    StockQuote,
    StockSearchResponse,
)
from backend.app.services.finnhub import (
    FinnhubProvider,
    ProviderRateLimitError,
    ProviderUnavailableError,
    StockNotFoundError,
)


router = APIRouter(prefix='/api/stocks', tags=['stocks'])


def get_finnhub_provider(request: Request) -> FinnhubProvider:
    return request.app.state.finnhub_provider


ProviderDependency = Annotated[FinnhubProvider, Depends(get_finnhub_provider)]


@router.get('/search', response_model=StockSearchResponse)
async def search_stocks(
    q: Annotated[str, Query(min_length=1)],
    provider: ProviderDependency,
) -> StockSearchResponse:
    query = q.strip()
    if not query:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail='Search query must not be blank.',
        )
    try:
        results = await provider.search(query)
    except ProviderRateLimitError:
        raise _rate_limit_error() from None
    except ProviderUnavailableError:
        raise _provider_unavailable_error() from None
    return StockSearchResponse(results=results)


@router.get('/{symbol}/quote', response_model=StockQuote)
async def get_stock_quote(symbol: str, provider: ProviderDependency) -> StockQuote:
    normalized_symbol = symbol.strip().upper()
    try:
        return await provider.quote(normalized_symbol)
    except StockNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                'code': 'stock_not_found',
                'message': (
                    f'No quote data was found for symbol {normalized_symbol}.'
                ),
            },
        ) from None
    except ProviderRateLimitError:
        raise _rate_limit_error() from None
    except ProviderUnavailableError:
        raise _provider_unavailable_error() from None


@router.get('/{symbol}/history', response_model=StockHistoryResponse)
async def get_stock_history(
    symbol: str,
    provider: ProviderDependency,
    history_range: Annotated[HistoryRange, Query(alias='range')] = '1Y',
) -> StockHistoryResponse:
    normalized_symbol = symbol.strip().upper()
    try:
        records = await provider.history(normalized_symbol, history_range)
    except StockNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                'code': 'stock_not_found',
                'message': (
                    f'No historical data was found for symbol {normalized_symbol}.'
                ),
            },
        ) from None
    except ProviderRateLimitError:
        raise _rate_limit_error() from None
    except ProviderUnavailableError:
        raise _provider_unavailable_error() from None
    return StockHistoryResponse(
        symbol=normalized_symbol,
        range=history_range,
        records=records,
    )


def _rate_limit_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail={
            'code': 'provider_rate_limit',
            'message': (
                'The stock data provider request limit was reached. '
                'Try again shortly.'
            ),
        },
    )


def _provider_unavailable_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail={
            'code': 'provider_unavailable',
            'message': 'Stock data is temporarily unavailable.',
        },
    )
