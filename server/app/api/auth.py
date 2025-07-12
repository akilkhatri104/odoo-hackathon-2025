from fastapi import APIRouter,Response,status,Cookie
from typing import Annotated
from ..lib.models import SignupRequest,SigninRequest
from ..lib.crud import create_user
import bcrypt
from ..lib.db import Users,database
from ..lib.auth import create_session,verify_jwt
from sqlalchemy import select

userRouter = APIRouter(prefix="/api/auth")

@userRouter.post("/signup")
async def signup(response: Response,user: SignupRequest):
    try:
        await database.connect()
        stmt = select(Users).where((Users.c.username == user.username) | (Users.c.email == user.email))
        user_exists = await database.fetch_one(stmt)
        if(user_exists != None):
            response.status_code = status.HTTP_400_BAD_REQUEST
            return {
                "message": "User with email or username already exists"
            }
        bytes = user.password.encode('utf-8')
        hashedPassword = bcrypt.hashpw(bytes,bcrypt.gensalt()).decode('utf-8')
        user.password = hashedPassword
        user_id = await create_user(user=user)
        print("User created: ",user_id)

        access_token = await create_session(user_id)

        response.set_cookie(
                key="access_token",
                value=str(access_token),
                httponly=True,      # Protect from JS (XSS)
                secure=True,        # Only over HTTPS
                samesite="strict",  # CSRF protection: 'strict' | 'lax' | 'none'
                max_age=3600,       # 1 hour in seconds
                path="/",           # Cookie is valid for all routes
                domain=None         # Set this if needed for subdomains
                                )
        response.status_code = status.HTTP_201_CREATED
        return {
            "message": "User signed up successfully",
            "success": True
        }
    except Exception as e:
        print(e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "message": "server error"
        }
    finally:
        await database.disconnect()

@userRouter.post("/logout")
async def logout(response: Response,access_token: Annotated[str | None,Cookie()] = None):
    try:
        user_id = await verify_jwt(access_token)
        if access_token is None or user_id is None:
            response.status_code = status.HTTP_403_FORBIDDEN
            return {
                "message": "User is already logged out"
            }
            
        
        response.set_cookie(key="access_token",value="")
        
        response.status_code = status.HTTP_200_OK
        return {
            "message": "User logged out successfully"
        }
    except Exception as e:
        print(e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
            "message": "Error while logging out",
            "error": e
        }
        
    

@userRouter.post("/login")   
async def login(response: Response,user: SigninRequest):
    try:
        await database.connect()
        stmt = select(Users).where(Users.c.username == user.username)
        print("Fetching user with username:", user.username)
        user_exists = await database.fetch_one(stmt)
        if(user_exists.count == 0):
            print("User with given username not found")
            response.status_code = status.HTTP_404_NOT_FOUND
            return {
                "message": "User with given username not found"
            }
        # bytes = user.password.encode('utf-8')
        # hashedPassword = bcrypt.hashpw(bytes,bcrypt.gensalt()).decode('utf-8')

        # decoded_password = bcrypt.checkpw()

        # print("Input Password: ",hashedPassword)
        # print("DB Password: ",user_exists["password"])
        if bcrypt.checkpw(user.password.encode('utf-8'),user_exists["password_hash"].encode('utf-8')) == False:
            print("User password does not match")
            response.status_code = status.HTTP_401_UNAUTHORIZED            
            return {
                "message": "User password does not match"
            }
        
        print("Creating session for user_id:", user_exists["user_id"])
        access_token = await create_session(user_exists["user_id"])

        print("Setting access token in response")
        response.set_cookie(
            key="access_token",
            value=str(access_token),
            httponly=True,      # Protect from JS (XSS)
            secure=True,        # Only over HTTPS
            samesite="strict",  # CSRF protection: 'strict' | 'lax' | 'none'
            max_age=3600,       # 1 hour in seconds
            path="/",           # Cookie is valid for all routes
            domain=None         # Set this if needed for subdomains
                            )
        response.status_code = status.HTTP_200_OK
        return {
            "message": "User signed in successfully",
            "success": True
        }
    except Exception as e:       
        print("Exception occured while signing in:", e)
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {
                "message": "Some internal error occured"
            }
    finally: 
        print("Disconnecting database")
        await database.disconnect()
    


    
