from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.core.database import connect_to_mongo, close_mongo_connection
import logging

from app.routers import donors
from app.routers import hopes
from app.routers import schools

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="ITVE Backend API", lifespan=lifespan)

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

app.include_router(donors.router, prefix="/api")
app.include_router(hopes.router, prefix="/api/hopes", tags=["Hopes / Donations"])
app.include_router(schools.router)

@app.get("/")
async def root():
    return {"message": "Donor API is up and running!"}
