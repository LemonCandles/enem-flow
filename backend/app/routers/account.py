"""The signed-in student's profile and preferences."""
from fastapi import APIRouter

from .. import schemas as s
from ..core.security import user_data
from ..dependencies import CurrentUser

router = APIRouter(prefix="/me", tags=["conta"])


@router.get("")
def me(user: CurrentUser):
    return user_data(user)


@router.put("/preferences")
def preferences(payload: s.Preferences, user: CurrentUser):
    user.name = payload.name
    user.preferences = payload.model_dump(exclude={"name"})
    return user_data(user)
