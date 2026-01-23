"""
Services module for SuiteMind PostgreSQL integration.

Due servizi separati e indipendenti:
1. PostgresSuitemindService: Chat generale su tutto il database
2. CasiPazientiService: Analisi rigida casi di successo pazienti
"""

from .postgres_suitemind_service import PostgresSuitemindService
from .casi_pazienti_service import CasiPazientiService, get_casi_pazienti_service

__all__ = [
    'PostgresSuitemindService',
    'CasiPazientiService',
    'get_casi_pazienti_service',
    'get_postgres_suitemind_service'
]

# Factory functions
def get_postgres_suitemind_service(sql_db=None):
    """
    Factory function per ottenere PostgresSuitemindService (chat generale).

    Args:
        sql_db: SQLDatabase con accesso a tutte le tabelle (158+)

    Returns:
        Istanza di PostgresSuitemindService con memoria conversazionale
    """
    return PostgresSuitemindService(sql_db=sql_db)