from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.health import router as health_router
from backend.app.api.stocks import router as stocks_router
from backend.app.core.config import settings
from backend.app.services.finnhub import FinnhubProvider


def create_app(transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(
            base_url=settings.FINNHUB_BASE_URL.rstrip('/'),
            timeout=httpx.Timeout(10.0),
            transport=transport,
        ) as client:
            app.state.finnhub_provider = FinnhubProvider(
                client=client,
                api_key=settings.FINNHUB_API_KEY,
            )
            yield

    application = FastAPI(
        title='Stock Market Dashboard API',
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=['http://localhost:5173'],
        allow_credentials=True,
        allow_methods=['*'],
        allow_headers=['*'],
    )
    application.include_router(health_router)
    application.include_router(stocks_router)
    return application


app = create_app()
