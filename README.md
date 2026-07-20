# Stock Market Dashboard

A production-style full-stack stock market dashboard built with **FastAPI**, **React**, and the **Twelve Data API**.

Users can search for publicly traded companies, retrieve current market data, and visualize historical stock performance through a responsive web interface.

---

## Features

- Stock search with autocomplete
- Current market quotes
- Historical price charts
- Responsive React dashboard
- FastAPI REST API
- Environment-based configuration
- Error handling for invalid symbols, rate limits, and provider failures
- Automated backend testing

---

## Tech Stack

### Frontend

- React
- JavaScript
- Axios
- Recharts

### Backend

- FastAPI
- Python
- httpx
- Pydantic
- Uvicorn

### External Services

- Twelve Data API

---

## Project Structure

```
backend/
frontend/
docs/
```

---

## Local Development

### Backend

```bash
python -m venv backend/.venv

backend/.venv/Scripts/python.exe -m pip install \
-r backend/requirements.txt \
-r backend/requirements-dev.txt

backend/.venv/Scripts/python.exe -m uvicorn backend.app.main:app --reload
```

### Frontend

```bash
cd frontend

npm install

npm run dev
```

---

## Environment Variables

Create:

```
backend/.env
```

Example:

```env
TWELVE_DATA_API_KEY=YOUR_API_KEY
TWELVE_DATA_BASE_URL=https://api.twelvedata.com
```

Do **not** commit your API key.

---

## Example API Endpoints

Search

```
GET /api/stocks/search?q=Apple
```

Current Quote

```
GET /api/stocks/AAPL/quote
```

Historical Prices

```
GET /api/stocks/AAPL/history?range=1Y
```

---

## Why This Project?

This project was built to gain experience developing a modern production-style web application while exploring AI-assisted software development.

OpenAI Codex was used throughout the project as a collaborative coding assistant. The development process emphasized system design, backend architecture, API integration, frontend composition, testing, and iterative refinement rather than simply generating code.

The objective was to understand how AI coding agents can accelerate software development while maintaining good engineering practices and code quality.
