from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import index as index_routes
from app.api import search as search_routes
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.media_root.mkdir(parents=True, exist_ok=True)
    settings.faiss_index_path.parent.mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(title="Local Semantic Video & Photo Search", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index_routes.router)
app.include_router(search_routes.router)

app.mount(
    "/media",
    StaticFiles(directory=str(settings.media_root.resolve())),
    name="media",
)
