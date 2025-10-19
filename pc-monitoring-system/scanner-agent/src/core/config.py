import json
import os
import uuid
from pathlib import Path
from typing import Dict, Any

class Config:
    
    def __init__(self):
        self.config_file = self._get_config_file_path()
        self.load_config()
    
    def _get_config_file_path(self) -> Path:
        base_dir = Path(__file__).parent.parent.parent
        
        config_paths = [
            base_dir / "config.json",
            base_dir / "config" / "config.json"
        ]
        
        for path in config_paths:
            if path.exists():
                return path
        
        return config_paths[0]
    
    def load_config(self):
        default_config = {
            "api_base_url": "http://localhost:8000/api/v1",
            "manager_id": "",
            "machine_id": str(uuid.uuid4()),
            "machine_name": os.environ.get('COMPUTERNAME', 'Unknown'),
            "scan_interval_minutes": 60,
            "check_interval": 300,
            "auto_start": False,
            "log_level": "INFO",
            "max_log_size_mb": 10,
            "max_log_files": 5
        }
        
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_config = json.load(f)
                    default_config.update(file_config)
            except Exception as e:
                print(f"Error al cargar configuración: {e}")
                print("Usando configuración por defecto")
        
        self.api_base_url = default_config["api_base_url"]
        self.manager_id = default_config["manager_id"]
        self.machine_id = default_config["machine_id"]
        self.machine_name = default_config["machine_name"]
        self.scan_interval_minutes = default_config["scan_interval_minutes"]
        self.check_interval = default_config["check_interval"]
        self.auto_start = default_config["auto_start"]
        self.log_level = default_config["log_level"]
        self.max_log_size_mb = default_config["max_log_size_mb"]
        self.max_log_files = default_config["max_log_files"]
        
        if not self.manager_id:
            raise ValueError("manager_id no está configurado. El agente debe ser configurado por un Cliente-Gerente.")
    
    def save_config(self):
        config_data = {
            "api_base_url": self.api_base_url,
            "manager_id": self.manager_id,
            "machine_id": self.machine_id,
            "machine_name": self.machine_name,
            "scan_interval_minutes": self.scan_interval_minutes,
            "check_interval": self.check_interval,
            "auto_start": self.auto_start,
            "log_level": self.log_level,
            "max_log_size_mb": self.max_log_size_mb,
            "max_log_files": self.max_log_files
        }
        
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error al guardar configuración: {e}")
    
    def update_from_server(self, server_config: Dict[str, Any]):
        updated = False
        
        if 'scan_interval_minutes' in server_config:
            if self.scan_interval_minutes != server_config['scan_interval_minutes']:
                self.scan_interval_minutes = server_config['scan_interval_minutes']
                updated = True
        
        if 'check_interval' in server_config:
            if self.check_interval != server_config['check_interval']:
                self.check_interval = server_config['check_interval']
                updated = True
        
        if updated:
            self.save_config()
    
    def get_headers(self) -> Dict[str, str]:
        return {
            'Content-Type': 'application/json',
            'User-Agent': f'ScannerAgent/1.0 (Machine: {self.machine_name})',
            'X-Manager-ID': self.manager_id,
            'X-Machine-ID': self.machine_id
        }
    
    def is_configured(self) -> bool:
        return bool(self.manager_id and self.api_base_url)
    
    def __str__(self) -> str:
        return f"Config(api={self.api_base_url}, manager={self.manager_id[:8]}..., machine={self.machine_name})"