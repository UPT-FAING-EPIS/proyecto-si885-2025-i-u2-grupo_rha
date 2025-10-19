import asyncio
import logging
import psutil
from datetime import datetime
from typing import Dict, Any, List

class ProcessScanner:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def scan(self) -> Dict[str, Any]:
        self.logger.info("Iniciando escaneo de procesos")
        
        try:
            process_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'running_processes': await self._get_running_processes(),
                'system_processes': await self._get_system_processes(),
                'suspicious_processes': await self._get_suspicious_processes(),
                'resource_usage': await self._get_resource_usage(),
                'network_connections': await self._get_network_connections(),
                'services': await self._get_windows_services()
            }
            
            self.logger.info("Escaneo de procesos completado")
            return process_info
            
        except Exception as e:
            self.logger.error(f"Error durante el escaneo de procesos: {str(e)}")
            raise
    
    async def _get_running_processes(self) -> List[Dict[str, Any]]:
        processes = []
        
        try:
            for proc in psutil.process_iter([
                'pid', 'name', 'exe', 'cmdline', 'username', 'create_time',
                'cpu_percent', 'memory_percent', 'memory_info', 'status'
            ]):
                try:
                    proc_info = proc.info
                    
                    process_data = {
                        'pid': proc_info['pid'],
                        'name': proc_info['name'],
                        'exe': proc_info['exe'],
                        'cmdline': ' '.join(proc_info['cmdline']) if proc_info['cmdline'] else '',
                        'username': proc_info['username'],
                        'status': proc_info['status'],
                        'cpu_percent': proc_info['cpu_percent'],
                        'memory_percent': proc_info['memory_percent'],
                        'memory_mb': round(proc_info['memory_info'].rss / 1024 / 1024, 2) if proc_info['memory_info'] else 0,
                        'create_time': datetime.fromtimestamp(proc_info['create_time']).isoformat() if proc_info['create_time'] else None
                    }
                    
                    try:
                        parent = proc.parent()
                        if parent:
                            process_data['parent_pid'] = parent.pid
                            process_data['parent_name'] = parent.name()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    
                    try:
                        process_data['num_threads'] = proc.num_threads()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                    
                    processes.append(process_data)
                    
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
            
            return processes
            
        except Exception as e:
            self.logger.error(f"Error obteniendo procesos en ejecución: {str(e)}")
            return []
    
    async def _get_system_processes(self) -> List[Dict[str, Any]]:
        system_process_names = [
            'System', 'smss.exe', 'csrss.exe', 'wininit.exe', 'winlogon.exe',
            'services.exe', 'lsass.exe', 'svchost.exe', 'explorer.exe',
            'dwm.exe', 'taskhost.exe', 'spoolsv.exe'
        ]
        
        system_processes = []
        
        try:
            all_processes = await self._get_running_processes()
            
            for proc in all_processes:
                if proc['name'].lower() in [name.lower() for name in system_process_names]:
                    system_processes.append(proc)
            
            return system_processes
            
        except Exception as e:
            self.logger.error(f"Error obteniendo procesos del sistema: {str(e)}")
            return []
    
    async def _get_suspicious_processes(self) -> List[Dict[str, Any]]:
        suspicious_processes = []
        
        suspicious_criteria = {
            'high_cpu': 80.0,
            'high_memory': 50.0,
            'suspicious_names': [
                'cmd.exe', 'powershell.exe', 'wscript.exe', 'cscript.exe',
                'mshta.exe', 'rundll32.exe', 'regsvr32.exe', 'bitsadmin.exe'
            ],
            'suspicious_locations': [
                'temp', 'tmp', 'appdata\\local\\temp', 'windows\\temp'
            ]
        }
        
        try:
            all_processes = await self._get_running_processes()
            
            for proc in all_processes:
                suspicion_reasons = []
                
                if proc.get('cpu_percent', 0) > suspicious_criteria['high_cpu']:
                    suspicion_reasons.append(f"Alto uso de CPU: {proc['cpu_percent']}%")
                
                if proc.get('memory_percent', 0) > suspicious_criteria['high_memory']:
                    suspicion_reasons.append(f"Alto uso de memoria: {proc['memory_percent']}%")
                
                if proc['name'].lower() in suspicious_criteria['suspicious_names']:
                    suspicion_reasons.append(f"Proceso potencialmente peligroso: {proc['name']}")
                
                exe_path = proc.get('exe', '').lower()
                for location in suspicious_criteria['suspicious_locations']:
                    if location in exe_path:
                        suspicion_reasons.append(f"Ejecutándose desde ubicación sospechosa: {exe_path}")
                        break
                
                if not proc.get('exe') and proc['name'] not in ['System', '[System Process]']:
                    suspicion_reasons.append("Proceso sin ruta de ejecutable")
                
                if suspicion_reasons:
                    suspicious_process = proc.copy()
                    suspicious_process['suspicion_reasons'] = suspicion_reasons
                    suspicious_processes.append(suspicious_process)
            
            return suspicious_processes
            
        except Exception as e:
            self.logger.error(f"Error identificando procesos sospechosos: {str(e)}")
            return []
    
    async def _get_resource_usage(self) -> Dict[str, Any]:
        try:
            all_processes = await self._get_running_processes()
            
            top_cpu = sorted(all_processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)[:10]
            
            top_memory = sorted(all_processes, key=lambda x: x.get('memory_percent', 0), reverse=True)[:10]
            
            total_processes = len(all_processes)
            total_memory_mb = sum(proc.get('memory_mb', 0) for proc in all_processes)
            
            return {
                'total_processes': total_processes,
                'total_memory_usage_mb': round(total_memory_mb, 2),
                'top_cpu_processes': top_cpu,
                'top_memory_processes': top_memory
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de recursos: {str(e)}")
            return {}
    
    async def _get_network_connections(self) -> List[Dict[str, Any]]:
        connections = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    connection_info = {
                        'fd': conn.fd,
                        'family': conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                        'type': conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                        'local_address': f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else None,
                        'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                        'status': conn.status,
                        'pid': conn.pid
                    }
                    
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            connection_info['process_name'] = proc.name()
                            connection_info['process_exe'] = proc.exe()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    connections.append(connection_info)
                    
                except Exception as e:
                    self.logger.debug(f"Error procesando conexión: {str(e)}")
                    continue
            
            return connections
            
        except Exception as e:
            self.logger.error(f"Error obteniendo conexiones de red: {str(e)}")
            return []
    
    async def _get_windows_services(self) -> List[Dict[str, Any]]:
        services = []
        
        try:
            import subprocess
            
            result = subprocess.run([
                'sc', 'query', 'state=', 'all'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_service = {}
                
                for line in lines:
                    line = line.strip()
                    
                    if line.startswith('SERVICE_NAME:'):
                        if current_service:
                            services.append(current_service)
                        current_service = {
                            'name': line.split(':', 1)[1].strip()
                        }
                    elif line.startswith('DISPLAY_NAME:'):
                        current_service['display_name'] = line.split(':', 1)[1].strip()
                    elif line.startswith('STATE'):
                        state_info = line.split()
                        if len(state_info) >= 4:
                            current_service['state'] = state_info[3]
                
                if current_service:
                    services.append(current_service)
            
            return services
            
        except Exception as e:
            self.logger.error(f"Error obteniendo servicios de Windows: {str(e)}")
            return []