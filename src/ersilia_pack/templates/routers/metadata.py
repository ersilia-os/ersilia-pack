import os
from typing import Dict, List, Union, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..default import CardField, Worker, APIInfo
from ..default import ROOT_ENDPOINT_LOADED, API_ID, API_START_TIME, MODEL_VERSION, RUNTIME, MAX_WORKERS, MIN_WORKERS, MAX_BATCH_SIZE, MAX_BATCH_DELAY, LOADED_AT_STARTUP
from ..utils import get_metadata, create_limiter, rate_limit, compute_memory_usage


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


def compute_status() -> str:
    global ROOT_ENDPOINT_LOADED
    return "READY" if ROOT_ENDPOINT_LOADED else "NOT_READY"

@router.get("/", tags=["Root"])
async def read_root(request: Request, metadata: Dict[str, Any] = Depends(get_metadata)):
  return {metadata["Identifier"]: metadata["Slug"]}

@router.get(
    "/info",
    tags=["Info"],
    summary="API Information",
    description="Detailed information about available API endpoints",
)
async def get_api_info(request: Request, metadata: Dict[str, Any] = Depends(get_metadata)):
    memory_usage = compute_memory_usage()
    status = compute_status()
    pid = os.getpid()

    worker_info = Worker(
        id=API_ID,
        startTime=API_START_TIME,
        status=status,
        memoryUsage=memory_usage,
        pid=pid
    )

    api_info = APIInfo(
        modelName=metadata["Identifier"],
        modelVersion=MODEL_VERSION,
        runtime=RUNTIME,
        minWorkers=MIN_WORKERS,
        maxWorkers=MAX_WORKERS,
        maxBatchSize=MAX_BATCH_SIZE,
        maxBatchDelay=MAX_BATCH_DELAY,
        loadedAtStartup=LOADED_AT_STARTUP,
        workers=[worker_info]
    )
    
    return JSONResponse(content=[api_info.dict()])