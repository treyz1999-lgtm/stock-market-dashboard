'''Normalized stock-data response models shared by routes and services.'''

from datetime import date
from typing import Literal

from pydantic import BaseModel


HistoryRange = Literal['1W', '1M', '3M', '6M', '1Y']


class StockSearchResult(BaseModel):
    '''Represent one normalized symbol-search match.'''

    symbol: str
    display_symbol: str
    name: str
    type: str


class StockSearchResponse(BaseModel):
    '''Wrap symbol-search matches returned to API clients.'''

    results: list[StockSearchResult]


class StockQuote(BaseModel):
    '''Represent a normalized current market quote.'''

    symbol: str
    current_price: float
    change: float
    percent_change: float
    high: float
    low: float
    open: float
    previous_close: float
    week52_high: float
    week52_low: float
    volume: int
    timestamp: int


class HistoricalPrice(BaseModel):
    '''Represent one normalized daily OHLCV price record.'''

    timestamp: int
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockHistoryResponse(BaseModel):
    '''Wrap ordered historical prices for a symbol and requested range.'''

    symbol: str
    range: HistoryRange
    records: list[HistoricalPrice]
