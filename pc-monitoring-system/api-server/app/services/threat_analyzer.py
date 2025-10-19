from typing import List, Dict, Any
from datetime import datetime

from ..models import Threat

class ThreatAnalyzer:
    def __init__(self):
        self.suspicious_ports = [1337, 31337, 4444, 5555, 6666, 7777, 8888, 9999]
        self.malicious_processes = [
            "netcat", "nc", "mimikatz", "psexec", "wce", "fgdump",
            "pwdump", "gsecdump", "cachedump", "lsadump"
        ]
        self.dangerous_extensions = [
            ".exe.pdf", ".pdf.exe", ".doc.exe", ".jpg.exe", 
            ".png.exe", ".txt.exe", ".scr", ".pif", ".bat.exe"
        ]
    
    def analyze_scan_data(self, machine_id: str, scan_data: Dict[str, Any]) -> List[Threat]:
        threats = []
        
        # Analizar puertos abiertos
        threats.extend(self._analyze_open_ports(machine_id, scan_data.get("security_scan", {}).get("open_ports", [])))
        
        # Analizar cuentas de usuario
        threats.extend(self._analyze_user_accounts(machine_id, scan_data.get("security_scan", {}).get("user_accounts", [])))
        
        # Analizar archivo hosts
        threats.extend(self._analyze_hosts_file(machine_id, scan_data.get("security_scan", {}).get("hosts_file", {})))
        
        # Analizar eventos de seguridad
        threats.extend(self._analyze_security_events(machine_id, scan_data.get("security_scan", {}).get("security_events", [])))
        
        # Analizar archivos recientes
        threats.extend(self._analyze_recent_files(machine_id, scan_data.get("activity_scan", {}).get("recent_files", [])))
        
        # Analizar tareas programadas
        threats.extend(self._analyze_scheduled_tasks(machine_id, scan_data.get("system_health", {}).get("scheduled_tasks", [])))
        
        # Analizar variables de entorno
        threats.extend(self._analyze_environment_variables(machine_id, scan_data.get("system_health", {}).get("environment_variables", {})))
        
        return threats
    
    def _analyze_open_ports(self, machine_id: str, open_ports: List[Dict]) -> List[Threat]:
        threats = []
        for port_info in open_ports:
            port = port_info.get("port")
            process_name = port_info.get("process_name", "").lower()
            
            if port in self.suspicious_ports:
                threats.append(Threat(
                    machine_id=machine_id,
                    threat_type="PUERTO_SOSPECHOSO",
                    description=f"Puerto sospechoso {port} abierto por {process_name}",
                    evidence=port_info,
                    detected_at=datetime.utcnow()
                ))
            
            if any(malware in process_name for malware in self.malicious_processes):
                threats.append(Threat(
                    machine_id=machine_id,
                    threat_type="PROCESO_MALICIOSO",
                    description=f"Proceso potencialmente malicioso detectado: {process_name}",
                    evidence=port_info,
                    detected_at=datetime.utcnow()
                ))
        
        return threats
    
    def _analyze_user_accounts(self, machine_id: str, user_accounts: List[Dict]) -> List[Threat]:
        threats = []
        admin_count = sum(1 for user in user_accounts if user.get("is_admin", False))
        
        if admin_count > 3:
            threats.append(Threat(
                machine_id=machine_id,
                threat_type="EXCESO_ADMINISTRADORES",
                description=f"Demasiadas cuentas de administrador detectadas: {admin_count}",
                evidence={"admin_count": admin_count, "users": user_accounts},
                detected_at=datetime.utcnow()
            ))
        
        for user in user_accounts:
            if not user.get("password_required", True):
                threats.append(Threat(
                    machine_id=machine_id,
                    threat_type="CUENTA_SIN_PASSWORD",
                    description=f"Cuenta sin contraseña: {user.get('username')}",
                    evidence=user,
                    detected_at=datetime.utcnow()
                ))
        
        return threats
    
    def _analyze_hosts_file(self, machine_id: str, hosts_data: Dict) -> List[Threat]:
        threats = []
        suspicious_entries = hosts_data.get("suspicious_entries", [])
        
        for entry in suspicious_entries:
            threats.append(Threat(
                machine_id=machine_id,
                threat_type="HOSTS_MODIFICADO",
                description=f"Entrada sospechosa en archivo hosts: {entry}",
                evidence=hosts_data,
                detected_at=datetime.utcnow()
            ))
        
        return threats
    
    def _analyze_security_events(self, machine_id: str, security_events: List[Dict]) -> List[Threat]:
        threats = []
        failed_logins = [event for event in security_events if event.get("event_id") == 4625]
        
        if len(failed_logins) > 10:
            threats.append(Threat(
                machine_id=machine_id,
                threat_type="MULTIPLES_INTENTOS_LOGIN",
                description=f"Múltiples intentos de login fallidos detectados: {len(failed_logins)}",
                evidence={"failed_login_count": len(failed_logins), "events": failed_logins[:5]},
                detected_at=datetime.utcnow()
            ))
        
        return threats
    
    def _analyze_recent_files(self, machine_id: str, recent_files: List[Dict]) -> List[Threat]:
        threats = []
        
        for file_info in recent_files:
            file_name = file_info.get("name", "").lower()
            
            if any(ext in file_name for ext in self.dangerous_extensions):
                threats.append(Threat(
                    machine_id=machine_id,
                    threat_type="ARCHIVO_SOSPECHOSO",
                    description=f"Archivo con extensión sospechosa: {file_name}",
                    evidence=file_info,
                    detected_at=datetime.utcnow()
                ))
        
        return threats
    
    def _analyze_scheduled_tasks(self, machine_id: str, scheduled_tasks: List[Dict]) -> List[Threat]:
        threats = []
        
        for task in scheduled_tasks:
            task_name = task.get("name", "").lower()
            command = task.get("command", "").lower()
            
            if any(malware in command for malware in self.malicious_processes):
                threats.append(Threat(
                    machine_id=machine_id,
                    threat_type="TAREA_MALICIOSA",
                    description=f"Tarea programada sospechosa: {task_name}",
                    evidence=task,
                    detected_at=datetime.utcnow()
                ))
        
        return threats
    
    def _analyze_environment_variables(self, machine_id: str, env_vars: Dict) -> List[Threat]:
        threats = []
        path_var = env_vars.get("PATH", "")
        
        suspicious_paths = [
            "temp", "tmp", "appdata\\local\\temp", "programdata"
        ]
        
        for suspicious_path in suspicious_paths:
            if suspicious_path in path_var.lower():
                threats.append(Threat(
                    machine_id=machine_id,
                    threat_type="PATH_MODIFICADO",
                    description=f"PATH contiene ruta sospechosa: {suspicious_path}",
                    evidence={"path": path_var, "suspicious_path": suspicious_path},
                    detected_at=datetime.utcnow()
                ))
        
        return threats