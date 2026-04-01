from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.openapi.docs import (
  get_redoc_html,
  get_swagger_ui_html,
)
from fastapi.staticfiles import StaticFiles

from ..default import MATE_CSS_URL, REDOC_JS_URL

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
static_dir = BASE_DIR / "static"


router.mount("/static", StaticFiles(directory=static_dir), name="static")


def resolve_root_path(scope):
  root_path = (scope.get("root_path") or "").strip()
  if not root_path or root_path == "/":
    return ""
  if not root_path.startswith("/"):
    root_path = "/" + root_path
  return root_path.rstrip("/")


def resolve_openapi_url(scope):
  root_path = resolve_root_path(scope)
  return "{0}/openapi.json".format(root_path) if root_path else "/openapi.json"


@router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html(request: Request):
  return get_swagger_ui_html(
    title="Ersilia-Pack - Docs",
    swagger_css_url=MATE_CSS_URL,
    openapi_url=resolve_openapi_url(request.scope),
  )


@router.get("/redoc", include_in_schema=False)
async def redoc_html(request: Request):
  return get_redoc_html(
    title="Ersilia-Pack - Redoc",
    redoc_js_url=REDOC_JS_URL,
    openapi_url=resolve_openapi_url(request.scope),
  )
