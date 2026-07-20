import { useEffect, useId, useState } from 'react'

import { isRequestCanceled, searchStocks } from '../api/stocks.js'
import ErrorMessage from './ErrorMessage.jsx'
import LoadingState from './LoadingState.jsx'
import SearchResults from './SearchResults.jsx'


const SEARCH_DELAY_MS = 350

function StockSearch({ selectedStock, onSelect }) {
  const inputId = useId()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState([])
  const [activeIndex, setActiveIndex] = useState(-1)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState('')
  const [hasSearched, setHasSearched] = useState(false)
  const [selectionLocked, setSelectionLocked] = useState(false)

  useEffect(() => {
    const trimmedQuery = query.trim()
    if (trimmedQuery.length < 2 || selectionLocked) {
      setResults([])
      setActiveIndex(-1)
      setIsLoading(false)
      setError('')
      setHasSearched(false)
      return undefined
    }

    const controller = new AbortController()
    const timeoutId = window.setTimeout(async () => {
      setIsLoading(true)
      setError('')
      try {
        const matches = await searchStocks(trimmedQuery, controller.signal)
        setResults(matches)
        setActiveIndex(matches.length ? 0 : -1)
        setHasSearched(true)
      } catch (requestError) {
        if (!isRequestCanceled(requestError)) {
          setResults([])
          setHasSearched(true)
          setError(requestError.message)
        }
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false)
        }
      }
    }, SEARCH_DELAY_MS)

    return () => {
      window.clearTimeout(timeoutId)
      controller.abort()
    }
  }, [query, selectionLocked])

  function handleChange(event) {
    setQuery(event.target.value)
    setSelectionLocked(false)
    setHasSearched(false)
  }

  function handleSelect(result) {
    setQuery(result.name || result.symbol)
    setSelectionLocked(true)
    setResults([])
    setActiveIndex(-1)
    onSelect(result)
  }

  function handleKeyDown(event) {
    if (!results.length || selectionLocked) {
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      setActiveIndex((current) => (current + 1) % results.length)
    } else if (event.key === 'ArrowUp') {
      event.preventDefault()
      setActiveIndex((current) =>
        current <= 0 ? results.length - 1 : current - 1,
      )
    } else if (event.key === 'Enter' && activeIndex >= 0) {
      event.preventDefault()
      handleSelect(results[activeIndex])
    } else if (event.key === 'Escape') {
      setResults([])
      setActiveIndex(-1)
    }
  }

  const showResults = !selectionLocked && query.trim().length >= 2

  return (
    <section className='search-block' aria-labelledby={`${inputId}-label`}>
      <div className='section-heading'>
        <div>
          <p className='eyebrow'>Symbol lookup</p>
          <h2 id={`${inputId}-label`}>Find a stock</h2>
        </div>
        {selectedStock && (
          <span className='selected-symbol'>{selectedStock.symbol}</span>
        )}
      </div>

      <div className='search-control'>
        <label className='sr-only' htmlFor={inputId}>Search by company or ticker</label>
        <span className='search-control__icon' aria-hidden='true'>⌕</span>
        <input
          id={inputId}
          value={query}
          type='search'
          autoComplete='off'
          placeholder='Search company or ticker'
          aria-autocomplete='list'
          aria-expanded={showResults && (results.length > 0 || hasSearched)}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
        />
      </div>

      {showResults && (
        <div className='search-popover'>
          {isLoading && <LoadingState label='Searching markets' />}
          {!isLoading && error && <ErrorMessage message={error} />}
          {!isLoading && !error && results.length > 0 && (
            <SearchResults
              results={results}
              activeIndex={activeIndex}
              onHover={setActiveIndex}
              onSelect={handleSelect}
            />
          )}
          {!isLoading && !error && hasSearched && results.length === 0 && (
            <p className='search-empty'>No matching US stocks found.</p>
          )}
        </div>
      )}
    </section>
  )
}

export default StockSearch
