from pathlib import Path

from fastapi import APIRouter
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


@router.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
  return get_swagger_ui_html(
    title="Ersilia-Pack - Docs",
    swagger_css_url=MATE_CSS_URL,
    openapi_url="/openapi.json",
  )


@router.get("/redoc", include_in_schema=False)
async def redoc_html():
  return get_redoc_html(
    title="Ersilia-Pack - Redoc",
    redoc_js_url=REDOC_JS_URL,
    openapi_url="/openapi.json",
  )
