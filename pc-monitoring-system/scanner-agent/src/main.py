#!/usr/bin/env python3

import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, Any

sys.path.append(os.path.join(os.path.dirname(__file__)))

from core.config import Config
from core.api_client import APIClient
from core.scheduler import ScanScheduler
from utils.logger import setup_logger
from scanners import SystemScanner, SoftwareScanner, ProcessScanner, NetworkScanner

class ScannerAgent:
    
    def __init__(self, config_path: str = None):
        self.config = Config(config_path)
        self.logger = setup_logger(self.config)
        self.api_client = APIClient(self.config)
        self.scheduler = ScanScheduler(self.config)
        
        self.scanners = {}
        self._load_scanners()
    
    def _load_scanners(self):
        try:
            modules_config = self.config.get('scanning.modules', {})
            
            if modules_config.get('system', True):
                self.scanners['system'] = SystemScanner()
                self.logger.info("Scanner de sistema cargado")
            
            if modules_config.get('software', True):
                self.scanners['software'] = SoftwareScanner()
                self.logger.info("Scanner de software cargado")
            
            if modules_config.get('processes', True):
                self.scanners['processes'] = ProcessScanner()
                self.logger.info("Scanner de procesos cargado")
            
            if modules_config.get('network', True):
                self.scanners['network'] = NetworkScanner()
                self.logger.info("Scanner de red cargado")
            
            self.logger.info(f"Scanners cargados exitosamente: {list(self.scanners.keys())}")
            
        except Exception as e:
            self.logger.error(f"Error cargando scanners: {str(e)}")
    
    async def perform_scan(self):
        self.logger.info("Iniciando escaneo completo del sistema")
        
        scan_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'machine_id': self.config.machine_id,
            'manager_id': self.config.manager_id,
            'scan_type': 'full',
            'data': {}
        }
        
        try:
            for scanner_name, scanner in self.scanners.items():
                self.logger.info(f"Ejecutando scanner: {scanner_name}")
                scanner_data = await scanner.scan()
                scan_data['data'][scanner_name] = scanner_data
                self.logger.info(f"Scanner {scanner_name} completado")
            
            self.logger.info("Enviando datos a la API")
            response = await self.api_client.send_scan_data(scan_data)
            
            if response.get('success'):
                self.logger.info("Escaneo enviado exitosamente")
                
                if 'scan_token' in response:
                    self.logger.info(f"Token de visualización: {response['scan_token']}")
                    print(f"\n🔍 Escaneo completado!")
                    print(f"📊 Ver resultados en: {self.config.api_base_url}/scan-result/{response['scan_token']}")
            else:
                self.logger.error(f"Error al enviar escaneo: {response.get('error', 'Error desconocido')}")
                
        except Exception as e:
            self.logger.error(f"Error durante el escaneo: {str(e)}")
            raise
    
    async def check_for_tasks(self):
        try:
            task_info = await self.api_client.check_tasks()
            
            if task_info.get('should_scan'):
                self.logger.info("Tarea de escaneo solicitada por el servidor")
                await self.perform_scan()
            
            if 'config_updates' in task_info:
                self.config.update_from_server(task_info['config_updates'])
                self.logger.info("Configuración actualizada desde el servidor")
                
        except Exception as e:
            self.logger.error(f"Error al verificar tareas: {str(e)}")
    
    async def run_continuous(self):
        self.logger.info("Iniciando modo continuo")
        
        while True:
            try:
                await self.check_for_tasks()
                
                if self.scheduler.should_scan():
                    await self.perform_scan()
                    self.scheduler.mark_scan_completed()
                
                await asyncio.sleep(self.config.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Deteniendo agente por solicitud del usuario")
                break
            except Exception as e:
                self.logger.error(f"Error en el bucle principal: {str(e)}")
                await asyncio.sleep(60)
    
    async def run_single_scan(self):
        self.logger.info("Ejecutando escaneo único")
        await self.perform_scan()

async def main():
    agent = ScannerAgent()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--scan':
            await agent.run_single_scan()
        elif sys.argv[1] == '--daemon':
            await agent.run_continuous()
        elif sys.argv[1] == '--help':
            print("Scanner Agent - Sistema de Monitoreo de PCs")
            print("Uso:")
            print("  python main.py --scan     Ejecutar un solo escaneo")
            print("  python main.py --daemon   Ejecutar en modo continuo")
            print("  python main.py --help     Mostrar esta ayuda")
            return
        else:
            print(f"Argumento desconocido: {sys.argv[1]}")
            print("Use --help para ver las opciones disponibles")
            return
    else:
        await agent.run_single_scan()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAgente detenido por el usuario")
    except Exception as e:
        print(f"Error fatal: {str(e)}")
        sys.exit(1)