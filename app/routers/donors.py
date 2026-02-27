from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from app.models.donor import DonorSignup, DonorProfileResponse, DonorUpdateProfile, AchievementPatch
from app.core.database import db_instance
from app.core.security import hash_password, create_access_token, decode_token
from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError

# Router initialization 
router = APIRouter(prefix="/donors", tags=["Donors"])
bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_donor_username(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    payload = decode_token(credentials.credentials)
    if not payload or payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    username = payload.get("sub")
    role = payload.get("role")
    if not username or role != "donor":
        raise HTTPException(status_code=403, detail="Invalid donor token")
    return username

# 1. POST /api/donors/signup
@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_donor(donor: DonorSignup):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    existing_user = await db["donors"].find_one({
        "$or": [{"email": donor.email}, {"username": donor.username}]
    })
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User with this email or username already exists.")

    hashed_pw = hash_password(donor.password)
    donor_dict = donor.model_dump()
    donor_dict["password"] = hashed_pw
    
    donor_dict.update({
        "followers_count": 0,
        "following_count": 0,
        "beneficiaries_count": 0,
        "total_amount_donated": 0.0,  # Or Decimal("0.00") if using Decimal in model
        "donor_class": "Starter",
        "donor_rank": 0,
        "achievements": [],
        "created_at": datetime.now(timezone.utc)
    })

    try:
        result = await db["donors"].insert_one(donor_dict)
    except DuplicateKeyError:
        raise HTTPException(status_code=400, detail="User with this email or username already exists.")

    token = create_access_token(subject={"sub": donor.username, "role": "donor"})

    return {
        "message": "Donor account created successfully!",
        "donor_id": str(result.inserted_id),
        "access_token": token
    }

# 2. GET /api/donors/{username}
@router.get("/{username}", response_model=DonorProfileResponse)
async def get_donor_profile(username: str):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    user = await db["donors"].find_one({"username": username})
    
    if not user:
        raise HTTPException(status_code=404, detail="Donor not found")
        
    return {
        "id": str(user["_id"]),
        "username": user.get("username", ""),
        "name": user.get("name", ""),
        "about": user.get("about", ""),
        "followers_count": user.get("followers_count", 0),
        "following_count": user.get("following_count", 0),
        "beneficiaries_count": user.get("beneficiaries_count", 0),
        "total_amount_donated": user.get("total_amount_donated", 0),
        "donor_class": user.get("donor_class", ""),
        "donor_rank": user.get("donor_rank", 0),
        "achievements": user.get("achievements", []),
        "profile_image_url": user.get("profile_image_url", ""),
    }

# 3. PATCH /api/donors/profile
@router.patch("/profile")
async def update_donor_profile(
    profile_data: DonorUpdateProfile,
    current_username: str = Depends(get_current_donor_username),
):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    # Only get fields that were actually provided in the request
    update_data = {k: v for k, v in profile_data.model_dump().items() if v is not None}
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No data provided to update")
        
    result = await db["donors"].update_one(
        {"username": current_username},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Donor not found")
        
    return {"message": "Profile updated successfully"}

# 4. PATCH /api/donors/achievements
@router.patch("/achievements")
async def update_donor_achievements(
    achievements_data: AchievementPatch,
    current_username: str = Depends(get_current_donor_username),
):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    achievements_list = [ach.model_dump() for ach in achievements_data.achievements]
    
    result = await db["donors"].update_one(
        {"username": current_username},
        {"$set": {"achievements": achievements_list}}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Donor not found")
        
    return {"message": "Achievements updated successfully"}

# 5. GET /api/donors (Get all donors list)
@router.get("/", response_model=List[DonorProfileResponse])
async def get_all_donors():
    """Fetch a list of all donors in the system"""
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    donors_list = []
    cursor = db["donors"].find({})

    async for user in cursor:
        donors_list.append(
            DonorProfileResponse(
                id=str(user["_id"]),
                username=user.get("username", ""),
                name=user.get("name", ""),
                about=user.get("about", ""),
                followers_count=user.get("followers_count", 0),
                following_count=user.get("following_count", 0),
                beneficiaries_count=user.get("beneficiaries_count", 0),
                total_amount_donated=user.get("total_amount_donated", 0.0),
                donor_class=user.get("donor_class", ""),
                donor_rank=user.get("donor_rank", 0),
                achievements=user.get("achievements", []),
                profile_image_url=user.get("profile_image_url", ""),
            )
        )

    return donors_list
