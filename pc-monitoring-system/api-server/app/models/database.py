from sqlalchemy import create_engine, Column, String, DateTime, Integer, Text, Enum as SQLEnum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
import enum

from ..core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class UserRole(enum.Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    AGENTE = "AGENTE"
    USUARIO = "USUARIO"

class ThreatStatus(enum.Enum):
    NUEVA = "NUEVA"
    EN_REVISION = "EN_REVISION"
    RESUELTA = "RESUELTA"

class ThreatLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class InvitationStatus(enum.Enum):
    PENDIENTE = "PENDIENTE"
    ACEPTADA = "ACEPTADA"
    EXPIRADA = "EXPIRADA"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), nullable=False, default=UserRole.USUARIO)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Manager(Base):
    __tablename__ = "managers"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), nullable=False)
    company_name = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Machine(Base):
    __tablename__ = "machines"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    manager_id = Column(UUID(as_uuid=True), nullable=False)
    hardware_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))  # hostname del sistema
    friendly_name = Column(String(255))  # nombre amigable asignado por el gerente
    inventory_data = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(UUID(as_uuid=True), nullable=False)
    scan_timestamp = Column(DateTime, nullable=False)
    performance_data = Column(JSONB)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

class Threat(Base):
    __tablename__ = "threats"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    machine_id = Column(UUID(as_uuid=True), nullable=False)
    threat_type = Column(String(100), nullable=False)
    level = Column(SQLEnum(ThreatLevel), nullable=False, default=ThreatLevel.MEDIUM)
    description = Column(Text, nullable=False)
    details = Column(JSONB)  # detalles técnicos de la amenaza
    status = Column(SQLEnum(ThreatStatus), nullable=False, default=ThreatStatus.NUEVA)
    resolved = Column(Boolean, nullable=False, default=False)
    evidence = Column(JSONB)  # evidencia de la detección
    detected_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()