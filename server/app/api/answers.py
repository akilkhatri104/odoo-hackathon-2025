from fastapi import APIRouter,Response,status,Cookie
from typing import Annotated
from ..lib.db import database,Answers
from ..lib.auth import verify_jwt
from sqlalchemy import update

#UserRouter for handling answer-related operations
userRouter = APIRouter(prefix="/api/answers")

# Route to handle upvoting an answer
@userRouter.post("/answer/{answer_id}/upvote")
async def upvote_answer(answer_id: int, access_token: Annotated[str | None, Cookie()] = None, response: Response = None):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}
    
    result = await database.fetch_one(Answers.select().where(Answers.c.id == answer_id))
    if not result:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"message": "Answer not found"}

    query = update(Answers).where(Answers.c.id == answer_id).values(upvotes=Answers.c.upvotes + 1)
    await database.execute(query)
    return {
        "success": True,
        "message": "Answer upvoted successfully",
        "answer_id": answer_id
        }

# Route to handle downvoting an answer
@userRouter.post("/answer/{answer_id}/downvote")
async def downvote_answer(answer_id: int, access_token: Annotated[str | None, Cookie()] = None, response: Response = None):
    user_id = await verify_jwt(access_token)
    if not user_id:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"message": "Unauthorized"}
    
    result = await database.fetch_one(Answers.select().where(Answers.c.id == answer_id))
    if not result:
        response.status_code = status.HTTP_404_NOT_FOUND
        return {"message": "Answer not found"}
    

    query = update(Answers).where(Answers.c.id == answer_id).values(downvotes=Answers.c.downvotes + 1)
    await database.execute(query)
    return {
        "success": True,
        "message": "Answer downvoted successfully",
        "answer_id": answer_id
        }