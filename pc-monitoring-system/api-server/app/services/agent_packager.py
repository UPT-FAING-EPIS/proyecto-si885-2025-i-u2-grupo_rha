"""
Servicio para empaquetar el agente scanner
"""

import os
import zipfile
import json
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class AgentPackager:
    """Maneja el empaquetado del agente scanner para distribución"""
    
    def __init__(self, scanner_path: str = "scanner-agent"):
        self.scanner_path = Path(scanner_path)
        self.temp_dir = Path(tempfile.gettempdir()) / "pc_monitor_packages"
        self.temp_dir.mkdir(exist_ok=True)
    
    def create_agent_package(self, manager_id: str, api_base_url: str = "http://localhost:8000/api/v1") -> bytes:
        """
        Crea un paquete ZIP con el agente scanner personalizado
        
        Args:
            manager_id: ID del manager para configurar el agente
            api_base_url: URL base de la API
            
        Returns:
            Bytes del archivo ZIP
        """
        package_path = self.temp_dir / f"agent_{manager_id}.zip"
        
        with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Agregar archivos del scanner
            self._add_scanner_files(zipf)
            
            # Crear configuración personalizada
            config = self._create_config(manager_id, api_base_url)
            zipf.writestr("config.json", json.dumps(config, indent=2))
            
            # Agregar scripts de instalación y ejecución
            install_script = self._create_install_script()
            zipf.writestr("install.bat", install_script)
            
            run_script = self._create_run_script()
            zipf.writestr("run_scanner.bat", run_script)
            
            service_script = self._create_service_script()
            zipf.writestr("install_service.bat", service_script)
            
            # Agregar requirements
            requirements = self._get_requirements()
            zipf.writestr("requirements.txt", requirements)
            
            # Agregar README
            readme = self._create_readme()
            zipf.writestr("README.txt", readme)
        
        # Leer el archivo y retornar bytes
        with open(package_path, 'rb') as f:
            package_data = f.read()
        
        # Limpiar archivo temporal
        package_path.unlink()
        
        return package_data
    
    def create_executable_package(self, manager_id: str, api_base_url: str = "http://localhost:8000/api/v1") -> bytes:
        """
        Crea un paquete con ejecutable compilado usando PyInstaller
        
        Args:
            manager_id: ID del manager para configurar el agente
            api_base_url: URL base de la API
            
        Returns:
            Bytes del archivo ZIP con el ejecutable
        """
        package_path = self.temp_dir / f"agent_exe_{manager_id}.zip"
        build_dir = self.temp_dir / f"build_{manager_id}"
        
        try:
            # Crear directorio temporal para build
            build_dir.mkdir(exist_ok=True)
            
            # Copiar archivos del scanner al directorio de build
            if self.scanner_path.exists():
                shutil.copytree(self.scanner_path / "src", build_dir / "src", dirs_exist_ok=True)
            else:
                # Crear scanner básico
                (build_dir / "src").mkdir(exist_ok=True)
                with open(build_dir / "src" / "main.py", 'w') as f:
                    f.write(self._create_basic_scanner())
            
            # Crear configuración
            config = self._create_config(manager_id, api_base_url)
            with open(build_dir / "config.json", 'w') as f:
                json.dump(config, f, indent=2)
            
            # Crear spec file para PyInstaller
            spec_content = self._create_pyinstaller_spec()
            with open(build_dir / "scanner.spec", 'w') as f:
                f.write(spec_content)
            
            # Crear el ZIP final
            with zipfile.ZipFile(package_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Agregar archivos de build
                for file_path in build_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(build_dir)
                        zipf.write(file_path, arcname)
                
                # Agregar scripts de build
                build_script = self._create_build_script()
                zipf.writestr("build_executable.bat", build_script)
                
                # Agregar README para ejecutable
                readme_exe = self._create_executable_readme()
                zipf.writestr("README_EXECUTABLE.txt", readme_exe)
            
            # Leer el archivo y retornar bytes
            with open(package_path, 'rb') as f:
                package_data = f.read()
            
            return package_data
            
        finally:
            # Limpiar directorios temporales
            if package_path.exists():
                package_path.unlink()
            if build_dir.exists():
                shutil.rmtree(build_dir)
    
    def _add_scanner_files(self, zipf: zipfile.ZipFile):
        """Agrega los archivos del scanner al ZIP"""
        if self.scanner_path.exists():
            # Agregar todos los archivos del scanner
            for file_path in self.scanner_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    arcname = file_path.relative_to(self.scanner_path)
                    zipf.write(file_path, arcname)
        else:
            # Si no existe, crear estructura básica
            zipf.writestr("src/main.py", self._create_basic_scanner())
            zipf.writestr("src/__init__.py", "")
    
    def _create_config(self, manager_id: str, api_base_url: str) -> Dict[str, Any]:
        """Crea la configuración personalizada para el agente"""
        return {
            "manager_id": manager_id,
            "api_base_url": api_base_url,
            "scan_interval_minutes": 60,
            "auto_start": True,
            "log_level": "INFO",
            "max_log_files": 10,
            "log_file_size_mb": 10
        }
    
    def _create_install_script(self) -> str:
        """Crea el script de instalación para Windows"""
        return """@echo off
echo ========================================
echo PC Monitor Scanner Agent - Instalacion
echo ========================================

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python no esta instalado o no esta en el PATH
    echo Por favor instale Python 3.8 o superior desde https://python.org
    echo.
    pause
    exit /b 1
)

echo Python detectado correctamente.
echo.

REM Crear entorno virtual
echo Creando entorno virtual...
python -m venv venv
if errorlevel 1 (
    echo Error: No se pudo crear el entorno virtual
    pause
    exit /b 1
)

REM Activar entorno virtual e instalar dependencias
echo Activando entorno virtual e instalando dependencias...
call venv\\Scripts\\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if errorlevel 1 (
    echo Error: No se pudieron instalar las dependencias
    pause
    exit /b 1
)

REM Crear directorios necesarios
if not exist "logs" mkdir logs
if not exist "temp" mkdir temp

echo.
echo ========================================
echo Instalacion completada exitosamente!
echo ========================================
echo.
echo Para ejecutar el scanner:
echo   1. Ejecutar: run_scanner.bat
echo   2. O manualmente: venv\\Scripts\\python.exe src\\main.py
echo.
echo Para instalar como servicio:
echo   1. Ejecutar como administrador: install_service.bat
echo.
pause
"""
    
    def _create_run_script(self) -> str:
        """Crea el script para ejecutar el scanner"""
        return """@echo off
echo Iniciando PC Monitor Scanner Agent...

REM Verificar si existe el entorno virtual
if not exist "venv\\Scripts\\python.exe" (
    echo Error: Entorno virtual no encontrado
    echo Por favor ejecute install.bat primero
    pause
    exit /b 1
)

REM Verificar si existe la configuracion
if not exist "config.json" (
    echo Error: Archivo de configuracion no encontrado
    pause
    exit /b 1
)

REM Activar entorno virtual y ejecutar
call venv\\Scripts\\activate.bat
python src\\main.py %*

if errorlevel 1 (
    echo.
    echo El scanner termino con errores. Revise los logs en la carpeta 'logs'
    pause
)
"""
    
    def _create_service_script(self) -> str:
        """Crea el script para instalar como servicio de Windows"""
        return """@echo off
echo ========================================
echo Instalando PC Monitor Scanner como Servicio
echo ========================================

REM Verificar privilegios de administrador
net session >nul 2>&1
if errorlevel 1 (
    echo Error: Este script debe ejecutarse como Administrador
    echo Haga clic derecho y seleccione "Ejecutar como administrador"
    pause
    exit /b 1
)

REM Verificar si existe el entorno virtual
if not exist "venv\\Scripts\\python.exe" (
    echo Error: Entorno virtual no encontrado
    echo Por favor ejecute install.bat primero
    pause
    exit /b 1
)

set SERVICE_NAME=PCMonitorScanner
set CURRENT_DIR=%~dp0
set PYTHON_EXE=%CURRENT_DIR%venv\\Scripts\\python.exe
set SCRIPT_PATH=%CURRENT_DIR%src\\main.py

echo Instalando servicio: %SERVICE_NAME%
echo Directorio: %CURRENT_DIR%
echo Python: %PYTHON_EXE%
echo Script: %SCRIPT_PATH%

REM Crear el servicio usando sc
sc create "%SERVICE_NAME%" binPath= "\"%PYTHON_EXE%\" \"%SCRIPT_PATH%\" --service" start= auto DisplayName= "PC Monitor Scanner Agent"

if errorlevel 1 (
    echo Error: No se pudo crear el servicio
    pause
    exit /b 1
)

REM Configurar descripcion del servicio
sc description "%SERVICE_NAME%" "Agente de monitoreo de PC que recolecta datos del sistema y los envia al servidor central"

REM Iniciar el servicio
echo Iniciando servicio...
sc start "%SERVICE_NAME%"

echo.
echo ========================================
echo Servicio instalado exitosamente!
echo ========================================
echo.
echo Para gestionar el servicio:
echo   - Iniciar: sc start %SERVICE_NAME%
echo   - Detener: sc stop %SERVICE_NAME%
echo   - Desinstalar: sc delete %SERVICE_NAME%
echo.
echo O use el Administrador de Servicios de Windows (services.msc)
echo.
pause
"""
    
    def _create_build_script(self) -> str:
        """Crea el script para compilar el ejecutable"""
        return """@echo off
echo ========================================
echo Compilando PC Monitor Scanner a Ejecutable
echo ========================================

REM Verificar si Python está instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python no esta instalado
    pause
    exit /b 1
)

REM Instalar PyInstaller si no está instalado
echo Instalando PyInstaller...
pip install pyinstaller

REM Compilar el ejecutable
echo Compilando ejecutable...
pyinstaller scanner.spec

if errorlevel 1 (
    echo Error: No se pudo compilar el ejecutable
    pause
    exit /b 1
)

REM Copiar archivos necesarios al directorio dist
echo Copiando archivos de configuracion...
copy config.json dist\\scanner\\
if not exist "dist\\scanner\\logs" mkdir dist\\scanner\\logs

echo.
echo ========================================
echo Compilacion completada!
echo ========================================
echo.
echo El ejecutable se encuentra en: dist\\scanner\\scanner.exe
echo.
echo Para distribuir, copie toda la carpeta dist\\scanner\\
echo.
pause
"""
    
    def _create_pyinstaller_spec(self) -> str:
        """Crea el archivo .spec para PyInstaller"""
        return """# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config.json', '.'),
    ],
    hiddenimports=[
        'psutil',
        'requests',
        'pydantic',
        'wmi',
        'win32api',
        'win32con',
        'win32service',
        'win32serviceutil',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='scanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='scanner',
)
"""
    
    def _get_requirements(self) -> str:
        """Retorna las dependencias necesarias"""
        return """psutil==5.9.6
requests==2.31.0
pydantic==2.5.0
cryptography==41.0.7
pywin32==306
wmi==1.5.1
"""
    
    def _create_readme(self) -> str:
        """Crea el archivo README"""
        return """========================================
PC Monitor Scanner Agent
========================================

Este paquete contiene el agente de monitoreo de PC que recolecta datos del sistema
y los envía al servidor central para análisis.

INSTALACION:
-----------
1. Ejecute install.bat como Administrador
2. Espere a que se instalen todas las dependencias
3. La instalación creará un entorno virtual Python aislado

EJECUCION:
---------
- Ejecución única: run_scanner.bat
- Ejecución continua: run_scanner.bat --continuous
- Como servicio: install_service.bat (como Administrador)

ARCHIVOS IMPORTANTES:
-------------------
- config.json: Configuración del agente (NO MODIFICAR)
- logs/: Directorio donde se guardan los logs
- install.bat: Script de instalación
- run_scanner.bat: Script para ejecutar el scanner
- install_service.bat: Script para instalar como servicio

REQUISITOS:
----------
- Windows 7 o superior
- Python 3.8 o superior
- Conexión a Internet
- Permisos de administrador (para instalación)

SOPORTE:
-------
Para soporte técnico, contacte al administrador del sistema.

NOTA DE SEGURIDAD:
-----------------
Este software recolecta información del sistema para propósitos de monitoreo
y seguridad. Todos los datos son enviados de forma segura al servidor central.
"""
    
    def _create_executable_readme(self) -> str:
        """Crea el README para la versión ejecutable"""
        return """========================================
PC Monitor Scanner Agent - Versión Ejecutable
========================================

Este paquete contiene los archivos fuente para compilar el agente de monitoreo
como un ejecutable independiente.

COMPILACION:
-----------
1. Ejecute build_executable.bat
2. Espere a que se complete la compilación
3. El ejecutable estará en dist/scanner/

DISTRIBUCION:
------------
Para distribuir el agente:
1. Copie toda la carpeta dist/scanner/ a la máquina destino
2. Ejecute scanner.exe desde esa carpeta
3. El archivo config.json ya está incluido y configurado

VENTAJAS DEL EJECUTABLE:
-----------------------
- No requiere Python instalado en la máquina destino
- Instalación más simple para usuarios finales
- Menor superficie de ataque
- Mejor rendimiento

REQUISITOS PARA COMPILACION:
---------------------------
- Python 3.8 o superior
- PyInstaller
- Todas las dependencias listadas en requirements.txt

REQUISITOS PARA EJECUCION:
-------------------------
- Windows 7 o superior
- Conexión a Internet
- NO requiere Python instalado
"""
    
    def _create_basic_scanner(self) -> str:
        """Crea un scanner básico si no existe el código fuente"""
        return '''#!/usr/bin/env python3
"""
PC Monitor Scanner Agent - Versión básica
"""

import json
import time
import requests
import psutil
import platform
import socket
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

class BasicScanner:
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
        self.setup_logging()
        
    def setup_logging(self):
        """Configura el sistema de logging"""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        logging.basicConfig(
            level=getattr(logging, self.config.get("log_level", "INFO")),
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_dir / "scanner.log"),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def load_config(self, config_file):
        """Carga la configuración desde archivo JSON"""
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: No se encontró el archivo {config_file}")
            return {
                "manager_id": "unknown",
                "api_base_url": "http://localhost:8000/api/v1",
                "scan_interval_minutes": 60,
                "log_level": "INFO"
            }
    
    def get_system_fingerprint(self):
        """Genera un fingerprint único del sistema"""
        try:
            import uuid
            machine_id = str(uuid.getnode())
            hostname = socket.gethostname()
            platform_info = platform.platform()
            return str(hash(f"{machine_id}-{hostname}-{platform_info}"))
        except Exception:
            return f"{socket.gethostname()}-{int(datetime.now().timestamp())}"
    
    def collect_system_data(self):
        """Recolecta datos básicos del sistema"""
        try:
            # Información básica del sistema
            system_info = {
                "hostname": socket.gethostname(),
                "platform": platform.platform(),
                "architecture": platform.architecture()[0],
                "processor": platform.processor(),
                "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
            }
            
            # Información de CPU y memoria
            cpu_info = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "cpu_count": psutil.cpu_count(),
                "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}
            }
            
            memory_info = psutil.virtual_memory()._asdict()
            
            # Información de disco
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "fstype": partition.fstype,
                        "total": usage.total,
                        "used": usage.used,
                        "free": usage.free,
                        "percent": usage.percent
                    })
                except PermissionError:
                    continue
            
            # Procesos en ejecución (top 20)
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Ordenar por uso de CPU y tomar los primeros 20
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            processes = processes[:20]
            
            # Conexiones de red
            network_connections = []
            try:
                for conn in psutil.net_connections(kind='inet'):
                    if conn.status == 'LISTEN':
                        network_connections.append({
                            "local_address": conn.laddr.ip if conn.laddr else "",
                            "local_port": conn.laddr.port if conn.laddr else 0,
                            "status": conn.status,
                            "pid": conn.pid
                        })
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                pass
            
            return {
                "scan_id": f"scan_{int(datetime.now().timestamp())}",
                "manager_id": self.config["manager_id"],
                "machine_fingerprint": self.get_system_fingerprint(),
                "machine_name": socket.gethostname(),
                "timestamp": datetime.now().isoformat(),
                "scanner_version": "1.0.0",
                "system_info": system_info,
                "cpu_info": cpu_info,
                "memory_info": memory_info,
                "disk_info": disk_info,
                "processes": processes,
                "network_connections": network_connections[:50]  # Limitar conexiones
            }
            
        except Exception as e:
            self.logger.error(f"Error recolectando datos del sistema: {e}")
            return {
                "scan_id": f"scan_{int(datetime.now().timestamp())}",
                "manager_id": self.config["manager_id"],
                "machine_fingerprint": self.get_system_fingerprint(),
                "machine_name": socket.gethostname(),
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def send_data(self, data):
        """Envía datos al servidor API"""
        try:
            url = f"{self.config['api_base_url']}/scans"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "PC-Monitor-Scanner/1.0.0"
            }
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            self.logger.info(f"Datos enviados exitosamente: {response.status_code}")
            return True
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error enviando datos: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error inesperado enviando datos: {e}")
            return False
    
    def run_scan(self):
        """Ejecuta un escaneo completo"""
        self.logger.info("=== INICIANDO ESCANEO ===")
        start_time = time.time()
        
        try:
            data = self.collect_system_data()
            success = self.send_data(data)
            
            duration = time.time() - start_time
            self.logger.info(f"=== ESCANEO COMPLETADO EN {duration:.2f} segundos ===")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error durante el escaneo: {e}")
            return False
    
    def run_continuous(self):
        """Ejecuta escaneos continuos"""
        interval = self.config.get("scan_interval_minutes", 60) * 60
        self.logger.info(f"Iniciando modo continuo (intervalo: {interval/60} minutos)")
        
        while True:
            try:
                self.run_scan()
                self.logger.info(f"Esperando {interval/60} minutos hasta el próximo escaneo...")
                time.sleep(interval)
                
            except KeyboardInterrupt:
                self.logger.info("Deteniendo scanner por solicitud del usuario...")
                break
            except Exception as e:
                self.logger.error(f"Error en modo continuo: {e}")
                self.logger.info("Esperando 60 segundos antes de reintentar...")
                time.sleep(60)
    
    def run_as_service(self):
        """Ejecuta como servicio de Windows"""
        try:
            import win32serviceutil
            import win32service
            import win32event
            
            class ScannerService(win32serviceutil.ServiceFramework):
                _svc_name_ = "PCMonitorScanner"
                _svc_display_name_ = "PC Monitor Scanner Agent"
                _svc_description_ = "Agente de monitoreo de PC"
                
                def __init__(self, args):
                    win32serviceutil.ServiceFramework.__init__(self, args)
                    self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
                    self.scanner = BasicScanner()
                
                def SvcStop(self):
                    self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
                    win32event.SetEvent(self.hWaitStop)
                
                def SvcDoRun(self):
                    self.scanner.run_continuous()
            
            if len(sys.argv) == 1:
                win32serviceutil.HandleCommandLine(ScannerService)
            else:
                self.run_continuous()
                
        except ImportError:
            self.logger.warning("Módulos de servicio de Windows no disponibles, ejecutando en modo continuo")
            self.run_continuous()

if __name__ == "__main__":
    scanner = BasicScanner()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--continuous":
            scanner.run_continuous()
        elif sys.argv[1] == "--service":
            scanner.run_as_service()
        else:
            scanner.run_scan()
    else:
        scanner.run_scan()
'''
    
    def _generate_install_script(self) -> str:
        return """@echo off
echo ========================================
echo    PC Monitor Agent - Instalador
echo ========================================
echo.

REM Crear directorio de instalación
echo Creando directorio de instalación...
mkdir "C:\\Program Files\\PCMonitor" 2>nul

REM Copiar archivos
echo Copiando archivos...
copy /Y *.* "C:\\Program Files\\PCMonitor\\" >nul

REM Cambiar al directorio de instalación
cd "C:\\Program Files\\PCMonitor"

REM Verificar si existe el ejecutable
if exist "scanner.exe" (
    echo Ejecutable encontrado. Configurando servicio...
    
    REM Crear tarea programada para el ejecutable
    schtasks /create /tn "PCMonitorAgent" /tr "\\"C:\\Program Files\\PCMonitor\\scanner.exe\\"" /sc daily /st 09:00 /f >nul
    
    echo Agente instalado como ejecutable.
) else (
    echo Ejecutable no encontrado. Instalando dependencias Python...
    
    REM Instalar dependencias Python
    pip install -r requirements.txt >nul
    
    REM Crear tarea programada para Python
    schtasks /create /tn "PCMonitorAgent" /tr "python \\"C:\\Program Files\\PCMonitor\\main.py\\"" /sc daily /st 09:00 /f >nul
    
    echo Agente instalado con Python.
)

echo.
echo ========================================
echo    Instalación completada exitosamente
echo ========================================
echo.
echo El agente se ejecutará diariamente a las 9:00 AM.
echo Para ejecutar manualmente: schtasks /run /tn "PCMonitorAgent"
echo Para desinstalar: schtasks /delete /tn "PCMonitorAgent" /f
echo.
pause
"""