import os
from jose import jwt
from dotenv import load_dotenv
from .db import database,Users
from sqlalchemy import update
load_dotenv()

ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
async def create_session(user_id: int):
    try:
        await database.connect()
        print("Creating session for user_id:", user_id)
        access_token = jwt.encode({'user_id': str(user_id)},ACCESS_TOKEN_SECRET,"HS256")
        print("Access token:", access_token)

        print("Returning access token")
        return access_token
    except Exception as e:
        print("Exception occured while creating session:", e)
        return None
    finally:
        print("Disconnecting database")
        await database.disconnect()


async def verify_jwt(token: str):
    try:
        await database.connect()
        payload = jwt.decode(token,ACCESS_TOKEN_SECRET,"HS256")
        print(payload['user_id'])
        user_id = int(payload['user_id'])
        query = Users.select().where(Users.c.user_id == user_id)
        user_exists = await database.fetch_one(query=query)

        if(user_exists == None):
            return None
        return user_id
    except Exception as e:
        print(e)
        return None
    finally: 
        await database.disconnect()




