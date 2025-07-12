from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.answers import router as answers_router
from app.api.questions import router as questions_router
from app.lib.db import database

app = FastAPI()

origins = [
    "*"  # Restrict to specific origins in production, e.g., ["http://localhost:3000"]
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(answers_router)
app.include_router(questions_router)

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()