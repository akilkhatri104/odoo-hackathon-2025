from .db import database,Users
from .models import UserRequest

async def create_user(user: UserRequest):
    await database.connect()
    query = Users.insert().values(username = user.username,email= user.email,password_hash=user.password,role=user.role,is_banned=False)
    result = await database.execute(query=query)
    await database.disconnect()
    return result

    