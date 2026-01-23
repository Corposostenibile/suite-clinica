"""
customers.models
================

Sub-package per i modelli SQLAlchemy *scoped* al dominio **customers**.

Espone pubblicamente le classi ORM così che:

* SQLAlchemy possa importarle tramite ``import customers.models``  
* Alembic / Flask-Migrate le rilevino in *env.py* ed includano le relative
  tabelle durante l’autogenerazione delle migrazioni.

Modelli inclusi
---------------
* **ActivityLog** – changelog granulare *field-level* per le modifiche a
  :class:`corposostenibile.models.Cliente`
"""
from __future__ import annotations

from .activity_log import ActivityLog

__all__: list[str] = ["ActivityLog"]
