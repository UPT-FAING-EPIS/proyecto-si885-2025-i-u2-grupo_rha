from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import urlencode
import secrets
import requests
from typing import Optional
from datetime import datetime

from ..models.database import get_db, User, Manager
from ..core.auth import get_current_user_dependency
from ..core.config import settings

router = APIRouter(prefix="/powerbi", tags=["powerbi"])

POWERBI_CLIENT_ID = getattr(settings, 'POWERBI_CLIENT_ID', 'your-powerbi-client-id')
POWERBI_CLIENT_SECRET = getattr(settings, 'POWERBI_CLIENT_SECRET', 'your-powerbi-client-secret')
POWERBI_REDIRECT_URI = getattr(settings, 'POWERBI_REDIRECT_URI', 'http://localhost:8000/api/v1/powerbi/callback')
POWERBI_SCOPE = "https://analysis.windows.net/powerbi/api/.default"

oauth_states = {}

@router.get("/connect")
async def connect_powerbi(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden conectar con Power BI"
        )
    
    try:
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        state = secrets.token_urlsafe(32)
        oauth_states[state] = {
            "manager_id": str(manager.id),
            "created_at": datetime.utcnow()
        }
        
        auth_params = {
            "client_id": POWERBI_CLIENT_ID,
            "response_type": "code",
            "redirect_uri": POWERBI_REDIRECT_URI,
            "scope": POWERBI_SCOPE,
            "state": state,
            "response_mode": "query"
        }
        
        auth_url = f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?{urlencode(auth_params)}"
        
        return {
            "auth_url": auth_url,
            "state": state,
            "message": "Redirige al usuario a auth_url para autorizar"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error iniciando conexión con Power BI: {str(e)}"
        )

@router.get("/callback")
async def powerbi_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    error_description: Optional[str] = None,
    db: Session = Depends(get_db)
):
    if error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error de autorización: {error_description or error}"
        )
    
    if not code or not state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Código de autorización o estado faltante"
        )
    
    if state not in oauth_states:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado OAuth inválido"
        )
    
    try:
        state_data = oauth_states[state]
        manager_id = state_data["manager_id"]
        
        token_data = {
            "client_id": POWERBI_CLIENT_ID,
            "client_secret": POWERBI_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": POWERBI_REDIRECT_URI,
            "scope": POWERBI_SCOPE
        }
        
        token_response = requests.post(
            "https://login.microsoftonline.com/common/oauth2/v2.0/token",
            data=token_data
        )
        
        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error obteniendo token de acceso"
            )
        
        tokens = token_response.json()
        
        manager = db.query(Manager).filter(Manager.id == manager_id).first()
        if manager:
            manager.powerbi_access_token = tokens.get("access_token")
            manager.powerbi_refresh_token = tokens.get("refresh_token")
            manager.powerbi_connected_at = datetime.utcnow()
            db.commit()
        
        del oauth_states[state]
        
        return {
            "status": "success",
            "message": "Conexión con Power BI establecida exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando callback de Power BI: {str(e)}"
        )

@router.get("/status")
async def get_powerbi_status(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden consultar el estado de Power BI"
        )
    
    manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de gerente no encontrado"
        )
    
    is_connected = bool(manager.powerbi_access_token)
    
    return {
        "connected": is_connected,
        "connected_at": manager.powerbi_connected_at.isoformat() if manager.powerbi_connected_at else None,
        "status": "connected" if is_connected else "disconnected"
    }

@router.delete("/disconnect")
async def disconnect_powerbi(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden desconectar Power BI"
        )
    
    manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de gerente no encontrado"
        )
    
    try:
        manager.powerbi_access_token = None
        manager.powerbi_refresh_token = None
        manager.powerbi_connected_at = None
        db.commit()
        
        return {
            "status": "success",
            "message": "Desconectado de Power BI exitosamente"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error desconectando Power BI: {str(e)}"
        )