from datetime import date
from typing import Literal

from pydantic import BaseModel


HistoryRange = Literal['1W', '1M', '3M', '6M', '1Y']


class StockSearchResult(BaseModel):
    symbol: str
    display_symbol: str
    name: str
    type: str


class StockSearchResponse(BaseModel):
    results: list[StockSearchResult]


class StockQuote(BaseModel):
    symbol: str
    current_price: float
    change: float
    percent_change: float
    high: float
    low: float
    open: float
    previous_close: float
    timestamp: int


class HistoricalPrice(BaseModel):
    timestamp: int
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class StockHistoryResponse(BaseModel):
    symbol: str
    range: HistoryRange
    records: list[HistoricalPrice]
