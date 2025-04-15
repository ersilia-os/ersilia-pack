import sys

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from .default import (
  API_DESCIPTION,
  ROOT,
  ENVIRONMENT,
  ALLOWED_ORIGINS,
)
from .exceptions.handlers import register_exception_handlers
from .middleware.rcontext import RequestContextMiddleware
from .routers import docs, metadata, run, health, job
from .utils import get_sync_metadata, create_limiter, init_redis

sys.path.insert(0, ROOT)

limiter = create_limiter()

metadata_card = get_sync_metadata()["card"]
app = FastAPI(
  title=f"{metadata_card['Identifier']}:{metadata_card['Slug']} Server",
  description=f"{metadata_card['Title']}. {API_DESCIPTION}",
  docs_url=None,
  redoc_url=None,
)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

if ENVIRONMENT == "prod":
  app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
  )


@app.on_event("startup")
async def startup_event():
  init_redis()


register_exception_handlers(app)
app.add_middleware(RequestContextMiddleware)

app.include_router(metadata.router)
app.include_router(run.router)
app.include_router(job.router)
app.include_router(docs.router)
app.include_router(health.router)
