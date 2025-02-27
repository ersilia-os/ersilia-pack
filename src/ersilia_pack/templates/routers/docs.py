from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends
from fastapi.openapi.docs import (
  get_redoc_html,
  get_swagger_ui_html,
)
from fastapi.staticfiles import StaticFiles

from ..default import MATE_CSS_URL, REDOC_JS_URL
from ..utils import get_metadata

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent
static_dir = BASE_DIR / "static"


@router.get("/info", tags=["Info"])
async def get_info(metadata: Dict[str, Any] = Depends(get_metadata)):
  return {
    "title": metadata["card"]["Identifier"],
    "description": metadata["card"]["Description"],
    "version": "latest",
  }


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
