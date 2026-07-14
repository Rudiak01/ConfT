from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status

from ..auth import get_current_user
from ..models import (
    ModelUser,
    ModelResponseGetConnectedUser,
    UserRole,
    UserUpdate,
)
from ..tools import (
    get_users,
    add_user,
    delete_user,
    get_user_by_token,
    update_user,
    user_role,
    update_expired_password,
)

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Not found"}},
)

Token = Annotated[ModelUser, Depends(get_current_user)]


@router.get("")
async def _get_users(token: Token):
    """
    List all users
    """
    return get_users(token)


@router.post("/new")
async def _post_user(User: ModelUser, token: Token):
    """
    Create user
    Return id
    """
    return add_user(User, token)


@router.delete("/delete")
async def _delete_user(token: Token, user_id: int | None = None):
    """
    Delete user
    """
    return delete_user(user_id, token)


@router.get("/user", response_model=ModelResponseGetConnectedUser)
async def _get_connected_user(token: Token):
    """
    Get user by id
    """
    return get_user_by_token(token)


@router.post("/update")
async def _post_update_user(
    data: UserUpdate,
    token: Token,
    operator_id: int | None = None,
):
    """
    update user infos
    """
    return update_user(data, token, operator_id)


@router.put("/role")
async def _put_user_role(
    UserRole: UserRole,
    token: Token,
    user_id: int | None = None,
):
    """
    Update user role
    """
    return user_role(UserRole, user_id, token)


@router.post("/password_update")
async def _update_user_password(password: str, token: Token):
    """
    change password when expired
    """
    return update_expired_password(password, token)

