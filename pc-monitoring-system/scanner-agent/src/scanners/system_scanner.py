import asyncio
import logging
import os
import platform
import psutil
import socket
import uuid
from datetime import datetime
from typing import Dict, Any, List

class SystemScanner:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def scan(self) -> Dict[str, Any]:
        self.logger.info("Iniciando escaneo del sistema")
        
        try:
            system_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'basic_info': await self._get_basic_info(),
                'hardware': await self._get_hardware_info(),
                'network': await self._get_network_info(),
                'security': await self._get_security_info(),
                'performance': await self._get_performance_info()
            }
            
            self.logger.info("Escaneo del sistema completado")
            return system_info
            
        except Exception as e:
            self.logger.error(f"Error durante el escaneo del sistema: {str(e)}")
            raise
    
    async def _get_basic_info(self) -> Dict[str, Any]:
        try:
            return {
                'hostname': socket.gethostname(),
                'platform': platform.platform(),
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'architecture': platform.architecture(),
                'python_version': platform.python_version(),
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'uptime_seconds': int((datetime.now() - datetime.fromtimestamp(psutil.boot_time())).total_seconds()),
                'timezone': str(datetime.now().astimezone().tzinfo),
                'user': os.environ.get('USERNAME', 'Unknown'),
                'domain': os.environ.get('USERDOMAIN', 'Unknown')
            }
        except Exception as e:
            self.logger.error(f"Error obteniendo información básica: {str(e)}")
            return {'error': str(e)}
    
    async def _get_hardware_info(self) -> Dict[str, Any]:
        try:
            cpu_info = {
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'max_frequency': psutil.cpu_freq().max if psutil.cpu_freq() else None,
                'current_frequency': psutil.cpu_freq().current if psutil.cpu_freq() else None,
                'cpu_usage_percent': psutil.cpu_percent(interval=1)
            }
            
            memory = psutil.virtual_memory()
            memory_info = {
                'total_gb': round(memory.total / (1024**3), 2),
                'available_gb': round(memory.available / (1024**3), 2),
                'used_gb': round(memory.used / (1024**3), 2),
                'percentage': memory.percent
            }
            
            disk_info = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disk_info.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2),
                        'percentage': round((usage.used / usage.total) * 100, 2)
                    })
                except PermissionError:
                    continue
            
            return {
                'cpu': cpu_info,
                'memory': memory_info,
                'disks': disk_info
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de hardware: {str(e)}")
            return {'error': str(e)}
    
    async def _get_network_info(self) -> Dict[str, Any]:
        try:
            network_interfaces = []
            for interface, addresses in psutil.net_if_addrs().items():
                interface_info = {
                    'name': interface,
                    'addresses': []
                }
                
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        interface_info['addresses'].append({
                            'type': 'IPv4',
                            'address': addr.address,
                            'netmask': addr.netmask,
                            'broadcast': addr.broadcast
                        })
                    elif addr.family == socket.AF_INET6:
                        interface_info['addresses'].append({
                            'type': 'IPv6',
                            'address': addr.address,
                            'netmask': addr.netmask
                        })
                
                if interface_info['addresses']:
                    network_interfaces.append(interface_info)
            
            net_io = psutil.net_io_counters()
            network_stats = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            }
            
            return {
                'interfaces': network_interfaces,
                'statistics': network_stats,
                'hostname': socket.gethostname(),
                'fqdn': socket.getfqdn()
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de red: {str(e)}")
            return {'error': str(e)}
    
    async def _get_security_info(self) -> Dict[str, Any]:
        try:
            security_info = {
                'is_admin': self._is_admin(),
                'firewall_enabled': await self._check_firewall(),
                'antivirus_info': await self._get_antivirus_info(),
                'windows_defender': await self._check_windows_defender(),
                'auto_updates': await self._check_auto_updates()
            }
            
            return security_info
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de seguridad: {str(e)}")
            return {'error': str(e)}
    
    async def _get_performance_info(self) -> Dict[str, Any]:
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    proc_info = proc.info
                    if proc_info['cpu_percent'] > 1.0 or proc_info['memory_percent'] > 1.0:
                        processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            processes.sort(key=lambda x: x['cpu_percent'], reverse=True)
            top_processes = processes[:10]
            
            return {
                'load_average': os.getloadavg() if hasattr(os, 'getloadavg') else None,
                'cpu_times': psutil.cpu_times()._asdict(),
                'top_processes': top_processes,
                'process_count': len(psutil.pids())
            }
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de rendimiento: {str(e)}")
            return {'error': str(e)}
    
    def _is_admin(self) -> bool:
        try:
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        except:
            return False
    
    async def _check_firewall(self) -> Dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run(
                ['netsh', 'advfirewall', 'show', 'allprofiles', 'state'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                output = result.stdout
                return {
                    'enabled': 'ON' in output,
                    'details': output
                }
            else:
                return {'enabled': None, 'error': 'No se pudo verificar'}
                
        except Exception as e:
            return {'enabled': None, 'error': str(e)}
    
    async def _get_antivirus_info(self) -> Dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run([
                'wmic', '/namespace:\\\\root\\SecurityCenter2', 'path', 'AntiVirusProduct',
                'get', 'displayName,productState', '/format:csv'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                antivirus_list = []
                
                for line in lines[1:]:
                    if line.strip():
                        parts = line.split(',')
                        if len(parts) >= 3:
                            antivirus_list.append({
                                'name': parts[1].strip(),
                                'state': parts[2].strip()
                            })
                
                return {'installed': antivirus_list}
            else:
                return {'installed': [], 'error': 'No se pudo verificar'}
                
        except Exception as e:
            return {'installed': [], 'error': str(e)}
    
    async def _check_windows_defender(self) -> Dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run([
                'powershell', '-Command', 'Get-MpComputerStatus | Select-Object AntivirusEnabled,RealTimeProtectionEnabled,BehaviorMonitorEnabled'
            ], capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0:
                output = result.stdout
                return {
                    'enabled': 'True' in output,
                    'details': output.strip()
                }
            else:
                return {'enabled': None, 'error': 'No se pudo verificar'}
                
        except Exception as e:
            return {'enabled': None, 'error': str(e)}
    
    async def _check_auto_updates(self) -> Dict[str, Any]:
        try:
            import subprocess
            result = subprocess.run([
                'reg', 'query', 'HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\WindowsUpdate\\Auto Update',
                '/v', 'AUOptions'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                output = result.stdout
                if 'AUOptions' in output:
                    return {'enabled': True, 'details': output.strip()}
                else:
                    return {'enabled': False, 'details': 'No configurado'}
            else:
                return {'enabled': None, 'error': 'No se pudo verificar'}
                
        except Exception as e:
            return {'enabled': None, 'error': str(e)}