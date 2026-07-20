'''Response model for the API health endpoint.'''

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    '''Represent a successful backend health check.'''

    status: Literal['ok']
