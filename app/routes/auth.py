from datetime import datetime, timedelta
from typing import Annotated, Dict
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from ..database.supabase_auth import get_user_by_email, verify_user_credentials
from ..models import Token, TokenData, UserResponse, LoginRequest, LoginResponse

router = APIRouter()

# to get a string like this run:
# openssl rand -hex 32
SECRET_KEY = "as4234#&^*@d5as@$P4d8as_+@)7d87!*$#_as-+++87"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> Dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = get_user_by_email(token_data.email)
    if user is None:
        raise credentials_exception
    return user

@router.post("/login", response_model=LoginResponse)
async def login(
    login_data: LoginRequest,
):
    ok = verify_user_credentials(login_data.email, login_data.password)
    if not ok:
        return LoginResponse(
            success=False,
            message="Invalid email or password"
        )

    user = get_user_by_email(login_data.email)
    token = create_access_token({"email": user.get("email")})
    return LoginResponse(
        success=True,
        token=token,
        user={
            "email": user.get("email"),
            "name": user.get("name")
        }
    )


# NOTE: Public registration is disabled. Users should be created
# manually via the `scripts/seed_users.py` script or directly in Supabase.

@router.get("/me", response_model=UserResponse)
async def read_users_me(
    current_user: Annotated[Dict, Depends(get_current_user)]
):
    # Return only fields expected by UserResponse
    return {
        "id": current_user.get("id"),
        "email": current_user.get("email"),
        "name": current_user.get("name"),
    }
