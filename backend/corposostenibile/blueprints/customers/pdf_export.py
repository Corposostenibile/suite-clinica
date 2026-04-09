"""
pdf_export.py – Generazione PDF Cartella Clinica completa.

Produce un PDF professionale con:
- Indice cliccabile (bookmark PDF)
- Immagini check embedded (weekly + iniziali)
- TUTTI i campi di TUTTE le tab del dettaglio paziente
- Design pulito e moderno, leggibile da chiunque
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime
from io import BytesIO
from typing import Any

from flask import current_app
from reportlab.lib import colors as rl_colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    Image,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
#  PALETTE & DESIGN TOKENS
# ═══════════════════════════════════════════════════════════════════════════════
_C = {
    "primary": rl_colors.HexColor("#16a34a"),       # green-600
    "primary_light": rl_colors.HexColor("#dcfce7"),  # green-100
    "primary_dark": rl_colors.HexColor("#166534"),   # green-800
    "blue": rl_colors.HexColor("#2563eb"),
    "blue_light": rl_colors.HexColor("#dbeafe"),
    "violet": rl_colors.HexColor("#7c3aed"),
    "violet_light": rl_colors.HexColor("#ede9fe"),
    "pink": rl_colors.HexColor("#db2777"),
    "pink_light": rl_colors.HexColor("#fce7f3"),
    "amber": rl_colors.HexColor("#d97706"),
    "amber_light": rl_colors.HexColor("#fef3c7"),
    "red": rl_colors.HexColor("#dc2626"),
    "red_light": rl_colors.HexColor("#fee2e2"),
    "slate": rl_colors.HexColor("#334155"),          # slate-700
    "slate_med": rl_colors.HexColor("#64748b"),      # slate-500
    "slate_light": rl_colors.HexColor("#f1f5f9"),    # slate-100
    "border": rl_colors.HexColor("#e2e8f0"),         # slate-200
    "white": rl_colors.white,
    "row_even": rl_colors.HexColor("#f8fafc"),
    "row_odd": rl_colors.white,
}

PAGE_W, PAGE_H = A4
L_MARGIN = 1.8 * cm
R_MARGIN = 1.8 * cm
T_MARGIN = 2.6 * cm
B_MARGIN = 2.0 * cm
CONTENT_W = PAGE_W - L_MARGIN - R_MARGIN
LABEL_W = 5.8 * cm
VALUE_W = CONTENT_W - LABEL_W
COL_W = [LABEL_W, VALUE_W]

# photo sizing
PHOTO_W = 4.8 * cm
PHOTO_H = 6.4 * cm
PHOTO_W_SMALL = 3.6 * cm
PHOTO_H_SMALL = 4.8 * cm


# ═══════════════════════════════════════════════════════════════════════════════
#  STYLES
# ═══════════════════════════════════════════════════════════════════════════════
def _build_styles():
    ss = getSampleStyleSheet()
    add = ss.add
    add(ParagraphStyle("CoverTitle", fontSize=30, leading=36, textColor=_C["primary_dark"],
                        alignment=TA_CENTER, spaceAfter=8, fontName="Helvetica-Bold"))
    add(ParagraphStyle("CoverSub", fontSize=14, leading=18, textColor=_C["slate_med"],
                        alignment=TA_CENTER, spaceAfter=24))
    add(ParagraphStyle("CoverInfo", fontSize=11, leading=15, textColor=_C["slate"],
                        alignment=TA_CENTER, spaceAfter=4))
    add(ParagraphStyle("TOCHeading", fontSize=18, leading=22, textColor=_C["primary_dark"],
                        spaceAfter=14, fontName="Helvetica-Bold"))
    add(ParagraphStyle("TOCEntry", fontSize=10, leading=16, textColor=_C["blue"],
                        leftIndent=8))
    add(ParagraphStyle("TOCSubEntry", fontSize=9, leading=14, textColor=_C["slate_med"],
                        leftIndent=24))
    add(ParagraphStyle("SectionNum", fontSize=16, leading=20, textColor=_C["white"],
                        fontName="Helvetica-Bold"))
    add(ParagraphStyle("SectionTitle", fontSize=14, leading=18, textColor=_C["primary_dark"],
                        fontName="Helvetica-Bold", spaceBefore=18, spaceAfter=6))
    add(ParagraphStyle("SubSection", fontSize=12, leading=16, textColor=_C["slate"],
                        fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=6))
    add(ParagraphStyle("SubSubSection", fontSize=10, leading=14, textColor=_C["slate_med"],
                        fontName="Helvetica-Bold", spaceBefore=8, spaceAfter=4))
    add(ParagraphStyle("Body", fontSize=9, leading=13, textColor=_C["slate"]))
    add(ParagraphStyle("BodyBold", fontSize=9, leading=13, textColor=_C["slate"],
                        fontName="Helvetica-Bold"))
    add(ParagraphStyle("Meta", fontSize=8, leading=11, textColor=_C["slate_med"]))
    add(ParagraphStyle("EmptyNote", fontSize=9, leading=13, textColor=_C["slate_med"],
                        fontStyle="italic"))
    add(ParagraphStyle("PhotoCaption", fontSize=8, leading=10, textColor=_C["slate_med"],
                        alignment=TA_CENTER))
    return ss


# ═══════════════════════════════════════════════════════════════════════════════
#  FORMAT HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _fv(value: Any) -> str:
    """Format value for display."""
    if value is None:
        return "-"
    if hasattr(value, "value"):
        value = value.value
    if isinstance(value, bool):
        return "Sì" if value else "No"
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y %H:%M")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, (list, tuple, set)):
        if not value:
            return "-"
        return ", ".join(_fv(i) for i in value)
    t = str(value).strip()
    return t if t else "-"


def _user(u) -> str:
    """Readable user label."""
    if not u:
        return "-"
    name = getattr(u, "full_name", None) or getattr(u, "email", None)
    return str(name) if name else f"Utente #{getattr(u, 'id', '?')}"


def _users_m2m(m2m_list, single_user=None) -> str:
    """Format M2M user list, fallback to single FK user."""
    if m2m_list:
        return ", ".join(_user(u) for u in m2m_list)
    return _user(single_user)


def _esc(text: str) -> str:
    """Escape HTML entities for ReportLab Paragraphs."""
    if not text:
        return ""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace("\n", "<br/>"))


# ═══════════════════════════════════════════════════════════════════════════════
#  IMAGE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _resolve_image_path(path_or_url: str | None) -> str | None:
    """Resolve a stored photo path to an absolute filesystem path."""
    if not path_or_url:
        return None
    # Already an absolute path that exists
    if os.path.isabs(path_or_url) and os.path.isfile(path_or_url):
        return path_or_url
    # External URL — skip (can't embed)
    if path_or_url.startswith("http"):
        return None
    # Try to resolve from UPLOAD_FOLDER
    upload_folder = current_app.config.get("UPLOAD_FOLDER", "uploads")
    # Extract relative part
    rel = path_or_url
    for prefix in ("/uploads/", "/static/uploads/", "uploads/"):
        idx = path_or_url.find(prefix)
        if idx != -1:
            rel = path_or_url[idx + len(prefix):]
            break
    full = os.path.join(upload_folder, rel)
    if os.path.isfile(full):
        return full
    return None


def _make_image(path: str | None, max_w=PHOTO_W, max_h=PHOTO_H):
    """Create a reportlab Image flowable, or None if unavailable."""
    resolved = _resolve_image_path(path)
    if not resolved:
        return None
    try:
        img = Image(resolved)
        iw, ih = img.imageWidth, img.imageHeight
        if iw <= 0 or ih <= 0:
            return None
        ratio = min(max_w / iw, max_h / ih, 1.0)
        img.drawWidth = iw * ratio
        img.drawHeight = ih * ratio
        img._restrictSize(max_w, max_h)
        return img
    except Exception as exc:
        logger.warning("Cannot embed image %s: %s", resolved, exc)
        return None


def _photo_row(ss, photos: list[tuple[str, str | None]], caption_style="PhotoCaption"):
    """Build a table row of photos with captions. Returns flowable or None."""
    cells = []
    for label, path in photos:
        img = _make_image(path)
        if img:
            cells.append([img, Paragraph(label, ss[caption_style])])
    if not cells:
        return None
    # Build a horizontal table
    data = [[c[0] for c in cells]]
    captions = [[c[1] for c in cells]]
    n = len(cells)
    col_w = [CONTENT_W / n] * n
    t = Table(data + captions, colWidths=col_w)
    t.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


# ═══════════════════════════════════════════════════════════════════════════════
#  TABLE HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def _data_table(ss, rows: list[tuple[str, Any]], col_widths=None):
    """Two-column label/value table with zebra striping."""
    if col_widths is None:
        col_widths = COL_W
    if not rows:
        return Paragraph("Nessun dato disponibile.", ss["EmptyNote"])
    data = []
    for label, value in rows:
        rendered = _fv(value)
        data.append([
            Paragraph(f"<b>{_esc(str(label))}</b>", ss["Body"]),
            Paragraph(_esc(rendered), ss["Body"]),
        ])
    t = Table(data, colWidths=col_widths, repeatRows=0)
    style_cmds = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, _C["border"]),
        ("BACKGROUND", (0, 0), (0, -1), _C["slate_light"]),
    ]
    # Zebra striping on value column
    for i in range(len(data)):
        bg = _C["row_even"] if i % 2 == 0 else _C["row_odd"]
        style_cmds.append(("BACKGROUND", (1, i), (1, i), bg))
    t.setStyle(TableStyle(style_cmds))
    t.splitInRow = 1
    return t


def _section_header(ss, number: str, title: str, color=None):
    """Colored section header with bookmark anchor."""
    c = color or _C["primary"]
    anchor = f"section_{number.replace('.', '_')}"
    # Colored bar with number + title
    bar_data = [[
        Paragraph(f'<a name="{anchor}"/><b>{_esc(number)}</b>', ss["SectionNum"]),
        Paragraph(f"<b>{_esc(title)}</b>",
                  ParagraphStyle("_sh", parent=ss["SectionTitle"], textColor=c)),
    ]]
    bar = Table(bar_data, colWidths=[1.2 * cm, CONTENT_W - 1.2 * cm])
    bar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), c),
        ("BACKGROUND", (1, 0), (1, 0), rl_colors.HexColor("#f0fdf4") if c == _C["primary"]
         else rl_colors.Color(c.red, c.green, c.blue, 0.08)),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (0, 0), 6),
        ("LEFTPADDING", (1, 0), (1, 0), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return bar


def _sub_header(ss, text: str):
    return Paragraph(f"<b>{_esc(text)}</b>", ss["SubSection"])


def _sub_sub_header(ss, text: str):
    return Paragraph(f"<b>{_esc(text)}</b>", ss["SubSubSection"])


# ═══════════════════════════════════════════════════════════════════════════════
#  COVER PAGE
# ═══════════════════════════════════════════════════════════════════════════════
def _build_cover(story, ss, cliente):
    story.append(Spacer(1, 2.5 * cm))
    # Decorative line
    line_data = [[""]]
    line = Table(line_data, colWidths=[CONTENT_W])
    line.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (0, 0), 3, _C["primary"]),
    ]))
    story.append(line)
    story.append(Spacer(1, 1 * cm))
    story.append(Paragraph("Cartella Clinica", ss["CoverTitle"]))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(f"{_esc(_fv(cliente.nome_cognome))}", ss["CoverSub"]))
    story.append(Spacer(1, 1 * cm))

    info = [
        ("Stato", _fv(cliente.stato_cliente)),
        ("Programma", _fv(cliente.programma_attuale)),
        ("Data di nascita", _fv(cliente.data_di_nascita)),
        ("Generato il", datetime.utcnow().strftime("%d/%m/%Y alle %H:%M UTC")),
    ]
    cover_data = []
    for label, val in info:
        cover_data.append([
            Paragraph(f"<b>{label}</b>", ss["Body"]),
            Paragraph(val, ss["Body"]),
        ])
    t = Table(cover_data, colWidths=[5 * cm, 8 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), _C["primary_light"]),
        ("BOX", (0, 0), (-1, -1), 1, _C["primary"]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.5, _C["border"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    # Center
    wrapper = Table([[t]], colWidths=[CONTENT_W])
    wrapper.setStyle(TableStyle([("ALIGN", (0, 0), (0, 0), "CENTER")]))
    story.append(wrapper)
    story.append(PageBreak())


# ═══════════════════════════════════════════════════════════════════════════════
#  TABLE OF CONTENTS
# ═══════════════════════════════════════════════════════════════════════════════
_TOC_SECTIONS = [
    ("1", "Anagrafica", [
        ("1.1", "Dati Personali"),
        ("1.2", "Storia e Obiettivi"),
        ("1.3", "Programma e Abbonamento"),
        ("1.4", "Date Piani Servizio"),
    ]),
    ("2", "Team", [
        ("2.1", "Team Attuale"),
        ("2.2", "Storico Assegnazioni"),
    ]),
    ("3", "Interventi Health Manager", [
        ("3.1", "Onboarding"),
        ("3.2", "Customer Care"),
        ("3.3", "Check-in"),
        ("3.4", "Rinnovo"),
        ("3.5", "Continuity Call"),
    ]),
    ("4", "Nutrizione", [
        ("4.1", "Stato e Configurazione"),
        ("4.2", "Patologie"),
        ("4.3", "Alert e Note"),
        ("4.4", "Anamnesi"),
        ("4.5", "Diario"),
        ("4.6", "Piani Alimentari"),
    ]),
    ("5", "Coaching", [
        ("5.1", "Stato e Configurazione"),
        ("5.2", "Patologie"),
        ("5.3", "Alert e Note"),
        ("5.4", "Anamnesi"),
        ("5.5", "Diario"),
        ("5.6", "Luoghi Allenamento"),
        ("5.7", "Piani Allenamento"),
        ("5.8", "Live Trainings"),
    ]),
    ("6", "Psicologia", [
        ("6.1", "Stato e Configurazione"),
        ("6.2", "Patologie"),
        ("6.3", "Alert e Note"),
        ("6.4", "Anamnesi"),
        ("6.5", "Diario"),
    ]),
    ("7", "Progresso e Metriche", [
        ("7.1", "Peso"),
        ("7.2", "Medie Benessere"),
    ]),
    ("8", "Check Iniziali", [
        ("8.1", "Risposte Form"),
        ("8.2", "Foto Check Iniziali"),
    ]),
    ("9", "Check Periodici", [
        ("9.1", "Configurazione"),
        ("9.2", "Weekly Check"),
        ("9.3", "Minor Check"),
        ("9.4", "DCA Check"),
    ]),
    ("10", "Marketing e Extra", [
        ("10.1", "Consensi e Contenuti Marketing"),
        ("10.2", "Video Recensione"),
        ("10.3", "Call Bonus"),
        ("10.4", "Referral"),
        ("10.5", "Trustpilot"),
    ]),
    ("11", "Allegati e Documenti", []),
]


def _build_toc(story, ss):
    story.append(Paragraph("Indice", ss["TOCHeading"]))
    for num, title, subs in _TOC_SECTIONS:
        anchor = f"section_{num.replace('.', '_')}"
        story.append(Paragraph(
            f'<a href="#{anchor}" color="#2563eb"><b>{num}.</b> {_esc(title)}</a>',
            ss["TOCEntry"]))
        for sub_num, sub_title in subs:
            sub_anchor = f"section_{sub_num.replace('.', '_')}"
            story.append(Paragraph(
                f'<a href="#{sub_anchor}" color="#64748b">{sub_num} {_esc(sub_title)}</a>',
                ss["TOCSubEntry"]))
    story.append(PageBreak())


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN EXPORT FUNCTION
# ═══════════════════════════════════════════════════════════════════════════════
def generate_clinical_folder_pdf(cliente, db_session) -> BytesIO:
    """Generate the complete clinical folder PDF. Returns a BytesIO buffer."""
    from corposostenibile.models import (
        CallBonus,
        CartellaClinica,
        CheckInIntervention,
        ClientCheckAssignment,
        ClientCheckResponse,
        ClienteMarketingContent,
        ClienteProfessionistaHistory,
        ContinuityCallIntervention,
        CustomerCareIntervention,
        DCACheck,
        DCACheckResponse,
        MealPlan,
        MinorCheck,
        MinorCheckResponse,
        RinnovoIntervention,
        ServiceAnamnesi,
        ServiceDiaryEntry,
        Ticket,
        TrainingLocation,
        TrainingPlan,
        TrustpilotReview,
        VideoReviewRequest,
        WeeklyCheck,
        WeeklyCheckResponse,
    )

    cid = cliente.cliente_id
    ss = _build_styles()

    # ── Fetch ALL related data ──────────────────────────────────────────
    weekly_checks = WeeklyCheck.query.filter_by(cliente_id=cid).all()
    weekly_responses = (
        WeeklyCheckResponse.query.join(WeeklyCheck)
        .filter(WeeklyCheck.cliente_id == cid)
        .order_by(WeeklyCheckResponse.submit_date.desc()).all()
    )
    check_assignments = ClientCheckAssignment.query.filter_by(cliente_id=cid).all()
    minor_responses = (
        MinorCheckResponse.query.join(MinorCheck)
        .filter(MinorCheck.cliente_id == cid)
        .order_by(MinorCheckResponse.submit_date.desc()).all()
    )
    dca_responses = (
        DCACheckResponse.query.join(DCACheck)
        .filter(DCACheck.cliente_id == cid)
        .order_by(DCACheckResponse.submit_date.desc()).all()
    )
    anamnesi_entries = ServiceAnamnesi.query.filter_by(cliente_id=cid).all()
    diary_entries = (
        ServiceDiaryEntry.query.filter_by(cliente_id=cid)
        .order_by(ServiceDiaryEntry.entry_date.desc()).all()
    )
    meal_plans = MealPlan.query.filter_by(cliente_id=cid).order_by(MealPlan.created_at.desc()).all()
    training_plans = TrainingPlan.query.filter_by(cliente_id=cid).order_by(TrainingPlan.created_at.desc()).all()
    training_locations = TrainingLocation.query.filter_by(cliente_id=cid).order_by(TrainingLocation.start_date.desc()).all()
    team_history = (
        ClienteProfessionistaHistory.query.filter_by(cliente_id=cid)
        .order_by(ClienteProfessionistaHistory.data_dal.desc()).all()
    )
    cc_interventions = CustomerCareIntervention.query.filter_by(cliente_id=cid).order_by(CustomerCareIntervention.intervention_date.desc()).all()
    ci_interventions = CheckInIntervention.query.filter_by(cliente_id=cid).order_by(CheckInIntervention.intervention_date.desc()).all()
    rinnovo_interventions = RinnovoIntervention.query.filter_by(cliente_id=cid).order_by(RinnovoIntervention.intervention_date.desc()).all()
    continuity_interventions = ContinuityCallIntervention.query.filter_by(cliente_id=cid).order_by(ContinuityCallIntervention.intervention_date.desc()).all()
    trustpilot_reviews = TrustpilotReview.query.filter_by(cliente_id=cid).order_by(TrustpilotReview.data_richiesta.desc()).all()
    video_reviews = VideoReviewRequest.query.filter_by(cliente_id=cid).order_by(VideoReviewRequest.created_at.desc()).all()
    cartelle = CartellaClinica.query.filter_by(cliente_id=cid).all()

    try:
        call_bonus_list = CallBonus.query.filter_by(cliente_id=cid).order_by(CallBonus.data_richiesta.desc()).all()
    except Exception:
        call_bonus_list = []
    try:
        tickets = Ticket.query.filter_by(cliente_id=cid).all()
    except Exception:
        tickets = []
    try:
        marketing_contents = ClienteMarketingContent.query.filter_by(cliente_id=cid).order_by(ClienteMarketingContent.checked_date.desc()).all()
    except Exception:
        marketing_contents = []

    # ── Metriche peso e rating ──────────────────────────────────────────
    first_weight = last_weight = None
    rating_keys = ("energy", "sleep", "mood", "motivation", "digestion", "strength", "hunger")
    rating_sums = {k: 0 for k in rating_keys}
    rating_counts = {k: 0 for k in rating_keys}
    for wr in weekly_responses:
        w = getattr(wr, "weight", None)
        if w:
            if last_weight is None:
                last_weight = w
            first_weight = w
        for rk in rating_keys:
            rv = getattr(wr, f"{rk}_rating", None)
            if rv is not None:
                rating_sums[rk] += rv
                rating_counts[rk] += 1
    weight_delta = round(last_weight - first_weight, 1) if first_weight and last_weight else None
    avg_ratings = {k: round(rating_sums[k] / rating_counts[k], 1) if rating_counts[k] else None for k in rating_keys}

    # ── Build PDF ──────────────────────────────────────────────────────
    buf = BytesIO()
    frame = Frame(L_MARGIN, B_MARGIN, CONTENT_W, PAGE_H - T_MARGIN - B_MARGIN, id="main")

    def _header_footer(canvas, doc):
        canvas.saveState()
        # Header bar
        canvas.setFillColor(_C["primary"])
        canvas.rect(0, PAGE_H - 1.6 * cm, PAGE_W, 1.6 * cm, fill=True, stroke=False)
        canvas.setFillColor(_C["white"])
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(L_MARGIN, PAGE_H - 1.15 * cm,
                          f"Cartella Clinica — {cliente.nome_cognome or 'N/D'}")
        canvas.setFont("Helvetica", 8)
        canvas.drawRightString(PAGE_W - R_MARGIN, PAGE_H - 1.15 * cm,
                               f"Pag. {doc.page}")
        # Footer
        canvas.setStrokeColor(_C["border"])
        canvas.line(L_MARGIN, B_MARGIN - 0.4 * cm, PAGE_W - R_MARGIN, B_MARGIN - 0.4 * cm)
        canvas.setFillColor(_C["slate_med"])
        canvas.setFont("Helvetica", 7)
        canvas.drawString(L_MARGIN, B_MARGIN - 0.75 * cm,
                          f"Generato il {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC — Documento riservato")
        canvas.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=L_MARGIN, rightMargin=R_MARGIN,
                          topMargin=T_MARGIN, bottomMargin=B_MARGIN)
    doc.addPageTemplates([PageTemplate(id="all", frames=[frame], onPage=_header_footer)])

    story: list = []

    # ══════════════════════════════════════════════════════════════════════
    #  COPERTINA + INDICE
    # ══════════════════════════════════════════════════════════════════════
    _build_cover(story, ss, cliente)
    _build_toc(story, ss)

    # ══════════════════════════════════════════════════════════════════════
    #  1. ANAGRAFICA
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "1", "Anagrafica"))
    story.append(Spacer(1, 4))

    # 1.1
    story.append(_sub_header(ss, '<a name="section_1_1"/>1.1 Dati Personali'))
    story.append(_data_table(ss, [
        ("Nome e Cognome", cliente.nome_cognome),
        ("Data di Nascita", cliente.data_di_nascita),
        ("Genere", cliente.genere),
        ("Email", cliente.mail),
        ("Telefono", cliente.numero_telefono),
        ("Professione", cliente.professione),
        ("Paese", cliente.paese),
        ("Indirizzo", cliente.indirizzo),
        ("Origine", getattr(cliente, "origine", None)),
    ]))
    story.append(Spacer(1, 8))

    # 1.2
    story.append(_sub_header(ss, '<a name="section_1_2"/>1.2 Storia e Obiettivi'))
    story.append(_data_table(ss, [
        ("Storia del Cliente", cliente.storia_cliente),
        ("Problema", cliente.problema),
        ("Paure", cliente.paure),
        ("Conseguenze", cliente.conseguenze),
    ]))
    story.append(Spacer(1, 8))

    # 1.3
    story.append(_sub_header(ss, '<a name="section_1_3"/>1.3 Programma e Abbonamento'))
    story.append(_data_table(ss, [
        ("Programma Attuale", cliente.programma_attuale),
        ("Dettaglio Programma", cliente.programma_attuale_dettaglio),
        ("Macrocategoria", cliente.macrocategoria),
        ("Obiettivo", cliente.obiettivo_semplicato),
        ("Obiettivo Dettagliato", cliente.obiettivo_cliente),
        ("Tipologia Cliente", cliente.tipologia_cliente),
        ("Stato Cliente", cliente.stato_cliente),
        ("Tipo Supporto Nutrizione", cliente.tipologia_supporto_nutrizione),
        ("Tipo Supporto Coach", cliente.tipologia_supporto_coach),
        ("Inizio Abbonamento", cliente.data_inizio_abbonamento),
        ("Durata Programma (giorni)", cliente.durata_programma_giorni),
        ("Data Rinnovo", cliente.data_rinnovo),
        ("Note Rinnovo", cliente.note_rinnovo),
        ("Modalità Pagamento", cliente.modalita_pagamento),
        ("Deposito Iniziale", cliente.deposito_iniziale),
    ]))
    story.append(Spacer(1, 8))

    # 1.4
    story.append(_sub_header(ss, '<a name="section_1_4"/>1.4 Date Piani Servizio'))
    story.append(_data_table(ss, [
        ("Inizio Nutrizione", cliente.data_inizio_nutrizione),
        ("Durata Nutrizione (gg)", cliente.durata_nutrizione_giorni),
        ("Scadenza Nutrizione", cliente.data_scadenza_nutrizione),
        ("Dieta Dal", cliente.dieta_dal),
        ("Nuova Dieta Dal", cliente.nuova_dieta_dal),
        ("Inizio Coach", cliente.data_inizio_coach),
        ("Durata Coach (gg)", cliente.durata_coach_giorni),
        ("Scadenza Coach", cliente.data_scadenza_coach),
        ("Allenamento Dal", cliente.allenamento_dal),
        ("Nuovo Allenamento Il", cliente.nuovo_allenamento_il),
        ("Inizio Psicologia", cliente.data_inizio_psicologia),
        ("Durata Psicologia (gg)", cliente.durata_psicologia_giorni),
        ("Scadenza Psicologia", cliente.data_scadenza_psicologia),
    ]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  2. TEAM
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "2", "Team", _C["blue"]))
    story.append(Spacer(1, 4))

    # 2.1
    story.append(_sub_header(ss, '<a name="section_2_1"/>2.1 Team Attuale'))
    story.append(_data_table(ss, [
        ("Nutrizionista", _users_m2m(cliente.nutrizionisti_multipli, cliente.nutrizionista_user)),
        ("Coach", _users_m2m(cliente.coaches_multipli, cliente.coach_user)),
        ("Psicologa", _users_m2m(cliente.psicologi_multipli, cliente.psicologa_user)),
        ("Consulente", _users_m2m(getattr(cliente, "consulenti_multipli", None), cliente.consulente_user)),
        ("Health Manager", _user(cliente.health_manager_user)),
    ]))
    story.append(Spacer(1, 8))

    # 2.2
    story.append(_sub_header(ss, '<a name="section_2_2"/>2.2 Storico Assegnazioni'))
    if team_history:
        rows = []
        for h in team_history:
            status = "Attivo" if h.is_active else "Terminato"
            detail = f"Dal {_fv(h.data_dal)} al {_fv(h.data_al)} — {status}"
            if h.motivazione_aggiunta:
                detail += f" | Motivo: {h.motivazione_aggiunta}"
            if h.motivazione_interruzione:
                detail += f" | Interruzione: {h.motivazione_interruzione}"
            rows.append((f"{_fv(h.tipo_professionista)} — {_user(h.professionista)}", detail))
        story.append(_data_table(ss, rows))
    else:
        story.append(Paragraph("Nessuno storico disponibile.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  3. INTERVENTI HEALTH MANAGER
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "3", "Interventi Health Manager", _C["amber"]))
    story.append(Spacer(1, 4))

    # 3.1 Onboarding
    story.append(_sub_header(ss, '<a name="section_3_1"/>3.1 Onboarding'))
    story.append(_data_table(ss, [
        ("Data Onboarding", cliente.onboarding_date),
        ("Note Criticità Iniziali", cliente.note_criticita_iniziali),
        ("Loom Link", cliente.loom_link),
    ]))
    story.append(Spacer(1, 8))

    def _intervention_section(anchor, title, items):
        story.append(_sub_header(ss, f'<a name="{anchor}"/>{title}'))
        if items:
            rows = []
            for i in items:
                note = (i.notes or "")
                loom = f" | Loom: {i.loom_link}" if getattr(i, "loom_link", None) else ""
                rows.append((_fv(i.intervention_date), f"{_user(i.created_by)}: {note}{loom}"))
            story.append(_data_table(ss, rows))
        else:
            story.append(Paragraph("Nessun intervento registrato.", ss["EmptyNote"]))
        story.append(Spacer(1, 8))

    _intervention_section("section_3_2", "3.2 Customer Care", cc_interventions)
    _intervention_section("section_3_3", "3.3 Check-in", ci_interventions)
    _intervention_section("section_3_4", "3.4 Rinnovo", rinnovo_interventions)
    _intervention_section("section_3_5", "3.5 Continuity Call", continuity_interventions)

    # ══════════════════════════════════════════════════════════════════════
    #  4. NUTRIZIONE
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "4", "Nutrizione"))
    story.append(Spacer(1, 4))

    # 4.1
    story.append(_sub_header(ss, '<a name="section_4_1"/>4.1 Stato e Configurazione'))
    story.append(_data_table(ss, [
        ("Nutrizionista", _users_m2m(cliente.nutrizionisti_multipli, cliente.nutrizionista_user)),
        ("Stato Servizio", cliente.stato_nutrizione),
        ("Stato Chat", cliente.stato_cliente_chat_nutrizione),
        ("Reach Out", cliente.reach_out_nutrizione),
        ("Call Iniziale", cliente.call_iniziale_nutrizionista),
        ("Data Call Iniziale", cliente.data_call_iniziale_nutrizionista),
        ("Dieta Dal", cliente.dieta_dal),
        ("Nuova Dieta Dal", cliente.nuova_dieta_dal),
        ("Piani Alimentari", len(meal_plans)),
    ]))
    story.append(Spacer(1, 8))

    # 4.2 Patologie
    story.append(_sub_header(ss, '<a name="section_4_2"/>4.2 Patologie'))
    pat_nutri = []
    if cliente.nessuna_patologia:
        pat_nutri.append(("Nessuna Patologia", "Sì"))
    for fn, lbl in [
        ("patologia_ibs", "IBS"), ("patologia_reflusso", "Reflusso"),
        ("patologia_gastrite", "Gastrite"), ("patologia_dca", "DCA"),
        ("patologia_insulino_resistenza", "Insulino-Resistenza"),
        ("patologia_diabete", "Diabete"), ("patologia_dislipidemie", "Dislipidemie"),
        ("patologia_steatosi_epatica", "Steatosi Epatica"),
        ("patologia_ipertensione", "Ipertensione"), ("patologia_pcos", "PCOS"),
        ("patologia_endometriosi", "Endometriosi"),
        ("patologia_obesita_sindrome", "Obesità/Sindrome Metabolica"),
        ("patologia_osteoporosi", "Osteoporosi"),
        ("patologia_diverticolite", "Diverticolite"), ("patologia_crohn", "Crohn"),
        ("patologia_stitichezza", "Stitichezza"), ("patologia_tiroidee", "Tiroidee"),
    ]:
        if getattr(cliente, fn, False):
            pat_nutri.append((lbl, "Sì"))
    if cliente.patologia_altro:
        pat_nutri.append(("Altro", cliente.patologia_altro))
    story.append(_data_table(ss, pat_nutri) if pat_nutri else Paragraph("Nessuna patologia indicata.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 4.3 Alert e Note
    story.append(_sub_header(ss, '<a name="section_4_3"/>4.3 Alert e Note'))
    story.append(_data_table(ss, [
        ("Alert", cliente.alert_nutrizione),
        ("Anamnesi (vecchio campo)", cliente.storia_nutrizione),
        ("Diario (vecchio campo)", cliente.note_extra_nutrizione),
    ]))
    story.append(Spacer(1, 8))

    # 4.4 Anamnesi
    story.append(_sub_header(ss, '<a name="section_4_4"/>4.4 Anamnesi'))
    anamnesi_nutri = next((a for a in anamnesi_entries if a.service_type == "nutrizione"), None)
    if anamnesi_nutri:
        story.append(_data_table(ss, [
            ("Contenuto", anamnesi_nutri.content),
            ("Creato il", anamnesi_nutri.created_at),
        ]))
    else:
        story.append(Paragraph("Nessuna anamnesi registrata.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 4.5 Diario
    story.append(_sub_header(ss, '<a name="section_4_5"/>4.5 Diario'))
    diary_nutri = [d for d in diary_entries if d.service_type == "nutrizione"]
    if diary_nutri:
        rows = [(_fv(d.entry_date), f"{_user(d.author)}: {d.content}") for d in diary_nutri]
        story.append(_data_table(ss, rows))
    else:
        story.append(Paragraph("Nessuna voce nel diario.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 4.6 Piani Alimentari
    story.append(_sub_header(ss, '<a name="section_4_6"/>4.6 Piani Alimentari'))
    if meal_plans:
        for mp in meal_plans:
            story.append(_sub_sub_header(ss, f"{mp.name} ({_fv(mp.start_date)} - {_fv(mp.end_date)})"))
            story.append(_data_table(ss, [
                ("Attivo", mp.is_active),
                ("Calorie Target", mp.target_calories),
                ("Proteine (g)", mp.target_proteins),
                ("Carboidrati (g)", mp.target_carbohydrates),
                ("Grassi (g)", mp.target_fats),
                ("Note", mp.notes),
                ("Creato da", _user(mp.created_by)),
            ]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Nessun piano alimentare.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  5. COACHING
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "5", "Coaching", _C["blue"]))
    story.append(Spacer(1, 4))

    # 5.1
    story.append(_sub_header(ss, '<a name="section_5_1"/>5.1 Stato e Configurazione'))
    story.append(_data_table(ss, [
        ("Coach", _users_m2m(cliente.coaches_multipli, cliente.coach_user)),
        ("Stato Servizio", cliente.stato_coach),
        ("Stato Chat", cliente.stato_cliente_chat_coaching),
        ("Reach Out", cliente.reach_out_coaching),
        ("Call Iniziale", cliente.call_iniziale_coach),
        ("Data Call Iniziale", cliente.data_call_iniziale_coach),
        ("Luogo Allenamento", cliente.luogo_di_allenamento),
        ("Allenamento Dal", cliente.allenamento_dal),
        ("Nuovo Allenamento Il", cliente.nuovo_allenamento_il),
        ("Live Trainings Acquistate", getattr(cliente, "live_trainings_acquistate", None)),
        ("Live Trainings Svolte", getattr(cliente, "live_trainings_svolte", None)),
        ("Piani Allenamento", len(training_plans)),
    ]))
    story.append(Spacer(1, 8))

    # 5.2 Patologie
    story.append(_sub_header(ss, '<a name="section_5_2"/>5.2 Patologie'))
    pat_coach = []
    if getattr(cliente, "nessuna_patologia_coach", False):
        pat_coach.append(("Nessuna Patologia", "Sì"))
    for fn, lbl in [
        ("patologia_coach_dca", "DCA"), ("patologia_coach_ipertensione", "Ipertensione"),
        ("patologia_coach_pcos", "PCOS"),
        ("patologia_coach_sindrome_metabolica", "Sindrome Metabolica/Obesità"),
        ("patologia_coach_endometriosi", "Endometriosi"),
        ("patologia_coach_osteoporosi", "Osteoporosi"),
        ("patologia_coach_menopausa", "Menopausa"), ("patologia_coach_artrosi", "Artrosi"),
        ("patologia_coach_artrite", "Artrite"),
        ("patologia_coach_sclerosi_multipla", "Sclerosi Multipla"),
        ("patologia_coach_fibromialgia", "Fibromialgia"),
        ("patologia_coach_lipedema", "Lipedema"), ("patologia_coach_linfedema", "Linfedema"),
        ("patologia_coach_gravidanza", "Gravidanza"),
        ("patologia_coach_riabilitazione_anca", "Riabilitazione Anca"),
        ("patologia_coach_riabilitazione_spalla", "Riabilitazione Spalla"),
        ("patologia_coach_riabilitazione_ginocchio", "Riabilitazione Ginocchio"),
        ("patologia_coach_lombalgia", "Lombalgia"),
        ("patologia_coach_spondilolistesi", "Spondilolistesi"),
        ("patologia_coach_spondilolisi", "Spondilolisi"),
    ]:
        if getattr(cliente, fn, False):
            pat_coach.append((lbl, "Sì"))
    if getattr(cliente, "patologia_coach_altro", None):
        pat_coach.append(("Altro", cliente.patologia_coach_altro))
    story.append(_data_table(ss, pat_coach) if pat_coach else Paragraph("Nessuna patologia indicata.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 5.3 Alert e Note
    story.append(_sub_header(ss, '<a name="section_5_3"/>5.3 Alert e Note'))
    story.append(_data_table(ss, [
        ("Alert", cliente.alert_coaching),
        ("Anamnesi (vecchio campo)", cliente.storia_coach),
        ("Diario (vecchio campo)", cliente.note_extra_coach),
    ]))
    story.append(Spacer(1, 8))

    # 5.4 Anamnesi
    story.append(_sub_header(ss, '<a name="section_5_4"/>5.4 Anamnesi'))
    anamnesi_coach = next((a for a in anamnesi_entries if a.service_type == "coaching"), None)
    if anamnesi_coach:
        story.append(_data_table(ss, [("Contenuto", anamnesi_coach.content), ("Creato il", anamnesi_coach.created_at)]))
    else:
        story.append(Paragraph("Nessuna anamnesi registrata.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 5.5 Diario
    story.append(_sub_header(ss, '<a name="section_5_5"/>5.5 Diario'))
    diary_coach = [d for d in diary_entries if d.service_type == "coaching"]
    if diary_coach:
        story.append(_data_table(ss, [(_fv(d.entry_date), f"{_user(d.author)}: {d.content}") for d in diary_coach]))
    else:
        story.append(Paragraph("Nessuna voce nel diario.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 5.6 Luoghi
    story.append(_sub_header(ss, '<a name="section_5_6"/>5.6 Luoghi Allenamento'))
    if training_locations:
        story.append(_data_table(ss, [
            (f"{_fv(tl.location)} dal {_fv(tl.start_date)}", tl.notes or "-") for tl in training_locations
        ]))
    else:
        story.append(Paragraph("Nessun luogo registrato.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 5.7 Piani Allenamento
    story.append(_sub_header(ss, '<a name="section_5_7"/>5.7 Piani Allenamento'))
    if training_plans:
        for tp in training_plans:
            story.append(_sub_sub_header(ss, f"{tp.name} ({_fv(tp.start_date)} - {_fv(tp.end_date)})"))
            story.append(_data_table(ss, [
                ("Attivo", tp.is_active), ("Note", tp.notes), ("Creato da", _user(tp.created_by)),
            ]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Nessun piano allenamento.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 5.8 Live Trainings
    story.append(_sub_header(ss, '<a name="section_5_8"/>5.8 Live Trainings'))
    story.append(_data_table(ss, [
        ("Acquistate", getattr(cliente, "live_trainings_acquistate", None)),
        ("Svolte", getattr(cliente, "live_trainings_svolte", None)),
    ]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  6. PSICOLOGIA
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "6", "Psicologia", _C["violet"]))
    story.append(Spacer(1, 4))

    # 6.1
    story.append(_sub_header(ss, '<a name="section_6_1"/>6.1 Stato e Configurazione'))
    story.append(_data_table(ss, [
        ("Psicologa", _users_m2m(cliente.psicologi_multipli, cliente.psicologa_user)),
        ("Stato Servizio", cliente.stato_psicologia),
        ("Stato Chat", cliente.stato_cliente_chat_psicologia),
        ("Reach Out", cliente.reach_out_psicologia),
        ("Call Iniziale", cliente.call_iniziale_psicologa),
        ("Data Call Iniziale", cliente.data_call_iniziale_psicologia),
        ("Sedute Comprate", cliente.sedute_psicologia_comprate),
        ("Sedute Svolte", cliente.sedute_psicologia_svolte),
    ]))
    story.append(Spacer(1, 8))

    # 6.2 Patologie
    story.append(_sub_header(ss, '<a name="section_6_2"/>6.2 Patologie'))
    pat_psico = []
    if getattr(cliente, "nessuna_patologia_psico", False):
        pat_psico.append(("Nessuna Patologia", "Sì"))
    for fn, lbl in [
        ("patologia_psico_dca", "DCA"),
        ("patologia_psico_obesita_psicoemotiva", "Obesità Psicoemotiva"),
        ("patologia_psico_ansia_umore_cibo", "Ansia/Umore/Cibo"),
        ("patologia_psico_comportamenti_disfunzionali", "Comportamenti Disfunzionali"),
        ("patologia_psico_immagine_corporea", "Immagine Corporea"),
        ("patologia_psico_psicosomatiche", "Psicosomatiche"),
        ("patologia_psico_relazionali_altro", "Relazionali/Altro"),
    ]:
        if getattr(cliente, fn, False):
            pat_psico.append((lbl, "Sì"))
    if getattr(cliente, "patologia_psico_altro", None):
        pat_psico.append(("Altro", cliente.patologia_psico_altro))
    story.append(_data_table(ss, pat_psico) if pat_psico else Paragraph("Nessuna patologia indicata.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 6.3 Alert e Note
    story.append(_sub_header(ss, '<a name="section_6_3"/>6.3 Alert e Note'))
    story.append(_data_table(ss, [
        ("Alert", cliente.alert_psicologia),
        ("Anamnesi (vecchio campo)", cliente.storia_psicologica),
        ("Diario (vecchio campo)", cliente.note_extra_psicologa),
    ]))
    story.append(Spacer(1, 8))

    # 6.4 Anamnesi
    story.append(_sub_header(ss, '<a name="section_6_4"/>6.4 Anamnesi'))
    anamnesi_psico = next((a for a in anamnesi_entries if a.service_type == "psicologia"), None)
    if anamnesi_psico:
        story.append(_data_table(ss, [("Contenuto", anamnesi_psico.content), ("Creato il", anamnesi_psico.created_at)]))
    else:
        story.append(Paragraph("Nessuna anamnesi registrata.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 6.5 Diario
    story.append(_sub_header(ss, '<a name="section_6_5"/>6.5 Diario'))
    diary_psico = [d for d in diary_entries if d.service_type == "psicologia"]
    if diary_psico:
        story.append(_data_table(ss, [(_fv(d.entry_date), f"{_user(d.author)}: {d.content}") for d in diary_psico]))
    else:
        story.append(Paragraph("Nessuna voce nel diario.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  7. PROGRESSO E METRICHE
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "7", "Progresso e Metriche", _C["pink"]))
    story.append(Spacer(1, 4))

    # 7.1 Peso
    story.append(_sub_header(ss, '<a name="section_7_1"/>7.1 Peso'))
    story.append(_data_table(ss, [
        ("Peso Iniziale", f"{first_weight} kg" if first_weight else "-"),
        ("Peso Attuale", f"{last_weight} kg" if last_weight else "-"),
        ("Variazione", f"{weight_delta:+.1f} kg" if weight_delta is not None else "-"),
        ("Check Compilati", len(weekly_responses)),
    ]))
    story.append(Spacer(1, 8))

    # 7.2 Medie
    story.append(_sub_header(ss, '<a name="section_7_2"/>7.2 Medie Benessere'))
    labels = {"energy": "Energia", "sleep": "Sonno", "mood": "Umore",
              "motivation": "Motivazione", "digestion": "Digestione",
              "strength": "Forza", "hunger": "Fame"}
    story.append(_data_table(ss, [
        (f"Media {labels[k]}", f"{avg_ratings[k]}/10" if avg_ratings[k] else "-") for k in rating_keys
    ]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  8. CHECK INIZIALI
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "8", "Check Iniziali", _C["amber"]))
    story.append(Spacer(1, 4))

    # 8.1 Risposte Form
    story.append(_sub_header(ss, '<a name="section_8_1"/>8.1 Risposte Form'))
    if check_assignments:
        for ca in check_assignments:
            form = ca.form
            form_name = form.name if form else f"Form #{ca.form_id}"
            fields_map = {}
            if form and hasattr(form, "fields"):
                for f in form.fields:
                    fields_map[str(f.id)] = f.label
            responses = list(ca.responses) if hasattr(ca.responses, "__iter__") else []
            if not responses:
                story.append(Paragraph(f"{form_name}: nessuna risposta", ss["EmptyNote"]))
                continue
            for ridx, resp in enumerate(responses, 1):
                story.append(_sub_sub_header(ss, f"{form_name} — Risposta #{ridx} ({_fv(resp.created_at)})"))
                resp_rows = []
                photos_to_embed = []
                if isinstance(resp.responses, dict):
                    for field_id, value in resp.responses.items():
                        label = fields_map.get(str(field_id), f"Domanda {field_id}")
                        # Detect photo paths
                        if isinstance(value, str) and ("/uploads/" in value or value.endswith((".jpg", ".jpeg", ".png"))):
                            photos_to_embed.append((label, value))
                        else:
                            resp_rows.append((label, value))
                if resp_rows:
                    story.append(_data_table(ss, resp_rows))
                # Embed photos
                if photos_to_embed:
                    pr = _photo_row(ss, photos_to_embed)
                    if pr:
                        story.append(Spacer(1, 4))
                        story.append(pr)
                story.append(Spacer(1, 6))
    else:
        story.append(Paragraph("Nessun check iniziale assegnato.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 8.2 Foto
    story.append(_sub_header(ss, '<a name="section_8_2"/>8.2 Foto Check Iniziali'))
    story.append(Paragraph("Le foto sono inserite inline nelle risposte sopra, quando disponibili.", ss["Meta"]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  9. CHECK PERIODICI
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "9", "Check Periodici", _C["pink"]))
    story.append(Spacer(1, 4))

    # 9.1 Config
    story.append(_sub_header(ss, '<a name="section_9_1"/>9.1 Configurazione'))
    story.append(_data_table(ss, [
        ("Weekly Check Configurati", len(weekly_checks)),
        ("Weekly Check Risposte", len(weekly_responses)),
        ("Minor Check Risposte", len(minor_responses)),
        ("DCA Check Risposte", len(dca_responses)),
        ("Giorno Check", cliente.check_day),
        ("Check Saltati", cliente.check_saltati),
    ]))
    story.append(Spacer(1, 8))

    # 9.2 Weekly Check (TUTTI)
    story.append(_sub_header(ss, '<a name="section_9_2"/>9.2 Weekly Check'))
    if weekly_responses:
        for idx, wr in enumerate(weekly_responses, 1):
            story.append(_sub_sub_header(ss, f"Weekly #{idx} — {_fv(wr.submit_date)}"))
            # Photos
            pr = _photo_row(ss, [
                ("Frontale", wr.photo_front),
                ("Laterale", wr.photo_side),
                ("Posteriore", wr.photo_back),
            ])
            if pr:
                story.append(pr)
                story.append(Spacer(1, 4))
            story.append(_data_table(ss, [
                ("Peso", f"{wr.weight} kg" if wr.weight else "-"),
                ("Cosa ha funzionato", wr.what_worked),
                ("Cosa non ha funzionato", wr.what_didnt_work),
                ("Cosa ho imparato", wr.what_learned),
                ("Su cosa concentrarmi", wr.what_focus_next),
                ("Aderenza Nutrizione", wr.nutrition_program_adherence),
                ("Aderenza Allenamento", wr.training_program_adherence),
                ("Passi Giornalieri", wr.daily_steps),
                ("Settimane Allenamento", wr.completed_training_weeks),
                ("Giorni Allenamento Pianificati", wr.planned_training_days),
                ("Modifiche Esercizi", wr.exercise_modifications),
                ("Infortuni e Note", wr.injuries_notes),
                ("Digestione", f"{wr.digestion_rating}/10" if wr.digestion_rating else "-"),
                ("Energia", f"{wr.energy_rating}/10" if wr.energy_rating else "-"),
                ("Forza", f"{wr.strength_rating}/10" if wr.strength_rating else "-"),
                ("Fame", f"{wr.hunger_rating}/10" if wr.hunger_rating else "-"),
                ("Sonno", f"{wr.sleep_rating}/10" if wr.sleep_rating else "-"),
                ("Umore", f"{wr.mood_rating}/10" if wr.mood_rating else "-"),
                ("Motivazione", f"{wr.motivation_rating}/10" if wr.motivation_rating else "-"),
                ("Valutazione Nutrizionista", f"{wr.nutritionist_rating}/10" if wr.nutritionist_rating else "-"),
                ("Feedback Nutrizionista", wr.nutritionist_feedback),
                ("Valutazione Coach", f"{wr.coach_rating}/10" if wr.coach_rating else "-"),
                ("Feedback Coach", wr.coach_feedback),
                ("Valutazione Psicologo/a", f"{wr.psychologist_rating}/10" if wr.psychologist_rating else "-"),
                ("Feedback Psicologo/a", wr.psychologist_feedback),
                ("Valutazione Progresso", f"{wr.progress_rating}/10" if wr.progress_rating else "-"),
                ("Referral", wr.referral),
                ("Commenti Extra", wr.extra_comments),
                ("Argomenti Live Session", wr.live_session_topics),
            ]))
            story.append(Spacer(1, 10))
    else:
        story.append(Paragraph("Nessun weekly check compilato.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 9.3 Minor Check
    story.append(_sub_header(ss, '<a name="section_9_3"/>9.3 Minor Check'))
    if minor_responses:
        for idx, mr in enumerate(minor_responses, 1):
            story.append(_sub_sub_header(ss, f"Minor Check #{idx} — {_fv(mr.submit_date)}"))
            rows = [
                ("Peso", f"{mr.peso_attuale} kg" if mr.peso_attuale else "-"),
                ("Altezza", f"{mr.altezza} cm" if mr.altezza else "-"),
            ]
            # EDE-Q6 scores
            if mr.score_global is not None:
                rows.extend([
                    ("Score Globale", f"{mr.score_global:.2f}"),
                    ("Restrizione", f"{mr.score_restraint:.2f}" if mr.score_restraint else "-"),
                    ("Preoccup. Alimentare", f"{mr.score_eating_concern:.2f}" if mr.score_eating_concern else "-"),
                    ("Preoccup. Forma", f"{mr.score_shape_concern:.2f}" if mr.score_shape_concern else "-"),
                    ("Preoccup. Peso", f"{mr.score_weight_concern:.2f}" if mr.score_weight_concern else "-"),
                ])
            # Nuovo questionario adolescenti
            rd = mr.responses_data or {}
            radio_labels = {
                "sentire_generale": ["Molto bene", "Bene", "Così così", "Non molto bene", "Male"],
                "percorso_vissuto": ["Mi sta aiutando molto", "Mi trovo bene", "È ok", "Mi crea qualche difficoltà", "Non mi trovo bene"],
                "ascoltato": ["Sì", "A volte", "No"],
                "pratica_quotidiana": ["Quasi sempre", "Spesso", "A volte", "Raramente"],
                "riconoscere_fame": ["Sì", "A volte", "No"],
                "riconoscere_sazieta": ["Sì", "A volte", "No"],
                "mangiare_senza_fame": ["Spesso", "A volte", "Raramente"],
                "energia": ["Alta", "Adeguata", "Bassa"],
                "sonno": ["Bene", "Abbastanza bene", "Male"],
                "sentimento_peso": ["Sereno/a", "Indifferente", "A disagio"],
            }

            def _radio_label(field, val):
                if val is None:
                    return None
                labels = radio_labels.get(field, [])
                try:
                    return labels[int(val)] if int(val) < len(labels) else str(val)
                except (ValueError, TypeError, IndexError):
                    return str(val)

            has_adolescent = rd.get("sentire_generale") is not None or rd.get("difficolta") is not None
            if has_adolescent:
                adolescent_fields = [
                    ("Come ti senti", _radio_label("sentire_generale", rd.get("sentire_generale"))),
                    ("Difficoltà", rd.get("difficolta")),
                    ("Come vivi il percorso", _radio_label("percorso_vissuto", rd.get("percorso_vissuto"))),
                    ("Racconto percorso", rd.get("percorso_racconto")),
                    ("Aspetti difficili", ", ".join(rd["aspetti_difficili"]) if isinstance(rd.get("aspetti_difficili"), list) else rd.get("aspetti_difficili")),
                    ("Dettaglio aspetti difficili", rd.get("aspetti_difficili_dettaglio")),
                    ("Ti senti ascoltato/a", _radio_label("ascoltato", rd.get("ascoltato"))),
                    ("Situazioni non ascoltato/a", rd.get("ascoltato_situazioni")),
                    ("Pratica quotidiana", _radio_label("pratica_quotidiana", rd.get("pratica_quotidiana"))),
                    ("Situazioni di fatica", ", ".join(rd["fatica_situazioni"]) if isinstance(rd.get("fatica_situazioni"), list) else rd.get("fatica_situazioni")),
                    ("Alimenti/momenti disagio", rd.get("alimenti_disagio")),
                    ("Riconosci fame", _radio_label("riconoscere_fame", rd.get("riconoscere_fame"))),
                    ("Riconosci sazietà", _radio_label("riconoscere_sazieta", rd.get("riconoscere_sazieta"))),
                    ("Mangi senza fame", _radio_label("mangiare_senza_fame", rd.get("mangiare_senza_fame"))),
                    ("Energia", _radio_label("energia", rd.get("energia"))),
                    ("Disturbi fisici", rd.get("disturbi_fisici")),
                    ("Sonno", _radio_label("sonno", rd.get("sonno"))),
                    ("Sentimento peso", _radio_label("sentimento_peso", rd.get("sentimento_peso"))),
                    ("Data misurazione", rd.get("data_misurazione")),
                    ("Modifiche percorso", rd.get("modifiche_percorso")),
                    ("Cosa funziona bene", rd.get("funzionamento_bene")),
                    ("Aspetti da approfondire", rd.get("approfondire")),
                ]
                rows.extend([(l, v) for l, v in adolescent_fields if v is not None])

            story.append(_data_table(ss, rows))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("Nessun minor check compilato.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 9.4 DCA Check
    story.append(_sub_header(ss, '<a name="section_9_4"/>9.4 DCA Check'))
    if dca_responses:
        for idx, dr in enumerate(dca_responses, 1):
            story.append(_sub_sub_header(ss, f"DCA #{idx} — {_fv(dr.submit_date)}"))
            story.append(_data_table(ss, [
                ("Equilibrio Umore", f"{dr.mood_balance_rating}/5" if dr.mood_balance_rating else "-"),
                ("Serenità Piano Alimentare", f"{dr.food_plan_serenity}/5" if dr.food_plan_serenity else "-"),
                ("Preoccupazione Peso/Cibo", f"{dr.food_weight_worry}/5" if dr.food_weight_worry else "-"),
                ("Emotional Eating", f"{dr.emotional_eating}/5" if dr.emotional_eating else "-"),
                ("Comfort Corporeo", f"{dr.body_comfort}/5" if dr.body_comfort else "-"),
                ("Rispetto del Corpo", f"{dr.body_respect}/5" if dr.body_respect else "-"),
                ("Esercizio Benessere", f"{dr.exercise_wellness}/5" if dr.exercise_wellness else "-"),
                ("Senso di Colpa Esercizio", f"{dr.exercise_guilt}/5" if dr.exercise_guilt else "-"),
                ("Sonno", f"{dr.sleep_satisfaction}/5" if dr.sleep_satisfaction else "-"),
                ("Tempo Relazioni", f"{dr.relationship_time}/5" if dr.relationship_time else "-"),
                ("Tempo Personale", f"{dr.personal_time}/5" if dr.personal_time else "-"),
                ("Interferenza Vita", f"{dr.life_interference}/5" if dr.life_interference else "-"),
                ("Gestione Imprevisti", f"{dr.unexpected_management}/5" if dr.unexpected_management else "-"),
                ("Auto-Compassione", f"{dr.self_compassion}/5" if dr.self_compassion else "-"),
                ("Dialogo Interiore", f"{dr.inner_dialogue}/5" if dr.inner_dialogue else "-"),
                ("Sostenibilità", f"{dr.long_term_sustainability}/5" if dr.long_term_sustainability else "-"),
                ("Allineamento Valori", f"{dr.values_alignment}/5" if dr.values_alignment else "-"),
                ("Motivazione", f"{dr.motivation_level}/5" if dr.motivation_level else "-"),
                ("Organizzazione Pasti", f"{dr.meal_organization}/5" if dr.meal_organization else "-"),
                ("Stress Pasti", f"{dr.meal_stress}/5" if dr.meal_stress else "-"),
                ("Digestione", f"{dr.digestion_rating}/10" if dr.digestion_rating else "-"),
                ("Energia", f"{dr.energy_rating}/10" if dr.energy_rating else "-"),
                ("Forza", f"{dr.strength_rating}/10" if dr.strength_rating else "-"),
                ("Fame", f"{dr.hunger_rating}/10" if dr.hunger_rating else "-"),
                ("Umore", f"{dr.mood_rating}/10" if dr.mood_rating else "-"),
                ("Motivazione (fisico)", f"{dr.motivation_rating}/10" if dr.motivation_rating else "-"),
                ("Referral", dr.referral),
                ("Commenti", dr.extra_comments),
            ]))
            story.append(Spacer(1, 8))
    else:
        story.append(Paragraph("Nessun DCA check compilato.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  10. MARKETING E EXTRA
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "10", "Marketing e Extra", _C["red"]))
    story.append(Spacer(1, 4))

    # 10.1 Consensi
    story.append(_sub_header(ss, '<a name="section_10_1"/>10.1 Consensi e Contenuti Marketing'))
    marketing_rows = [
        ("Note Marketing", getattr(cliente, "note_marketing", None)),
        ("Consenso Social Richiesto", cliente.consenso_social_richiesto),
        ("Consenso Social Accettato", cliente.consenso_social_accettato),
        ("Consenso Social Note", cliente.consenso_social_note),
        ("Video Feedback Richiesto", cliente.video_feedback_richiesto),
        ("Video Feedback Svolto", cliente.video_feedback_svolto),
        ("Video Feedback Condiviso", cliente.video_feedback_condiviso),
        ("Trasformazione Fisica", cliente.trasformazione_fisica),
        ("Trasformazione Condivisa", cliente.trasformazione_fisica_condivisa),
        ("Recensione Richiesta", cliente.recensione_richiesta),
        ("Recensione Accettata", cliente.recensione_accettata),
        ("Recensione Stelle", cliente.recensione_stelle),
        ("Exit Call Richiesta", cliente.exit_call_richiesta),
        ("Exit Call Svolta", cliente.exit_call_svolta),
        ("Exit Call Note", cliente.exit_call_note),
    ]
    story.append(_data_table(ss, marketing_rows))

    if marketing_contents:
        story.append(Spacer(1, 6))
        story.append(_sub_sub_header(ss, "Contenuti Marketing"))
        for mc in marketing_contents:
            ct = _fv(getattr(mc, "content_type", ""))
            checked = "Editato" if getattr(mc, "checked", False) else "Non editato"
            d = _fv(getattr(mc, "checked_date", None))
            influencers = ""
            links = getattr(mc, "influencer_links", None) or []
            if links:
                inf_names = []
                for link in links:
                    inf = getattr(link, "influencer", None)
                    if inf:
                        inf_names.append(getattr(inf, "name", "") or getattr(inf, "handle", "") or str(inf))
                influencers = ", ".join(inf_names)
            story.append(_data_table(ss, [
                ("Tipo", ct), ("Stato", checked), ("Data", d), ("Influencer", influencers or "-"),
            ]))
            story.append(Spacer(1, 4))
    story.append(Spacer(1, 8))

    # 10.2 Video Recensione
    story.append(_sub_header(ss, '<a name="section_10_2"/>10.2 Video Recensione'))
    if video_reviews:
        for vr in video_reviews:
            story.append(_data_table(ss, [
                ("Stato", getattr(vr, "status", "-")),
                ("Richiesto da", _user(getattr(vr, "requested_by_user", None))),
                ("Confermato il", _fv(getattr(vr, "booking_confirmed_at", None))),
                ("Loom Link", getattr(vr, "loom_link", None)),
            ]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Nessuna video recensione.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 10.3 Call Bonus
    story.append(_sub_header(ss, '<a name="section_10_3"/>10.3 Call Bonus'))
    if call_bonus_list:
        for cb in call_bonus_list:
            story.append(_data_table(ss, [
                ("Data Richiesta", cb.data_richiesta),
                ("Stato", cb.status),
                ("Note Richiesta", getattr(cb, "note_richiesta", None)),
                ("Note HM", getattr(cb, "note_hm", None)),
            ]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Nessun call bonus.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # 10.4 Referral
    story.append(_sub_header(ss, '<a name="section_10_4"/>10.4 Referral'))
    story.append(_data_table(ss, [
        ("Bonus Scelto", cliente.referral_bonus_scelto),
        ("Bonus Utilizzato", cliente.referral_bonus_utilizzato),
        ("Bonus Da Utilizzare", cliente.referral_bonus_da_utilizzare),
        ("Note Referral", cliente.referral_richiesti_note),
    ]))
    story.append(Spacer(1, 8))

    # 10.5 Trustpilot
    story.append(_sub_header(ss, '<a name="section_10_5"/>10.5 Trustpilot'))
    if trustpilot_reviews:
        for tr in trustpilot_reviews:
            story.append(_data_table(ss, [
                ("Data Richiesta", tr.data_richiesta),
                ("Stelle", getattr(tr, "stelle", None)),
            ]))
            story.append(Spacer(1, 4))
    else:
        story.append(Paragraph("Nessuna recensione Trustpilot.", ss["EmptyNote"]))
    story.append(Spacer(1, 8))

    # ══════════════════════════════════════════════════════════════════════
    #  11. ALLEGATI E DOCUMENTI
    # ══════════════════════════════════════════════════════════════════════
    story.append(_section_header(ss, "11", "Allegati e Documenti", _C["slate_med"]))
    story.append(Spacer(1, 4))

    story.append(_data_table(ss, [
        ("Cartelle Cliniche", len(cartelle)),
        ("Allegati Totali", sum(len(c.allegati) for c in cartelle) if cartelle else 0),
        ("Ticket Aperti", len(tickets)),
        ("Loom Link", cliente.loom_link),
    ]))

    if cartelle:
        story.append(Spacer(1, 6))
        for cc in cartelle:
            story.append(_sub_sub_header(ss, f"Cartella: {getattr(cc, 'nome', 'N/D')}"))
            cc_rows = [("Note", getattr(cc, "note", None))]
            for alleg in (cc.allegati or []):
                cc_rows.append((
                    f"Allegato: {getattr(alleg, 'file_type', 'file')}",
                    f"{getattr(alleg, 'note', '-')} — {_fv(getattr(alleg, 'upload_date', None))}",
                ))
            story.append(_data_table(ss, cc_rows))
            story.append(Spacer(1, 4))

    # ── Build and return ──
    doc.build(story)
    buf.seek(0)
    return buf
