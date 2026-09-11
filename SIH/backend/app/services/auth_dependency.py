import jwt
from fastapi import Header, HTTPException
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
