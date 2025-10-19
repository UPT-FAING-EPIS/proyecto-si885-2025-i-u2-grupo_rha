from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from ..core.auth import verify_password, create_access_token, get_password_hash
from ..models.database import get_db, User

router = APIRouter(prefix="/auth", tags=["authentication"])

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_role: str

@router.post("/register")
async def register_user(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password_hash=hashed_password,
        role="PROSPECTO"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "status": "success",
        "message": "Usuario registrado exitosamente",
        "user_id": new_user.id,
        "role": new_user.role
    }

@router.post("/login", response_model=Token)
async def login_user(
    user_data: UserLogin,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == user_data.email).first()
    
    if not user or not verify_password(user_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_role": user.role.value
    }