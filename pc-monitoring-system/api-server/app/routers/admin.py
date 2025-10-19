from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from ..models.database import get_db, User, UserRole
from ..core.auth import get_current_user_dependency

router = APIRouter(prefix="/admin", tags=["admin"])

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    created_at: str
    
    class Config:
        from_attributes = True

class RoleUpdateRequest(BaseModel):
    role: UserRole

@router.get("/users", response_model=List[UserResponse])
async def get_all_users(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden acceder a esta función"
        )
    
    try:
        users = db.query(User).all()
        return [
            UserResponse(
                id=user.id,
                name=user.name,
                email=user.email,
                role=user.role,
                created_at=user.created_at.isoformat()
            )
            for user in users
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo usuarios: {str(e)}"
        )

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    role_update: RoleUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role != UserRole.ADMINISTRADOR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden cambiar roles de usuario"
        )
    
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )
        
        if user.role == role_update.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El usuario ya tiene el rol {role_update.role.value}"
            )
        
        old_role = user.role
        user.role = role_update.role
        db.commit()
        
        return {
            "message": f"Rol actualizado exitosamente de {old_role.value} a {role_update.role.value}",
            "user_id": user_id,
            "old_role": old_role.value,
            "new_role": role_update.role.value
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando rol de usuario: {str(e)}"
        )