from fastapi import APIRouter, Depends
from src.schemas import UserBase
from src.services.auth import get_current_user
from src.database.models import User

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserBase)
async def me(user: User = Depends(get_current_user)):
    return user
