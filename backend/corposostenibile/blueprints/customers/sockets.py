"""
customers.sockets
=================

Endpoint **WebSocket** per l’evento *customer_updated*.

* URL: ``/ws/customers``  
* Protocollo: JSON **text frames** con schema:

    ```json
    {
      "event": "customer_updated",
      "clienteId": 123,
      "userId": 17,              // facoltativo (None se system)
      "ts": "2025-05-21T14:33:07Z"
    }
    ```

Il client (es. sul dettaglio cliente) stabilisce la connessione e rimane in
ascolto; ogni volta che un record *Cliente* viene creato / aggiornato /
ripristinato, **signals.py** invoca :pyfunc:`broadcast_customer_updated`
che spinge il payload a **tutti** i peer ancora collegati.

Dipendenze
----------
* Flask-Sock ≥ 0.5 (`pip install flask-sock`)
* ``sock`` inizializzato in :pymod:`corposostenibile.extensions`
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from typing import Set

from flask import current_app
from flask_sock import Server as SockServer, Sock  # type: ignore

from corposostenibile.extensions import sock  # istanza globale creata in extensions.py

__all__ = ["broadcast_customer_updated"]

# ----------------------------------------------------------------------------
# Gestione connessioni                                                         #
# ----------------------------------------------------------------------------
_clients: Set[SockServer] = set()
_lock = threading.Lock()


@sock.route("/ws/customers")
def _customers_ws(ws: SockServer) -> None:  # pragma: no cover
    """
    Mantiene aperto il canale WebSocket “fire-hose” per gli eventi clienti.

    Args:
        ws (SockServer): Parametro `ws` della route

    Returns:
        Risposta HTTP per `metodo configurato in route` su `/ws/customers` in formato JSON/response Flask.
    """
    with _lock:
        _clients.add(ws)
    current_app.logger.debug("[WS] /ws/customers connected. Peers=%s", len(_clients))

    try:
        while True:  # keep-alive
            msg = ws.receive()
            if msg is None:  # client chiuso
                break
            # eventuali ping/echo – opzionale
            if msg == "ping":
                ws.send("pong")
    except Exception as exc:  # pragma: no cover
        current_app.logger.debug("[WS] exception: %s", exc)
    finally:
        with _lock:
            _clients.discard(ws)
        current_app.logger.debug("[WS] /ws/customers disconnected. Peers=%s", len(_clients))


# ----------------------------------------------------------------------------
# Broadcast helper                                                            #
# ----------------------------------------------------------------------------
def _safe_send(peer: SockServer, text: str) -> bool:
    """Ritorna **True** se l’invio è andato a buon fine, altrimenti chiude peer."""
    try:
        peer.send(text)
        return True
    except Exception:  # client morto / errore rete
        try:
            peer.close()  # type: ignore[attr-defined]
        finally:
            return False


def broadcast_customer_updated(
    *,
    cliente_id: int,
    user_id: int | None = None,
    ts: datetime | None = None,
) -> None:
    """
    Invia a **tutti** i client collegati un evento ``customer_updated``.
    Può essere importato e usato dai signal/servizi di dominio.

    Parameters
    ----------
    cliente_id:
        ID del cliente coinvolto.
    user_id:
        Utente che ha effettuato la modifica (``None`` se sistema).
    ts:
        Timestamp dell’evento; se omesso, UTC *now*.
    """
    payload = json.dumps(
        {
            "event": "customer_updated",
            "clienteId": cliente_id,
            "userId": user_id,
            "ts": (ts or datetime.now(timezone.utc)).isoformat(),
        }
    )

    stale: list[SockServer] = []
    with _lock:
        for peer in _clients:
            if not _safe_send(peer, payload):
                stale.append(peer)
        # rimuovi connessioni morte
        for dead in stale:
            _clients.discard(dead)

    current_app.logger.debug(
        "[WS] broadcast customer_updated(%s) to %d peer(s)",
        cliente_id,
        len(_clients),
    )
