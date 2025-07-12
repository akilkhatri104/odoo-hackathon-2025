from fastapi import APIRouter, Depends, HTTPException, status
from databases import Database
from typing import List
from datetime import datetime
import re
from .db import database, Notifications, NotificationType, Users, Questions, Answers
from .model import NotificationResponse
from fastapi_jwt_auth import AuthJWT

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("/", response_model=List[NotificationResponse])
async def get_notifications(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    user_id = int(Authorize.get_jwt_subject())
    
    await database.connect()
    query = Notifications.select().where(Notifications.c.user_id == user_id).order_by(Notifications.c.created_at.desc())
    notifications = await database.fetch_all(query)
    await database.disconnect()
    
    return [
        NotificationResponse(
            notification_id=notification["notification_id"],
            user_id=notification["user_id"],
            type=notification["type"],
            related_id=notification["related_id"],
            message=notification["message"],
            is_read=notification["is_read"],
            created_at=notification["created_at"]
        )
        for notification in notifications
    ]

@router.put("/{notification_id}/read")
async def mark_notification_read(notification_id: int, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    user_id = int(Authorize.get_jwt_subject())
    
    await database.connect()
    query = Notifications.select().where(
        Notifications.c.notification_id == notification_id,
        Notifications.c.user_id == user_id
    )
    notification = await database.fetch_one(query)
    
    if not notification:
        await database.disconnect()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Notification not found or not authorized"
        )
    
    update_query = (
        Notifications.update()
        .where(Notifications.c.notification_id == notification_id)
        .values(is_read=True)
    )
    await database.execute(update_query)
    await database.disconnect()
    
    return {"message": "Notification marked as read", "notification_id": notification_id}

@router.put("/read-all")
async def mark_all_notifications_read(Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    user_id = int(Authorize.get_jwt_subject())
    
    await database.connect()
    update_query = (
        Notifications.update()
        .where(Notifications.c.user_id == user_id, Notifications.c.is_read == False)
        .values(is_read=True)
    )
    await database.execute(update_query)
    await database.disconnect()
    
    return {"message": "All notifications marked as read"}

@router.post("/answer")
async def create_answer_notification(answer_id: int, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user_id = int(Authorize.get_jwt_subject())
    
    await database.connect()
    # Fetch answer and related question
    answer_query = Answers.select().where(Answers.c.answer_id == answer_id)
    answer = await database.fetch_one(answer_query)
    
    if not answer:
        await database.disconnect()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found"
        )
    
    question_query = Questions.select().where(Questions.c.question_id == answer["question_id"])
    question = await database.fetch_one(question_query)
    
    if not question:
        await database.disconnect()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    # Get question owner's user_id
    recipient_id = question["user_id"]
    
    # Prevent self-notification
    if recipient_id == current_user_id:
        await database.disconnect()
        return {"message": "No notification created (self-answer)"}
    
    # Create notification
    user_query = Users.select().where(Users.c.user_id == current_user_id)
    user = await database.fetch_one(user_query)
    message = f"User {user['username']} answered your question: {question['title']}"
    
    query = Notifications.insert().values(
        user_id=recipient_id,
        type=NotificationType.answer,
        related_id=answer_id,
        message=message,
        is_read=False,
        created_at=datetime.utcnow()
    )
    notification_id = await database.execute(query)
    await database.disconnect()
    
    return {"message": "Notification created", "notification_id": notification_id}

@router.post("/mention")
async def create_mention_notification(answer_id: int, Authorize: AuthJWT = Depends()):
    Authorize.jwt_required()
    current_user_id = int(Authorize.get_jwt_subject())
    
    await database.connect()
    # Fetch answer
    answer_query = Answers.select().where(Answers.c.answer_id == answer_id)
    answer = await database.fetch_one(answer_query)
    
    if not answer:
        await database.disconnect()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Answer not found"
        )
    
    # Parse answer description for mentions
    mentions = re.findall(r'@(\w+)', answer["description"])
    if not mentions:
        await database.disconnect()
        return {"message": "No mentions found in answer"}
    
    # Fetch question for context
    question_query = Questions.select().where(Questions.c.question_id == answer["question_id"])
    question = await database.fetch_one(question_query)
    if not question:
        await database.disconnect()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Question not found"
        )
    
    current_user_query = Users.select().where(Users.c.user_id == current_user_id)
    current_user = await database.fetch_one(current_user_query)
    
    notification_ids = []
    for username in mentions:
        # Fetch mentioned user
        user_query = Users.select().where(Users.c.username == username)
        mentioned_user = await database.fetch_one(user_query)
        
        if not mentioned_user or mentioned_user["user_id"] == current_user_id:
            continue  # Skip if user not found or self-mention
        
        # Create notification
        message = f"User {current_user['username']} mentioned you in an answer to question: {question['title']}"
        query = Notifications.insert().values(
            user_id=mentioned_user["user_id"],
            type=NotificationType.mention,
            related_id=answer_id,
            message=message,
            is_read=False,
            created_at=datetime.utcnow()
        )
        notification_id = await database.execute(query)
        notification_ids.append(notification_id)
    
    await database.disconnect()
    
    if not notification_ids:
        return {"message": "No valid mentions processed"}
    return {"message": "Notifications created", "notification_ids": notification_ids}