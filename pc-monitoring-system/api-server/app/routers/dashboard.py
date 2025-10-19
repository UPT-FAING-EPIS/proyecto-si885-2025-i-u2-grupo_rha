from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pydantic import BaseModel

from ..models.database import get_db, User, Manager, Machine, Scan, Threat, ThreatLevel
from ..core.auth import get_current_user_dependency

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

class DashboardSummary(BaseModel):
    total_machines: int
    machines_ok: int
    machines_critical: int
    recent_threats: int
    last_scan_time: str = None
    threat_breakdown: Dict[str, int]
    machine_status_breakdown: Dict[str, int]

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden acceder al dashboard"
        )
    
    try:
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        total_machines = db.query(Machine).filter(Machine.manager_id == manager.id).count()
        
        machines_with_recent_scans = db.query(Machine).join(Scan).filter(
            Machine.manager_id == manager.id,
            Scan.scan_time >= datetime.now() - timedelta(hours=24)
        ).distinct().count()
        
        machines_critical = db.query(Machine).join(Threat).filter(
            Machine.manager_id == manager.id,
            Threat.level == ThreatLevel.CRITICO,
            Threat.resolved == False
        ).distinct().count()
        
        machines_ok = total_machines - machines_critical
        
        recent_threats = db.query(Threat).join(Machine).filter(
            Machine.manager_id == manager.id,
            Threat.detected_at >= datetime.now() - timedelta(days=7)
        ).count()
        
        last_scan = db.query(Scan).join(Machine).filter(
            Machine.manager_id == manager.id
        ).order_by(desc(Scan.scan_time)).first()
        
        last_scan_time = last_scan.scan_time.isoformat() if last_scan else None
        
        threat_breakdown = {}
        for level in ThreatLevel:
            count = db.query(Threat).join(Machine).filter(
                Machine.manager_id == manager.id,
                Threat.level == level,
                Threat.resolved == False
            ).count()
            threat_breakdown[level.value] = count
        
        machine_status_breakdown = {
            "ok": machines_ok,
            "critical": machines_critical,
            "offline": max(0, total_machines - machines_with_recent_scans)
        }
        
        return DashboardSummary(
            total_machines=total_machines,
            machines_ok=machines_ok,
            machines_critical=machines_critical,
            recent_threats=recent_threats,
            last_scan_time=last_scan_time,
            threat_breakdown=threat_breakdown,
            machine_status_breakdown=machine_status_breakdown
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo resumen del dashboard: {str(e)}"
        )