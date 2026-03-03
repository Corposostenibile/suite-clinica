"""
templates.py
============
Template JSON per Adaptive Cards del Teams bot.
Il bot e' solo notifiche + guida alla Kanban Board.
"""

from __future__ import annotations

from datetime import datetime


# ─────────────────────── Costanti di stile ─────────────────────── #

_STATUS = {
    "aperto": {"icon": "\U0001f7e0", "label": "Aperto", "color": "Warning"},
    "in_lavorazione": {"icon": "\U0001f535", "label": "In Lavorazione", "color": "Accent"},
    "risolto": {"icon": "\U0001f7e2", "label": "Risolto", "color": "Good"},
    "chiuso": {"icon": "\u26ab", "label": "Chiuso", "color": "Default"},
}

_PRIORITY = {
    "alta": {"icon": "\U0001f534", "label": "Alta"},
    "media": {"icon": "\U0001f7e1", "label": "Media"},
    "bassa": {"icon": "\U0001f7e2", "label": "Bassa"},
}


def _status_badge(status: str) -> dict:
    s = _STATUS.get(status, {"icon": "", "label": status, "color": "Default"})
    return {
        "type": "TextBlock",
        "text": f"{s['icon']}  {s['label']}",
        "color": s["color"],
        "weight": "Bolder",
        "size": "Small",
        "spacing": "None",
    }


def _priority_badge(priority: str) -> dict:
    p = _PRIORITY.get(priority, {"icon": "", "label": priority})
    return {
        "type": "TextBlock",
        "text": f"{p['icon']}  {p['label']}",
        "size": "Small",
        "spacing": "None",
    }


# ─────────────────────── Helper riusabili ─────────────────────── #

def _header(title: str, subtitle: str | None = None, icon: str = "") -> dict:
    items = [
        {
            "type": "TextBlock",
            "text": f"{icon}  {title}" if icon else title,
            "weight": "Bolder",
            "size": "Large",
            "color": "Accent",
            "wrap": True,
        },
    ]
    if subtitle:
        items.append({
            "type": "TextBlock",
            "text": subtitle,
            "spacing": "None",
            "isSubtle": True,
            "wrap": True,
        })
    return {
        "type": "Container",
        "style": "emphasis",
        "bleed": True,
        "items": items,
    }


def _card(body: list[dict], actions: list[dict] | None = None) -> dict:
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body,
    }
    if actions:
        card["actions"] = actions
    return card


def _time_ago(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        now = datetime.utcnow()
        if dt.tzinfo:
            dt = dt.replace(tzinfo=None)
        diff = now - dt
        mins = int(diff.total_seconds() / 60)
        if mins < 1:
            return "ora"
        if mins < 60:
            return f"{mins} min fa"
        hours = mins // 60
        if hours < 24:
            return f"{hours} or{'a' if hours == 1 else 'e'} fa"
        days = hours // 24
        if days < 30:
            return f"{days} giorn{'o' if days == 1 else 'i'} fa"
        months = days // 30
        return f"{months} mes{'e' if months == 1 else 'i'} fa"
    except Exception:
        return ""


def _greeting() -> str:
    hour = datetime.utcnow().hour
    if hour < 13:
        return "Buongiorno"
    if hour < 18:
        return "Buon pomeriggio"
    return "Buonasera"


# ═══════════════════════════════════════════════════════════════ #
#                        ERROR CARD                                #
# ═══════════════════════════════════════════════════════════════ #

def error_card(title: str = "Errore", message: str = "Si e' verificato un errore.") -> dict:
    body = [
        {
            "type": "Container",
            "style": "attention",
            "bleed": True,
            "items": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "verticalContentAlignment": "Center",
                            "items": [{
                                "type": "TextBlock",
                                "text": "\u26a0\ufe0f",
                                "size": "Large",
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": title,
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Attention",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": message,
                                    "wrap": True,
                                    "spacing": "None",
                                    "size": "Small",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ]
    return _card(body)


# ═══════════════════════════════════════════════════════════════ #
#                     WELCOME / GUIDE CARD                         #
# ═══════════════════════════════════════════════════════════════ #

def welcome_card(user_name: str | None = None) -> dict:
    """Card di benvenuto che spiega come usare la Kanban Board nella tab Teams."""
    greeting = _greeting()
    greeting_text = f"{greeting}, {user_name}!" if user_name else f"{greeting}!"

    body: list[dict] = [
        _header(
            "\U0001f3ab  SUMI Ticket Board",
            greeting_text,
        ),
        # Intro
        {
            "type": "TextBlock",
            "text": "Gestisci i tuoi ticket dalla **Ticket Board** "
                    "nella tab in alto \u2191",
            "wrap": True,
            "spacing": "Medium",
            "size": "Medium",
        },
        # Guida step-by-step
        {
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "\U0001f4cb  Come funziona",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Accent",
                },
                {
                    "type": "TextBlock",
                    "text": "\u2795  **Creare un ticket**\n"
                            "Clicca il bottone **+ Nuovo Ticket** nella board. "
                            "Inserisci titolo, descrizione, priorita', "
                            "assegnatario e paziente.",
                    "wrap": True,
                    "spacing": "Small",
                },
                {
                    "type": "TextBlock",
                    "text": "\U0001f5c2\ufe0f  **Gestire i ticket**\n"
                            "Trascina le card tra le colonne per cambiare stato: "
                            "**Aperto** \u2192 **In Lavorazione** \u2192 "
                            "**Risolto** \u2192 **Chiuso**.",
                    "wrap": True,
                    "spacing": "Small",
                },
                {
                    "type": "TextBlock",
                    "text": "\U0001f4ac  **Rispondere e allegare**\n"
                            "Clicca su una card per aprire il dettaglio. "
                            "Puoi scrivere messaggi, caricare allegati e "
                            "cambiare lo stato.",
                    "wrap": True,
                    "spacing": "Small",
                },
                {
                    "type": "TextBlock",
                    "text": "\U0001f50d  **Filtrare e cercare**\n"
                            "Usa la barra filtri per cercare per testo, "
                            "filtrare per priorita' o vedere solo i ticket "
                            "creati da te o assegnati a te.",
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
        },
        # Notifiche
        {
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "\U0001f514  Notifiche",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": "Accent",
                },
                {
                    "type": "TextBlock",
                    "text": "Riceverai una notifica qui in chat quando:\n"
                            "\u2022  Un ticket che hai creato viene aggiornato\n"
                            "\u2022  Ti viene assegnato un nuovo ticket\n"
                            "\u2022  Qualcuno risponde a un tuo ticket\n"
                            "\u2022  Lo stato di un tuo ticket cambia",
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
        },
        # Footer
        {
            "type": "TextBlock",
            "text": "\U0001f449  Apri la tab **Ticket Board** qui sopra per iniziare!",
            "wrap": True,
            "spacing": "Large",
            "weight": "Bolder",
            "color": "Accent",
        },
    ]

    return _card(body, actions=[
        {
            "type": "Action.OpenUrl",
            "title": "\U0001f4cb  Apri Ticket Board",
            "url": "https://clinica.corposostenibile.com/teams-kanban/",
        },
    ])


# ═══════════════════════════════════════════════════════════════ #
#                    NOTIFICATION CARD                              #
# ═══════════════════════════════════════════════════════════════ #

def ticket_notification_card(
    ticket: dict,
    event_type: str = "update",
    message: str | None = None,
    status_change: str | None = None,
    sender_name: str | None = None,
    assigned_to_you: bool = False,
) -> dict:
    """Card di notifica proattiva per aggiornamenti ticket.

    event_type: 'created', 'assigned', 'status_changed', 'message', 'update'
    """
    title_display = ticket.get("title") or ticket.get("ticket_number", "")
    ticket_number = ticket.get("ticket_number", "")

    # Header diverso per tipo di evento
    if event_type == "assigned" or assigned_to_you:
        header_icon = "\U0001f4cc"
        header_text = "Ticket assegnato a te"
        header_color = "Warning"
    elif event_type == "created":
        header_icon = "\u2795"
        header_text = "Nuovo ticket creato"
        header_color = "Good"
    elif event_type == "status_changed":
        header_icon = "\U0001f504"
        header_text = "Stato ticket aggiornato"
        header_color = "Accent"
    elif event_type == "message":
        header_icon = "\U0001f4ac"
        header_text = "Nuovo messaggio"
        header_color = "Accent"
    else:
        header_icon = "\U0001f514"
        header_text = "Aggiornamento ticket"
        header_color = "Accent"

    body: list[dict] = [
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"{header_icon}  {header_text}",
                    "weight": "Bolder",
                    "size": "Medium",
                    "color": header_color,
                },
                {
                    "type": "TextBlock",
                    "text": f"{ticket_number} \u2014 {title_display}",
                    "wrap": True,
                    "spacing": "None",
                },
            ],
        },
    ]

    # Dettagli ticket
    s = _STATUS.get(ticket.get("status", ""), {"icon": "", "label": ""})
    p = _PRIORITY.get(ticket.get("priority", ""), {"icon": "", "label": ""})
    assignees = ", ".join(u["name"] for u in ticket.get("assigned_users", [])) or "Nessuno"
    patient = ticket.get("cliente_nome") or "N/A"
    created_by = ticket.get("created_by_name") or "Sconosciuto"

    body.append({
        "type": "FactSet",
        "spacing": "Medium",
        "facts": [
            {"title": "Stato", "value": f"{s['icon']}  {s['label']}"},
            {"title": "Priorita'", "value": f"{p['icon']}  {p['label']}"},
            {"title": "Assegnatari", "value": assignees},
            {"title": "Paziente", "value": patient},
            {"title": "Creato da", "value": created_by},
        ],
    })

    # Status change highlight
    if status_change:
        sc = _STATUS.get(status_change, {"icon": "", "label": status_change, "color": "Default"})
        body.append({
            "type": "Container",
            "style": "accent",
            "items": [{
                "type": "TextBlock",
                "text": f"Nuovo stato:  {sc['icon']}  **{sc['label']}**",
                "wrap": True,
            }],
        })

    # Messaggio
    if message and sender_name:
        body.append({
            "type": "Container",
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"**{sender_name}** ha scritto:",
                    "size": "Small",
                    "isSubtle": True,
                },
                {
                    "type": "TextBlock",
                    "text": message[:300],
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
        })

    # Descrizione (troncata)
    desc = ticket.get("description", "")
    if desc and event_type in ("created", "assigned"):
        body.append({
            "type": "TextBlock",
            "text": desc[:200],
            "wrap": True,
            "isSubtle": True,
            "spacing": "Small",
        })

    return _card(body, actions=[
        {
            "type": "Action.OpenUrl",
            "title": "\U0001f4cb  Apri nella Board",
            "url": "https://clinica.corposostenibile.com/teams-kanban/",
        },
    ])
