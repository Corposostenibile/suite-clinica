"""
Generazione caption via Claude API (Marketing Automation).
Usa linee guida da caption_guidelines e trascrizione dal contesto Frame.io.
"""

from typing import Any, Dict, Optional

from .caption_guidelines import get_guidelines


def generate_caption(context: Dict[str, Any], app) -> Optional[str]:
    """
    Genera una caption per il video usando Claude.
    context: dict con almeno "name", "description" (trascrizione), opzionale "view_url".
    Ritorna la caption come stringa, o None in caso di errore o API key non configurata.
    """
    logger = app.logger
    api_key = app.config.get("ANTHROPIC_API_KEY")
    if not api_key or not api_key.strip():
        logger.debug("[Marketing Automation] Claude: ANTHROPIC_API_KEY non configurata, skip.")
        return None

    name = context.get("name") or "Video"
    transcript = (context.get("description") or "").strip()
    if not transcript:
        logger.warning("[Marketing Automation] Claude: trascrizione vuota, impossibile generare caption.")
        return None

    guidelines = get_guidelines(app)
    model = app.config.get("CLAUDE_CAPTION_MODEL", "claude-sonnet-4-20250514")

    user_content = f"""Genera una caption per social (Instagram/Reel) per questo video.

Titolo/nome del video: {name}

Trascrizione del video:
---
{transcript}
---

Scrivi solo la caption, senza spiegazioni aggiuntive. La caption può avere una prima riga come titolo e il resto come corpo."""

    try:
        import anthropic
        import httpx
        # Client HTTP esplicito senza proxy, per evitare incompatibilità con httpx (proxies vs proxy)
        with httpx.Client() as http_client:
            client = anthropic.Anthropic(api_key=api_key, http_client=http_client)
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=guidelines,
                messages=[{"role": "user", "content": user_content}],
            )
        text = ""
        for block in response.content:
            if getattr(block, "type", None) == "text":
                text += getattr(block, "text", "") or ""
        caption = text.strip() if text else None
        if caption:
            logger.info("[Marketing Automation] Claude caption generata: %s caratteri", len(caption))
        else:
            logger.warning("[Marketing Automation] Claude ha restituito risposta vuota.")
        return caption
    except Exception as e:
        logger.exception("[Marketing Automation] Errore chiamata Claude: %s", e)
        return None
