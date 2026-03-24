import os
import uuid
from fastapi import UploadFile, HTTPException

# Define the directory for storing profile images
UPLOAD_DIR = "uploads/profiles"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

async def save_profile_image(file: UploadFile) -> str:
    # 1. Validate file extension/type
    if file.content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail="Invalid image format. Only JPG, PNG, and WEBP are allowed."
        )
    
    # 2. Validate file size
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400, 
            detail="File size too large. Maximum allowed size is 5MB."
        )

    # 3. Generate a unique filename to prevent overwriting
    ext = file.filename.split(".")[-1]
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    # 4. Save the file to the local directory
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Ensure forward slashes for URLs
    normalized_path = file_path.replace("\\", "/")
    return f"/{normalized_path}"