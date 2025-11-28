"""
API endpoints for fetching external models.
"""
import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

router = APIRouter()

class FetchModelsRequest(BaseModel):
    url: str = Field(..., description="URL of the external models endpoint.")
    api_key: str | None = Field(None, description="Optional API key for authorization.")

@router.post("/fetch", summary="Fetch models from an external provider")
async def fetch_models(request: FetchModelsRequest):
    """
    Fetches the models from an external provider using the provided URL and API key.
    """
    headers = {}
    if request.api_key:
        headers["Authorization"] = f"Bearer {request.api_key}"

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{request.url}/models", headers=headers)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Error fetching models: {e.response.text}",
            )
        except httpx.RequestError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"An error occurred while requesting the models: {e}",
            )
