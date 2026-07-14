import os
from datetime import timedelta, datetime, timezone
from typing import Annotated
import jwt
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from jwt.exceptions import InvalidTokenError
from backend.crud import user, auth
from pwdlib import PasswordHash
from api.models import TokenData

SECRET_KEY = os.environ.get("FASTAPI_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def verify_password(plain_password, hashed_password):
    """
    verify password exists in db
    return true or false
    """
    return password_hash.verify(plain_password, hashed_password)


def get_password_hash(password):
    """
    hash the password
    return the hash
    """
    return password_hash.hash(password)


def get_user_username(login):
    """
    get user by login
    return user information
    """
    a = auth.Auth()
    res = a.get_user(login)
    return res


def get_user_by_id(user_id):
    """
    Get user by id
    """
    u = user.User()
    res = u.get_user(user_id)
    return res

def authenticated_user(login: str, password: str):
    """
    Verify login informations
    return user informations
    """
    user = get_user_username(login)
    if not user:
        return False
    if not verify_password(password, user[2]):
        return False
    if user[3] == "inactive":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account Deactivated. please contact your administrator",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """
    Create a New token or update expire time to 30 minutes
    return the token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    verify the validity of the token
    return user information
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        rowid = int(payload.get("rowid"))
        role = str(payload.get("role"))
        if rowid is None:
            raise credentials_exception
        token_data = TokenData(rowid=rowid, role=role)
    except InvalidTokenError:
        raise credentials_exception
    return token_data


def login(username, password):
    """
    check if the user logins are correct
    return a token if true
    """
    user = authenticated_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=240)
    access_token = create_access_token(
        data={"rowid": str(user[0]), "role": str(user[3]), "scope": "access"},
        expires_delta=access_token_expires,
    )
    return access_token, user[0]


def is_admin(token: Annotated[str, Depends(oauth2_scheme)]):
    """
    check if user is an admin
    return True
    """
    if token.role == "admin":
        return True
    else:
        return False


def update_password(current_password, token):
    a = auth.Auth()

    if not current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must provide your current password to set a new one.",
        )

    current_password_hash = a.get_user_for_update(token.rowid)
    verified_user = verify_password(current_password, current_password_hash)

    if not verified_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid current password.",
        )

    return True
