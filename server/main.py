from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.answers import userRouter
from app.api.questions import questionsRouter
from app.lib.db import database

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router=userRouter)
app.include_router(router=questionsRouter)