"""
Linee guida per la generazione caption (Marketing Automation).
Placeholder fino all'integrazione dei PDF; sovrascrivibile via CLAUDE_CAPTION_GUIDELINES.
"""

# Placeholder: sostituire con testo distillato dai PDF quando disponibili
DEFAULT_GUIDELINES = """Sei un copywriter esperto in contenuti per social (Instagram, Reel).
Scrivi una caption in italiano: coinvolgente, in linea con il brand, adatta ai social.
Usa solo le informazioni presenti nella trascrizione del video; non inventare dettagli.
La caption deve essere pronta per essere incollata (può includere una prima riga come titolo e il resto come corpo)."""


def get_guidelines(app) -> str:
    """Ritorna le linee guida: da config se impostate, altrimenti il placeholder."""
    custom = app.config.get("CLAUDE_CAPTION_GUIDELINES")
    if custom and str(custom).strip():
        return str(custom).strip()
    return DEFAULT_GUIDELINES
