from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from ..models.database import get_db, User, Manager, Machine, Scan
from ..core.auth import get_current_user_dependency

router = APIRouter(prefix="/machines", tags=["machines"])

class MachineResponse(BaseModel):
    id: int
    fingerprint: str
    name: str
    friendly_name: Optional[str]
    last_seen: Optional[str]
    status: Optional[str]
    scan_count: int
    
    class Config:
        from_attributes = True

class MachineUpdateRequest(BaseModel):
    friendly_name: str

class ScanResponse(BaseModel):
    id: int
    timestamp: str
    status: str
    scan_data: dict
    threats_detected: int
    
    class Config:
        from_attributes = True

@router.get("", response_model=List[MachineResponse])
async def get_machines(
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden acceder a las máquinas"
        )
    
    try:
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        machines = db.query(Machine).filter(Machine.manager_id == manager.id).all()
        
        result = []
        for machine in machines:
            last_scan = db.query(Scan).filter(
                Scan.machine_id == machine.id
            ).order_by(desc(Scan.timestamp)).first()
            
            scan_count = db.query(Scan).filter(Scan.machine_id == machine.id).count()
            
            result.append(MachineResponse(
                id=machine.id,
                fingerprint=machine.fingerprint,
                name=machine.name,
                friendly_name=machine.friendly_name,
                last_seen=last_scan.timestamp.isoformat() if last_scan else None,
                status=last_scan.status if last_scan else "UNKNOWN",
                scan_count=scan_count
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo máquinas: {str(e)}"
        )

@router.get("/{machine_id}/scans", response_model=List[ScanResponse])
async def get_machine_scans(
    machine_id: int,
    limit: int = Query(50),
    offset: int = Query(0),
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden acceder a los escaneos"
        )
    
    try:
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        machine = db.query(Machine).filter(
            Machine.id == machine_id,
            Machine.manager_id == manager.id
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Máquina no encontrada"
            )
        
        scans = db.query(Scan).filter(
            Scan.machine_id == machine_id
        ).order_by(desc(Scan.timestamp)).offset(offset).limit(limit).all()
        
        result = []
        for scan in scans:
            threats_count = len(scan.threats) if hasattr(scan, 'threats') else 0
            
            result.append(ScanResponse(
                id=scan.id,
                timestamp=scan.timestamp.isoformat(),
                status=scan.status,
                scan_data=scan.scan_data,
                threats_detected=threats_count
            ))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo escaneos: {str(e)}"
        )

@router.put("/{machine_id}", response_model=MachineResponse)
async def update_machine(
    machine_id: int,
    machine_update: MachineUpdateRequest,
    current_user: User = Depends(get_current_user_dependency),
    db: Session = Depends(get_db)
):
    if current_user.role.value != "GERENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los gerentes pueden actualizar máquinas"
        )
    
    try:
        manager = db.query(Manager).filter(Manager.user_id == current_user.id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de gerente no encontrado"
            )
        
        machine = db.query(Machine).filter(
            Machine.id == machine_id,
            Machine.manager_id == manager.id
        ).first()
        
        if not machine:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Máquina no encontrada"
            )
        
        machine.friendly_name = machine_update.friendly_name
        db.commit()
        
        last_scan = db.query(Scan).filter(
            Scan.machine_id == machine.id
        ).order_by(desc(Scan.timestamp)).first()
        
        scan_count = db.query(Scan).filter(Scan.machine_id == machine.id).count()
        
        return MachineResponse(
            id=machine.id,
            fingerprint=machine.fingerprint,
            name=machine.name,
            friendly_name=machine.friendly_name,
            last_seen=last_scan.timestamp.isoformat() if last_scan else None,
            status=last_scan.status if last_scan else "UNKNOWN",
            scan_count=scan_count
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando máquina: {str(e)}"
        )