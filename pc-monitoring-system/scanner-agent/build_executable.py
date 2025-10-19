#!/usr/bin/env python3

import os
import sys
import shutil
import subprocess
import argparse
from pathlib import Path

def install_pyinstaller():
    try:
        import PyInstaller
        print("✓ PyInstaller ya está instalado")
        return True
    except ImportError:
        print("Instalando PyInstaller...")
        try:
            subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'pyinstaller'])
            print("✓ PyInstaller instalado correctamente")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Error instalando PyInstaller: {e}")
            return False

def create_spec_file():
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config/config.json', 'config'),
        ('README.md', '.'),
    ],
    hiddenimports=[
        'psutil',
        'requests',
        'aiohttp',
        'asyncio',
        'json',
        'logging',
        'datetime',
        'platform',
        'subprocess',
        'socket',
        'winreg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='ScannerAgent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico' if os.path.exists('icon.ico') else None,
)
'''
    
    with open('scanner_agent.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Archivo .spec creado")

def build_executable():
    print("Construyendo ejecutable...")
    
    try:
        if os.path.exists('build'):
            shutil.rmtree('build')
        if os.path.exists('dist'):
            shutil.rmtree('dist')
        
        subprocess.check_call([
            'pyinstaller',
            '--clean',
            '--noconfirm',
            'scanner_agent.spec'
        ])
        
        print("✓ Ejecutable creado exitosamente")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"✗ Error construyendo ejecutable: {e}")
        return False

def create_installer_package():
    print("Creando paquete de instalación...")
    
    package_dir = Path('package')
    if package_dir.exists():
        shutil.rmtree(package_dir)
    
    package_dir.mkdir()
    
    exe_path = Path('dist/ScannerAgent.exe')
    if exe_path.exists():
        shutil.copy2(exe_path, package_dir / 'ScannerAgent.exe')
    else:
        print("✗ No se encontró el ejecutable")
        return False
    
    shutil.copy2('config/config.json', package_dir / 'config.json')
    shutil.copy2('README.md', package_dir / 'README.md')
    
    install_script = '''@echo off
echo === Instalador del Scanner Agent ===
echo.

set /p API_URL="Ingrese la URL de la API (ej: http://localhost:8000): "
set /p MANAGER_ID="Ingrese el ID del Cliente-Gerente: "
set /p MACHINE_NAME="Ingrese el nombre de la máquina (opcional): "

echo.
echo Configurando scanner...

:: Crear directorio de logs
if not exist "logs" mkdir logs
if not exist "data" mkdir data

:: Actualizar configuración (simplificado)
echo Configuración completada.
echo.
echo Para ejecutar el scanner:
echo   ScannerAgent.exe --continuous
echo.
echo Presione cualquier tecla para continuar...
pause >nul
'''
    
    with open(package_dir / 'install.bat', 'w') as f:
        f.write(install_script)
    
    run_script = '''@echo off
echo Iniciando Scanner Agent...
ScannerAgent.exe --continuous
pause
'''
    
    with open(package_dir / 'run.bat', 'w') as f:
        f.write(run_script)
    
    print("✓ Paquete de instalación creado en 'package/'")
    return True

def create_zip_package():
    print("Creando archivo ZIP...")
    
    try:
        shutil.make_archive('ScannerAgent_Package', 'zip', 'package')
        print("✓ Archivo ZIP creado: ScannerAgent_Package.zip")
        return True
    except Exception as e:
        print(f"✗ Error creando ZIP: {e}")
        return False

def cleanup():
    print("Limpiando archivos temporales...")
    
    temp_files = ['scanner_agent.spec', 'build', 'dist']
    
    for item in temp_files:
        if os.path.exists(item):
            if os.path.isdir(item):
                shutil.rmtree(item)
            else:
                os.remove(item)
    
    print("✓ Limpieza completada")

def main():
    parser = argparse.ArgumentParser(description='Constructor de ejecutable del Scanner Agent')
    parser.add_argument('--no-cleanup', action='store_true', help='No limpiar archivos temporales')
    parser.add_argument('--no-zip', action='store_true', help='No crear archivo ZIP')
    parser.add_argument('--spec-only', action='store_true', help='Solo crear archivo .spec')
    
    args = parser.parse_args()
    
    print("=== Constructor de Ejecutable del Scanner Agent ===")
    print()
    
    if not os.path.exists('src/main.py'):
        print("✗ Error: Ejecutar desde el directorio raíz del scanner-agent")
        sys.exit(1)
    
    if not install_pyinstaller():
        sys.exit(1)
    
    create_spec_file()
    
    if args.spec_only:
        print("✓ Archivo .spec creado. Ejecute 'pyinstaller scanner_agent.spec' para construir.")
        sys.exit(0)
    
    if not build_executable():
        sys.exit(1)
    
    if not create_installer_package():
        sys.exit(1)
    
    if not args.no_zip:
        create_zip_package()
    
    if not args.no_cleanup:
        cleanup()
    
    print()
    print("✓ Proceso completado exitosamente!")
    print("📦 Paquete disponible en: package/")
    if not args.no_zip:
        print("📦 Archivo ZIP: ScannerAgent_Package.zip")
    print()
    print("Para distribuir:")
    print("1. Enviar ScannerAgent_Package.zip al cliente")
    print("2. El cliente debe extraer y ejecutar install.bat")
    print("3. Luego ejecutar run.bat para iniciar el scanner")

if __name__ == "__main__":
    main()