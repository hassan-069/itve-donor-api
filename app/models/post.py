from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# ==========================================
# Helper Functions for Formatting
# ==========================================
def format_number(num: int) -> str:
    """Converts large numbers into readable formats like 1.2K or 2.9M."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M".replace(".0M", "M")
    if num >= 1_000:
        return f"{num / 1_000:.1f}K".replace(".0K", "K")
    return str(num)

def format_date_custom(dt: datetime) -> str:
    """Formats date as DD/M/YYYY."""
    return dt.strftime("%d/%m/%Y").replace("/0", "/")

def format_time_custom(dt: datetime) -> str:
    """Formats time as HH:MM am/pm."""
    return dt.strftime("%I:%M %p").lower()

# ==========================================
# 1. POST RESPONSE MODEL (Scalable Architecture)
# ==========================================
class PostResponse(BaseModel):
    postId: str
    schoolId: str
    
    # Author Details (Embedded for fast feed loading)
    authorName: str
    authorUsername: str
    authorProfilePic: str
    isVerified: bool = False
    
    # Post Content
    content: str
    imageUrl: Optional[str] = ""
    
    # Counters (Denormalized for performance)
    likesCount: int = 0
    commentsCount: int = 0
    sharesCount: int = 0
    viewsCount: int = 0
    
    # Formatted Strings for Frontend UI
    formattedViews: str
    formattedLikes: str
    
    # UI Interaction Flags
    isLikedByMe: bool = False
    isSavedByMe: bool = False
    isEdited: bool = False
    
    # Timestamps
    createdAtDate: str
    createdAtTime: str

class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000,
                           description="Text content of the comment")