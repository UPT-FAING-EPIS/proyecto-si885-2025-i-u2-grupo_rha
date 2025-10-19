"""
Versión temporal de la base de datos usando SQLite para pruebas
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
import enum

# Configuración temporal para SQLite
SQLITE_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLITE_DATABASE_URL, 
    connect_args={"check_same_thread": False}  # Solo para SQLite
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Enums
class UserRole(enum.Enum):
    PROSPECTO = "PROSPECTO"
    GERENTE = "GERENTE"
    AGENTE = "AGENTE"
    ADMINISTRADOR = "ADMINISTRADOR"

class ThreatLevel(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ThreatStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    RESOLVED = "RESOLVED"
    IGNORED = "IGNORED"

class InvitationStatus(enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    EXPIRED = "EXPIRED"

# Modelos simplificados para pruebas
class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.PROSPECTO)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)

class Manager(Base):
    __tablename__ = "managers"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    company_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)

class Machine(Base):
    __tablename__ = "machines"
    
    id = Column(Integer, primary_key=True, index=True)
    manager_id = Column(Integer, ForeignKey("managers.id"))
    fingerprint = Column(String(255), unique=True, index=True)
    name = Column(String(255))
    friendly_name = Column(String(255))
    last_seen = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class Scan(Base):
    __tablename__ = "scans"
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"))
    timestamp = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="COMPLETED")
    scan_data = Column(Text)  # JSON como texto para SQLite

class Threat(Base):
    __tablename__ = "threats"
    
    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"))
    scan_id = Column(Integer, ForeignKey("scans.id"))
    threat_type = Column(String(100))
    level = Column(SQLEnum(ThreatLevel))
    description = Column(Text)
    details = Column(Text)  # JSON como texto para SQLite
    detected_at = Column(DateTime, default=datetime.utcnow)
    resolved = Column(Boolean, default=False)

# Crear todas las tablas
Base.metadata.create_all(bind=engine)

# Dependency para obtener la sesión de base de datos
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()