from fastapi import APIRouter,HTTPException,Response,status,Cookie
from pydantic import BaseModel
from typing import Annotated,List
from ..lib.auth import verify_jwt
from ..lib.db import database,Questions


questionsRouter = APIRouter(prefix="/api/questions")

class QuestionRequest(BaseModel):
    title: str
    description: str
    tags: List[str]


@questionsRouter.post("/")
async def create_post(response: Response,question: QuestionRequest,access_token: Annotated[str | None,Cookie()] = None):
    try:
        user_id = await verify_jwt(access_token)
        if access_token is None or user_id is None:
            response.status_code = status.HTTP_401_UNAUTHORIZED
            return {
                    "message": "Unauthorized"
                }
        
        await database.connect()
        stmt = Questions.insert().values(user_id=user_id,tags=question.tags,title=question.title,description=question.description)
        result = await database.execute(stmt)
        
        return {"message": "Post created"}
    except Exception as e:
        print(e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "message" : "Server error while creating post"
        }

