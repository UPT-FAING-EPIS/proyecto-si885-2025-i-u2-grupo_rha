import logging
import logging.handlers
import os
from pathlib import Path
from typing import Optional

def setup_logger(config=None) -> logging.Logger:
    
    log_level = getattr(config, 'log_level', 'INFO') if config else 'INFO'
    max_log_size_mb = getattr(config, 'max_log_size_mb', 10) if config else 10
    max_log_files = getattr(config, 'max_log_files', 5) if config else 5
    
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "scanner_agent.log"
    
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_log_size_mb * 1024 * 1024,
        backupCount=max_log_files,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    logger.addHandler(console_handler)
    
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    
    logger.info("Sistema de logging configurado")
    logger.info(f"Nivel de log: {log_level}")
    logger.info(f"Archivo de log: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)