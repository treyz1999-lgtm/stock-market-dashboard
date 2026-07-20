'''FastAPI application construction and shared resource lifecycle.'''

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.core.config import settings
from backend.app.routes.health_router import router as health_router
from backend.app.routes.stocks_router import router as stocks_router
from backend.app.services.twelve_data import TwelveDataProvider


def create_app(transport: httpx.AsyncBaseTransport | None = None) -> FastAPI:
    '''Create the API application with a shared Twelve Data HTTP client.'''

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with httpx.AsyncClient(
            base_url=settings.TWELVE_DATA_BASE_URL.rstrip('/'),
            headers={
                'Authorization': f'apikey {settings.TWELVE_DATA_API_KEY}',
            },
            timeout=httpx.Timeout(10.0),
            transport=transport,
        ) as client:
            app.state.stock_provider = TwelveDataProvider(client=client)
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
