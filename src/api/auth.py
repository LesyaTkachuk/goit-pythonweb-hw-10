from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from src.schemas import UserCreate, Token, UserBase
from src.services.auth import create_access_token, Hash
from src.services.users import UserService
from src.database.db import get_db
from src.conf import messages

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=UserBase, status_code=status.HTTP_201_CREATED)
async def register(body: UserCreate, db: Session = Depends(get_db)):
    user_service = UserService(db)

    email_user = await user_service.get_user_by_email(body.email)
    if email_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=messages.USER_EMAIL_OR_NAME_ALREADY_EXISTS
        )

    username_user = await user_service.get_user_by_username(body.username)
    if username_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=messages.USER_EMAIL_OR_NAME_ALREADY_EXISTS
        )

    body.password = Hash().get_password_hash(body.password)
    return await user_service.create_user(body)

# login
@router.post("/login", response_model=Token)
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user_service = UserService(db)
    user  = await user_service.get_user_by_username(form_data.username)

    if not user or not Hash().verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=messages.INVALID_CREDENTIALS,
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = await create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}