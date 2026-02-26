from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.database import connect_to_mongo, close_mongo_connection
import logging

logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # When the FastAPI server starts, this function will be called to establish a connection to MongoDB.
    await connect_to_mongo()
    yield
    # When the FastAPI server is shutting down, this function will be called to close the MongoDB connection gracefully.
    await close_mongo_connection()

app = FastAPI(title="ITVE Donor API", lifespan=lifespan)

@app.get("/")
async def root():
    return {"message": "Donor API is up and DB is connected!"}