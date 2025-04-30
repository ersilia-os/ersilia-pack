import asyncio, uuid, sys

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from fastapi.responses import ORJSONResponse

from ..input_schemas.compound.single import InputSchema, exemplary_input
from ..utils import (
  get_metadata,
  orient_to_json,
  get_cached_or_compute,
  create_limiter,
  rate_limit,
  extract_input,
)
from ..exceptions.errors import breaker
from ..default import OrientEnum, ErrorMessages
from ..default import ROOT
from ..exceptions.errors import AppException

sys.path.insert(0, ROOT)

limiter = create_limiter()

router = APIRouter(prefix="/job", tags=["Job"])

jobs = {}


@router.post("/submit")
@limiter.limit(rate_limit())
async def run(
  request: Request,
  requests: InputSchema = Body(..., example=exemplary_input),
  orient: OrientEnum = Query(OrientEnum.RECORDS),
  min_workers: int = Query(1, ge=1),
  max_workers: int = Query(12, ge=1),
  metadata: dict = Depends(get_metadata),
):
  if not requests:
    raise AppException(status.HTTP_400_BAD_REQUEST, ErrorMessages.EMPTY_REQUEST)

  data = requests.model_dump()
  data = extract_input(data)
  if not data:
    raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorMessages.EMPTY_DATA)

  job_id = str(uuid.uuid4())
  jobs[job_id] = {"status": "pending", "result": None}

  asyncio.create_task(
    process_job(
      job_id=job_id,
      identifier=metadata["Identifier"],
      data=data,
      max_workers=max_workers,
      min_workers=min_workers,
      metadata=metadata,
      orient=orient,
    )
  )

  return {"job_id": job_id, "message": "Job submitted successfully."}


async def process_job(
  job_id: str,
  identifier: str,
  data: dict,
  max_workers: int,
  min_workers: int,
  metadata: dict,
  orient,
):
  try:
    results, header = await asyncio.to_thread(
      breaker.call,
      get_cached_or_compute,
      identifier,
      data,
      job_id,
      max_workers,
      min_workers,
      metadata,
    )
    results = orient_to_json(results, header, data, orient, metadata["Output Type"])
    jobs[job_id]["result"] = results
    jobs[job_id]["status"] = "completed"
  except Exception as e:
    jobs[job_id]["status"] = "failed"
    jobs[job_id]["result"] = {"error": str(e)}


@router.get("/status/{job_id}")
async def get_job_status(job_id: str):
  job = jobs.get(job_id)
  if not job:
    raise HTTPException(status_code=404, detail="Job not found")
  return {"job_id": job_id, "status": job["status"]}


@router.get("/result/{job_id}")
async def get_job_result(job_id: str):
  job = jobs.get(job_id)
  if not job:
    raise HTTPException(status_code=404, detail="Job not found")
  if job["status"] != "completed":
    return {"job_id": job_id, "status": job["status"], "result": None}
  return ORJSONResponse(job["result"])


@router.post("/jobs/reset")
async def reset_jobs():  # TODO: this of course requires admin auth
  jobs.clear()
  return {"message": "All jobs have been reset."}
