import uuid, sys, psutil
from fastapi import APIRouter, Body, Depends, Query, Request, status
from fastapi.responses import ORJSONResponse
from ..input_schemas.compound.single import InputSchema, exemplary_input
from ..utils import (
  get_metadata,
  orient_to_json,
  load_csv_data,
  get_cached_or_compute,
  create_limiter,
  rate_limit,
  extract_input,
)
from ..exceptions.errors import breaker
from ..default import OrientEnum, ErrorMessages
from ..default import (
  ROOT,
  generic_example_input_file,
  generic_example_output_file,
  MAX_CPU_PERC,
  MAX_MEM_PERC,
)
from ..exceptions.errors import AppException

sys.path.insert(0, ROOT)

router = APIRouter()
limiter = create_limiter()


@router.get("/run/example/input", tags=["Run"])
async def example_input(
  request: Request,
  orient: OrientEnum = Query(OrientEnum.RECORDS),
  metdata: dict = Depends(get_metadata),
):
  rows = load_csv_data(generic_example_input_file)[1]
  inputs = [element for row in rows for element in row]
  return inputs


@router.get("/run/example/output", tags=["Run"])
async def example_output(
  request: Request,
  orient: OrientEnum = Query(OrientEnum.RECORDS),
  metdata: dict = Depends(get_metadata),
):
  header, rows = load_csv_data(generic_example_output_file)

  index = [row[0] for row in rows]

  response = orient_to_json(rows, header, index, orient, metdata["Output Type"])
  return response


@router.get("/run/columns/input", tags=["Run"])
async def columns_input(request: Request):
  header = load_csv_data(generic_example_input_file)[0]
  return header


@router.get("/run/columns/output", tags=["Run"])
async def columns_output(request: Request):
  header = load_csv_data(generic_example_output_file)[0]
  return header

@router.post("/run", tags=["Run"])
@breaker
@limiter.limit(rate_limit())
def run(
  request: Request,
  requests: InputSchema = Body(..., example=exemplary_input),
  orient: OrientEnum = Query(OrientEnum.RECORDS),
  min_workers: int = Query(1, ge=1),
  max_workers: int = Query(1, ge=1),
  metadata: dict = Depends(get_metadata),
):
  if (
    psutil.cpu_percent() > MAX_CPU_PERC
    or psutil.virtual_memory().percent > MAX_MEM_PERC
  ):
    raise AppException(status.HTTP_503_SERVICE_UNAVAILABLE, ErrorMessages.RESOURCE)

  if not requests:
    raise AppException(status.HTTP_400_BAD_REQUEST, ErrorMessages.EMPTY_REQUEST)
  data = requests.model_dump()
  data = extract_input(data)

  if not data:
    raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorMessages.EMPTY_DATA)
  tag = str(uuid.uuid4())
  results, header = get_cached_or_compute(
    metadata["Identifier"], data, tag, max_workers, min_workers, metadata
  )
  results = orient_to_json(results, header, data, orient, metadata["Output Type"])
  return ORJSONResponse(results)