# from passlib.ext.django.models import password_context
from datetime import timedelta, datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import JWTError
from passlib.context import CryptContext
# from passlib.ext.django.models import password_context
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette import status

from database import SessionLocal
from models import Users

router = APIRouter(
    prefix="/auth",
    tags=['auth']
)

SECRET_KEY = '02ea2e10bd00a89945ccada4c46eb3a7fb86d6cd2ef2bada64c20cfe2b8a4ead'
ALGORITHM = 'HS256'

bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="auth/token")

class CreateUserRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db_dependency = Annotated[Session, Depends(get_db)]

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(db: db_dependency, create_user_request: CreateUserRequest):
    create_user_model = Users(
        username= create_user_request.username,
        hashed_password= bcrypt_context.hash(create_user_request.password)
    )

    db.add(create_user_model)
    db.commit()
    db.refresh(create_user_model)

    return {"message": "User created successfully", "user": create_user_model.username}

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: db_dependency):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail= 'could not validate user.')

    token = create_access_token(user.username, user.id, timedelta(days=1))

    return {'access_token': token, 'token_type': 'bearer'}


def authenticate_user(username: str, password: str, db):
    user: Users = db.query(Users).filter(Users.username == username).first()
    print(user.username)
    if not user:
        return False
    if not bcrypt_context.verify(password, user.hashed_password):
        return False
    return user

def create_access_token(username: str, user_id: int, expires_delta: timedelta):
    encode = {'sub': username, 'id': user_id}
    expires = datetime.now() + expires_delta
    encode.update({'exp': expires})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: Annotated[str, Depends(oauth2_bearer)]):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get('sub')
        user_id: int = payload.get('id')

        if username is None or user_id is None:
            raise HTTPException(status_code= status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')
        return {'username': username, 'id': user_id}

    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Could not validate user')