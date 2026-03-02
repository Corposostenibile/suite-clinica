"""
templates.py
============
Template JSON per Adaptive Cards del Teams bot.
Design coerente con navbar di navigazione sempre visibile.
"""

from __future__ import annotations

from datetime import datetime


# ─────────────────────── Navbar comune (4 bottoni) ─────────────────────── #

def _nav_bar() -> list[dict]:
    """Ritorna la barra di navigazione come elementi body, da appendere a ogni card."""
    return [
        {
            "type": "ActionSet",
            "separator": True,
            "spacing": "Medium",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "\u2795 Nuovo Ticket",
                    "style": "positive",
                    "data": {"action": "new_ticket"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83d\udccc Assegnati a Me",
                    "data": {"action": "tickets_assigned_to_me"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83d\udccb I Miei Ticket",
                    "data": {"action": "tickets_mine"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83d\udcda Knowledge Base",
                    "data": {"action": "kb_chat"},
                },
            ],
        },
    ]


# ─────────────────────── Costanti di stile ─────────────────────── #

_STATUS = {
    "aperto": {"icon": "\ud83d\udfe0", "label": "Aperto", "color": "Warning"},
    "in_lavorazione": {"icon": "\ud83d\udd35", "label": "In Lavorazione", "color": "Accent"},
    "risolto": {"icon": "\ud83d\udfe2", "label": "Risolto", "color": "Good"},
    "chiuso": {"icon": "\u26ab", "label": "Chiuso", "color": "Default"},
}

_PRIORITY = {
    "alta": {"icon": "\ud83d\udd34", "label": "Alta"},
    "media": {"icon": "\ud83d\udfe1", "label": "Media"},
    "bassa": {"icon": "\ud83d\udfe2", "label": "Bassa"},
}


def _status_badge(status: str) -> dict:
    """TextBlock badge per lo status."""
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
    """TextBlock badge per la priorita'."""
    p = _PRIORITY.get(priority, {"icon": "", "label": priority})
    return {
        "type": "TextBlock",
        "text": f"{p['icon']}  {p['label']}",
        "size": "Small",
        "spacing": "None",
    }


# ─────────────────────── Helper riusabili ─────────────────────── #

def _header(title: str, subtitle: str | None = None, icon: str = "") -> dict:
    """Container header coerente con stile emphasis."""
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
    """Wrapper per creare una card con navbar inclusa."""
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body + _nav_bar(),
    }
    if actions:
        card["actions"] = actions
    return card


def _time_ago(iso: str | None) -> str:
    """Calcola 'X giorni fa' da una data ISO."""
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
    """Saluto basato sull'ora corrente."""
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
    """Card di errore con icona, messaggio e nav bar."""
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
#                        SUCCESS CARD                               #
# ═══════════════════════════════════════════════════════════════ #

def success_card(
    title: str,
    message: str,
    actions: list[dict] | None = None,
) -> dict:
    """Card di successo riusabile con icona, messaggio e azioni opzionali."""
    body = [
        {
            "type": "Container",
            "style": "good",
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
                                "text": "\u2705",
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
                                    "color": "Good",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": message,
                                    "wrap": True,
                                    "spacing": "None",
                                    "isSubtle": True,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
    ]
    return _card(body, actions=actions)


# ═══════════════════════════════════════════════════════════════ #
#                        WELCOME CARD                               #
# ═══════════════════════════════════════════════════════════════ #

def welcome_card(
    assigned_tickets: list[dict] | None = None,
    my_open_tickets: list[dict] | None = None,
    user_name: str | None = None,
    stats: dict | None = None,
) -> dict:
    """Card di benvenuto con saluto, riepilogo e menu principale."""
    greeting = _greeting()
    greeting_text = f"{greeting}, {user_name}!" if user_name else f"{greeting}!"

    body: list[dict] = [
        _header(
            "\ud83c\udfab  Team Tickets",
            greeting_text,
        ),
    ]

    # ── Barra riepilogo stats ──
    if stats:
        parts = []
        if stats.get("aperti"):
            parts.append(f"{stats['aperti']} aperti")
        if stats.get("in_lavorazione"):
            parts.append(f"{stats['in_lavorazione']} in lavorazione")
        if stats.get("risolti"):
            parts.append(f"{stats['risolti']} risolti")
        if parts:
            body.append({
                "type": "TextBlock",
                "text": " \u00b7 ".join(parts),
                "size": "Small",
                "isSubtle": True,
                "spacing": "Small",
            })

    # ── Ticket alta priorita' ──
    high_priority = []
    for ticket_list in [assigned_tickets, my_open_tickets]:
        if ticket_list:
            high_priority.extend(
                t for t in ticket_list if t.get("priority") == "alta"
            )
    # Deduplica
    seen_ids = set()
    unique_high = []
    for t in high_priority:
        if t["id"] not in seen_ids:
            seen_ids.add(t["id"])
            unique_high.append(t)

    if unique_high:
        body.append({
            "type": "Container",
            "style": "attention",
            "spacing": "Small",
            "items": [
                {
                    "type": "TextBlock",
                    "text": f"\ud83d\udd34  {len(unique_high)} ticket ad alta priorita'",
                    "weight": "Bolder",
                    "size": "Small",
                    "color": "Attention",
                },
            ],
        })

    # ── Riepilogo ticket assegnati a me (aperti) ──
    if assigned_tickets:
        items: list[dict] = [
            {
                "type": "TextBlock",
                "text": f"\ud83d\udccc  Ticket assegnati a te ({len(assigned_tickets)})",
                "weight": "Bolder",
                "color": "Warning",
            },
        ]
        for t in assigned_tickets[:5]:
            s = _STATUS.get(t.get("status", ""), {"icon": "", "label": ""})
            p = _PRIORITY.get(t.get("priority", ""), {"icon": ""})
            title = t.get("title") or (t.get("description") or "")[:50]
            ago = _time_ago(t.get("created_at"))
            items.append({
                "type": "ColumnSet",
                "spacing": "Small",
                "selectAction": {
                    "type": "Action.Submit",
                    "data": {"action": "view_ticket", "ticket_id": t["id"]},
                },
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"{s['icon']} {p['icon']}",
                            "size": "Small",
                            "spacing": "None",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"**{t['ticket_number']}**  {title}",
                            "size": "Small",
                            "wrap": True,
                            "spacing": "None",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{
                            "type": "TextBlock",
                            "text": ago,
                            "size": "Small",
                            "isSubtle": True,
                            "spacing": "None",
                        }],
                    },
                ],
            })
        if len(assigned_tickets) > 5:
            items.append({
                "type": "TextBlock",
                "text": f"_...e altri {len(assigned_tickets) - 5}_",
                "size": "Small",
                "isSubtle": True,
                "spacing": "Small",
            })
        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": items,
        })

    # ── Riepilogo ticket che ho aperto (ancora aperti) ──
    if my_open_tickets:
        items2: list[dict] = [
            {
                "type": "TextBlock",
                "text": f"\ud83d\udce2  Ticket aperti da te ({len(my_open_tickets)})",
                "weight": "Bolder",
                "color": "Accent",
            },
        ]
        for t in my_open_tickets[:5]:
            s = _STATUS.get(t.get("status", ""), {"icon": "", "label": ""})
            p = _PRIORITY.get(t.get("priority", ""), {"icon": ""})
            title = t.get("title") or (t.get("description") or "")[:50]
            ago = _time_ago(t.get("created_at"))
            items2.append({
                "type": "ColumnSet",
                "spacing": "Small",
                "selectAction": {
                    "type": "Action.Submit",
                    "data": {"action": "view_ticket", "ticket_id": t["id"]},
                },
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"{s['icon']} {p['icon']}",
                            "size": "Small",
                            "spacing": "None",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"**{t['ticket_number']}**  {title}",
                            "size": "Small",
                            "wrap": True,
                            "spacing": "None",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{
                            "type": "TextBlock",
                            "text": ago,
                            "size": "Small",
                            "isSubtle": True,
                            "spacing": "None",
                        }],
                    },
                ],
            })
        if len(my_open_tickets) > 5:
            items2.append({
                "type": "TextBlock",
                "text": f"_...e altri {len(my_open_tickets) - 5}_",
                "size": "Small",
                "isSubtle": True,
                "spacing": "Small",
            })
        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": items2,
        })

    # Se non ha nessun ticket aperto
    if not assigned_tickets and not my_open_tickets:
        body.append({
            "type": "TextBlock",
            "text": "\u2705  Nessun ticket aperto al momento",
            "isSubtle": True,
            "spacing": "Large",
        })

    # Label menu
    body.append({
        "type": "TextBlock",
        "text": "Seleziona un'azione:",
        "weight": "Bolder",
        "spacing": "Large",
    })

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body + _nav_bar(),
    }


# ═══════════════════════════════════════════════════════════════ #
#                      CREATE TICKET FORM                          #
# ═══════════════════════════════════════════════════════════════ #

def create_ticket_form() -> dict:
    """Form creazione ticket con typeahead per assegnatario e paziente."""
    body = [
        _header("\ud83d\udcdd  Nuovo Ticket"),
        # Titolo
        {
            "type": "TextBlock",
            "text": "Titolo *",
            "weight": "Bolder",
            "spacing": "Medium",
        },
        {
            "type": "Input.Text",
            "id": "title",
            "placeholder": "Titolo breve del ticket...",
            "isRequired": True,
        },
        # Descrizione
        {
            "type": "TextBlock",
            "text": "Descrizione *",
            "weight": "Bolder",
            "spacing": "Medium",
        },
        {
            "type": "Input.Text",
            "id": "description",
            "placeholder": "Descrivi il problema o la richiesta...",
            "isMultiline": True,
            "isRequired": True,
        },
        # Priorita' + Assegnatario su due colonne
        {
            "type": "ColumnSet",
            "spacing": "Medium",
            "columns": [
                {
                    "type": "Column",
                    "width": "1",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Priorita'",
                            "weight": "Bolder",
                        },
                        {
                            "type": "Input.ChoiceSet",
                            "id": "priority",
                            "value": "media",
                            "choices": [
                                {"title": "\ud83d\udd34  Alta", "value": "alta"},
                                {"title": "\ud83d\udfe1  Media", "value": "media"},
                                {"title": "\ud83d\udfe2  Bassa", "value": "bassa"},
                            ],
                        },
                    ],
                },
                {
                    "type": "Column",
                    "width": "2",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "Assegnatario",
                            "weight": "Bolder",
                        },
                        {
                            "type": "Input.ChoiceSet",
                            "id": "assignee_id",
                            "style": "filtered",
                            "placeholder": "Cerca utente...",
                            "choices": [],
                            "choices.data": {
                                "type": "Data.Query",
                                "dataset": "users",
                            },
                        },
                    ],
                },
            ],
        },
        # Paziente
        {
            "type": "TextBlock",
            "text": "Paziente",
            "weight": "Bolder",
            "spacing": "Medium",
        },
        {
            "type": "Input.ChoiceSet",
            "id": "cliente_id",
            "style": "filtered",
            "placeholder": "Cerca per nome, email o telefono...",
            "choices": [],
            "choices.data": {
                "type": "Data.Query",
                "dataset": "patients",
            },
        },
    ]

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\u2705  Crea Ticket",
            "style": "positive",
            "data": {"action": "submit_ticket"},
        },
        {
            "type": "Action.Submit",
            "title": "\u274c  Annulla",
            "data": {"action": "home"},
        },
    ])


# ═══════════════════════════════════════════════════════════════ #
#                    CONFIRMATION CARD                              #
# ═══════════════════════════════════════════════════════════════ #

def ticket_confirmation_card(ticket: dict) -> dict:
    """Card di conferma dopo creazione ticket."""
    assignees = ", ".join(u["name"] for u in ticket.get("assigned_users", [])) or "Nessuno"
    title_display = ticket.get("title") or "(Senza titolo)"
    p = _PRIORITY.get(ticket.get("priority", ""), {"icon": "", "label": ticket.get("priority", "")})

    body = [
        # Banner successo
        {
            "type": "Container",
            "style": "good",
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
                                "text": "\u2705",
                                "size": "Large",
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": "Ticket Creato!",
                                    "weight": "Bolder",
                                    "size": "Large",
                                    "color": "Good",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": ticket["ticket_number"],
                                    "spacing": "None",
                                    "isSubtle": True,
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        # Dettagli
        {
            "type": "FactSet",
            "spacing": "Medium",
            "facts": [
                {"title": "Titolo", "value": title_display},
                {"title": "Priorita'", "value": f"{p['icon']}  {p['label']}"},
                {"title": "Assegnatari", "value": assignees},
                {"title": "Paziente", "value": ticket.get("cliente_nome") or "N/A"},
            ],
        },
    ]

    # Descrizione (troncata)
    desc = ticket.get("description", "")
    if desc:
        body.append({
            "type": "TextBlock",
            "text": desc[:200],
            "wrap": True,
            "isSubtle": True,
            "spacing": "Small",
        })

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\ud83d\udcce  Aggiungi Allegato",
            "data": {"action": "add_attachment", "ticket_id": ticket["id"]},
        },
        {
            "type": "Action.Submit",
            "title": "\ud83d\udd0d  Vedi Dettaglio",
            "data": {"action": "view_ticket", "ticket_id": ticket["id"]},
        },
    ])


# ═══════════════════════════════════════════════════════════════ #
#                    CLOSE CONFIRMATION CARD                        #
# ═══════════════════════════════════════════════════════════════ #

def close_confirmation_card(ticket_id: int, ticket_number: str, title: str) -> dict:
    """Card di conferma prima di chiudere un ticket."""
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
                                    "text": "Conferma Chiusura",
                                    "weight": "Bolder",
                                    "size": "Medium",
                                    "color": "Attention",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"Sei sicuro di voler chiudere **{ticket_number}**?",
                                    "wrap": True,
                                    "spacing": "None",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        {
            "type": "TextBlock",
            "text": title[:100] if title else "(Senza titolo)",
            "wrap": True,
            "isSubtle": True,
            "spacing": "Small",
        },
    ]

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\ud83d\udd12  Conferma Chiusura",
            "style": "destructive",
            "data": {"action": "confirm_close_ticket", "ticket_id": ticket_id},
        },
        {
            "type": "Action.Submit",
            "title": "\u2190  Annulla",
            "data": {"action": "view_ticket", "ticket_id": ticket_id},
        },
    ])


# ═══════════════════════════════════════════════════════════════ #
#                    NOTIFICATION CARD                              #
# ═══════════════════════════════════════════════════════════════ #

def ticket_notification_card(
    ticket: dict,
    message: str | None = None,
    status_change: str | None = None,
    sender_name: str | None = None,
) -> dict:
    """Card di notifica per aggiornamenti da admin."""
    title_display = ticket.get("title") or ticket["ticket_number"]

    header_items = [
        {
            "type": "TextBlock",
            "text": "\ud83d\udd14  Aggiornamento Ticket",
            "weight": "Bolder",
            "size": "Medium",
            "color": "Accent",
        },
        {
            "type": "TextBlock",
            "text": f"{ticket['ticket_number']} \u2014 {title_display}",
            "wrap": True,
            "spacing": "None",
        },
    ]

    body: list[dict] = [
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": header_items,
        },
    ]

    if status_change:
        s = _STATUS.get(status_change, {"icon": "", "label": status_change, "color": "Default"})
        body.append({
            "type": "Container",
            "style": "accent",
            "items": [{
                "type": "TextBlock",
                "text": f"Stato aggiornato:  {s['icon']}  **{s['label']}**",
                "wrap": True,
            }],
        })

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

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\u2709\ufe0f  Rispondi",
            "data": {"action": "reply_ticket", "ticket_id": ticket["id"]},
        },
        {
            "type": "Action.Submit",
            "title": "\ud83d\udd0d  Vedi Dettaglio",
            "data": {"action": "view_ticket", "ticket_id": ticket["id"]},
        },
    ])


# ═══════════════════════════════════════════════════════════════ #
#                       TICKET LIST CARD                            #
# ═══════════════════════════════════════════════════════════════ #

def ticket_list_card(
    tickets: list[dict],
    list_title: str = "I Miei Ticket",
    page: int = 1,
    has_next: bool = False,
    list_action: str | None = None,
) -> dict:
    """Card con lista ticket (2 righe per ticket, paginata)."""
    total_display = f"{len(tickets)} ticket" if page == 1 and not has_next else f"Pagina {page}"

    body: list[dict] = [
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [{
                "type": "ColumnSet",
                "columns": [
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"\ud83d\udccb  {list_title}",
                            "weight": "Bolder",
                            "size": "Large",
                            "color": "Accent",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "verticalContentAlignment": "Center",
                        "items": [{
                            "type": "TextBlock",
                            "text": total_display,
                            "isSubtle": True,
                            "size": "Small",
                        }],
                    },
                ],
            }],
        },
    ]

    if not tickets:
        body.append({
            "type": "Container",
            "spacing": "Large",
            "items": [{
                "type": "TextBlock",
                "text": "Nessun ticket trovato.",
                "isSubtle": True,
                "horizontalAlignment": "Center",
                "spacing": "Large",
            }],
        })
        return _card(body)

    for i, t in enumerate(tickets[:10]):
        status = t.get("status", "")
        priority = t.get("priority", "")
        title_text = t.get("title") or "(Senza titolo)"
        assignees = ", ".join(u["name"] for u in t.get("assigned_users", [])) or "\u2014"
        patient = t.get("cliente_nome") or "\u2014"
        ago = _time_ago(t.get("created_at"))
        s = _STATUS.get(status, {"icon": "", "label": status, "color": "Default"})
        p = _PRIORITY.get(priority, {"icon": "", "label": priority})
        msg_count = t.get("messages_count", 0)
        att_count = t.get("attachments_count", 0)

        counters = []
        if msg_count:
            counters.append(f"\ud83d\udcac{msg_count}")
        if att_count:
            counters.append(f"\ud83d\udcce{att_count}")
        counters_text = " ".join(counters)

        # Riga 1: status + numero + titolo + priorita'
        # Riga 2: assegnatari + paziente + data
        ticket_container = {
            "type": "Container",
            "separator": i > 0,
            "spacing": "Small",
            "selectAction": {
                "type": "Action.Submit",
                "data": {"action": "view_ticket", "ticket_id": t["id"]},
            },
            "items": [
                {
                    "type": "ColumnSet",
                    "spacing": "None",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [{
                                "type": "TextBlock",
                                "text": f"{s['icon']} {p['icon']}",
                                "size": "Small",
                                "spacing": "None",
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [{
                                "type": "TextBlock",
                                "text": f"**{t['ticket_number']}**  {title_text}",
                                "wrap": True,
                                "size": "Small",
                                "spacing": "None",
                            }],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [{
                                "type": "TextBlock",
                                "text": counters_text,
                                "size": "Small",
                                "isSubtle": True,
                                "spacing": "None",
                            }],
                        },
                    ],
                },
                {
                    "type": "TextBlock",
                    "text": f"\ud83d\udc64 {assignees}   \u00b7   \ud83c\udfe5 {patient}   \u00b7   {ago}",
                    "size": "Small",
                    "isSubtle": True,
                    "wrap": True,
                    "spacing": "None",
                },
            ],
        }
        body.append(ticket_container)

    # Paginazione
    if page > 1 or has_next:
        page_actions = []
        if page > 1 and list_action:
            page_actions.append({
                "type": "Action.Submit",
                "title": "\u2190 Precedente",
                "data": {"action": list_action, "page": page - 1},
            })
        if has_next and list_action:
            page_actions.append({
                "type": "Action.Submit",
                "title": "Successivo \u2192",
                "data": {"action": list_action, "page": page + 1},
            })
        if page_actions:
            body.append({
                "type": "ActionSet",
                "spacing": "Medium",
                "actions": page_actions,
            })

    return _card(body)


# ═══════════════════════════════════════════════════════════════ #
#                     TICKET DETAIL CARD                            #
# ═══════════════════════════════════════════════════════════════ #

def ticket_detail_card(ticket: dict) -> dict:
    """Card con dettaglio completo di un ticket con transizioni stato complete."""
    status = ticket.get("status", "")
    priority = ticket.get("priority", "")
    title_display = ticket.get("title") or "(Senza titolo)"
    assignees = ", ".join(u["name"] for u in ticket.get("assigned_users", [])) or "Nessuno"
    patient = ticket.get("cliente_nome") or "N/A"
    created = (ticket.get("created_at") or "")[:16].replace("T", " ")
    created_ago = _time_ago(ticket.get("created_at"))
    source_label = "\ud83d\udfe3 Teams" if ticket.get("source") == "teams" else "\ud83d\udd35 Admin"
    created_by = ticket.get("created_by_name") or "Teams"

    s_info = _STATUS.get(status, {"icon": "", "label": status, "color": "Default"})
    p_info = _PRIORITY.get(priority, {"icon": "", "label": priority})

    body: list[dict] = [
        # Header con badges nel titolo
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [
                {
                    "type": "ColumnSet",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": ticket["ticket_number"],
                                    "size": "Small",
                                    "isSubtle": True,
                                    "spacing": "None",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": title_display,
                                    "weight": "Bolder",
                                    "size": "Large",
                                    "wrap": True,
                                    "spacing": "None",
                                },
                            ],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "verticalContentAlignment": "Center",
                            "items": [
                                {
                                    "type": "TextBlock",
                                    "text": f"{s_info['icon']} {s_info['label']}",
                                    "weight": "Bolder",
                                    "color": s_info["color"],
                                    "size": "Small",
                                    "spacing": "None",
                                },
                                {
                                    "type": "TextBlock",
                                    "text": f"{p_info['icon']} {p_info['label']}",
                                    "size": "Small",
                                    "spacing": "None",
                                },
                            ],
                        },
                    ],
                },
            ],
        },
        # Info principali
        {
            "type": "FactSet",
            "separator": True,
            "spacing": "Medium",
            "facts": [
                {"title": "\ud83d\udc64  Assegnatari", "value": assignees},
                {"title": "\ud83c\udfe5  Paziente", "value": patient},
                {"title": "\ud83d\udcc5  Creato", "value": f"{created}  ({created_ago})  da {created_by}"},
                {"title": "\ud83d\udcf1  Fonte", "value": source_label},
            ],
        },
    ]

    # Descrizione
    desc = ticket.get("description", "")
    if desc:
        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": [
                {
                    "type": "TextBlock",
                    "text": "Descrizione",
                    "weight": "Bolder",
                    "size": "Small",
                    "isSubtle": True,
                },
                {
                    "type": "TextBlock",
                    "text": desc[:500],
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
        })

    # Allegati con download link
    attachments = ticket.get("attachments", [])
    if attachments:
        att_items: list[dict] = [
            {
                "type": "TextBlock",
                "text": f"\ud83d\udcce  Allegati ({len(attachments)})",
                "weight": "Bolder",
                "size": "Small",
                "isSubtle": True,
            },
        ]
        for att in attachments:
            filename = att.get("filename", "file")
            size_bytes = att.get("file_size", 0)
            if size_bytes >= 1_048_576:
                size_str = f"{size_bytes / 1_048_576:.1f} MB"
            elif size_bytes >= 1024:
                size_str = f"{size_bytes / 1024:.0f} KB"
            else:
                size_str = f"{size_bytes} B"
            is_img = att.get("is_image", False)
            icon = "\ud83d\uddbc\ufe0f" if is_img else "\ud83d\udcc4"
            source_badge = "\ud83d\udfe3" if att.get("source") == "teams" else "\ud83d\udd35"
            date = (att.get("created_at") or "")[:10]

            att_items.append({
                "type": "ColumnSet",
                "spacing": "Small",
                "columns": [
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"{icon}",
                            "size": "Small",
                            "spacing": "None",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "stretch",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"[**{filename}**](/api/team-tickets/attachments/{att.get('id', '')})  ({size_str})",
                            "size": "Small",
                            "wrap": True,
                            "spacing": "None",
                        }],
                    },
                    {
                        "type": "Column",
                        "width": "auto",
                        "items": [{
                            "type": "TextBlock",
                            "text": f"{source_badge} {date}",
                            "size": "Small",
                            "isSubtle": True,
                            "spacing": "None",
                        }],
                    },
                ],
            })

        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": att_items,
        })

    # Ultimi messaggi con differenziazione visiva
    messages = ticket.get("messages", [])
    if messages:
        msg_items: list[dict] = [
            {
                "type": "TextBlock",
                "text": "Conversazione",
                "weight": "Bolder",
                "size": "Small",
                "isSubtle": True,
            },
        ]
        for msg in messages[-5:]:
            sender = msg.get("sender_name") or "Anonimo"
            content = (msg.get("content") or "")[:150]
            is_teams = msg.get("source") == "teams"
            badge = "\ud83d\udfe3" if is_teams else "\ud83d\udd35"
            ago = _time_ago(msg.get("created_at"))
            msg_items.append({
                "type": "Container",
                "style": "emphasis" if is_teams else "default",
                "spacing": "Small",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"{badge}  **{sender}**  \u00b7  {ago}",
                        "size": "Small",
                        "isSubtle": True,
                        "spacing": "None",
                    },
                    {
                        "type": "TextBlock",
                        "text": content,
                        "wrap": True,
                        "size": "Small",
                        "spacing": "None",
                    },
                ],
            })

        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": msg_items,
        })

    # Azioni contestuali con transizioni di stato complete
    actions = []

    if status == "aperto":
        actions.extend([
            {
                "type": "Action.Submit",
                "title": "\u2709\ufe0f  Rispondi",
                "data": {"action": "reply_ticket", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\ude80  Prendi in Carico",
                "style": "positive",
                "data": {"action": "take_ticket", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\udcce  Allegato",
                "data": {"action": "add_attachment", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\udd12  Chiudi",
                "style": "destructive",
                "data": {"action": "close_ticket", "ticket_id": ticket["id"]},
            },
        ])
    elif status == "in_lavorazione":
        actions.extend([
            {
                "type": "Action.Submit",
                "title": "\u2709\ufe0f  Rispondi",
                "data": {"action": "reply_ticket", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\u2705  Segna Risolto",
                "style": "positive",
                "data": {"action": "resolve_ticket", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\udcce  Allegato",
                "data": {"action": "add_attachment", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\udd12  Chiudi",
                "style": "destructive",
                "data": {"action": "close_ticket", "ticket_id": ticket["id"]},
            },
        ])
    elif status == "risolto":
        actions.extend([
            {
                "type": "Action.Submit",
                "title": "\ud83d\udd12  Chiudi",
                "style": "destructive",
                "data": {"action": "close_ticket", "ticket_id": ticket["id"]},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\udd04  Riapri",
                "data": {"action": "reopen_ticket", "ticket_id": ticket["id"]},
            },
        ])
    elif status == "chiuso":
        actions.append({
            "type": "Action.Submit",
            "title": "\ud83d\udd04  Riapri",
            "data": {"action": "reopen_ticket", "ticket_id": ticket["id"]},
        })

    return _card(body, actions=actions or None)


# ═══════════════════════════════════════════════════════════════ #
#                       REPLY FORM CARD                             #
# ═══════════════════════════════════════════════════════════════ #

def reply_form_card(
    ticket_id: int,
    ticket_number: str,
    title: str | None = None,
    last_messages: list[dict] | None = None,
) -> dict:
    """Form per rispondere a un ticket da Teams, con contesto conversazione."""
    body = [
        _header(
            f"\u2709\ufe0f  Rispondi a {ticket_number}",
            title[:80] if title else None,
        ),
    ]

    # Contesto: ultimi messaggi
    if last_messages:
        context_items: list[dict] = [
            {
                "type": "TextBlock",
                "text": "Conversazione recente:",
                "size": "Small",
                "isSubtle": True,
                "spacing": "Medium",
            },
        ]
        for msg in last_messages[-3:]:
            sender = msg.get("sender_name") or "Anonimo"
            content = (msg.get("content") or "")[:100]
            badge = "\ud83d\udfe3" if msg.get("source") == "teams" else "\ud83d\udd35"
            context_items.append({
                "type": "TextBlock",
                "text": f"{badge} **{sender}**: {content}",
                "size": "Small",
                "isSubtle": True,
                "wrap": True,
                "spacing": "None",
            })
        body.append({
            "type": "Container",
            "style": "emphasis",
            "spacing": "Small",
            "items": context_items,
        })

    body.append({
        "type": "Input.Text",
        "id": "reply_content",
        "placeholder": "Scrivi la tua risposta...",
        "isMultiline": True,
        "isRequired": True,
        "spacing": "Medium",
    })

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\ud83d\udce8  Invia Risposta",
            "style": "positive",
            "data": {"action": "submit_reply", "ticket_id": ticket_id},
        },
        {
            "type": "Action.Submit",
            "title": "\u2190  Annulla",
            "data": {"action": "view_ticket", "ticket_id": ticket_id},
        },
    ])


# ═══════════════════════════════════════════════════════════════ #
#                    KNOWLEDGE BASE CARDS                           #
# ═══════════════════════════════════════════════════════════════ #

def kb_chat_card(doc_count: int, chunks_count: int) -> dict:
    """Card iniziale Knowledge Base con stats e campo domanda."""
    body = [
        _header(
            "\ud83d\udcda  Knowledge Base",
            f"{doc_count} documenti indicizzati, {chunks_count} chunks",
        ),
        {
            "type": "TextBlock",
            "text": "Fai una domanda sulla documentazione:",
            "weight": "Bolder",
            "spacing": "Large",
        },
        {
            "type": "Input.Text",
            "id": "kb_question",
            "placeholder": "Fai una domanda...",
            "isMultiline": True,
        },
    ]

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\ud83d\udd0d  Cerca nella Knowledge Base",
            "style": "positive",
            "data": {"action": "kb_ask"},
        },
        {
            "type": "Action.Submit",
            "title": "\ud83c\udfe0  Torna alla Home",
            "data": {"action": "home"},
        },
    ])


def kb_response_card(answer: str, sources: list[str], question: str) -> dict:
    """Card risposta Knowledge Base con fonti e campo follow-up."""
    question_display = question[:80] + ("..." if len(question) > 80 else "")

    body: list[dict] = [
        _header(f"\ud83d\udcda  {question_display}"),
        # Risposta
        {
            "type": "Container",
            "spacing": "Medium",
            "items": [{
                "type": "TextBlock",
                "text": answer[:2000],
                "wrap": True,
            }],
        },
    ]

    # Fonti
    if sources:
        source_items: list[dict] = [
            {
                "type": "TextBlock",
                "text": "\ud83d\udcc4  Fonti",
                "weight": "Bolder",
                "size": "Small",
                "isSubtle": True,
            },
        ]
        for src in sources:
            source_items.append({
                "type": "TextBlock",
                "text": f"\u2022  {src}",
                "size": "Small",
                "isSubtle": True,
                "spacing": "None",
                "wrap": True,
            })
        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": source_items,
        })

    # Campo follow-up
    body.append({
        "type": "Input.Text",
        "id": "kb_question",
        "placeholder": "Fai un'altra domanda...",
        "isMultiline": True,
        "spacing": "Large",
    })

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\ud83d\udd0d  Chiedi ancora",
            "style": "positive",
            "data": {"action": "kb_ask"},
        },
        {
            "type": "Action.Submit",
            "title": "\ud83d\uddd1\ufe0f  Nuova conversazione",
            "data": {"action": "kb_new_session"},
        },
        {
            "type": "Action.Submit",
            "title": "\ud83c\udfe0  Torna alla Home",
            "data": {"action": "home"},
        },
    ])
