"""
Route per Marketing Automation: webhook Frame.io e OAuth Adobe per token.
"""

import secrets
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from flask import request, jsonify, current_app, redirect, session

from . import bp
from .security import require_frameio_webhook_signature
from .services import process_frameio_webhook_sync, send_to_airtable
from .claude_caption import generate_caption

# Endpoint OAuth 2.0 Adobe IMS (per Frame.io)
ADOBE_IMS_AUTHORIZE = "https://ims-na1.adobelogin.com/ims/authorize/v2"
ADOBE_IMS_TOKEN = "https://ims-na1.adobelogin.com/ims/token/v3"
# Scope per Frame.io (come configurato in Adobe Console)
ADOBE_OAUTH_SCOPES = "openid,profile,email,additional_info.roles,offline_access"


def _redirect_uri():
    """URI di callback OAuth: da config o derivato dalla request (ngrok)."""
    uri = current_app.config.get("FRAMEIO_OAUTH_REDIRECT_URI")
    if uri:
        return uri.rstrip("/")
    base = request.url_root.rstrip("/")
    return f"{base}/marketing-automation/oauth/callback"


@bp.route("/oauth/start", methods=["GET"])
def oauth_start():
    """
    Avvia il flusso OAuth: reindirizza l'utente ad Adobe per il login.
    Apri questo URL (tramite ngrok) per ottenere un token una tantum.
    """
    client_id = current_app.config.get("FRAMEIO_CLIENT_ID")
    if not client_id:
        return jsonify({"error": "FRAMEIO_CLIENT_ID non configurato"}), 500

    state = secrets.token_urlsafe(32)
    session["frameio_oauth_state"] = state

    params = {
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "scope": ADOBE_OAUTH_SCOPES,
        "response_type": "code",
        "state": state,
    }
    auth_url = f"{ADOBE_IMS_AUTHORIZE}?{urlencode(params)}"
    return redirect(auth_url)


@bp.route("/oauth/callback", methods=["GET"])
def oauth_callback():
    """
    Callback OAuth: riceve il code da Adobe, lo scambia con access_token (e refresh_token).
    Mostra il token sulla pagina (da copiare) e opzionalmente chiama Frame.io per account/workspace.
    """
    client_id = current_app.config.get("FRAMEIO_CLIENT_ID")
    client_secret = current_app.config.get("FRAMEIO_CLIENT_SECRET")
    if not client_id or not client_secret:
        return jsonify({"error": "Credenziali Frame.io non configurate"}), 500

    saved_state = session.pop("frameio_oauth_state", None)
    state = request.args.get("state")
    code = request.args.get("code")
    error = request.args.get("error")

    if error:
        current_app.logger.warning("[Marketing Automation] OAuth error: %s", error)
        return jsonify({"error": f"Adobe ha restituito: {error}"}), 400

    if not code:
        return jsonify({"error": "Manca il parametro code nella callback"}), 400

    if not state or state != saved_state:
        current_app.logger.warning("[Marketing Automation] OAuth state mismatch")
        return jsonify({"error": "State non valido, riprova da /marketing-automation/oauth/start"}), 400

    redirect_uri = _redirect_uri()
    body = urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
    }).encode("utf-8")

    req = Request(ADOBE_IMS_TOKEN, data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
    except HTTPError as e:
        body_err = e.read().decode("utf-8") if e.fp else ""
        current_app.logger.error(
            "[Marketing Automation] Token exchange failed: %s %s", e.code, body_err
        )
        return jsonify({"error": f"Scambio token fallito: {e.code}", "detail": body_err}), 400
    except URLError as e:
        current_app.logger.exception("[Marketing Automation] Token request error")
        return jsonify({"error": str(e.reason)}), 502

    import json as _json
    token_data = _json.loads(data)
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_in = token_data.get("expires_in")

    current_app.logger.info(
        "[Marketing Automation] Token ottenuto, expires_in=%s", expires_in
    )

    # Risposta HTML semplice con token da copiare
    html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="utf-8"><title>Frame.io token</title></head>
    <body style="font-family:sans-serif; max-width:800px; margin:2rem auto; padding:1rem;">
    <h1>Token Frame.io ottenuto</h1>
    <p>Usa questi valori per creare il webhook e per le chiamate API.</p>
    <h2>Access token</h2>
    <pre style="background:#eee; padding:1rem; overflow:auto;">{access_token or "(mancante)"}</pre>
    <h2>Refresh token</h2>
    <pre style="background:#eee; padding:1rem; overflow:auto;">{refresh_token or "(mancante)"}</pre>
    <p><small>Expires in: {expires_in} secondi</small></p>
    <p><a href="/marketing-automation/oauth/start">Rifai il login</a></p>
    </body></html>
    """
    from flask import Response
    return Response(html, mimetype="text/html; charset=utf-8")


@bp.route("/test-caption", methods=["GET"])
def test_caption():
    """
    Route di test per la generazione caption con Claude (solo in dev).
    Query: transcript=... (obbligatorio), name=... (opzionale).
    Abilitata solo se DEBUG=True o MARKETING_AUTOMATION_TEST_CAPTION=1.
    """
    if not current_app.debug and not current_app.config.get("MARKETING_AUTOMATION_TEST_CAPTION"):
        return jsonify({"error": "Route disabilitata"}), 404
    transcript = request.args.get("transcript", "").strip()
    name = request.args.get("name", "Video test")
    if not transcript:
        return jsonify({
            "error": "Parametro 'transcript' obbligatorio (es. ?transcript=testo trascrizione...)",
        }), 400
    context = {"name": name, "description": transcript, "view_url": ""}
    caption = generate_caption(context, current_app)
    if caption is None:
        return jsonify({"error": "Impossibile generare caption (verifica ANTHROPIC_API_KEY e log)"}), 502
    return jsonify({"caption": caption})


@bp.route("/webhook/frameio", methods=["POST"])
@require_frameio_webhook_signature
def webhook_frameio():
    """
    Riceve webhook Frame.io (file.updated o metadata.value.updated).
    Inoltra il payload a un task Celery che recupera i dettagli del file e, se approved, prepara per Poppy.
    """
    payload = request.get_json(silent=True) or {}
    event_type = payload.get("type", "")
    resource = payload.get("resource", {})

    current_app.logger.info(
        "[Marketing Automation] Webhook Frame.io ricevuto: type=%s resource_id=%s resource_type=%s",
        event_type,
        resource.get("id"),
        resource.get("type"),
    )
    current_app.logger.debug("[Marketing Automation] Payload completo: %s", payload)

    result = process_frameio_webhook_sync(payload, current_app)
    if result.get("approved") and result.get("context"):
        context = result["context"]
        caption = generate_caption(context, current_app)
        send_to_airtable(context, current_app, caption=caption)

    return jsonify({"ok": True, "received": event_type}), 200
