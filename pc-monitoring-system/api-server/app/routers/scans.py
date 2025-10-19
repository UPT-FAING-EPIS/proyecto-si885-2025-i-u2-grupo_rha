from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from datetime import datetime

from ..models.database import get_db, Machine, Scan, Manager, Threat
from ..services import ThreatAnalyzer

router = APIRouter(tags=["scans"])

class ScanData(BaseModel):
    manager_id: str
    machine_name: str
    machine_id: Optional[str] = None
    scan_data: Dict[str, Any]

@router.post("/scans")
async def receive_scan_data(
    scan_data: ScanData,
    db: Session = Depends(get_db)
):
    try:
        manager = db.query(Manager).filter(Manager.id == scan_data.manager_id).first()
        if not manager:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Manager no encontrado"
            )
        
        # Buscar o crear la máquina
        machine = db.query(Machine).filter(
            Machine.manager_id == scan_data.manager_id,
            Machine.machine_name == scan_data.machine_name
        ).first()
        
        if not machine:
            machine = Machine(
                manager_id=scan_data.manager_id,
                machine_name=scan_data.machine_name,
                machine_id=scan_data.machine_id or scan_data.machine_name,
                status="ACTIVE"
            )
            db.add(machine)
            db.commit()
            db.refresh(machine)
        
        # Crear registro de escaneo
        scan = Scan(
            machine_id=machine.id,
            scan_data=scan_data.scan_data,
            scan_date=datetime.utcnow()
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        
        # Analizar amenazas
        analyzer = ThreatAnalyzer()
        threats = analyzer.analyze_scan_data(scan_data.scan_data)
        
        # Guardar amenazas detectadas
        for threat_data in threats:
            threat = Threat(
                machine_id=machine.id,
                threat_type=threat_data.threat_type,
                description=threat_data.description,
                status="ACTIVE",
                evidence=threat_data.evidence,
                detected_at=datetime.utcnow()
            )
            db.add(threat)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Datos de escaneo procesados correctamente",
            "scan_id": scan.id,
            "threats_detected": len(threats)
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando datos de escaneo: {str(e)}"
        )