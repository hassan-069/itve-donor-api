from fastapi import APIRouter, HTTPException, status, Form, File, UploadFile, Depends
from bson import ObjectId
from datetime import datetime, timezone
from typing import Optional             

from app.core.database import db_instance
from app.core.security import get_current_user_id
from app.utils.file_handlers import save_profile_image
from app.models.post import PostResponse, format_number, format_date_custom, format_time_custom , CommentCreate

router = APIRouter(prefix="/api/posts", tags=["Posts"])

# 1. POST /api/posts (Create a new post)
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    content: str = Form(""),
    image: UploadFile = File(None),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Creates a new post. Requires authentication.
    Accepts text content and an optional image file.
    """
    if not content and not image:
        raise HTTPException(
            status_code=400, 
            detail="Post must contain either text content or an image."
        )

    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    # 1. Fetch the author's (school's) details to embed in the post
    author = await db["schools"].find_one({"_id": ObjectId(current_user_id)})
    if not author:
        raise HTTPException(status_code=404, detail="Author profile not found.")

    # 2. Process the image if provided (reusing our robust image handler)
    image_url = ""
    if image:
        image_url = await save_profile_image(image)

    # 3. Prepare the post document
    now = datetime.now(timezone.utc)
    
    post_document = {
        "schoolId": current_user_id,
        "authorName": author.get("name", "Unknown"),
        "authorUsername": author.get("username", "unknown"),
        "authorProfilePic": author.get("profilePicture", ""),
        "isVerified": author.get("badge", False),  # Using 'badge' from your Phase 1 model
        "content": content,
        "imageUrl": image_url,
        "likesCount": 0,
        "commentsCount": 0,
        "sharesCount": 0,
        "viewsCount": 0,
        "isEdited": False,
        "createdAt": now,
        "updatedAt": now
    }

    # 4. Insert into the database
    result = await db["posts"].insert_one(post_document)
    post_id = str(result.inserted_id)

    # 5. Return the formatted response matching our PostResponse schema
    return {
        "success": True,
        "message": "Post created successfully.",
        "data": {
            "postId": post_id,
            "schoolId": current_user_id,
            "authorName": post_document["authorName"],
            "authorUsername": post_document["authorUsername"],
            "authorProfilePic": post_document["authorProfilePic"],
            "isVerified": post_document["isVerified"],
            "content": post_document["content"],
            "imageUrl": post_document["imageUrl"],
            "likesCount": 0,
            "commentsCount": 0,
            "sharesCount": 0,
            "viewsCount": 0,
            "formattedViews": "0",
            "formattedLikes": "0",
            "isLikedByMe": False,
            "isSavedByMe": False,
            "isEdited": False,
            "createdAtDate": format_date_custom(now),
            "createdAtTime": format_time_custom(now)
        }
    }

# 2. GET /api/posts (Get Feed with Pagination)
@router.get("/", status_code=status.HTTP_200_OK)
async def get_all_posts(
    page: int = 1,
    limit: int = 10,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Fetches the posts feed with pagination.
    Latest posts appear first.
    """
    db = db_instance.db
    if db is None:
        raise HTTPException(status_code=500, detail="Database connection failed.")

    # Calculate skip for MongoDB pagination
    skip = (page - 1) * limit
    
    # Fetch posts sorted by newest first (-1)
    cursor = db["posts"].find().sort("createdAt", -1).skip(skip).limit(limit)
    posts = await cursor.to_list(length=limit)
    
    # Get total count for frontend pagination logic
    total_posts = await db["posts"].count_documents({})

    # Format the data exactly as the frontend expects
    formatted_posts = []
    for post in posts:
        post_id = str(post["_id"])
        
        # NOTE: For now, isLikedByMe and isSavedByMe are False. 
        # We will update these in the "Engagement" step when we query the likes collection.
        formatted_posts.append({
            "postId": post_id,
            "schoolId": post["schoolId"],
            "authorName": post.get("authorName", ""),
            "authorUsername": post.get("authorUsername", ""),
            "authorProfilePic": post.get("authorProfilePic", ""),
            "isVerified": post.get("isVerified", False),
            "content": post.get("content", ""),
            "imageUrl": post.get("imageUrl", ""),
            "likesCount": post.get("likesCount", 0),
            "commentsCount": post.get("commentsCount", 0),
            "sharesCount": post.get("sharesCount", 0),
            "viewsCount": post.get("viewsCount", 0),
            "formattedViews": format_number(post.get("viewsCount", 0)),
            "formattedLikes": format_number(post.get("likesCount", 0)),
            "isLikedByMe": False, 
            "isSavedByMe": False,
            "isEdited": post.get("isEdited", False),
            "createdAtDate": format_date_custom(post["createdAt"]),
            "createdAtTime": format_time_custom(post["createdAt"])
        })

    return {
        "success": True,
        "message": "Posts fetched successfully.",
        "data": formatted_posts,
        "pagination": {
            "totalPosts": total_posts,
            "currentPage": page,
            "totalPages": (total_posts + limit - 1) // limit,
            "limit": limit
        }
    }

# 3. PUT /api/posts/{postId} (Edit Post)
@router.put("/{postId}", status_code=status.HTTP_200_OK)
async def edit_post(
    postId: str,
    content: Optional[str] = Form(None),
    image: UploadFile = File(None),
    current_user_id: str = Depends(get_current_user_id)
    ):
    """
    Edits an existing post. Only the owner can edit.
    Flags the post as 'isEdited: True'.
    """
    db = db_instance.db
    try:
        obj_id = ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Post ID.")

    # 1. Find the post
    post = await db["posts"].find_one({"_id": obj_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    # 2. Security Check: Only the author can edit
    if post["schoolId"] != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden. You can only edit your own posts.")

    # 3. Prepare updates
    update_fields = {"isEdited": True, "updatedAt": datetime.now(timezone.utc)}
    
    if content is not None:
        update_fields["content"] = content
        
    if image:
        image_url = await save_profile_image(image)
        update_fields["imageUrl"] = image_url

    # 4. Save to DB
    await db["posts"].update_one({"_id": obj_id}, {"$set": update_fields})

    return {
        "success": True,
        "message": "Post updated successfully."
    }

# 4. DELETE /api/posts/{postId} (Delete Post)
@router.delete("/{postId}", status_code=status.HTTP_200_OK)
async def delete_post(
    postId: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Deletes a post. Only the owner can delete.
    """
    db = db_instance.db
    try:
        obj_id = ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Post ID.")

    # 1. Find the post
    post = await db["posts"].find_one({"_id": obj_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    # 2. Security Check: Only the author can delete
    if post["schoolId"] != current_user_id:
        raise HTTPException(status_code=403, detail="Forbidden. You can only delete your own posts.")

    # 3. Delete from DB
    await db["posts"].delete_one({"_id": obj_id})
    
    # NOTE: In an enterprise app, we would also delete the associated likes/comments here.
    # We will handle that cleanup logic later if needed.

    return {
        "success": True,
        "message": "Post deleted successfully."
    }

# 5. POST /api/posts/{postId}/like (Toggle Like)
@router.post("/{postId}/like", status_code=status.HTTP_200_OK)
async def toggle_like(
    postId: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Toggles a like on a post. 
    If already liked, removes the like. If not liked, adds the like.
    """
    db = db_instance.db
    try:
        obj_id = ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Post ID.")

    # 1. Check if the post exists
    post = await db["posts"].find_one({"_id": obj_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    # 2. Check if the user has already liked this post
    existing_like = await db["post_likes"].find_one({
        "postId": postId,
        "schoolId": current_user_id
    })

    if existing_like:
        # User already liked it -> UNLIKE action
        await db["post_likes"].delete_one({"_id": existing_like["_id"]})
        # Decrement the counter in the posts collection (ensure it doesn't go below 0)
        new_likes_count = max(0, post.get("likesCount", 0) - 1)
        await db["posts"].update_one({"_id": obj_id}, {"$set": {"likesCount": new_likes_count}})
        
        return {
            "success": True,
            "message": "Post unliked.",
            "data": {
                "isLikedByMe": False,
                "likesCount": new_likes_count,
                "formattedLikes": format_number(new_likes_count)
            }
        }
    else:
        # User hasn't liked it -> LIKE action
        like_doc = {
            "postId": postId,
            "schoolId": current_user_id,
            "createdAt": datetime.now(timezone.utc)
        }
        await db["post_likes"].insert_one(like_doc)
        # Increment the counter
        new_likes_count = post.get("likesCount", 0) + 1
        await db["posts"].update_one({"_id": obj_id}, {"$set": {"likesCount": new_likes_count}})
        
        return {
            "success": True,
            "message": "Post liked.",
            "data": {
                "isLikedByMe": True,
                "likesCount": new_likes_count,
                "formattedLikes": format_number(new_likes_count)
            }
        }
    

# 6. POST /api/posts/{postId}/comments (Add Comment)

@router.post("/{postId}/comments", status_code=status.HTTP_201_CREATED)
async def add_comment(
    postId: str,
    comment: CommentCreate,
    current_user_id: str = Depends(get_current_user_id)
):
    """Adds a comment to a specific post."""
    db = db_instance.db
    try:
        obj_id = ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Post ID.")

    post = await db["posts"].find_one({"_id": obj_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found.")

    user = await db["schools"].find_one({"_id": ObjectId(current_user_id)})
    now = datetime.now(timezone.utc)
    
    comment_doc = {
        "postId": postId,
        "userId": current_user_id,
        "username": user.get("username", "Unknown"),
        "userProfilePic": user.get("profilePicture", ""),
        "text": comment.text,
        "createdAt": now
    }
    
    await db["post_comments"].insert_one(comment_doc)

    new_comments_count = post.get("commentsCount", 0) + 1
    await db["posts"].update_one({"_id": obj_id}, {"$set": {"commentsCount": new_comments_count}})

    return {
        "success": True,
        "message": "Comment added successfully.",
        "data": {
            "commentId": str(comment_doc["_id"]),
            "text": comment.text,
            "commentsCount": new_comments_count,
            "createdAtDate": format_date_custom(now),
            "createdAtTime": format_time_custom(now)
        }
    }


# 7. GET /api/posts/{postId}/comments (Fetch Comments)

@router.get("/{postId}/comments", status_code=status.HTTP_200_OK)
async def get_comments(
    postId: str,
    page: int = 1,
    limit: int = 10,
    current_user_id: str = Depends(get_current_user_id)
):
    """Fetches comments for a post with pagination."""
    db = db_instance.db
    skip = (page - 1) * limit
    
    cursor = db["post_comments"].find({"postId": postId}).sort("createdAt", -1).skip(skip).limit(limit)
    comments = await cursor.to_list(length=limit)
    total_comments = await db["post_comments"].count_documents({"postId": postId})

    formatted_comments = []
    for c in comments:
        formatted_comments.append({
            "commentId": str(c["_id"]),
            "userId": c["userId"],
            "username": c.get("username", ""),
            "userProfilePic": c.get("userProfilePic", ""),
            "text": c["text"],
            "createdAtDate": format_date_custom(c["createdAt"]),
            "createdAtTime": format_time_custom(c["createdAt"])
        })

    return {
        "success": True,
        "data": formatted_comments,
        "pagination": {
            "totalComments": total_comments,
            "currentPage": page,
            "totalPages": (total_comments + limit - 1) // limit
        }
    }


# 8. POST /api/posts/{postId}/view (Track Unique View)

@router.post("/{postId}/view", status_code=status.HTTP_200_OK)
async def track_view(
    postId: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Tracks a unique view from a user for a post."""
    db = db_instance.db
    try:
        obj_id = ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Post ID.")

    existing_view = await db["post_views"].find_one({"postId": postId, "userId": current_user_id})

    if not existing_view:
        await db["post_views"].insert_one({
            "postId": postId,
            "userId": current_user_id,
            "createdAt": datetime.now(timezone.utc)
        })
        await db["posts"].update_one({"_id": obj_id}, {"$inc": {"viewsCount": 1}})
        
        updated_post = await db["posts"].find_one({"_id": obj_id})
        views = updated_post.get("viewsCount", 1)
        
        return {
            "success": True,
            "message": "View tracked.",
            "data": {"viewsCount": views, "formattedViews": format_number(views)}
        }
        
    return {"success": True, "message": "Already viewed."}


# 9. POST /api/posts/{postId}/share (Track Share)

@router.post("/{postId}/share", status_code=status.HTTP_200_OK)
async def track_share(
    postId: str,
    current_user_id: str = Depends(get_current_user_id)
):
    """Increments the share count of a post."""
    db = db_instance.db
    try:
        obj_id = ObjectId(postId)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Post ID.")

    await db["posts"].update_one({"_id": obj_id}, {"$inc": {"sharesCount": 1}})
    updated_post = await db["posts"].find_one({"_id": obj_id})
    shares = updated_post.get("sharesCount", 1)

    return {
        "success": True,
        "message": "Share tracked.",
        "data": {"sharesCount": shares}
    }