"""
customers.signals
=================

Registry dei *domain signals* relativi al feature-package **customers**.

I servizi di ``customers.services`` possono emettere questi segnali per
informare altri componenti dell’applicazione (audit-log, notifiche,
integrazioni di terze parti…), evitando dipendenze circolari.

Segnali pubblici
----------------
* ``customer_created``  – emesso subito dopo la commit di creazione
* ``customer_updated``  – emesso dopo un update **significativo**
* ``customer_deleted``  – emesso al termine di soft- o hard-delete

Il **sender** è sempre l’istanza di :class:`corposostenibile.models.Cliente`;
gli extra-kwargs possono includere ``user_id``, ``actor_id``, ``changed`` ecc.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from flask import current_app

# --------------------------------------------------------------------------- #
#  Blinker – opzionale                                                        #
# --------------------------------------------------------------------------- #
try:
    from blinker import Namespace
except ModuleNotFoundError:  # pragma: no cover – Blinker non installato
    # Fallback minimale: oggetti no-op compatibili con .send/.connect
    class _DummySignal:                                            # noqa: D401
        def send(self, *_a, **_kw):                                 # type: ignore[no-self-use]
            return []

        def connect(self, *_a, **_kw):                              # type: ignore[no-self-use]
            return None

    class _DummyNamespace:                                         # noqa: D401
        def signal(self, _name: str):                              # type: ignore[no-self-use]
            return _DummySignal()

    Namespace = _DummyNamespace  # type: ignore[assignment]

# --------------------------------------------------------------------------- #
#  Namespace & segnali                                                        #
# --------------------------------------------------------------------------- #
_signals = Namespace()             # reale o dummy

customer_created = _signals.signal("customer-created")
customer_updated = _signals.signal("customer-updated")
customer_deleted = _signals.signal("customer-deleted")

__all__ = [
    # segnali grezzi
    "customer_created",
    "customer_updated",
    "customer_deleted",
    # helper sintattici
    "emit_created",
    "emit_updated",
    "emit_deleted",
]

# --------------------------------------------------------------------------- #
#  Helper di emissione (uso rapido in services.py)                            #
# --------------------------------------------------------------------------- #
def emit_created(cliente, **extra: Dict[str, Any]) -> None:        # noqa: D401
    """Emetti ``customer_created``."""
    customer_created.send(cliente, **extra)


def emit_updated(cliente, **extra: Dict[str, Any]) -> None:        # noqa: D401
    """Emetti ``customer_updated``."""
    customer_updated.send(cliente, **extra)


def emit_deleted(cliente, **extra: Dict[str, Any]) -> None:        # noqa: D401
    """Emetti ``customer_deleted``."""
    customer_deleted.send(cliente, **extra)


# --------------------------------------------------------------------------- #
#  WebSocket bridge → /ws/customers                                           #
# --------------------------------------------------------------------------- #
try:
    # broadcast_customer_updated() è definita in customers.sockets
    from .sockets import broadcast_customer_updated
except Exception:                             # pragma: no cover – dip. mancante
    broadcast_customer_updated = None         # type: ignore[assignment]


def _on_customer_updated(sender, **extra) -> None:                  # noqa: D401
    """
    Listener interno: inoltra l’evento ``customer_updated`` a TUTTI i client
    WebSocket collegati a ``/ws/customers`` attraverso
    :func:`broadcast_customer_updated`.
    """
    if broadcast_customer_updated is None:        # WS layer non disponibile
        return

    try:
        user_id: Optional[int] = extra.get("user_id") or extra.get("actor_id")
        broadcast_customer_updated(
            cliente_id=getattr(sender, "cliente_id", None),
            user_id=user_id,
        )
    except Exception:                             # pragma: no cover
        current_app.logger.exception("broadcast_customer_updated failed")


# Registrazione listener (solo se Blinker reale)
customer_updated.connect(_on_customer_updated)     # type: ignore[arg-type]
