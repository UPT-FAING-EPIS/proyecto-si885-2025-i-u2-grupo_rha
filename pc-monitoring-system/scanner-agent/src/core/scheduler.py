import logging
from datetime import datetime, timedelta
from typing import Optional

class ScanScheduler:
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.last_scan_time: Optional[datetime] = None
        self.next_scan_time: Optional[datetime] = None
        self._calculate_next_scan()
    
    def _calculate_next_scan(self):
        if self.last_scan_time is None:
            self.next_scan_time = datetime.now()
        else:
            interval = timedelta(minutes=self.config.scan_interval_minutes)
            self.next_scan_time = self.last_scan_time + interval
        
        self.logger.debug(f"Próximo escaneo programado para: {self.next_scan_time}")
    
    def should_scan(self) -> bool:
        if self.next_scan_time is None:
            return True
        
        now = datetime.now()
        should_scan = now >= self.next_scan_time
        
        if should_scan:
            self.logger.info("Es hora de realizar un escaneo programado")
        
        return should_scan
    
    def mark_scan_completed(self):
        self.last_scan_time = datetime.now()
        self._calculate_next_scan()
        
        self.logger.info(f"Escaneo completado. Próximo escaneo: {self.next_scan_time}")
    
    def force_next_scan(self):
        self.next_scan_time = datetime.now()
        self.logger.info("Escaneo forzado para ejecución inmediata")
    
    def get_time_until_next_scan(self) -> timedelta:
        if self.next_scan_time is None:
            return timedelta(0)
        
        now = datetime.now()
        if now >= self.next_scan_time:
            return timedelta(0)
        
        return self.next_scan_time - now
    
    def get_next_scan_info(self) -> dict:
        time_until = self.get_time_until_next_scan()
        
        return {
            'next_scan_time': self.next_scan_time.isoformat() if self.next_scan_time else None,
            'last_scan_time': self.last_scan_time.isoformat() if self.last_scan_time else None,
            'time_until_next_scan_seconds': int(time_until.total_seconds()),
            'scan_interval_minutes': self.config.scan_interval_minutes,
            'should_scan_now': self.should_scan()
        }
    
    def update_interval(self, new_interval_minutes: int):
        old_interval = self.config.scan_interval_minutes
        self.config.scan_interval_minutes = new_interval_minutes
        
        self._calculate_next_scan()
        
        self.logger.info(f"Intervalo de escaneo actualizado de {old_interval} a {new_interval_minutes} minutos")
    
    def get_status(self) -> str:
        if self.next_scan_time is None:
            return "No programado"
        
        time_until = self.get_time_until_next_scan()
        
        if time_until.total_seconds() <= 0:
            return "Listo para escanear"
        
        hours, remainder = divmod(int(time_until.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        
        if hours > 0:
            return f"Próximo escaneo en {hours}h {minutes}m"
        elif minutes > 0:
            return f"Próximo escaneo en {minutes}m {seconds}s"
        else:
            return f"Próximo escaneo en {seconds}s"