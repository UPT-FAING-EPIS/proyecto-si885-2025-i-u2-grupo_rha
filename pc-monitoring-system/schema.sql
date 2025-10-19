-- Habilitar la extensión para generar UUIDs si no está habilitada
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Crear tipos ENUM para roles y estados para mantener la integridad de los datos
CREATE TYPE user_role AS ENUM ('ADMIN', 'GERENTE', 'AGENTE', 'USUARIO');
CREATE TYPE threat_status AS ENUM ('NUEVA', 'EN_REVISION', 'RESUELTA');
CREATE TYPE invitation_status AS ENUM ('PENDIENTE', 'ACEPTADA', 'EXPIRADA');

-- Tabla para gestionar la autenticación y los roles base
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role user_role NOT NULL DEFAULT 'USUARIO',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla con información específica del cliente (Gerente)
CREATE TABLE managers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    company_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla para gestionar las invitaciones a los Agentes
CREATE TABLE invitations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manager_id UUID NOT NULL REFERENCES managers(id) ON DELETE CASCADE,
    invitee_email VARCHAR(255) NOT NULL,
    token VARCHAR(255) UNIQUE NOT NULL,
    status invitation_status NOT NULL DEFAULT 'PENDIENTE',
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla para las políticas de monitoreo personalizadas
CREATE TABLE policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manager_id UUID NOT NULL REFERENCES managers(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    scan_interval_minutes INTEGER NOT NULL DEFAULT 1440, -- 24 horas por defecto
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla del inventario de todas las PCs (Agentes) monitoreadas
CREATE TABLE machines (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    manager_id UUID NOT NULL REFERENCES managers(id) ON DELETE CASCADE,
    policy_id UUID REFERENCES policies(id) ON DELETE SET NULL,
    user_id UUID UNIQUE REFERENCES users(id) ON DELETE SET NULL,
    hardware_id VARCHAR(255) UNIQUE NOT NULL,
    hostname VARCHAR(255),
    inventory_data JSONB, -- Guarda datos estáticos: SO, CPU, RAM total, software
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla para el historial de datos de rendimiento de cada escaneo
CREATE TABLE scans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id UUID NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    scan_timestamp TIMESTAMPTZ NOT NULL,
    performance_data JSONB, -- Guarda datos volátiles: %CPU, %RAM, etc.
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Tabla para el registro de cada amenaza o "mala práctica" detectada
CREATE TABLE threats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    machine_id UUID NOT NULL REFERENCES machines(id) ON DELETE CASCADE,
    threat_type VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    status threat_status NOT NULL DEFAULT 'NUEVA',
    evidence JSONB, -- Guarda la prueba: {"rule_triggered": "DOUBLE_EXTENSION", "file_path": "C:/Downloads/file.pdf.exe"}
    detected_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Crear índices para acelerar las consultas comunes
CREATE INDEX idx_machines_manager_id ON machines(manager_id);
CREATE INDEX idx_scans_machine_id ON scans(machine_id);
CREATE INDEX idx_threats_machine_id ON threats(machine_id);