"""
Logica sincrona per Marketing Automation: webhook Frame.io → GET file → preparazione per Poppy.
Eseguita nella richiesta HTTP (senza Celery).
Supporta: Developer Token (API v2, da developer.frame.io) oppure Access Token OAuth (API v4).
"""

import json
from typing import Any, Dict, Tuple
from urllib.parse import quote

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

FRAMEIO_API_V2 = "https://api.frame.io/v2"
FRAMEIO_API_V4 = "https://api.frame.io/v4"


def _headers(token: str) -> list:
    return [
        ("Authorization", f"Bearer {token}"),
        ("Accept", "application/json"),
        ("User-Agent", "SuiteClinica-MarketingAutomation/1.0"),
    ]


def _fetch_file_metadata_v4(
    account_id: str, file_id: str, token: str, app
) -> Dict[str, Any]:
    """
    Recupera i metadati del file (campi custom: Transcript, Notes, ecc.) via API v4.
    Restituisce un dict field_definition_name -> value (solo valori stringa).
    """
    url = f"{FRAMEIO_API_V4}/accounts/{account_id}/files/{file_id}/metadata"
    req = Request(url, method="GET")
    for k, v in _headers(token):
        req.add_header(k, v)
    req.add_header("api-version", "experimental")
    result = {}
    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        app.logger.warning(
            "[Marketing Automation] GET metadata Frame.io v4 fallito: %s %s",
            e.code,
            body[:300],
        )
        return result
    except URLError:
        app.logger.debug("[Marketing Automation] Errore richiesta metadata Frame.io")
        return result
    try:
        raw = json.loads(data)
        wrap = raw.get("data", raw) if isinstance(raw, dict) else raw
        meta_list = wrap.get("metadata") if isinstance(wrap, dict) else []
        if not isinstance(meta_list, list):
            app.logger.info("[Marketing Automation] Metadati Frame.io: risposta senza lista metadata")
            return result
        names_with_type = []
        for field in meta_list:
            if not isinstance(field, dict):
                continue
            name = field.get("field_definition_name")
            val = field.get("value")
            ftype = field.get("field_type", "")
            if name:
                names_with_type.append(f"{name}({type(val).__name__})")
            if name and val is not None:
                if isinstance(val, str) and val.strip():
                    result[name] = val.strip()
                elif isinstance(val, list) and val and isinstance(val[0], dict) and val[0].get("display_name"):
                    result[name] = (" ".join(str(x.get("display_name", "")) for x in val)).strip()
                elif isinstance(val, list) and all(isinstance(x, str) for x in val):
                    result[name] = " ".join(val).strip()
        app.logger.info(
            "[Marketing Automation] Metadati Frame.io: %s campi -> %s",
            len(meta_list),
            names_with_type or "(nessun nome)",
        )
    except (json.JSONDecodeError, TypeError) as e:
        app.logger.debug("[Marketing Automation] Parse metadata fallito: %s", e)
    return result


def _fetch_subtitles_text_v2(file_id: str, token: str, app) -> str:
    """
    Prova a recuperare il testo della trascrizione via API v2 (sottotitoli).
    GET /v2/assets/{id}/subtitles restituisce URL di tracce; scarica la prima e estrae il testo (SRT/VTT).
    Restituisce stringa vuota se non disponibile (es. asset solo v4, 404).
    """
    url = f"{FRAMEIO_API_V2}/assets/{file_id}/subtitles"
    req = Request(url, method="GET")
    for k, v in _headers(token):
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=10) as resp:
            data = resp.read().decode("utf-8")
    except HTTPError as e:
        if e.code == 404:
            app.logger.debug("[Marketing Automation] Sottotitoli v2: 404 (asset solo v4 o nessuna traccia)")
        return ""
    except URLError:
        return ""
    try:
        raw = json.loads(data)
        tracks = raw.get("subtitle_tracks") or []
        if not tracks or not isinstance(tracks[0], str):
            return ""
        track_url = tracks[0]
        tr_req = Request(track_url, method="GET")
        tr_req.add_header("Authorization", f"Bearer {token}")
        with urlopen(tr_req, timeout=15) as tr:
            content = tr.read().decode("utf-8", errors="replace")
    except Exception:
        return ""
    # SRT: blocchi numerici + timestamp; righe di testo tra blocchi. VTT: simile. Estrai righe che non sono solo numeri/timestamp.
    lines = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():
            continue
        if "-->" in line or line.startswith("WEBVTT") or (len(line) == 8 and ":" in line and line.count(":") == 2):
            continue
        lines.append(line)
    return " ".join(lines).strip() if lines else ""


def _fetch_asset_v2(file_id: str, token: str, app) -> Tuple[dict, None] | Tuple[None, dict]:
    """Usa API v2 (Developer Token): GET /v2/assets/{id}. Restituisce (file_data, None) o (None, error)."""
    url = f"{FRAMEIO_API_V2}/assets/{file_id}"
    req = Request(url, method="GET")
    for k, v in _headers(token):
        req.add_header(k, v)
    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        return None, {"code": e.code, "body": body[:500]}
    except URLError as e:
        app.logger.exception("[Marketing Automation] Errore richiesta Frame.io v2")
        return None, {"code": 0, "body": str(e)}
    raw = json.loads(data)
    # v2 restituisce l'asset direttamente (nome, label, type, properties)
    return (raw, None)


def process_frameio_webhook_sync(payload: Dict[str, Any], app) -> Dict[str, Any]:
    """
    Riceve il payload del webhook Frame.io.
    Recupera i dettagli del file (v2 o v4), legge nome/descrizione/label; se approved, restituisce contesto per Poppy.
    """
    logger = app.logger
    resource = payload.get("resource", {})
    file_id = resource.get("id")
    resource_type = resource.get("type", "")
    account_id = payload.get("account", {}).get("id")

    if not file_id or resource_type != "file":
        logger.warning(
            "[Marketing Automation] Payload senza file id o resource non file: %s",
            payload,
        )
        return {"success": False, "reason": "no_file_id"}

    dev_token = app.config.get("FRAMEIO_DEVELOPER_TOKEN")
    access_token = app.config.get("FRAMEIO_ACCESS_TOKEN")

    # Prova prima v2 (Developer Token) se impostato
    if dev_token:
        file_data, err = _fetch_asset_v2(file_id, dev_token, app)
        if not err:
            name = file_data.get("name") or ""
            label = file_data.get("label") or ""
            description = (file_data.get("properties") or {}).get("description") or ""
            logger.info(
                "[Marketing Automation] File Frame.io (v2): name=%s label=%s description_len=%s",
                name, label, len(description),
            )
            logger.debug("[Marketing Automation] File payload v2: %s", file_data)
            return _finish_approval_check(
                payload=payload, file_id=file_id, name=name, description=description, label=label, logger=logger
            )
        if err.get("code") == 404:
            # Risorsa creata in V4 (next.frame.io) non esiste in v2; prova V4 se abbiamo token
            logger.info(
                "[Marketing Automation] v2 404 (risorsa solo in V4?). Provo API v4 con Access Token."
            )
        else:
            logger.error(
                "[Marketing Automation] GET asset Frame.io v2 fallito: %s %s",
                err.get("code"),
                err.get("body", "")[:300],
            )
            return {"success": False, "reason": "frameio_api_error", "code": err.get("code")}

    if not access_token:
        logger.warning(
            "[Marketing Automation] Nessun token configurato. Imposta FRAMEIO_DEVELOPER_TOKEN (da https://developer.frame.io/ → Create a Token) "
            "oppure FRAMEIO_ACCESS_TOKEN (da /marketing-automation/oauth/start)."
        )
        return {"success": False, "reason": "no_token"}

    if not account_id:
        logger.warning("[Marketing Automation] Payload senza account.id")
        return {"success": False, "reason": "no_account_id"}

    # V4: GET /v4/accounts/{account_id}/files/{file_id}
    url = f"{FRAMEIO_API_V4}/accounts/{account_id}/files/{file_id}"
    req = Request(url, method="GET")
    for k, v in _headers(access_token):
        req.add_header(k, v)

    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        logger.error(
            "[Marketing Automation] GET file Frame.io v4 fallito: %s %s", e.code, body[:500]
        )
        if e.code == 401:
            logger.warning(
                "[Marketing Automation] Token scaduto? Rifare login OAuth e aggiornare FRAMEIO_ACCESS_TOKEN"
            )
            # Come per 403: se il webhook dice già Approved, usiamo contesto minimo
            if payload.get("type") == "metadata.value.updated":
                meta = payload.get("metadata", {})
                if meta.get("field_name") == "Status" and "Approved" in (meta.get("value") or []):
                    logger.warning(
                        "[Marketing Automation] Token v4 scaduto; uso contesto minimo da webhook (name/description vuoti)."
                    )
                    return _finish_approval_check(
                        payload=payload,
                        file_id=file_id,
                        name="",
                        description="",
                        label="Approved",
                        logger=logger,
                    )
        elif e.code == 403:
            try:
                me_req = Request(f"{FRAMEIO_API_V4}/me", method="GET")
                for k, v in _headers(access_token):
                    me_req.add_header(k, v)
                with urlopen(me_req, timeout=10) as me_resp:
                    me_data = json.loads(me_resp.read().decode("utf-8"))
                logger.info(
                    "[Marketing Automation] Token valido (GET /me ok). 403 = permessi su questo file/account. Me: %s",
                    me_data.get("data", me_data),
                )
            except HTTPError as me_err:
                me_body = me_err.read().decode("utf-8") if me_err.fp else ""
                logger.warning(
                    "[Marketing Automation] GET /me Frame.io: %s. Frame.io rifiuta il token Adobe IMS. "
                    "Usa un Developer Token da https://developer.frame.io/ (Create a Token) e imposta FRAMEIO_DEVELOPER_TOKEN in .env. "
                    "Oppure contatta il supporto Frame.io per collegare il tuo Adobe ID. %s",
                    me_err.code,
                    me_body[:200],
                )
            except Exception as ex:
                logger.debug("[Marketing Automation] GET /me fallito: %s", ex)
        # v4 403 ma il webhook ci dice già che è approvato: contesto minimo così il flusso può continuare
        if payload.get("type") == "metadata.value.updated":
            meta = payload.get("metadata", {})
            if meta.get("field_name") == "Status" and "Approved" in (meta.get("value") or []):
                logger.warning(
                    "[Marketing Automation] Impossibile recuperare dettagli file (v2 404, v4 403). "
                    "Uso contesto minimo da webhook; name/description vuoti."
                )
                return _finish_approval_check(
                    payload=payload,
                    file_id=file_id,
                    name="",
                    description="",
                    label="Approved",
                    logger=logger,
                )
        return {"success": False, "reason": "frameio_api_error", "code": e.code}
    except URLError as e:
        logger.exception("[Marketing Automation] Errore richiesta Frame.io")
        return {"success": False, "reason": "network_error"}

    raw = json.loads(data)
    file_data = raw.get("data", raw) if isinstance(raw, dict) else raw
    name = file_data.get("name") or ""
    description = file_data.get("description") or ""
    label = file_data.get("label") or ""

    # Trascrizione/testo per caption: da metadati (Notes) o da tracce sottotitoli v2
    meta = _fetch_file_metadata_v4(account_id, file_id, access_token, app)
    if meta:
        description = (meta.get("Transcript") or meta.get("Notes") or description) or ""
        if meta.get("Notes"):
            logger.info(
                "[Marketing Automation] Testo da Frame.io (Notes): %s caratteri",
                len(description),
            )
    if not description and dev_token:
        # Prova a recuperare testo da sottotitoli v2 (traccia SRT/VTT) se l'asset è raggiungibile
        sub_text = _fetch_subtitles_text_v2(file_id, dev_token, app)
        if sub_text:
            description = sub_text
            logger.info(
                "[Marketing Automation] Trascrizione da sottotitoli v2: %s caratteri",
                len(description),
            )

    logger.info(
        "[Marketing Automation] File Frame.io (v4): name=%s label=%s description_len=%s",
        name, label, len(description),
    )
    logger.debug("[Marketing Automation] File payload v4: %s", file_data)
    return _finish_approval_check(
        payload=payload,
        file_id=file_id,
        name=name,
        description=description,
        label=label,
        logger=logger,
        view_url=file_data.get("view_url") or "",
    )


def _finish_approval_check(
    payload: Dict[str, Any],
    file_id: str,
    name: str,
    description: str,
    label: str,
    logger,
    view_url: str = "",
) -> Dict[str, Any]:
    """Determina se il file è approvato e restituisce il contesto per Airtable (e opzionale Poppy)."""
    is_approved = (label or "").lower() == "approved"
    if payload.get("type") == "metadata.value.updated":
        meta = payload.get("metadata", {})
        if meta.get("field_name") == "Status" and "Approved" in (meta.get("value") or []):
            is_approved = True

    if not is_approved:
        logger.info(
            "[Marketing Automation] File non approvato (label=%s), skip.", label
        )
        return {"success": True, "approved": False, "name": name}

    context = {
        "file_id": file_id,
        "name": name,
        "description": description,
        "label": label,
        "view_url": view_url,
    }
    logger.info(
        "[Marketing Automation] File approvato, dati pronti per Airtable: %s",
        context,
    )
    return {"success": True, "approved": True, "context": context}


AIRTABLE_API_BASE = "https://api.airtable.com/v0"


def send_to_airtable(context: Dict[str, Any], app) -> None:
    """
    Crea un record in Airtable con i dati del video approvato.
    L'automation Airtable (trigger: record creato → Generate with AI) compila il campo Caption.
    """
    logger = app.logger
    token = app.config.get("AIRTABLE_ACCESS_TOKEN")
    base_id = app.config.get("AIRTABLE_BASE_ID")
    table_id = app.config.get("AIRTABLE_TABLE_ID")
    if not token or not base_id or not table_id:
        logger.info(
            "[Marketing Automation] Airtable non configurato (AIRTABLE_ACCESS_TOKEN, AIRTABLE_BASE_ID, AIRTABLE_TABLE_ID). Skip."
        )
        return
    url = f"{AIRTABLE_API_BASE}/{base_id}/{quote(table_id, safe='')}"
    # Nomi campi devono coincidere con la tabella Airtable; Caption lasciato vuoto per l'automation AI
    fields = {
        "Video name": context.get("name") or "",
        "View URL": context.get("view_url") or "",
        "Description": context.get("description") or "",
        "Frame.io file ID": context.get("file_id") or "",
        "Status": "Approved",
    }
    payload = json.dumps({"fields": fields}).encode("utf-8")
    req = Request(url, data=payload, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=15) as resp:
            data = resp.read().decode("utf-8")
        result = json.loads(data)
        logger.info(
            "[Marketing Automation] Record Airtable creato: id=%s",
            result.get("id", ""),
        )
    except HTTPError as e:
        body = e.read().decode("utf-8") if e.fp else ""
        logger.error(
            "[Marketing Automation] Airtable POST fallito: %s %s", e.code, body[:400]
        )
    except URLError as e:
        logger.exception("[Marketing Automation] Errore richiesta Airtable")


def request_poppy_caption(context: Dict[str, Any], app) -> None:
    """
    Invia il contesto a Poppy per la generazione caption (opzionale, se API attiva).
    """
    logger = app.logger
    if not app.config.get("POPPY_API_KEY"):
        return
    base_url = app.config.get("POPPY_API_BASE_URL", "").rstrip("/")
    logger.info(
        "[Marketing Automation] Poppy configurato (base_url=%s); chiamata caption da implementare. Contesto: %s",
        base_url or "(non impostato)",
        context,
    )
