# Stock Market Dashboard

A production-oriented stock market dashboard project.

## Project structure

- `backend/` — backend application and tests
- `frontend/` — frontend application workspace
- `docs/` — project documentation and roadmap

This repository currently contains only the initial project structure.

## Backend development

From the repository root on Windows:

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt
backend/.venv/Scripts/python.exe -m pytest backend/tests
backend/.venv/Scripts/ruff.exe check backend
```

## Frontend development

From the `frontend/` directory:

```powershell
npm install
npm run dev
```

Create a production build with:

```powershell
npm run build
```

## Stock API examples

Copy `backend/.env.example` to `backend/.env` and set a Twelve Data API key:

```env
TWELVE_DATA_API_KEY=your_api_key_here
TWELVE_DATA_BASE_URL=https://api.twelvedata.com
```

Run the backend development server from the repository root:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn backend.app.main:app --reload
```

Search for US-listed symbols by company name or ticker:

```text
GET http://127.0.0.1:8000/api/stocks/search?q=Apple
```

Retrieve a current normalized quote:

```text
GET http://127.0.0.1:8000/api/stocks/AAPL/quote
```

Retrieve normalized daily price history:

```text
GET http://127.0.0.1:8000/api/stocks/AAPL/history?range=1Y
```

Twelve Data credentials are loaded server-side from `backend/.env` and must not be
included in browser requests.
