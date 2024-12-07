from datetime import datetime, timedelta, UTC
from typing import Literal, Optional

from fastapi import Depends, HTTPException, status
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from src.database.db import get_db
from src.conf.config import config
from src.conf import messages
from src.services.users import UserService


class Hash:
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def verify_password(self, plain_password, hashed_password):
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str):
        return self.pwd_context.hash(password)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# define a function to generate a new access token
async def create_token(
    data: dict, token_type: Literal["access", "refresh"], expires_delta: timedelta
):
    to_encode = data.copy()
    now = datetime.now(UTC)
    expire = now + timedelta(seconds=expires_delta)

    to_encode.update({"exp": expire, "iat": now, "token_type": token_type})
    encoded_jwt = jwt.encode(
        to_encode, config.JWT_SECRET, algorithm=config.JWT_ALGORITHM
    )
    return encoded_jwt


# define a function to create a new access token
async def create_access_token(data: dict, expires_delta: Optional[float] = None):
    if expires_delta:
        access_token = await create_token(data, "access", expires_delta)
    else:
        access_token = await create_token(data, "access", config.JWT_EXPIRATION_SECONDS)
    return access_token


# define a function to create a new refresh token
async def create_refresh_token(data: dict, expires_delta: Optional[float] = None):
    if expires_delta:
        refresh_token = await create_token(data, "refresh", expires_delta)
    else:
        refresh_token = await create_token(
            data, "refresh", config.JWT_REFRESH_EXPIRATION_SECONDS
        )
    return refresh_token


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=messages.UNVERIFIED_CREDENTIALS,
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        # decode JWT
        payload = jwt.decode(
            token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        token_type = payload.get("token_type")
        if username is None or token_type != "access":
            raise credentials_exception
    except JWTError as e:
        raise credentials_exception

    user_service = UserService(db)
    user = await user_service.get_user_by_username(username=username)
    if user is None:
        raise credentials_exception
    return user


async def verify_refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=messages.UNVERIFIED_CREDENTIALS,
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            refresh_token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM]
        )
        username = payload.get("sub")
        token_type = payload.get("token_type")
        if username is None or token_type != "refresh":
            raise credentials_exception
        user = await UserService(db).get_user_by_username(username, refresh_token)
        return user
    except JWTError as e:
        raise credentials_exception
