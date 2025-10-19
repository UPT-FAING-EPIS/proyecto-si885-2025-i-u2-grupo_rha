import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional

class APIClient:
    
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(
                timeout=timeout,
                headers=self.config.get_headers()
            )
        return self.session
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        url = f"{self.config.api_base_url}{endpoint}"
        
        try:
            session = await self._get_session()
            
            kwargs = {}
            if data:
                kwargs['json'] = data
            
            async with session.request(method, url, **kwargs) as response:
                response_text = await response.text()
                
                if response.status == 200:
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {'success': True, 'data': response_text}
                else:
                    self.logger.error(f"Error HTTP {response.status}: {response_text}")
                    return {
                        'success': False,
                        'error': f"HTTP {response.status}: {response_text}",
                        'status_code': response.status
                    }
                    
        except aiohttp.ClientError as e:
            self.logger.error(f"Error de conexión: {str(e)}")
            return {
                'success': False,
                'error': f"Error de conexión: {str(e)}"
            }
        except Exception as e:
            self.logger.error(f"Error inesperado: {str(e)}")
            return {
                'success': False,
                'error': f"Error inesperado: {str(e)}"
            }
    
    async def send_scan_data(self, scan_data: Dict[str, Any]) -> Dict[str, Any]:
        self.logger.info("Enviando datos de escaneo al servidor")
        
        scan_data.update({
            'manager_id': self.config.manager_id,
            'machine_id': self.config.machine_id,
            'machine_name': self.config.machine_name
        })
        
        response = await self._make_request('POST', '/scans', scan_data)
        
        if response.get('success'):
            self.logger.info("Datos de escaneo enviados exitosamente")
        else:
            self.logger.error(f"Error al enviar datos: {response.get('error')}")
        
        return response
    
    async def check_tasks(self) -> Dict[str, Any]:
        self.logger.debug("Verificando tareas pendientes")
        
        response = await self._make_request('GET', '/agent/check-task')
        
        if response.get('success'):
            self.logger.debug("Verificación de tareas completada")
        else:
            self.logger.warning(f"Error al verificar tareas: {response.get('error')}")
        
        return response
    
    async def register_machine(self) -> Dict[str, Any]:
        self.logger.info("Registrando máquina en el servidor")
        
        machine_data = {
            'machine_id': self.config.machine_id,
            'machine_name': self.config.machine_name,
            'manager_id': self.config.manager_id
        }
        
        response = await self._make_request('POST', '/machines/register', machine_data)
        
        if response.get('success'):
            self.logger.info("Máquina registrada exitosamente")
        else:
            self.logger.error(f"Error al registrar máquina: {response.get('error')}")
        
        return response
    
    async def get_scan_result_url(self, scan_token: str) -> str:
        return f"{self.config.api_base_url}/agent/scan-result/{scan_token}"
    
    async def test_connection(self) -> bool:
        self.logger.info("Probando conexión con el servidor")
        
        try:
            response = await self._make_request('GET', '/agent/check-task')
            
            if response.get('success') or response.get('status_code') == 401:
                self.logger.info("Conexión con el servidor exitosa")
                return True
            else:
                self.logger.error("No se pudo conectar con el servidor")
                return False
                
        except Exception as e:
            self.logger.error(f"Error al probar conexión: {str(e)}")
            return False
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
            self.logger.debug("Sesión HTTP cerrada")
    
    def __del__(self):
        if hasattr(self, 'session') and self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.session.close())
                else:
                    loop.run_until_complete(self.session.close())
            except:
                pass