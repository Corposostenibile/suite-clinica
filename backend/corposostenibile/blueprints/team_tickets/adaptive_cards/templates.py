"""
templates.py
============
Template JSON per Adaptive Cards del Teams bot.
Design coerente con navbar di navigazione sempre visibile.
"""

from __future__ import annotations


# ─────────────────────── Navbar per sezione ─────────────────────── #

def _nav_bar_home() -> list[dict]:
    """Singolo bottone Home per tornare alla intro card."""
    return [
        {
            "type": "ActionSet",
            "separator": True,
            "spacing": "Medium",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "\ud83c\udfe0 Home",
                    "data": {"action": "go_home"},
                },
            ],
        },
    ]


def _nav_bar_tickets() -> list[dict]:
    """Navbar con pulsanti solo ticket + Home."""
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
                    "title": "\ud83d\udce2 Miei Aperti",
                    "data": {"action": "tickets_my_open"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83d\udcc1 Ho Aperto",
                    "data": {"action": "tickets_i_opened"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83d\udd04 Ho Gestito",
                    "data": {"action": "tickets_i_managed"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83c\udfe0 Home",
                    "data": {"action": "go_home"},
                },
            ],
        },
    ]


def _nav_bar_kb() -> list[dict]:
    """Navbar con pulsanti solo KB + Home."""
    return [
        {
            "type": "ActionSet",
            "separator": True,
            "spacing": "Medium",
            "actions": [
                {
                    "type": "Action.Submit",
                    "title": "\ud83d\uddd1\ufe0f Nuova Conversazione",
                    "data": {"action": "kb_new_session"},
                },
                {
                    "type": "Action.Submit",
                    "title": "\ud83c\udfe0 Home",
                    "data": {"action": "go_home"},
                },
            ],
        },
    ]


def _get_nav_bar(section: str) -> list[dict]:
    """Ritorna la navbar appropriata per la sezione."""
    if section == "tickets":
        return _nav_bar_tickets()
    elif section == "kb":
        return _nav_bar_kb()
    else:
        return _nav_bar_home()


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


def _card(body: list[dict], actions: list[dict] | None = None, section: str = "home") -> dict:
    """Wrapper per creare una card con navbar inclusa.

    section: "home" | "tickets" | "kb" — determina quale navbar mostrare.
    """
    card = {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body + _get_nav_bar(section),
    }
    if actions:
        card["actions"] = actions
    return card


# ═══════════════════════════════════════════════════════════════ #
#                        INTRO CARD                               #
# ═══════════════════════════════════════════════════════════════ #

def intro_card() -> dict:
    """Card introduttiva che presenta le funzionalita' del bot SUMI."""
    body: list[dict] = [
        # Header
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": "Ciao! Sono SUMI",
                    "weight": "Bolder",
                    "size": "ExtraLarge",
                    "color": "Accent",
                },
                {
                    "type": "TextBlock",
                    "text": "Il tuo assistente su Teams. Ecco cosa posso fare per te:",
                    "spacing": "None",
                    "isSubtle": True,
                    "wrap": True,
                },
            ],
        },
        # Due colonne con descrizione sezioni
        {
            "type": "ColumnSet",
            "spacing": "Large",
            "columns": [
                {
                    "type": "Column",
                    "width": "1",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "\ud83c\udfab Ticket",
                            "weight": "Bolder",
                            "size": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": "Crea, gestisci e monitora i ticket del team",
                            "wrap": True,
                            "size": "Small",
                            "isSubtle": True,
                            "spacing": "Small",
                        },
                    ],
                },
                {
                    "type": "Column",
                    "width": "1",
                    "items": [
                        {
                            "type": "TextBlock",
                            "text": "\ud83d\udcda Knowledge Base",
                            "weight": "Bolder",
                            "size": "Medium",
                        },
                        {
                            "type": "TextBlock",
                            "text": "Cerca nelle procedure e documenti aziendali",
                            "wrap": True,
                            "size": "Small",
                            "isSubtle": True,
                            "spacing": "Small",
                        },
                    ],
                },
            ],
        },
    ]

    return {
        "type": "AdaptiveCard",
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "version": "1.4",
        "body": body,
        "actions": [
            {
                "type": "Action.Submit",
                "title": "\ud83c\udfab Apri Ticket",
                "style": "positive",
                "data": {"action": "section_tickets"},
            },
            {
                "type": "Action.Submit",
                "title": "\ud83d\udcda Apri Knowledge Base",
                "data": {"action": "section_kb"},
            },
        ],
    }


# ═══════════════════════════════════════════════════════════════ #
#                        WELCOME CARD                             #
# ═══════════════════════════════════════════════════════════════ #

def welcome_card(
    assigned_tickets: list[dict] | None = None,
    my_open_tickets: list[dict] | None = None,
) -> dict:
    """Card home della sezione Ticket con riepilogo ticket aperti."""
    body: list[dict] = [
        # Header
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": "\ud83c\udfab  Ticket",
                    "weight": "Bolder",
                    "size": "ExtraLarge",
                    "color": "Accent",
                },
                {
                    "type": "TextBlock",
                    "text": "Gestisci i ticket del team direttamente da Teams",
                    "spacing": "None",
                    "isSubtle": True,
                    "wrap": True,
                },
            ],
        },
    ]

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
        "body": body + _nav_bar_tickets(),
    }


# ═══════════════════════════════════════════════════════════════ #
#                      CREATE TICKET FORM                         #
# ═══════════════════════════════════════════════════════════════ #

def create_ticket_form() -> dict:
    """Form creazione ticket con typeahead per assegnatario e paziente."""
    body = [
        # Header
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [{
                "type": "TextBlock",
                "text": "\ud83d\udcdd  Nuovo Ticket",
                "weight": "Bolder",
                "size": "Large",
                "color": "Accent",
            }],
        },
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
    ], section="tickets")


# ═══════════════════════════════════════════════════════════════ #
#                    CONFIRMATION CARD                            #
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
    ], section="tickets")


# ═══════════════════════════════════════════════════════════════ #
#                    NOTIFICATION CARD                            #
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
            "text": f"{ticket['ticket_number']} — {title_display}",
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
            "title": "\ud83d\udd12  Chiudi Ticket",
            "data": {"action": "close_ticket", "ticket_id": ticket["id"]},
        },
    ], section="tickets")


# ═══════════════════════════════════════════════════════════════ #
#                       TICKET LIST CARD                          #
# ═══════════════════════════════════════════════════════════════ #

def ticket_list_card(tickets: list[dict], list_title: str = "I Miei Ticket") -> dict:
    """Card con lista ticket e dettagli."""
    body: list[dict] = [
        # Header
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
                            "text": f"{len(tickets)} ticket",
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
        return _card(body, section="tickets")

    for i, t in enumerate(tickets[:10]):
        status = t.get("status", "")
        priority = t.get("priority", "")
        title_text = t.get("title") or "(Senza titolo)"
        desc_preview = (t.get("description") or "")[:80]
        assignees = ", ".join(u["name"] for u in t.get("assigned_users", [])) or "—"
        patient = t.get("cliente_nome") or "—"
        created = (t.get("created_at") or "")[:10]
        s = _STATUS.get(status, {"icon": "", "label": status, "color": "Default"})
        p = _PRIORITY.get(priority, {"icon": "", "label": priority})
        msg_count = t.get("messages_count", 0)
        att_count = t.get("attachments_count", 0)

        # Contatori
        counters = []
        if msg_count:
            counters.append(f"\ud83d\udcac {msg_count}")
        if att_count:
            counters.append(f"\ud83d\udcce {att_count}")
        counters_text = "   ".join(counters)

        ticket_container = {
            "type": "Container",
            "separator": i > 0,
            "spacing": "Medium",
            "selectAction": {
                "type": "Action.Submit",
                "data": {"action": "view_ticket", "ticket_id": t["id"]},
            },
            "items": [
                # Riga 1: Numero + Titolo
                {
                    "type": "TextBlock",
                    "text": f"**{t['ticket_number']}**  —  {title_text}",
                    "wrap": True,
                    "weight": "Bolder",
                },
                # Riga 2: Status + Priority badges
                {
                    "type": "ColumnSet",
                    "spacing": "Small",
                    "columns": [
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [_status_badge(status)],
                        },
                        {
                            "type": "Column",
                            "width": "auto",
                            "items": [_priority_badge(priority)],
                        },
                        {
                            "type": "Column",
                            "width": "stretch",
                            "items": [{
                                "type": "TextBlock",
                                "text": f"\ud83d\udcc5 {created}   {counters_text}",
                                "size": "Small",
                                "isSubtle": True,
                                "horizontalAlignment": "Right",
                                "spacing": "None",
                            }],
                        },
                    ],
                },
                # Riga 3: Descrizione preview
                {
                    "type": "TextBlock",
                    "text": desc_preview,
                    "wrap": True,
                    "size": "Small",
                    "isSubtle": True,
                    "maxLines": 2,
                    "spacing": "Small",
                },
                # Riga 4: Assegnatario + Paziente
                {
                    "type": "TextBlock",
                    "text": f"\ud83d\udc64 {assignees}   \u00b7   \ud83c\udfe5 {patient}",
                    "size": "Small",
                    "isSubtle": True,
                    "wrap": True,
                    "spacing": "Small",
                },
            ],
        }
        body.append(ticket_container)

    return _card(body, section="tickets")


# ═══════════════════════════════════════════════════════════════ #
#                     TICKET DETAIL CARD                          #
# ═══════════════════════════════════════════════════════════════ #

def ticket_detail_card(ticket: dict) -> dict:
    """Card con dettaglio completo di un ticket."""
    status = ticket.get("status", "")
    priority = ticket.get("priority", "")
    title_display = ticket.get("title") or "(Senza titolo)"
    assignees = ", ".join(u["name"] for u in ticket.get("assigned_users", [])) or "Nessuno"
    patient = ticket.get("cliente_nome") or "N/A"
    created = (ticket.get("created_at") or "")[:16].replace("T", " ")
    source_label = "\ud83d\udfe3 Teams" if ticket.get("source") == "teams" else "\ud83d\udd35 Admin"
    created_by = ticket.get("created_by_name") or "Teams"

    body: list[dict] = [
        # Header con numero e titolo
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
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
        # Badges: Status + Priority + Source
        {
            "type": "ColumnSet",
            "spacing": "Medium",
            "columns": [
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [_status_badge(status)],
                },
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [_priority_badge(priority)],
                },
                {
                    "type": "Column",
                    "width": "auto",
                    "items": [{
                        "type": "TextBlock",
                        "text": source_label,
                        "size": "Small",
                        "spacing": "None",
                    }],
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
                {"title": "\ud83d\udcc5  Creato", "value": f"{created}  da {created_by}"},
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

    # Allegati
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
            uploaded_by = att.get("uploaded_by_name") or ""
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
                            "text": f"**{filename}**  ({size_str})",
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

    # Ultimi messaggi
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
            msg_items.append({
                "type": "Container",
                "style": "emphasis" if is_teams else "default",
                "spacing": "Small",
                "items": [{
                    "type": "TextBlock",
                    "text": f"{badge}  **{sender}**:  {content}",
                    "wrap": True,
                    "size": "Small",
                }],
            })

        body.append({
            "type": "Container",
            "separator": True,
            "spacing": "Medium",
            "items": msg_items,
        })

    # Azioni contestuali
    actions = []
    if status not in ("chiuso", "risolto"):
        actions.extend([
            {
                "type": "Action.Submit",
                "title": "\u2709\ufe0f  Rispondi",
                "data": {"action": "reply_ticket", "ticket_id": ticket["id"]},
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

    return _card(body, actions=actions or None, section="tickets")


# ═══════════════════════════════════════════════════════════════ #
#                       REPLY FORM CARD                           #
# ═══════════════════════════════════════════════════════════════ #

def reply_form_card(ticket_id: int, ticket_number: str) -> dict:
    """Form per rispondere a un ticket da Teams."""
    body = [
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [{
                "type": "TextBlock",
                "text": f"\u2709\ufe0f  Rispondi a {ticket_number}",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent",
            }],
        },
        {
            "type": "Input.Text",
            "id": "reply_content",
            "placeholder": "Scrivi la tua risposta...",
            "isMultiline": True,
            "isRequired": True,
        },
    ]

    return _card(body, actions=[
        {
            "type": "Action.Submit",
            "title": "\ud83d\udce8  Invia Risposta",
            "style": "positive",
            "data": {"action": "submit_reply", "ticket_id": ticket_id},
        },
    ], section="tickets")


# ═══════════════════════════════════════════════════════════════ #
#                    KNOWLEDGE BASE CARDS                         #
# ═══════════════════════════════════════════════════════════════ #

def kb_chat_card(doc_count: int, chunks_count: int) -> dict:
    """Card iniziale Knowledge Base con stats e campo domanda."""
    body = [
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [
                {
                    "type": "TextBlock",
                    "text": "\ud83d\udcda  Knowledge Base",
                    "weight": "Bolder",
                    "size": "ExtraLarge",
                    "color": "Accent",
                },
                {
                    "type": "TextBlock",
                    "text": f"{doc_count} documenti indicizzati, {chunks_count} chunks",
                    "spacing": "None",
                    "isSubtle": True,
                    "wrap": True,
                },
            ],
        },
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
    ], section="kb")


def kb_response_card(answer: str, sources: list[str], question: str) -> dict:
    """Card risposta Knowledge Base con fonti e campo follow-up."""
    question_display = question[:80] + ("..." if len(question) > 80 else "")

    body: list[dict] = [
        # Header con domanda originale
        {
            "type": "Container",
            "style": "emphasis",
            "bleed": True,
            "items": [{
                "type": "TextBlock",
                "text": f"\ud83d\udcda  {question_display}",
                "weight": "Bolder",
                "size": "Medium",
                "color": "Accent",
                "wrap": True,
            }],
        },
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
    ], section="kb")
