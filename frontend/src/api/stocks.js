import axios from 'axios'


const apiBaseUrl = (
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
).replace(/\/+$/, '')

const apiClient = axios.create({
  baseURL: apiBaseUrl,
  timeout: 12000,
})

/** Search supported stocks using the backend autocomplete endpoint. */
export async function searchStocks(query, signal) {
  try {
    const response = await apiClient.get('/api/stocks/search', {
      params: { q: query },
      signal,
    })
    return response.data.results ?? []
  } catch (error) {
    throw normalizeApiError(error, 'search')
  }
}

/** Fetch the latest normalized quote for a stock symbol. */
export async function getStockQuote(symbol, signal) {
  try {
    const response = await apiClient.get(
      `/api/stocks/${encodeURIComponent(symbol)}/quote`,
      { signal },
    )
    return response.data
  } catch (error) {
    throw normalizeApiError(error, 'quote')
  }
}

/** Fetch normalized daily history for a symbol and dashboard range. */
export async function getStockHistory(symbol, range, signal) {
  try {
    const response = await apiClient.get(
      `/api/stocks/${encodeURIComponent(symbol)}/history`,
      {
        params: { range },
        signal,
      },
    )
    return response.data
  } catch (error) {
    throw normalizeApiError(error, 'history')
  }
}

/** Return whether an API failure was caused by request cancellation. */
export function isRequestCanceled(error) {
  return error?.code === 'ERR_CANCELED'
}

function normalizeApiError(error, requestType) {
  if (axios.isCancel(error) || error?.code === 'ERR_CANCELED') {
    return error
  }

  const status = error.response?.status
  if (status === 404) {
    return createApiError(
      'not_found',
      requestType === 'history'
        ? 'No historical prices are available for this stock.'
        : 'This stock could not be found.',
      status,
    )
  }
  if (status === 429) {
    return createApiError(
      'rate_limit',
      'Market data requests are temporarily limited. Please try again shortly.',
      status,
    )
  }
  if (status === 502) {
    return createApiError(
      'provider_unavailable',
      'Market data is temporarily unavailable. Please try again.',
      status,
    )
  }
  if (!error.response) {
    return createApiError(
      'network',
      'Unable to reach the stock service. Check that the API is running.',
    )
  }
  return createApiError(
    'unknown',
    'Something went wrong while loading market data.',
    status,
  )
}

function createApiError(code, message, status) {
  const error = new Error(message)
  error.code = code
  error.status = status
  return error
}
