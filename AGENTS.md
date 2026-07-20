# Contributor Guidelines

These instructions apply throughout the repository.

## Architecture

- Keep backend HTTP interfaces in `backend/app/api/`.
- Keep configuration and shared infrastructure in `backend/app/core/`.
- Keep persistence models in `backend/app/models/`.
- Keep validation and transport schemas in `backend/app/schemas/`.
- Keep business and integration logic in `backend/app/services/`.
- Keep backend tests in `backend/tests/`.
- Keep frontend work isolated in `frontend/`.
- Keep project documentation in `docs/`.

## Engineering expectations

- Do not commit secrets, credentials, or local environment files.
- Add tests alongside behavior changes.
- Keep changes focused and document significant architectural decisions.
- Prefer explicit configuration and clear module boundaries.

## Development commands

- Install backend dependencies with `backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt -r backend/requirements-dev.txt`.
- Run backend tests with `backend/.venv/Scripts/python.exe -m pytest backend/tests`.
- Run backend lint checks with `backend/.venv/Scripts/ruff.exe check backend`.
- Run the frontend development server from `frontend/` with `npm run dev`.
- Verify a frontend production build from `frontend/` with `npm run build`.

## Project conventions

- Keep the Python virtual environment at `backend/.venv/`.
- Use JavaScript, not TypeScript, for the frontend.
- Record runtime and development Python dependencies in their respective requirements files.
- Record frontend dependencies in `frontend/package.json` and commit its lockfile.
