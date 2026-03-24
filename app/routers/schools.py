from fastapi import APIRouter, HTTPException, status, Form, File, UploadFile, Depends
from pydantic import ValidationError
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime, timezone

# Model Imports
from app.models.school import (
    SchoolSignup, 
    SchoolProfileResponse, 
    SchoolProfileUpdate, 
    SchoolLogin
)

# Core & Utility Imports
from app.core.database import db_instance
from app.core.security import (
    hash_password, 
    verify_password, 
    create_access_token, 
    get_current_user_id
)
from fastapi.encoders import jsonable_encoder
from app.utils.file_handlers import save_profile_image

router = APIRouter(prefix="/api/schools", tags=["Schools"])

# 1. POST /api/schools/signup

@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup_school(school: SchoolSignup):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    # 1. Check for Duplicate Email or Username
    existing_school = await db["schools"].find_one({
        "$or": [{"email": school.email}, {"username": school.username}]
    })
    if existing_school:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Validation Error: School with this email or username already exists."
        )

    # 2. Convert Pydantic Model to Dictionary & Remove confirmPassword
    school_dict = school.model_dump(exclude={"confirmPassword"})

    # 3. Hash the Password
    school_dict["password"] = hash_password(school_dict["password"])

    # 4. Inject Default Backend Values (Hidden Fields)
    school_dict.update({
        "bio": "",
        "profilePicture": "",
        "badge": False,
        "stats": {
            "followers": 0,
            "students": 0,
            "followings": 0
        },
        "details": {
            "rank": 0,
            "principal": school.name, # Using the signup name as default principal
            "totalStudentsEnrolled": 0,
            "alumni": 0
        },
        "facilities": [],
        "labs": [],
        "created_at": datetime.now(timezone.utc)
    })

    # 5. Save to Database
    result = await db["schools"].insert_one(school_dict)

    # 6. Return Success Response
    return {
        "schoolId": str(result.inserted_id),
        "message": "School registered successfully"
    }

# 2. GET /api/schools/{schoolId}

@router.get("/{schoolId}", response_model=SchoolProfileResponse)
async def get_school_profile(schoolId: str):
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    # Validate if the provided ID is a valid MongoDB ObjectId
    try:
        obj_id = ObjectId(schoolId)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid School ID format")

    # Fetch from Database
    school_data = await db["schools"].find_one({"_id": obj_id})
    
    if not school_data:
        raise HTTPException(status_code=404, detail="School not found")

    # Map MongoDB document to Pydantic response model
    return SchoolProfileResponse(
        schoolId=str(school_data["_id"]),
        username=school_data.get("username", ""),
        instituteName=school_data.get("instituteName", ""),
        name=school_data.get("name", ""),
        email=school_data.get("email", ""),
        phone=school_data.get("phone", ""),
        cnic=school_data.get("cnic", ""),
        gender=school_data.get("gender", ""),
        bio=school_data.get("bio", ""),
        profilePicture=school_data.get("profilePicture", ""),
        badge=school_data.get("badge", False),
        stats=school_data.get("stats", {}),
        details=school_data.get("details", {}),
        facilities=school_data.get("facilities", []),
        labs=school_data.get("labs", []),
        location=school_data.get("locationName", "") # Map locationName to location for frontend
    )

# 3. PUT /api/schools/{schoolId}/profile
@router.put("/{schoolId}/profile", status_code=status.HTTP_200_OK)
async def update_school_profile(
    schoolId: str,
    name: str = Form(...),
    instituteName: str = Form(...),
    bio: str = Form(""),
    gender: str = Form(...),
    dateOfBirth: str = Form(...),
    username: str = Form(...),
    locationName: str = Form(...),
    profileImage: UploadFile = File(None),
    current_user_id: str = Depends(get_current_user_id)  # 🔒 THE SECURITY LOCK
):
    """
    Updates the school profile. Requires a valid JWT token.
    Only the owner of the profile can update their own data.
    """
    # 0. STRICT AUTHORIZATION CHECK
    # Ensure the logged-in user is only updating their OWN profile
    if current_user_id != schoolId:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden. You can only edit your own school profile."
        )

    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    # Validate Object ID format
    try:
        obj_id = ObjectId(schoolId)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid School ID format.")

    # 1. Validate form inputs using the Pydantic model
    try:
        validated_data = SchoolProfileUpdate(
            name=name,
            instituteName=instituteName,
            bio=bio,
            gender=gender,
            dateOfBirth=dateOfBirth,
            username=username,
            locationName=locationName
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=jsonable_encoder(e.errors()))

    # 2. Check for username collisions (excluding the current user)
    existing_user = await db["schools"].find_one({
        "_id": {"$ne": obj_id},
        "username": validated_data.username
    })
    
    if existing_user:
        raise HTTPException(status_code=409, detail="Username is already taken.")

    # 3. Prepare the update dictionary
    update_dict = validated_data.model_dump()
    update_dict["updatedAt"] = datetime.now(timezone.utc)

    # 4. Process and store the profile image if provided
    if profileImage:
        image_url = await save_profile_image(profileImage)
        update_dict["profilePicture"] = image_url

    # 5. Execute an atomic update in the database
    result = await db["schools"].find_one_and_update(
        {"_id": obj_id},
        {"$set": update_dict},
        return_document=True
    )

    if not result:
        raise HTTPException(status_code=404, detail="School not found.")

    # 6. Return standard success response
    return {
        "success": True,
        "message": "School profile updated successfully.",
        "data": {
            "schoolId": str(result["_id"]),
            "name": result.get("name"),
            "instituteName": result.get("instituteName"),
            "username": result.get("username"),
            "profilePicture": result.get("profilePicture", "")
        }
    }

# 4. POST /api/schools/login

@router.post("/login", status_code=status.HTTP_200_OK)
async def login_school(credentials: SchoolLogin):
    """
    Authenticates a school user and returns a JWT access token.
    """
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    # 1. Find school by email OR username (case-insensitive)
    identifier_lower = credentials.identifier.lower()
    school_data = await db["schools"].find_one({
        "$or": [
            {"email": identifier_lower},
            {"username": identifier_lower}
        ]
    })

    # 2. Verify if school exists and password matches
    if not school_data or not verify_password(credentials.password, school_data["password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email/username or password."
        )

    # 3. Generate JWT Token using YOUR existing security function
    school_id_str = str(school_data["_id"])
    
    # We pass the school ID as the 'sub' (subject) and mention the role
    access_token = create_access_token(
        subject={"sub": school_id_str, "role": "school"}
    )

    # 4. Return the token
    return {
        "success": True,
        "message": "Login successful.",
        "token": access_token,
        "school": {
            "schoolId": school_id_str,
            "username": school_data.get("username"),
            "instituteName": school_data.get("instituteName")
        }
    }