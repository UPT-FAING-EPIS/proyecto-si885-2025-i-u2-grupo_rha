import asyncio
import logging
import subprocess
import winreg
from datetime import datetime
from typing import Dict, Any, List, Optional

class SoftwareScanner:
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def scan(self) -> Dict[str, Any]:
        self.logger.info("Iniciando escaneo de software")
        
        try:
            software_info = {
                'timestamp': datetime.utcnow().isoformat(),
                'installed_programs': await self._get_installed_programs(),
                'windows_features': await self._get_windows_features(),
                'startup_programs': await self._get_startup_programs(),
                'browser_info': await self._get_browser_info(),
                'office_info': await self._get_office_info(),
                'development_tools': await self._get_development_tools(),
                'security_software': await self._get_security_software()
            }
            
            self.logger.info("Escaneo de software completado")
            return software_info
            
        except Exception as e:
            self.logger.error(f"Error durante el escaneo de software: {str(e)}")
            raise
    
    async def _get_installed_programs(self) -> List[Dict[str, Any]]:
        programs = []
        
        try:
            registry_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall")
            ]
            
            for hkey, path in registry_paths:
                try:
                    programs.extend(await self._scan_registry_path(hkey, path))
                except Exception as e:
                    self.logger.warning(f"Error escaneando {path}: {str(e)}")
            
            unique_programs = {}
            for program in programs:
                name = program.get('name', '').lower()
                if name and name not in unique_programs:
                    unique_programs[name] = program
            
            return list(unique_programs.values())
            
        except Exception as e:
            self.logger.error(f"Error obteniendo programas instalados: {str(e)}")
            return []
    
    async def _scan_registry_path(self, hkey: int, path: str) -> List[Dict[str, Any]]:
        programs = []
        
        try:
            with winreg.OpenKey(hkey, path) as key:
                i = 0
                while True:
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        program_info = await self._get_program_info(hkey, f"{path}\\{subkey_name}")
                        
                        if program_info and program_info.get('name'):
                            programs.append(program_info)
                        
                        i += 1
                    except OSError:
                        break
                        
        except Exception as e:
            self.logger.warning(f"Error accediendo a {path}: {str(e)}")
        
        return programs
    
    async def _get_program_info(self, hkey: int, path: str) -> Optional[Dict[str, Any]]:
        try:
            with winreg.OpenKey(hkey, path) as key:
                program_info = {}
                
                fields = {
                    'DisplayName': 'name',
                    'DisplayVersion': 'version',
                    'Publisher': 'publisher',
                    'InstallDate': 'install_date',
                    'EstimatedSize': 'size_kb',
                    'InstallLocation': 'install_location',
                    'UninstallString': 'uninstall_string'
                }
                
                for reg_field, info_field in fields.items():
                    try:
                        value, _ = winreg.QueryValueEx(key, reg_field)
                        program_info[info_field] = value
                    except FileNotFoundError:
                        continue
                
                if program_info.get('name'):
                    if 'install_date' in program_info:
                        try:
                            date_str = str(program_info['install_date'])
                            if len(date_str) == 8:
                                formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
                                program_info['install_date'] = formatted_date
                        except:
                            pass
                    
                    return program_info
                
        except Exception as e:
            self.logger.debug(f"Error obteniendo info de programa en {path}: {str(e)}")
        
        return None
    
    async def _get_windows_features(self) -> List[Dict[str, Any]]:
        try:
            result = subprocess.run([
                'dism', '/online', '/get-features', '/format:table'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                features = []
                lines = result.stdout.split('\n')
                
                for line in lines:
                    if '|' in line and 'Enabled' in line:
                        parts = [part.strip() for part in line.split('|')]
                        if len(parts) >= 2:
                            features.append({
                                'name': parts[0],
                                'state': parts[1]
                            })
                
                return features
            else:
                return []
                
        except Exception as e:
            self.logger.warning(f"Error obteniendo características de Windows: {str(e)}")
            return []
    
    async def _get_startup_programs(self) -> List[Dict[str, Any]]:
        startup_programs = []
        
        try:
            startup_paths = [
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce"),
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce")
            ]
            
            for hkey, path in startup_paths:
                try:
                    with winreg.OpenKey(hkey, path) as key:
                        i = 0
                        while True:
                            try:
                                name, value, _ = winreg.EnumValue(key, i)
                                startup_programs.append({
                                    'name': name,
                                    'command': value,
                                    'location': 'HKLM' if hkey == winreg.HKEY_LOCAL_MACHINE else 'HKCU'
                                })
                                i += 1
                            except OSError:
                                break
                except Exception as e:
                    self.logger.debug(f"Error accediendo a {path}: {str(e)}")
            
            return startup_programs
            
        except Exception as e:
            self.logger.error(f"Error obteniendo programas de inicio: {str(e)}")
            return []
    
    async def _get_browser_info(self) -> Dict[str, Any]:
        browsers = {}
        
        browser_paths = {
            'Chrome': r"SOFTWARE\\Google\\Chrome\\BLBeacon",
            'Firefox': r"SOFTWARE\\Mozilla\\Mozilla Firefox",
            'Edge': r"SOFTWARE\\Microsoft\\Edge\\BLBeacon",
            'Internet Explorer': r"SOFTWARE\\Microsoft\\Internet Explorer"
        }
        
        for browser_name, path in browser_paths.items():
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                    try:
                        version, _ = winreg.QueryValueEx(key, "version")
                        browsers[browser_name] = {'version': version, 'installed': True}
                    except FileNotFoundError:
                        browsers[browser_name] = {'installed': True, 'version': 'Unknown'}
            except FileNotFoundError:
                browsers[browser_name] = {'installed': False}
            except Exception as e:
                self.logger.debug(f"Error verificando {browser_name}: {str(e)}")
        
        return browsers
    
    async def _get_office_info(self) -> Dict[str, Any]:
        office_info = {}
        
        try:
            office_paths = [
                r"SOFTWARE\\Microsoft\\Office",
                r"SOFTWARE\\WOW6432Node\\Microsoft\\Office"
            ]
            
            for path in office_paths:
                try:
                    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
                        i = 0
                        while True:
                            try:
                                version_key = winreg.EnumKey(key, i)
                                if version_key.replace('.', '').isdigit():
                                    office_info[f"Office_{version_key}"] = {
                                        'version': version_key,
                                        'installed': True
                                    }
                                i += 1
                            except OSError:
                                break
                except FileNotFoundError:
                    continue
            
            return office_info
            
        except Exception as e:
            self.logger.error(f"Error obteniendo información de Office: {str(e)}")
            return {}
    
    async def _get_development_tools(self) -> List[Dict[str, Any]]:
        dev_tools = []
        
        tools_to_check = [
            'Visual Studio', 'Visual Studio Code', 'Git', 'Python', 'Node.js',
            'Java', 'Docker', 'VirtualBox', 'VMware', 'IntelliJ IDEA',
            'Eclipse', 'Android Studio', 'Xcode'
        ]
        
        try:
            installed_programs = await self._get_installed_programs()
            
            for tool in tools_to_check:
                for program in installed_programs:
                    program_name = program.get('name', '').lower()
                    if tool.lower() in program_name:
                        dev_tools.append({
                            'name': tool,
                            'full_name': program.get('name'),
                            'version': program.get('version'),
                            'publisher': program.get('publisher')
                        })
                        break
            
            return dev_tools
            
        except Exception as e:
            self.logger.error(f"Error obteniendo herramientas de desarrollo: {str(e)}")
            return []
    
    async def _get_security_software(self) -> List[Dict[str, Any]]:
        security_software = []
        
        security_keywords = [
            'antivirus', 'firewall', 'malware', 'security', 'defender',
            'kaspersky', 'norton', 'mcafee', 'avast', 'avg', 'bitdefender',
            'trend micro', 'eset', 'sophos', 'symantec'
        ]
        
        try:
            installed_programs = await self._get_installed_programs()
            
            for program in installed_programs:
                program_name = program.get('name', '').lower()
                program_publisher = program.get('publisher', '').lower()
                
                for keyword in security_keywords:
                    if keyword in program_name or keyword in program_publisher:
                        security_software.append({
                            'name': program.get('name'),
                            'version': program.get('version'),
                            'publisher': program.get('publisher'),
                            'type': 'security'
                        })
                        break
            
            return security_software
            
        except Exception as e:
            self.logger.error(f"Error obteniendo software de seguridad: {str(e)}")
            return []