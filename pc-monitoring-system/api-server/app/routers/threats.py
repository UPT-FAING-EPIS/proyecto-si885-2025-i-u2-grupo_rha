from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

from ..models.database import get_db, User, Manager, Machine, Threat, ThreatLevel
from ..core.auth import get_current_user_dependency

router = APIRouter(prefix="/threats", tags=["threats"])

class ThreatResponse(BaseModel):
    id: int
    machine_id: int
    machine_name: str
    machine_friendly_name: Optional[str]
    threat_type: str
    level: ThreatLevel
    description: str
    details: dict
    detected_at: str
    resolved: bool
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[ThreatResponse])
async def get_threats(
    threat_type: Optional[str] = Query(None),
    level: Optional[ThreatLevel] = Query(None),
    days: int = Query(30),
    resolved: Optional[bool] = Query(None),
    limit: int = Query(100),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden acceder a las amenazas"
        )
    
    try:
        # Obtener el manager
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        # Construir query base
        query = db.query(Threat, Machine).join(
            Machine, Threat.machine_id == Machine.id
        ).filter(
            Machine.manager_id == manager.id
        )
        
        # Aplicar filtros
        if days > 0:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = query.filter(Threat.detected_at >= cutoff_date)
        
        if threat_type:
            query = query.filter(Threat.threat_type == threat_type)
        
        if level:
            query = query.filter(Threat.level == level)
        
        if resolved is not None:
            query = query.filter(Threat.resolved == resolved)
        
        # Ordenar por fecha de detección (más recientes primero)
        query = query.order_by(desc(Threat.detected_at))
        
        # Aplicar paginación
        threats_with_machines = query.offset(offset).limit(limit).all()
        
        result = []
        for threat, machine in threats_with_machines:
            result.append(ThreatResponse(
                id=threat.id,
                machine_id=machine.id,
                machine_name=machine.name,
                machine_friendly_name=machine.friendly_name,
                threat_type=threat.threat_type,
                level=threat.level,
                description=threat.description,
                details=threat.details,
                detected_at=threat.detected_at.isoformat(),
                resolved=threat.resolved
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo amenazas: {str(e)}"
        )

@router.put("/{threat_id}/resolve")
async def resolve_threat(
    threat_id: int,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden resolver amenazas"
        )
    
    try:
        # Obtener el manager
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        # Verificar que la amenaza pertenece al manager
        threat = db.query(Threat).join(
            Machine, Threat.machine_id == Machine.id
        ).filter(
            Threat.id == threat_id,
            Machine.manager_id == manager.id
        ).first()
        
        if not threat:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Amenaza no encontrada"
            )
        
        if threat.resolved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La amenaza ya está marcada como resuelta"
            )
        
        # Marcar como resuelta
        threat.resolved = True
        threat.resolved_at = datetime.now()
        db.commit()
        
        return {
            "message": "Amenaza marcada como resuelta exitosamente",
            "threat_id": threat_id,
            "resolved_at": threat.resolved_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resolviendo amenaza: {str(e)}"
        )

@router.get("/stats")
async def get_threat_stats(
    days: int = Query(30),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden acceder a las estadísticas"
        )
    
    try:
        # Obtener el manager
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Estadísticas por nivel
        stats_by_level = {}
        for level in ThreatLevel:
            count = db.query(Threat).join(
                Machine, Threat.machine_id == Machine.id
            ).filter(
                Machine.manager_id == manager.id,
                Threat.level == level,
                Threat.detected_at >= cutoff_date
            ).count()
            stats_by_level[level.value] = count
        
        # Estadísticas por tipo
        threat_types = db.query(Threat.threat_type).join(
            Machine, Threat.machine_id == Machine.id
        ).filter(
            Machine.manager_id == manager.id,
            Threat.detected_at >= cutoff_date
        ).distinct().all()
        
        stats_by_type = {}
        for (threat_type,) in threat_types:
            count = db.query(Threat).join(
                Machine, Threat.machine_id == Machine.id
            ).filter(
                Machine.manager_id == manager.id,
                Threat.threat_type == threat_type,
                Threat.detected_at >= cutoff_date
            ).count()
            stats_by_type[threat_type] = count
        
        # Total de amenazas
        total_threats = db.query(Threat).join(
            Machine, Threat.machine_id == Machine.id
        ).filter(
            Machine.manager_id == manager.id,
            Threat.detected_at >= cutoff_date
        ).count()
        
        # Amenazas resueltas
        resolved_threats = db.query(Threat).join(
            Machine, Threat.machine_id == Machine.id
        ).filter(
            Machine.manager_id == manager.id,
            Threat.detected_at >= cutoff_date,
            Threat.resolved == True
        ).count()
        
        return {
            "period_days": days,
            "total_threats": total_threats,
            "resolved_threats": resolved_threats,
            "pending_threats": total_threats - resolved_threats,
            "resolution_rate": (resolved_threats / total_threats * 100) if total_threats > 0 else 0,
            "by_level": stats_by_level,
            "by_type": stats_by_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )