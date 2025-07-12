from typing_extensions import Annotated
from typing import Optional  # Add for Python 3.8 compatibility
from fastapi import APIRouter, Response, status, Cookie, HTTPException, UploadFile, File
from sqlalchemy import select, update, insert
from datetime import datetime
from ..lib.db import database, Answers, Questions, Users, Notifications, NotificationType
from ..lib.auth import verify_jwt
from ..lib.cloudinary import upload_image_file
import json

# Router for handling answer-related operations
router = APIRouter(prefix="/api/answers", tags=["Answers"])

# POST /api/answers - Create a new answer
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_answer(
    question_id: int,
    description: str,
    tags: str = "[]",  # Default to empty list, expects JSON string
    image: UploadFile = File(None),  # Optional file upload
    response: Response = None,
    access_token: Annotated[Optional[str], Cookie()] = None  # Changed str | None to Optional[str]
):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}

    await database.connect()
    try:
        # Validate input
        if not question_id or not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question ID and description are required"
            )

        # Parse tags (expects JSON string, e.g., '["tag1", "tag2"]')
        try:
            tags_list = json.loads(tags) if tags else []
            if not isinstance(tags_list, list):
                raise ValueError("Tags must be a list")
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tags format; must be a JSON array"
            )

        # Check if question exists
        question_query = select(Questions).where(Questions.c.question_id == question_id)
        question = await database.fetch_one(question_query)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )

        # Handle image upload if provided
        final_img_url = None
        if image:
            final_img_url = upload_image_file(image.file, folder="answers")

        # Insert answer
        query = insert(Answers).values(
            question_id=question_id,
            user_id=user_id,
            description=description,
            img_url=final_img_url,
            tags=tags_list,
            upvotes=0,
            downvotes=0,
            is_accepted=False,
            created_at=datetime.utcnow()
        )
        answer_id = await database.execute(query)

        # Create notification for question owner
        question_owner_id = question["user_id"]
        if question_owner_id != user_id:  # Prevent self-notification
            user_query = select(Users).where(Users.c.user_id == user_id)
            user = await database.fetch_one(user_query)
            message = f"User {user['username']} answered your question: {question['title']}"
            notification_query = insert(Notifications).values(
                user_id=question_owner_id,
                type=NotificationType.answer,
                related_id=answer_id,
                message=message,
                is_read=False,
                created_at=datetime.utcnow()
            )
            await database.execute(notification_query)

        # Fetch the created answer with username
        result_query = select(Answers, Users.c.username).join(
            Users, Answers.c.user_id == Users.c.user_id
        ).where(Answers.c.answer_id == answer_id)
        result = await database.fetch_one(result_query)

        return {
            "answer_id": result["answer_id"],
            "question_id": result["question_id"],
            "user_id": result["user_id"],
            "description": result["description"],
            "img_url": result["img_url"],
            "tags": result["tags"],
            "upvotes": result["upvotes"],
            "downvotes": result["downvotes"],
            "is_accepted": result["is_accepted"],
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
            "username": result["username"]
        }
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Error creating answer: {str(e)}"}
    finally:
        await database.disconnect()

# POST /api/answers/<id>/vote - Upvote or downvote an answer
@router.post("/{answer_id}/vote")
async def vote_answer(
    answer_id: int,
    vote: dict,
    response: Response,
    access_token: Annotated[Optional[str], Cookie()] = None  # Changed str | None to Optional[str]
):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}

    await database.connect()
    try:
        # Check if answer exists
        answer_query = select(Answers).where(Answers.c.answer_id == answer_id)
        answer = await database.fetch_one(answer_query)
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer not found"
            )

        # Validate vote type
        vote_type = vote.get("vote_type")  # Expecting "upvote" or "downvote"
        if vote_type not in ["upvote", "downvote"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid vote type. Must be 'upvote' or 'downvote'"
            )

        # Check if user has already voted (simple check, assumes one vote per user)
        if answer["upvotes"] > 0 or answer["downvotes"] > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User has already voted on this answer"
            )

        # Update vote count
        update_values = {}
        if vote_type == "upvote":
            update_values["upvotes"] = Answers.c.upvotes + 1
        else:  # downvote
            update_values["downvotes"] = Answers.c.downvotes + 1
        update_values["updated_at"] = datetime.utcnow()

        update_query = update(Answers).where(
            Answers.c.answer_id == answer_id
        ).values(**update_values)
        await database.execute(update_query)

        return {
            "success": True,
            "message": f"Answer {vote_type}d successfully",
            "answer_id": answer_id
        }
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Error voting on answer: {str(e)}"}
    finally:
        await database.disconnect()
        