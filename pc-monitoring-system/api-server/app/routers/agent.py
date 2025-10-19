from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import secrets
from datetime import datetime

from ..core.auth import get_current_user_dependency
from ..models.database import get_db, Manager, User, Scan, Machine
from ..services import AgentPackager

router = APIRouter(prefix="/agent", tags=["agent"])

@router.get("/download")
async def download_agent(
    package_type: str = Query("python"),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden descargar el agente"
        )
    
    if package_type not in ["python", "executable"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de paquete debe ser 'python' o 'executable'"
        )
    
    manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
    if not manager:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil de gerente no encontrado"
        )
    
    try:
        packager = AgentPackager()
        
        if package_type == "executable":
            package_data = packager.create_executable_package(str(manager.id))
            filename = f"pc_monitor_agent_executable_{manager.id}.zip"
        else:
            package_data = packager.create_agent_package(str(manager.id))
            filename = f"pc_monitor_agent_python_{manager.id}.zip"
        
        return StreamingResponse(
            io.BytesIO(package_data),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando paquete del agente: {str(e)}"
        )

@router.get("/check-task")
async def check_agent_task(
    machine_id: str = Query(...),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "AGENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los agentes pueden consultar tareas"
        )
    
    machine = db.query(Machine).filter(Machine.machine_id == machine_id).first()
    if not machine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Máquina no encontrada"
        )
    
    return {
        "has_task": False,
        "task_type": None,
        "scan_interval": 3600,
        "immediate_scan": False,
        "config_update": None
    }

scan_tokens = {}

@router.get("/scan-result/{scan_token}")
async def get_scan_result(
    scan_token: str,
    db: Session = Depends(get_db)
):
    if scan_token not in scan_tokens:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Token de escaneo inválido o expirado"
        )
    
    token_data = scan_tokens[scan_token]
    
    if (datetime.utcnow() - token_data["created_at"]).seconds > 3600:
        del scan_tokens[scan_token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de escaneo expirado"
        )
    
    scan = db.query(Scan).filter(Scan.id == token_data["scan_id"]).first()
    if not scan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escaneo no encontrado"
        )
    
    del scan_tokens[scan_token]
    
    return {
        "scan_id": scan.id,
        "scan_date": scan.scan_date,
        "machine_name": scan.machine.machine_name,
        "scan_data": scan.scan_data,
        "status": "completed"
    }

def create_scan_token(scan_id: str) -> str:
    token = secrets.token_urlsafe(32)
    scan_tokens[token] = {
        "scan_id": scan_id,
        "created_at": datetime.utcnow()
    }
    return token