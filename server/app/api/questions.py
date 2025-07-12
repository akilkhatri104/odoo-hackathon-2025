from typing_extensions import Annotated
from typing import Optional
from fastapi import APIRouter, Response, status, Cookie, HTTPException
from sqlalchemy import select, update, insert
from datetime import datetime
from ..lib.db import database, Questions, Answers, Users, Notifications, NotificationType
from ..lib.auth import verify_jwt
import json

# Router for handling question-related operations
router = APIRouter(prefix="/api/questions", tags=["Questions"])

# GET /api/questions - Fetch all questions
@router.get("/")
async def get_questions():
    try:
        query = select(Questions, Users.c.username).join(
            Users, Questions.c.user_id == Users.c.user_id
        )
        questions = await database.fetch_all(query)
        return [
            {
                "question_id": q["question_id"],
                "user_id": q["user_id"],
                "title": q["title"],
                "description": q["description"],
                "tags": q["tags"],
                "created_at": q["created_at"],
                "updated_at": q["updated_at"],
                "username": q["username"]
            }
            for q in questions
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching questions: {str(e)}"
        )

# GET /api/questions/<id> - Fetch a specific question with its answers
@router.get("/{question_id}")
async def get_question(question_id: int):
    try:
        # Fetch question
        query = select(Questions, Users.c.username).join(
            Users, Questions.c.user_id == Users.c.user_id
        ).where(Questions.c.question_id == question_id)
        question = await database.fetch_one(query)
        
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )

        # Fetch answers
        answers_query = select(Answers, Users.c.username).join(
            Users, Answers.c.user_id == Users.c.user_id
        ).where(Answers.c.question_id == question_id)
        answers = await database.fetch_all(answers_query)

        return {
            "question": {
                "question_id": question["question_id"],
                "user_id": question["user_id"],
                "title": question["title"],
                "description": question["description"],
                "tags": question["tags"],
                "created_at": question["created_at"],
                "updated_at": question["updated_at"],
                "username": question["username"]
            },
            "answers": [
                {
                    "answer_id": a["answer_id"],
                    "user_id": a["user_id"],
                    "description": a["description"],
                    "img_url": a["img_url"],
                    "tags": a["tags"],
                    "upvotes": a["upvotes"],
                    "downvotes": a["downvotes"],
                    "is_accepted": a["is_accepted"],
                    "created_at": a["created_at"],
                    "updated_at": a["updated_at"],
                    "username": a["username"]
                }
                for a in answers
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching question: {str(e)}"
        )

# POST /api/questions - Create a new question
@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_question(
    question: dict,
    response: Response,
    access_token: Annotated[Optional[str], Cookie()] = None
):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}

    try:
        # Validate input
        title = question.get("title")
        description = question.get("description")
        tags = question.get("tags", [])

        if not title or not description:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Title and description are required"
            )

        # Validate tags
        if not isinstance(tags, list):
            try:
                tags = json.loads(tags) if tags else []
                if not isinstance(tags, list):
                    raise ValueError("Tags must be a list")
            except (json.JSONDecodeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tags format; must be a JSON array"
                )

        # Insert question
        query = insert(Questions).values(
            user_id=user_id,
            title=title,
            description=description,
            tags=tags,
            created_at=datetime.utcnow()
        )
        question_id = await database.execute(query)
        
        # Fetch the created question with username
        result_query = select(Questions, Users.c.username).join(
            Users, Questions.c.user_id == Users.c.user_id
        ).where(Questions.c.question_id == question_id)
        result = await database.fetch_one(result_query)

        return {
            "question_id": result["question_id"],
            "user_id": result["user_id"],
            "title": result["title"],
            "description": result["description"],
            "tags": result["tags"],
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
            "username": result["username"]
        }
    except (json.JSONDecodeError, ValueError) as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Error creating question: {str(e)}"}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"message": f"Unexpected error: {str(e)}"}

# PUT /api/questions/<id> - Update a question
@router.put("/{question_id}")
async def update_question(
    question_id: int,
    question: dict,
    response: Response,
    access_token: Annotated[Optional[str], Cookie()] = None
):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}

    try:
        # Check if question exists and user is owner
        query = select(Questions).where(Questions.c.question_id == question_id)
        existing_question = await database.fetch_one(query)
        
        if not existing_question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        
        if existing_question["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to edit this question"
            )

        # Prepare update values
        update_values = {}
        if "title" in question and question["title"]:
            update_values["title"] = question["title"]
        if "description" in question and question["description"]:
            update_values["description"] = question["description"]
        if "tags" in question and question["tags"]:
            try:
                tags = question["tags"]
                if isinstance(tags, str):
                    tags = json.loads(tags)
                if not isinstance(tags, list):
                    raise ValueError("Tags must be a list")
                update_values["tags"] = tags
            except (json.JSONDecodeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid tags format; must be a JSON array"
                )
        if update_values:
            update_values["updated_at"] = datetime.utcnow()

        # Update question
        update_query = update(Questions).where(
            Questions.c.question_id == question_id
        ).values(**update_values)
        await database.execute(update_query)

        # Fetch updated question with username
        result_query = select(Questions, Users.c.username).join(
            Users, Questions.c.user_id == Users.c.user_id
        ).where(Questions.c.question_id == question_id)
        result = await database.fetch_one(result_query)

        return {
            "question_id": result["question_id"],
            "user_id": result["user_id"],
            "title": result["title"],
            "description": result["description"],
            "tags": result["tags"],
            "created_at": result["created_at"],
            "updated_at": result["updated_at"],
            "username": result["username"]
        }
    except (json.JSONDecodeError, ValueError) as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Error updating question: {str(e)}"}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"message": f"Unexpected error: {str(e)}"}

# POST /api/questions/<question_id>/accept/<answer_id> - Accept an answer
@router.post("/{question_id}/accept/{answer_id}")
async def accept_answer(
    question_id: int,
    answer_id: int,
    response: Response,
    access_token: Annotated[Optional[str], Cookie()] = None
):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}

    try:
        # Check if question exists and user is owner
        question_query = select(Questions).where(Questions.c.question_id == question_id)
        question = await database.fetch_one(question_query)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found"
            )
        if question["user_id"] != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to accept answers for this question"
            )

        # Check if answer exists and belongs to the question
        answer_query = select(Answers).where(
            (Answers.c.answer_id == answer_id) & (Answers.c.question_id == question_id)
        )
        answer = await database.fetch_one(answer_query)
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Answer not found or does not belong to this question"
            )

        # Reset any previously accepted answer
        reset_query = update(Answers).where(
            (Answers.c.question_id == question_id) & (Answers.c.is_accepted == True)
        ).values(is_accepted=False)
        await database.execute(reset_query)

        # Mark the selected answer as accepted
        update_query = update(Answers).where(
            Answers.c.answer_id == answer_id
        ).values(is_accepted=True, updated_at=datetime.utcnow())
        await database.execute(update_query)

        # Create notification for the answer's author
        answer_user_id = answer["user_id"]
        if answer_user_id != user_id:  # Prevent self-notification
            user_query = select(Users).where(Users.c.user_id == user_id)
            user = await database.fetch_one(user_query)
            message = f"User {user['username']} accepted your answer to question: {question['title']}"
            notification_query = insert(Notifications).values(
                user_id=answer_user_id,
                type=NotificationType.answer,
                related_id=answer_id,
                message=message,
                is_read=False,
                created_at=datetime.utcnow()
            )
            await database.execute(notification_query)

        return {
            "success": True,
            "message": "Answer accepted successfully",
            "question_id": question_id,
            "answer_id": answer_id
        }
    except Exception as e:
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"message": f"Error accepting answer: {str(e)}"}