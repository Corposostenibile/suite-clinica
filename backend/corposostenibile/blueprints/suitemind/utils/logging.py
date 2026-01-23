"""
Centralized logging configuration for SuiteMind blueprint.
Provides a consistent logging setup across all SuiteMind services.
"""

import logging
import sys
from typing import Optional


def get_suitemind_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Ottiene un logger configurato per SuiteMind.
    
    Args:
        name: Nome del logger (solitamente __name__ del modulo chiamante)
        level: Livello di logging (default: INFO)
        
    Returns:
        Logger configurato per SuiteMind
    """
    # Crea il logger con il prefisso suitemind
    logger_name = f"suitemind.{name.split('.')[-1]}" if '.' in name else f"suitemind.{name}"
    logger = logging.getLogger(logger_name)
    
    # Solo se il logger non ha già handler configurati
    if not logger.handlers:
        # Crea un handler che scrive su stdout per compatibilità Docker
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        # Formato del log ottimizzato per SuiteMind
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Aggiungi l'handler al logger
        logger.addHandler(handler)
        logger.setLevel(level)
        
        # Evita la propagazione per prevenire log duplicati
        logger.propagate = False
    
    return logger


def configure_suitemind_logging(level: int = logging.INFO) -> None:
    """
    Configura il logging globale per tutto il modulo SuiteMind.
    
    Args:
        level: Livello di logging da applicare a tutti i logger SuiteMind
    """
    # Configura il logger root di suitemind
    root_logger = logging.getLogger('suitemind')
    
    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(level)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s in %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        root_logger.addHandler(handler)
        root_logger.setLevel(level)
        root_logger.propagate = False


def set_suitemind_log_level(level: int) -> None:
    """
    Imposta il livello di logging per tutti i logger SuiteMind esistenti.
    
    Args:
        level: Nuovo livello di logging
    """
    # Aggiorna il logger root
    root_logger = logging.getLogger('suitemind')
    root_logger.setLevel(level)
    
    # Aggiorna tutti gli handler
    for handler in root_logger.handlers:
        handler.setLevel(level)
    
    # Aggiorna tutti i logger figli
    for logger_name in logging.Logger.manager.loggerDict:
        if logger_name.startswith('suitemind.'):
            logger = logging.getLogger(logger_name)
            logger.setLevel(level)
            for handler in logger.handlers:
                handler.setLevel(level)