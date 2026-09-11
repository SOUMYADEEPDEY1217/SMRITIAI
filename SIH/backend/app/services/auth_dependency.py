import jwt
from fastapi import Header, HTTPException, Depends
from app.config import settings

def get_current_user(authorization: str = Header(None)) -> dict:
    """
    Use as a route dependency: `user: dict = Depends(get_current_user)`
    Frontend must send: Authorization: Bearer <jwt_token>
    Returns the decoded token dict, which includes uid, email, role, etc.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.split(" ", 1)[1]
    
    try:
        decoded = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
        return decoded
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def require_role(*allowed_roles: str):
    """
    Route dependency factory that enforces role-based access control.
    Usage: `user: dict = Depends(require_role("doctor", "admin"))`
    Rejects with 403 if the authenticated user's role isn't in allowed_roles.
    """
    def _checker(user: dict = Depends(get_current_user)) -> dict:
        role = user.get("role")
        if role not in allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of these roles: {', '.join(allowed_roles)}.",
            )
        return user
    return _checker
