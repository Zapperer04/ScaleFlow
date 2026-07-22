from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from backend.platform.security.auth import AuthManager
from backend.platform.security.permissions import PermissionManager

router = APIRouter(tags=["Authentication"])
security = HTTPBearer()

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    # Setup simple authentication
    if req.username in ("admin", "manager", "user") and req.password == "password":
        role = req.username
        token = AuthManager.create_access_token({"sub": req.username, "role": role})
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Invalid username or password")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    payload = AuthManager.decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"username": payload.get("sub"), "role": payload.get("role", "user")}

def require_permission(permission: str):
    def dependency(user: dict = Depends(get_current_user)):
        if not PermissionManager.has_permission(user["role"], permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}"
            )
        return user
    return dependency
