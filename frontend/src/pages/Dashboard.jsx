import { useEffect, useState } from 'react'

import {
  getStockHistory,
  getStockQuote,
  isRequestCanceled,
} from '../api/stocks.js'
import PriceChart from '../components/PriceChart.jsx'
import RangeSelector from '../components/RangeSelector.jsx'
import StockSearch from '../components/StockSearch.jsx'
import StockSummary from '../components/StockSummary.jsx'


function Dashboard() {
  const [selectedStock, setSelectedStock] = useState(null)
  const [range, setRange] = useState('1Y')
  const [quote, setQuote] = useState(null)
  const [history, setHistory] = useState([])
  const [quoteLoading, setQuoteLoading] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [quoteError, setQuoteError] = useState('')
  const [historyError, setHistoryError] = useState('')

  const selectedSymbol = selectedStock?.symbol

  useEffect(() => {
    if (!selectedSymbol) {
      return undefined
    }

    const controller = new AbortController()
    setQuoteLoading(true)
    setQuoteError('')

    getStockQuote(selectedSymbol, controller.signal)
      .then(setQuote)
      .catch((error) => {
        if (!isRequestCanceled(error)) {
          setQuoteError(error.message)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setQuoteLoading(false)
        }
      })

    return () => controller.abort()
  }, [selectedSymbol])

  useEffect(() => {
    if (!selectedSymbol) {
      return undefined
    }

    const controller = new AbortController()
    setHistoryLoading(true)
    setHistoryError('')

    getStockHistory(selectedSymbol, range, controller.signal)
      .then((response) => setHistory(response.records ?? []))
      .catch((error) => {
        if (!isRequestCanceled(error)) {
          setHistoryError(error.message)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setHistoryLoading(false)
        }
      })

    return () => controller.abort()
  }, [selectedSymbol, range])

  function handleStockSelect(stock) {
    const normalizedStock = {
      ...stock,
      symbol: stock.symbol.trim().toUpperCase(),
    }

    if (normalizedStock.symbol !== selectedSymbol) {
      setQuote(null)
      setHistory([])
      setQuoteError('')
      setHistoryError('')
    }
    setSelectedStock(normalizedStock)
  }

  return (
    <div className='dashboard-shell'>
      <header className='app-header'>
        <div className='brand'>
          <span className='brand__mark' aria-hidden='true'>M</span>
          <div>
            <span className='brand__name'>Market Ledger</span>
            <span className='brand__descriptor'>US equities tracker</span>
          </div>
        </div>
        <div className='market-status'>
          <span className='market-status__dot' aria-hidden='true' />
          Live market data
        </div>
      </header>

      <main className='dashboard-grid'>
        <aside className='dashboard-sidebar'>
          <div className='panel search-panel'>
            <StockSearch
              selectedStock={selectedStock}
              onSelect={handleStockSelect}
            />
          </div>
          <StockSummary
            stock={selectedStock}
            quote={quote}
            isLoading={quoteLoading}
            error={quoteError}
          />
        </aside>

        <section className='panel chart-panel' aria-labelledby='chart-title'>
          <div className='chart-panel__header'>
            <div>
              <p className='eyebrow'>Price history</p>
              <h1 id='chart-title'>
                {selectedStock
                  ? `${selectedStock.symbol} closing price`
                  : 'Market performance'}
              </h1>
            </div>
            <RangeSelector
              value={range}
              onChange={setRange}
              disabled={!selectedStock}
            />
          </div>

          <div className='chart-panel__body'>
            <PriceChart
              records={history}
              isLoading={historyLoading}
              error={historyError}
              symbol={selectedSymbol}
            />
          </div>
        </section>
      </main>

      <footer className='app-footer'>
        Data is provided for informational purposes and may be delayed.
      </footer>
    </div>
  )
}

export default Dashboard
