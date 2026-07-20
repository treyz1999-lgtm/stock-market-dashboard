/** Render keyboard- and pointer-selectable stock autocomplete results. */
function SearchResults({ results, activeIndex, onHover, onSelect }) {
  return (
    <ul className='search-results' role='listbox' aria-label='Stock matches'>
      {results.map((result, index) => (
        <li key={`${result.symbol}-${index}`} role='presentation'>
          <button
            className={`search-result ${index === activeIndex ? 'is-active' : ''}`}
            type='button'
            role='option'
            aria-selected={index === activeIndex}
            onMouseEnter={() => onHover(index)}
            onMouseDown={(event) => event.preventDefault()}
            onClick={() => onSelect(result)}
          >
            <span className='search-result__name'>{result.name || result.symbol}</span>
            <span className='search-result__symbol'>
              {result.display_symbol || result.symbol}
            </span>
          </button>
        </li>
      ))}
    </ul>
  )
}

export default SearchResults
