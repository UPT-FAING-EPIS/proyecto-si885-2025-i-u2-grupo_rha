import asyncio
import logging
import psutil
import socket
import subprocess
from datetime import datetime
from typing import Dict, Any, List

class NetworkScanner:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def scan(self) -> Dict[str, Any]:
        self.logger.info("Iniciando escaneo de red")
        
        try:
            network_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'interfaces': await self._get_network_interfaces(),
                'connections': await self._get_active_connections(),
                'listening_ports': await self._get_listening_ports(),
                'routing_table': await self._get_routing_table(),
                'dns_config': await self._get_dns_configuration(),
                'firewall_status': await self._get_firewall_status(),
                'wifi_networks': await self._get_wifi_networks(),
                'network_shares': await self._get_network_shares(),
                'network_statistics': await self._get_network_statistics()
            }
            
            self.logger.info("Escaneo de red completado")
            return network_info
            
        except Exception as e:
            self.logger.error(f"Error durante el escaneo de red: {str(e)}")
            raise
    
    async def _get_network_interfaces(self) -> List[Dict[str, Any]]:
        interfaces = []
        
        try:
            net_if_stats = psutil.net_if_stats()
            net_if_addrs = psutil.net_if_addrs()
            
            for interface_name, addresses in net_if_addrs.items():
                interface_info = {
                    'name': interface_name,
                    'addresses': [],
                    'is_up': False,
                    'duplex': None,
                    'speed': None,
                    'mtu': None
                }
                
                if interface_name in net_if_stats:
                    stats = net_if_stats[interface_name]
                    interface_info.update({
                        'is_up': stats.isup,
                        'duplex': stats.duplex.name if hasattr(stats.duplex, 'name') else str(stats.duplex),
                        'speed': stats.speed,
                        'mtu': stats.mtu
                    })
                
                for addr in addresses:
                    addr_info = {
                        'family': addr.family.name if hasattr(addr.family, 'name') else str(addr.family),
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'broadcast': addr.broadcast
                    }
                    interface_info['addresses'].append(addr_info)
                
                interfaces.append(interface_info)
            
            return interfaces
            
        except Exception as e:
            self.logger.error(f"Error obteniendo interfaces de red: {str(e)}")
            return []
    
    async def _get_active_connections(self) -> List[Dict[str, Any]]:
        connections = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                try:
                    connection_info = {
                        'family': conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                        'type': conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                        'local_address': None,
                        'remote_address': None,
                        'status': conn.status,
                        'pid': conn.pid,
                        'process_name': None
                    }
                    
                    if conn.laddr:
                        connection_info['local_address'] = f"{conn.laddr.ip}:{conn.laddr.port}"
                    
                    if conn.raddr:
                        connection_info['remote_address'] = f"{conn.raddr.ip}:{conn.raddr.port}"
                    
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            connection_info['process_name'] = proc.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    connections.append(connection_info)
                    
                except Exception as e:
                    self.logger.debug(f"Error procesando conexión: {str(e)}")
                    continue
            
            return connections
            
        except Exception as e:
            self.logger.error(f"Error obteniendo conexiones activas: {str(e)}")
            return []
    
    async def _get_listening_ports(self) -> List[Dict[str, Any]]:
        listening_ports = []
        
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == psutil.CONN_LISTEN and conn.laddr:
                    port_info = {
                        'port': conn.laddr.port,
                        'address': conn.laddr.ip,
                        'family': conn.family.name if hasattr(conn.family, 'name') else str(conn.family),
                        'type': conn.type.name if hasattr(conn.type, 'name') else str(conn.type),
                        'pid': conn.pid,
                        'process_name': None
                    }
                    
                    if conn.pid:
                        try:
                            proc = psutil.Process(conn.pid)
                            port_info['process_name'] = proc.name()
                        except (psutil.NoSuchProcess, psutil.AccessDenied):
                            pass
                    
                    listening_ports.append(port_info)
            
            return listening_ports
            
        except Exception as e:
            self.logger.error(f"Error obteniendo puertos en escucha: {str(e)}")
            return []
    
    async def _get_routing_table(self) -> List[Dict[str, Any]]:
        routes = []
        
        try:
            result = subprocess.run([
                'route', 'print'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_routes_section = False
                
                for line in lines:
                    line = line.strip()
                    
                    if 'IPv4 Route Table' in line:
                        in_routes_section = True
                        continue
                    
                    if in_routes_section and line and not line.startswith('='):
                        parts = line.split()
                        if len(parts) >= 5:
                            route_info = {
                                'destination': parts[0],
                                'netmask': parts[1],
                                'gateway': parts[2],
                                'interface': parts[3],
                                'metric': parts[4] if len(parts) > 4 else None
                            }
                            routes.append(route_info)
            
            return routes
            
        except Exception as e:
            self.logger.error(f"Error obteniendo tabla de enrutamiento: {str(e)}")
            return []
    
    async def _get_dns_configuration(self) -> Dict[str, Any]:
        dns_config = {}
        
        try:
            result = subprocess.run([
                'nslookup', 'localhost'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'Server:' in line:
                        dns_config['primary_dns'] = line.split(':')[1].strip()
                    elif 'Address:' in line and '#53' in line:
                        dns_config['primary_dns_address'] = line.split(':')[1].replace('#53', '').strip()
            
            result = subprocess.run([
                'ipconfig', '/all'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                dns_servers = []
                lines = result.stdout.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if 'DNS Servers' in line:
                        if ':' in line:
                            dns_server = line.split(':')[1].strip()
                            if dns_server:
                                dns_servers.append(dns_server)
                    elif line and '.' in line and len(line.split('.')) == 4:
                        try:
                            socket.inet_aton(line)
                            dns_servers.append(line)
                        except socket.error:
                            pass
                
                dns_config['dns_servers'] = dns_servers
            
            return dns_config
            
        except Exception as e:
            self.logger.error(f"Error obteniendo configuración DNS: {str(e)}")
            return {}
    
    async def _get_firewall_status(self) -> Dict[str, Any]:
        firewall_status = {}
        
        try:
            result = subprocess.run([
                'netsh', 'advfirewall', 'show', 'allprofiles', 'state'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                current_profile = None
                
                for line in lines:
                    line = line.strip()
                    
                    if 'Profile' in line and 'Settings' in line:
                        current_profile = line.replace('Profile Settings:', '').strip()
                    elif 'State' in line and current_profile:
                        state = line.split()[-1] if line.split() else 'Unknown'
                        firewall_status[current_profile.lower()] = state
            
            return firewall_status
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estado del firewall: {str(e)}")
            return {}
    
    async def _get_wifi_networks(self) -> List[Dict[str, Any]]:
        wifi_networks = []
        
        try:
            result = subprocess.run([
                'netsh', 'wlan', 'show', 'profiles'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                for line in lines:
                    if 'All User Profile' in line:
                        profile_name = line.split(':')[1].strip()
                        
                        detail_result = subprocess.run([
                            'netsh', 'wlan', 'show', 'profile', profile_name, 'key=clear'
                        ], capture_output=True, text=True, timeout=10)
                        
                        if detail_result.returncode == 0:
                            detail_lines = detail_result.stdout.split('\n')
                            network_info = {'name': profile_name}
                            
                            for detail_line in detail_lines:
                                detail_line = detail_line.strip()
                                if 'Authentication' in detail_line:
                                    network_info['authentication'] = detail_line.split(':')[1].strip()
                                elif 'Cipher' in detail_line:
                                    network_info['cipher'] = detail_line.split(':')[1].strip()
                                elif 'Key Content' in detail_line:
                                    network_info['has_saved_password'] = True
                            
                            wifi_networks.append(network_info)
            
            return wifi_networks
            
        except Exception as e:
            self.logger.error(f"Error obteniendo redes WiFi: {str(e)}")
            return []
    
    async def _get_network_shares(self) -> List[Dict[str, Any]]:
        shares = []
        
        try:
            result = subprocess.run([
                'net', 'share'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                for line in lines:
                    line = line.strip()
                    if line and not line.startswith('-') and not 'Share name' in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            share_info = {
                                'name': parts[0],
                                'resource': ' '.join(parts[1:]) if len(parts) > 1 else ''
                            }
                            shares.append(share_info)
            
            return shares
            
        except Exception as e:
            self.logger.error(f"Error obteniendo recursos compartidos: {str(e)}")
            return []
    
    async def _get_network_statistics(self) -> Dict[str, Any]:
        try:
            net_io = psutil.net_io_counters()
            
            statistics = {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            }
            
            return statistics
            
        except Exception as e:
            self.logger.error(f"Error obteniendo estadísticas de red: {str(e)}")
            return {}