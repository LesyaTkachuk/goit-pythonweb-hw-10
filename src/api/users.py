from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from src.database.db import get_db
from src.services.upload_file import UploadFileService
from src.services.users import UserService
from src.schemas import UserBase
from src.services.auth import get_current_user
from src.database.models import User
from src.conf.config import config


router = APIRouter(prefix="/users", tags=["users"])
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/me", response_model=UserBase, description="No more than 10 requests per minute"
)
@limiter.limit("10/minute")
async def me(
    request: Request,
    user: User = Depends(get_current_user),
):
    return user


@router.patch("/avatar", response_model=UserBase)
async def update_avatar(
    file: UploadFile = File(),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    avatar_url = UploadFileService(
        config.CLD_NAME, config.CLD_API_KEY, config.CLD_API_SECRET
    ).upload_file(file, user.username)

    user_service = UserService(db)
    user = await user_service.update_avatar_url(user.email, avatar_url)
    return user
