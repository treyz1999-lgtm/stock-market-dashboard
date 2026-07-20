'''Health-check route for service availability monitoring.'''

from fastapi import APIRouter

from backend.app.schemas.health import HealthResponse


router = APIRouter(prefix='/api', tags=['health'])


@router.get('/health', response_model=HealthResponse)
async def get_health() -> HealthResponse:
    '''Return a lightweight indication that the API process is healthy.'''

    return HealthResponse(status='ok')
