from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone
from app.models.hope import HopeCreate, HopeResponse
from app.core.database import db_instance

router = APIRouter()

# 1. POST API: Create a new "Hope" (Donation program)
@router.post("/", response_model=HopeResponse, status_code=201)
async def create_hope(hope: HopeCreate):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    # Convert data to a dictionary for MongoDB insertion
    hope_dict = hope.model_dump(by_alias=True)
    hope_dict["created_at"] = datetime.now(timezone.utc)

    # Insert into the database
    result = await db["hopes"].insert_one(hope_dict)

    # Return the response
    return HopeResponse(
        id=str(result.inserted_id),
        name=hope_dict.get("name", ""),
        details=hope_dict.get("details", ""),
        type_of_donation=hope_dict.get("type_of_donation", ""),
        support_field=hope_dict.get("fields", ""),
        amount=hope_dict.get("amount", 0.0),
        grade_requirement=hope_dict.get("grade_requirement"),
        students=hope_dict.get("students", []),
        created_at=hope_dict["created_at"],
    )

# 2. GET API: Fetch the list of all "Hopes"
@router.get("/", response_model=List[HopeResponse])
async def get_all_hopes():
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    hopes_list = []
    cursor = db["hopes"].find({})
    
    async for hope in cursor:
        hopes_list.append(
            HopeResponse(
                id=str(hope["_id"]),
                name=hope.get("name", ""),
                details=hope.get("details", ""),
                type_of_donation=hope.get("type_of_donation", ""),
                support_field=hope.get("fields", ""),
                amount=hope.get("amount", 0.0),
                grade_requirement=hope.get("grade_requirement"),
                students=hope.get("students", []),
                created_at=hope.get("created_at")
            )
        )
        
    return hopes_list
