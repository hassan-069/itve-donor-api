from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import connect_to_mongo, close_mongo_connection
import logging

from app.routers import donors
from app.routers import hopes

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="ITVE Donor API", lifespan=lifespan)

app.include_router(donors.router, prefix="/api")
app.include_router(hopes.router, prefix="/api/hopes", tags=["Hopes / Donations"])

@app.get("/")
async def root():
    return {"message": "Donor API is up and running!"}