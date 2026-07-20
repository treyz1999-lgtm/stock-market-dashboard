const RANGES = ['1W', '1M', '3M', '6M', '1Y']

function RangeSelector({ value, onChange, disabled = false }) {
  return (
    <div className='range-selector' aria-label='Historical price range'>
      {RANGES.map((range) => (
        <button
          key={range}
          className={range === value ? 'is-selected' : ''}
          type='button'
          aria-pressed={range === value}
          disabled={disabled}
          onClick={() => onChange(range)}
        >
          {range}
        </button>
      ))}
    </div>
  )
}

export default RangeSelector
