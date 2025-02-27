from typing import Dict, List, Union

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..default import CardField
from ..utils import get_metadata, create_limiter, rate_limit


router = APIRouter()
limiter = create_limiter()


@router.get(
  "/card",
  tags=["Metadata"],
  summary="Complete Model Metadata",
)
@limiter.limit(rate_limit())
async def get_card_metadata(request: Request, metadata: dict = Depends(get_metadata)):
  return metadata


limiter = create_limiter()


@router.get(
  "/card/{field}",
  tags=["Metadata"],
  summary="Specific Metadata Field",
  response_model=Dict[str, Union[str, List[str]]],
)
@limiter.limit(rate_limit())
async def get_specific_field(
  request: Request,
  field: CardField,
  metadata: dict = Depends(get_metadata),
):
  field_value = field.value
  if field_value not in metadata:
    raise HTTPException(
      status_code=status.HTTP_404_NOT_FOUND,
      detail=f"Field {field_value} not found in metadata",
    )
  return {field_value: metadata[field_value]}


@router.get(
  "/info",
  tags=["Info"],
  summary="API Information",
  description="Detailed information about available API endpoints",
)
async def get_api_info(request: Request):
  return JSONResponse(content={"apis_list": ["run"]})
