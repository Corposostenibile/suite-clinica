from __future__ import annotations

import os
from pathlib import Path
from typing import Final

from flask import Blueprint, send_from_directory, Response, jsonify, current_app

###############################################################################
# Percorsi statici                                                             #
###############################################################################

MODULE_DIR: Final[Path] = Path(__file__).resolve().parent
STATIC_DIR: Final[str] = str(MODULE_DIR / "static")
ICONS_DIR: Final[str] = os.path.join(STATIC_DIR, "icons")

###############################################################################
# Blueprint                                                                   #
###############################################################################

pwa_bp: Final[Blueprint] = Blueprint(
    "pwa",
    __name__,
    static_folder=STATIC_DIR,
    static_url_path="/static/pwa"
)

###############################################################################
# Routing                                                                     #
###############################################################################

@pwa_bp.route("/manifest.webmanifest")
def manifest():
    try:
        response = send_from_directory(
            os.path.join(pwa_bp.root_path, "static"),
            "manifest.webmanifest"
        )
        response.mimetype = "application/manifest+json"
        return response
    except Exception as e:
        current_app.logger.exception("Errore nel servire il manifest:")
        return jsonify(error="manifest error", detail=str(e)), 500


@pwa_bp.route("/service-worker.js")
def service_worker() -> Response:
    """Serve il service‑worker JS con intestazione *Service‑Worker‑Allowed*."""
    response = send_from_directory(
        os.path.join(pwa_bp.root_path, "static"),
        "service-worker.js"
    )
    response.mimetype = "application/javascript"
    response.headers["Service-Worker-Allowed"] = "/"
    return response


@pwa_bp.route("/icons/<path:filename>")
def icons(filename: str) -> Response:
    """Serve le icone del PWA (PNG quadrati di varie dimensioni)."""
    return send_from_directory(
        ICONS_DIR,
        filename,
        conditional=True
    )

__all__ = ["pwa_bp"]
