#!/usr/bin/env python3

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

def install_dependencies():
    print("Instalando dependencias...")
    
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'
        ])
        print("✓ Dependencias instaladas correctamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error instalando dependencias: {e}")
        return False

def create_directories():
    directories = ['logs', 'data']
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"Directorio '{directory}' creado")

def configure_scanner(api_url, manager_id, machine_name=None):
    config_path = Path('config/config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        config['api']['base_url'] = api_url
        config['machine']['manager_id'] = manager_id
        
        if machine_name:
            config['machine']['name'] = machine_name
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        
        print("✓ Configuración actualizada")
        return True
        
    except Exception as e:
        print(f"✗ Error configurando scanner: {e}")
        return False

def create_service_script():
    script_content = '''@echo off
cd /d "%~dp0"
python src/main.py --continuous
pause
'''
    
    with open('run_scanner.bat', 'w') as f:
        f.write(script_content)
    
    print("✓ Script de servicio creado (run_scanner.bat)")

def test_installation(api_url):
    print("\nProbando instalación...")
    
    try:
        sys.path.append('src')
        from main import ScannerAgent
        
        scanner = ScannerAgent()
        print("✓ Scanner inicializado correctamente")
        
        return True
        
    except Exception as e:
        print(f"✗ Error en la prueba: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Instalador del Scanner Agent')
    parser.add_argument('--api-url', required=True, help='URL de la API (ej: http://localhost:8000)')
    parser.add_argument('--manager-id', required=True, help='ID del Cliente-Gerente')
    parser.add_argument('--machine-name', help='Nombre de la máquina (opcional)')
    parser.add_argument('--skip-deps', action='store_true', help='Omitir instalación de dependencias')
    parser.add_argument('--test-only', action='store_true', help='Solo probar la instalación')
    
    args = parser.parse_args()
    
    print("=== Instalador del Scanner Agent ===")
    print(f"API URL: {args.api_url}")
    print(f"Manager ID: {args.manager_id}")
    print(f"Machine Name: {args.machine_name or 'Auto-detectar'}")
    print()
    
    if args.test_only:
        success = test_installation(args.api_url)
        sys.exit(0 if success else 1)
    
    create_directories()
    
    if not args.skip_deps:
        if not install_dependencies():
            print("Error en la instalación de dependencias")
            sys.exit(1)
    
    if not configure_scanner(args.api_url, args.manager_id, args.machine_name):
        print("Error en la configuración")
        sys.exit(1)
    
    create_service_script()
    
    if test_installation(args.api_url):
        print("\n✓ Instalación completada exitosamente!")
        print("\nPara ejecutar el scanner:")
        print("  - Modo continuo: python src/main.py --continuous")
        print("  - Escaneo único: python src/main.py --single")
        print("  - Usar script: run_scanner.bat")
    else:
        print("\n✗ La instalación falló en las pruebas")
        sys.exit(1)

if __name__ == "__main__":
    main()