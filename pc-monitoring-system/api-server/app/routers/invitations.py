from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import secrets

from ..models.database import get_db, User, Manager, UserRole
from ..core.auth import get_password_hash

router = APIRouter(prefix="/invitations", tags=["invitations"])

class AcceptInvitation(BaseModel):
    token: str
    password: str

invitation_tokens = {}

@router.post("/accept")
async def accept_invitation(
    invitation_data: AcceptInvitation,
    db: Session = Depends(get_db)
):
    try:
        if invitation_data.token not in invitation_tokens:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Token de invitación inválido o expirado"
            )
        
        token_data = invitation_tokens[invitation_data.token]
        
        if (datetime.utcnow() - token_data["created_at"]).days > 7:
            del invitation_tokens[invitation_data.token]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de invitación expirado"
            )
        
        manager = db.query(Manager).filter(Manager.id == token_data["manager_id"]).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager asociado no encontrado"
            )
        
        existing_user = db.query(User).filter(User.email == token_data["email"]).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un usuario con este email"
            )
        
        hashed_password = get_password_hash(invitation_data.password)
        new_user = User(
            name=token_data["email"].split("@")[0],
            email=token_data["email"],
            password_hash=hashed_password,
            role=UserRole.AGENTE
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        
        del invitation_tokens[invitation_data.token]
        
        return {
            "status": "success",
            "message": "Cuenta de agente creada exitosamente",
            "user_id": new_user.id,
            "manager_id": manager.id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando invitación: {str(e)}"
        )

def create_invitation_token(manager_id: str, email: str) -> str:
    token = secrets.token_urlsafe(32)
    invitation_tokens[token] = {
        "manager_id": manager_id,
        "email": email,
        "created_at": datetime.utcnow()
    }
    return token

@router.get("/validate/{token}")
async def validate_invitation_token(token: str):
    if token not in invitation_tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token de invitación inválido"
        )
    
    token_data = invitation_tokens[token]
    
    if (datetime.utcnow() - token_data["created_at"]).days > 7:
        del invitation_tokens[token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de invitación expirado"
        )
    
    return {
        "status": "valid",
        "email": token_data["email"],
        "expires_in_days": 7 - (datetime.utcnow() - token_data["created_at"]).days
    }