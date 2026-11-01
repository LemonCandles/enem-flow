"""The signed-in student's profile and preferences."""
from fastapi import APIRouter, Depends

from .. import models as m, schemas as s
from ..security import current_user, user_data

router = APIRouter(prefix="/me", tags=["conta"])


@router.get("")
def me(user: m.User = Depends(current_user)):
    return user_data(user)


@router.put("/preferences")
def preferences(payload: s.Preferences, user: m.User = Depends(current_user)):
    user.name = payload.name
    user.preferences = payload.model_dump(exclude={"name"})
    return user_data(user)
