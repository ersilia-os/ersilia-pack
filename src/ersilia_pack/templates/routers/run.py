import uuid, sys
from fastapi import APIRouter, Body, Depends, Query, Request, status
from fastapi.responses import ORJSONResponse
from fastapi.responses import Response
from ..input_schemas.compound.single import InputSchema, exemplary_input
from ..utils import (
  get_metadata,
  orient_to_json,
  load_csv_data,
  get_cached_or_compute,
  create_limiter,
  rate_limit,
  extract_input,
  generate_resp_body,
)
from ..exceptions.errors import breaker
from ..default import OrientEnum, ErrorMessages, TaskTypeEnum
from ..default import (
  ROOT,
  CONTENT_DESP,
  MEDIA_TYPE,
  generic_example_input_file,
  generic_example_output_file,
  cprint,
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
  fetch_cache: bool = Query(True),
  save_cache: bool = Query(True),
  cache_only: bool = Query(False),
  min_workers: int = Query(1, ge=1),
  max_workers: int = Query(16, ge=1),
  output_type: str = Query("simple"),
  metadata: dict = Depends(get_metadata),
):
  if not requests:
    raise AppException(status.HTTP_400_BAD_REQUEST, ErrorMessages.EMPTY_REQUEST)
  data = requests.model_dump()
  data = extract_input(data)

  if not data:
    raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, ErrorMessages.EMPTY_DATA)
  tag = str(uuid.uuid4())
  import time

  st = time.perf_counter()
  results, header = get_cached_or_compute(
    metadata["Identifier"],
    data,
    tag,
    max_workers,
    min_workers,
    metadata,
    fetch_cache,
    save_cache,
    cache_only,
    output_type,
  )
  et = time.perf_counter()
  cprint(f"Execution Time: {et - st:.6f}", fg="cyan", bold=True)
  cprint(f"Generating a response for {output_type} task", fg="cyan", bold=True)

  if output_type == TaskTypeEnum.HEAVY:
    payload = generate_resp_body(results, metadata["Output Type"][0], header)
    return Response(
      content=payload,
      media_type=MEDIA_TYPE,
      headers={
        "Content-Disposition": CONTENT_DESP,
        "Content-Length": str(len(payload)),
      },
    )

  results = orient_to_json(results, header, data, orient, metadata["Output Type"])
  return ORJSONResponse(results)
