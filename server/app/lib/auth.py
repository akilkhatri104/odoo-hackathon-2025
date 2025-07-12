import os
from jose import jwt, JWTError
from dotenv import load_dotenv
from .db import database, Users
from sqlalchemy import select
from fastapi import HTTPException, status
from typing import Optional  # Add this import

load_dotenv()

# Validate environment variables
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
if not ACCESS_TOKEN_SECRET:
    raise ValueError("ACCESS_TOKEN_SECRET environment variable not set")

async def create_session(user_id: int) -> str:
    """
    Generate a JWT access token for a given user_id.
    Returns the token as a string or raises an exception on failure.
    """
    try:
        # Encode JWT with user_id as payload
        access_token = jwt.encode({"user_id": user_id}, ACCESS_TOKEN_SECRET, algorithm="HS256")
        print(f"Created access token for user_id {user_id}: {access_token}")
        return access_token
    except JWTError as e:
        print(f"JWT encoding error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )

async def verify_jwt(token: str) -> Optional[int]:  # Changed from int | None to Optional[int]
    """
    Verify a JWT token and return the user_id if valid and the user exists.
    Returns None if the token is invalid or the user doesn't exist.
    """
    try:
        # Decode JWT
        payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=["HS256"])
        user_id = int(payload["user_id"])
        
        # Query the database for the user
        query = select([Users]).where(Users.c.user_id == user_id)
        user = await database.fetch_one(query)
        
        if not user:
            print(f"No user found with user_id {user_id}")
            return None
            
        print(f"Verified user_id {user_id}")
        return user_id
    except JWTError as e:
        print(f"JWT decoding error: {e}")
        return None
    except ValueError as e:
        print(f"Invalid user_id format: {e}")
        return None
    finally:
        # Only disconnect if connection was opened here
        if database.is_connected:
            await database.disconnect()