import ErrorMessage from './ErrorMessage.jsx'
import LoadingState from './LoadingState.jsx'


const moneyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

const numberFormatter = new Intl.NumberFormat('en-US', {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Render the selected company and its latest normalized quote. */
function StockSummary({ stock, quote, isLoading, error }) {
  if (!stock) {
    return (
      <section className='summary-card empty-state' aria-label='Stock summary'>
        <div className='empty-state__icon' aria-hidden='true'>&#8599;</div>
        <h2>Select a stock to begin</h2>
        <p>Search by company name or ticker to view its latest market snapshot.</p>
      </section>
    )
  }

  const movement = quote?.change > 0 ? 'positive' : quote?.change < 0 ? 'negative' : 'neutral'
  const movementPrefix = quote?.change > 0 ? '+' : ''

  return (
    <section className='summary-card' aria-labelledby='summary-title'>
      <div className='summary-card__header'>
        <h2 id='summary-title'>{stock.name || stock.symbol}</h2>
        <span className='summary-card__symbol'>{stock.symbol}</span>
      </div>

      {error && <ErrorMessage message={error} />}
      {isLoading && !quote && <LoadingState label='Loading latest quote' />}

      {quote && (
        <div className={isLoading ? 'quote-content is-refreshing' : 'quote-content'}>
          <div className='quote-primary'>
            <span className='quote-primary__price'>
              {moneyFormatter.format(quote.current_price)}
            </span>
            <span className={`movement movement--${movement}`}>
              {movementPrefix}{numberFormatter.format(quote.change)}
              {' '}
              ({movementPrefix}{quote.percent_change.toFixed(2)}%)
            </span>
          </div>

          <dl className='quote-grid'>
            <QuoteMetric label='Open' value={quote.open} />
            <QuoteMetric label='High' value={quote.high} />
            <QuoteMetric label='Low' value={quote.low} />
            <QuoteMetric label='Prev Close' value={quote.previous_close} />
          </dl>

          <p className='quote-updated'>
            Last updated {formatTimestamp(quote.timestamp)}
          </p>
        </div>
      )}
    </section>
  )
}

function QuoteMetric({ label, value }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{moneyFormatter.format(value)}</dd>
    </div>
  )
}

function formatTimestamp(timestamp) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(timestamp * 1000))
}

export default StockSummary
