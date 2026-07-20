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
