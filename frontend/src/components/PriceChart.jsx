import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import ErrorMessage from './ErrorMessage.jsx'
import LoadingState from './LoadingState.jsx'


const moneyFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

/** Render responsive closing-price history with direction-aware styling. */
function PriceChart({ records, isLoading, error, symbol }) {
  if (!symbol) {
    return (
      <div className='chart-empty'>
        <div className='chart-empty__line' aria-hidden='true' />
        <p>Historical closing prices will appear here.</p>
      </div>
    )
  }

  if (isLoading && records.length === 0) {
    return <LoadingState label='Loading price history' />
  }

  if (error && records.length === 0) {
    return <ErrorMessage message={error} />
  }

  if (records.length === 0) {
    return <p className='chart-empty'>No historical prices are available.</p>
  }

  const isPositive = records.at(-1).close >= records[0].close
  const directionColor = isPositive ? '#28d17c' : '#ff5c6c'
  const prices = records.map((record) => record.close)
  const pricePadding = Math.max((Math.max(...prices) - Math.min(...prices)) * 0.12, 1)
  const domain = [
    Math.max(0, Math.min(...prices) - pricePadding),
    Math.max(...prices) + pricePadding,
  ]

  return (
    <div className={isLoading ? 'chart-wrap is-refreshing' : 'chart-wrap'}>
      {error && <ErrorMessage message={error} />}
      <ResponsiveContainer width='100%' height='100%'>
        <ComposedChart data={records} margin={{ top: 16, right: 12, left: 6, bottom: 4 }}>
          <CartesianGrid stroke='#222831' strokeDasharray='3 6' vertical={false} />
          <XAxis
            dataKey='date'
            axisLine={false}
            tickLine={false}
            minTickGap={34}
            tick={{ fill: '#6f7884', fontSize: 12 }}
            tickFormatter={formatShortDate}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            width={70}
            domain={domain}
            tick={{ fill: '#6f7884', fontSize: 12 }}
            tickFormatter={(value) => `$${value.toFixed(0)}`}
          />
          <Tooltip
            content={<ChartTooltip color={directionColor} />}
            cursor={{ stroke: '#596574', strokeWidth: 1 }}
          />
          <Area
            type='monotone'
            dataKey='close'
            stroke='none'
            fill={directionColor}
            fillOpacity={0.07}
            isAnimationActive={false}
          />
          <Line
            type='monotone'
            dataKey='close'
            stroke={directionColor}
            strokeWidth={2}
            dot={false}
            activeDot={{
              r: 7,
              fill: directionColor,
              stroke: '#11151a',
              strokeWidth: 3,
              style: {
                filter: `drop-shadow(0 0 5px ${directionColor})`,
              },
            }}
            isAnimationActive={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}

function ChartTooltip({ active, payload, color }) {
  if (!active || !payload?.length) {
    return null
  }

  const record = payload[0].payload
  return (
    <div className='chart-tooltip' style={{ '--chart-accent': color }}>
      <span className='chart-tooltip__date'>{formatLongDate(record.date)}</span>
      <span className='chart-tooltip__label'>Close</span>
      <strong style={{ color }}>{moneyFormatter.format(record.close)}</strong>
    </div>
  )
}

function formatShortDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${date}T00:00:00Z`))
}

function formatLongDate(date) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    timeZone: 'UTC',
  }).format(new Date(`${date}T00:00:00Z`))
}

export default PriceChart
