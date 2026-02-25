from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import connect_to_mongo, close_mongo_connection
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # App start hotay hi DB connect karo
    await connect_to_mongo()
    yield
    # App band hotay hi DB disconnect karo
    await close_mongo_connection()

app = FastAPI(title="ITVE Donor API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Donor API is up and DB is connected!"}