"""
Corposostenibile – modelli SQLAlchemy (schema completo)
======================================================

✓ Copertura 100 % dello `schema.mmd`
✓ ENUM Postgres normalizzati (snake‑case, senza accenti) e registrati una sola volta
✓ Relationship bidirezionali dove utili
✓ TimestampMixin con `created_at` / `updated_at`
"""

from __future__ import annotations

from datetime import datetime, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import List

from sqlalchemy import Index, CheckConstraint, or_, func
from sqlalchemy.dialects.postgresql import ENUM, ARRAY, NUMERIC, JSONB, TSVECTOR
from sqlalchemy.orm import relationship, configure_mappers, validates
from sqlalchemy_utils import TSVectorType

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy_continuum import version_class


from corposostenibile.extensions import db

import enum

# ───────────────────────── ENUM helper ──────────────────────────── #
# ───────────────────────── ENUM helper ──────────────────────────── #
_enum_registry: List[ENUM] = []

def _pg_enum(enum_cls: type[Enum]) -> ENUM:
    """Ritorna un ENUM Postgres e lo registra per la creazione (nome snake-case)."""
    pg_enum = ENUM(
        *[m.value for m in enum_cls],
        name=enum_cls.__name__.lower(),
        schema="public",          # 👈 AGGIUNGI QUESTA RIGA
        create_type=False,        # verrà creato in register_enums()
    )
    _enum_registry.append(pg_enum)
    return pg_enum


def register_enums() -> None:
    """Esegue `CREATE TYPE` per tutti gli ENUM registrati (idempotente)."""
    for e in _enum_registry:
        e.create(db.engine, checkfirst=True)

# helper per riutilizzare il tipo Postgres esistente senza ricrearlo
_def = lambda enum_cls: db.Enum(
    enum_cls,
    name=enum_cls.__name__.lower(),
    schema="public",             # 👈 ANCHE QUI
    create_type=False,
)

# ─────────────────────────── ENUM definiti ─────────────────────────── #
class TeamEnum(str, Enum):
    interno = "interno"
    sales_team = "sales_team"
    setter_team = "setter_team"
    sito = "sito"
    va_team = "va_team"


class PagamentoEnum(str, Enum):
    bonifico = "bonifico"
    klarna = "klarna"
    stripe = "stripe"
    paypal = "paypal"
    carta = "carta"
    contanti = "contanti"


class PagamentoInternoStatusEnum(str, Enum):
    """Status per pagamenti interni"""
    completato = "completato"
    in_sospeso = "in_sospeso"
    fallito = "fallito"
    annullato = "annullato"


class TipoPagamentoInternoEnum(str, Enum):
    """Tipi di pagamento interni per approvazione"""
    deposito_iniziale = "deposito_iniziale"
    saldo_acconto = "saldo_acconto"
    rinnovo = "rinnovo"
    upsell = "upsell"
    downgrade = "downgrade"
    ritorna_cliente = "ritorna_cliente"
    live_trainings = "live_trainings"
    promo_natale = "promo_natale"
    sedute_psicologia = "sedute_psicologia"


class AttribuibileAEnum(str, Enum):
    """A chi è attribuibile un rinnovo"""
    sales = "sales"
    team_interno = "team_interno"
    nutrizionista = "nutrizionista"
    coach = "coach"
    psicologo = "psicologo"
    health_manager = "health_manager"


class TeamPaymentStatusEnum(str, Enum):
    """Status per pagamenti team"""
    da_valutare = "da_valutare"
    approvato = "approvato"
    rifiutato = "rifiutato"


class KPITypeEnum(str, Enum):
    """Tipi di KPI aziendali"""
    tasso_rinnovi = "tasso_rinnovi"
    tasso_referral = "tasso_referral"


class GiornoEnum(str, Enum):
    lun = "lun"
    mar = "mar"
    mer = "mer"
    gio = "gio"
    ven = "ven"
    sab = "sab"
    dom = "dom"
    # Valori completi per compatibilità Excel
    lunedi = "lunedi"
    martedi = "martedi"
    mercoledi = "mercoledi"
    giovedi = "giovedi"
    venerdi = "venerdi"
    sabato = "sabato"
    domenica = "domenica"


class StatoClienteEnum(str, Enum):
    attivo = "attivo"
    ghost = "ghost"
    pausa = "pausa"
    stop = "stop"
    insoluto = "insoluto"
    freeze = "freeze"  # NUOVO: stato per blocco temporaneo gestito da Health Manager


class CheckSaltatiEnum(str, Enum):
    uno = "1"
    due = "2"
    tre = "3"
    tre_plus = "3_plus"


class LuogoAllenEnum(str, Enum):
    casa = "casa"
    palestra = "palestra"
    ibrido = "ibrido"


class PlanTypeEnum(str, Enum):
    """Tipo di piano per file extra"""
    meal_plan = "meal_plan"
    training_plan = "training_plan"


class FiguraRifEnum(str, Enum):
    coach = "coach"
    nutrizionista = "nutrizionista"
    psicologa = "psicologa"


class TipoProfessionistaEnum(str, Enum):
    """Tipi di professionista per storico assegnazioni"""
    nutrizionista = "nutrizionista"
    coach = "coach"
    psicologa = "psicologa"
    health_manager = "health_manager"
    consulente = "consulente"


class CallBonusStatusEnum(str, Enum):
    """Stati della richiesta di call bonus"""
    proposta = "proposta"
    accettata = "accettata"
    rifiutata = "rifiutata"
    confermata = "confermata"
    non_andata_buon_fine = "non_andata_buon_fine"


class TrasformazioneEnum(str, Enum):
    no = "no"
    si = "si"


class BonusBandEnum(str, Enum):
    """Bande bonus Quality Score trimestrale"""
    band_100 = "100%"
    band_60 = "60%"
    band_30 = "30%"
    band_0 = "0%"


class CheckTypeEnum(str, Enum):
    """Tipo di check response per Quality Score"""
    weekly_check = "weekly_check"
    typeform = "typeform"
    dca_check = "dca_check"


class GenereEnum(str, Enum):
    uomo = "uomo"
    donna = "donna"


class TipologiaClienteEnum(str, Enum):
    a = "a"
    b = "b"
    c = "c"
    stop = "stop"
    recupero = "recupero"
    pausa_gt_30 = "pausa_gt_30"


class CatEnum(str, Enum):
    trasformazione = "trasformazione"
    trasformazione_dca = "trasformazione_dca"


class SalesRoleEnum(str, Enum):
    venditore = "venditore"
    setter = "setter"
    altro = "altro"


class UserRoleEnum(str, Enum):
    """Ruoli utente per il sistema Team"""
    admin = "admin"
    team_leader = "team_leader"
    professionista = "professionista"
    team_esterno = "team_esterno"
    influencer = "influencer"


class UserSpecialtyEnum(str, Enum):
    """Specializzazioni utente per il sistema Team"""
    # Admin specialties
    amministrazione = "amministrazione"
    cco = "cco"
    # Team Leader / Professionista specialties
    nutrizione = "nutrizione"
    psicologia = "psicologia"
    coach = "coach"
    # Professionista specific
    nutrizionista = "nutrizionista"
    psicologo = "psicologo"


class TeamTypeEnum(str, Enum):
    """Tipologie di team per specializzazione"""
    nutrizione = "nutrizione"
    coach = "coach"
    psicologia = "psicologia"


class InfluencerFlagEnum(str, Enum):
    yes = "yes"
    no = "no"


class CampaignPlatformEnum(str, Enum):
    """Canale da cui proviene il candidato / la campagna recruiting."""
    linkedin  = "linkedin"
    facebook  = "facebook"
    instagram = "instagram"



class PeriodTypeEnum(str, Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"


class CenterTypeEnum(str, Enum):
    team = "team"
    software = "software"
    influencer = "influencer"
    hr = "hr"
    altro = "altro"


class TransactionTypeEnum(str, Enum):
    deposito = "deposito"
    rinnovo = "rinnovo"
    rimborso = "rimborso"


class CommissionRoleEnum(str, Enum):
    sales = "sales"
    setter = "setter"
    coach = "coach"
    nutrizionista = "nutrizionista"
    psicologa = "psicologa"
    influencer = "influencer"
    altro = "altro"


# ENUM di staff estratti dai file excel (snake‑case)
class NutrizionistaEnum(str, Enum):
    alice_p     = "alice_p"
    caterina_e  = "caterina_e"
    clara_r     = "clara_r"
    elisa_m     = "elisa_m"
    federica_c  = "federica_c"
    isabella_r  = "isabella_r"
    manuela_m   = "manuela_m"   # NEW
    marta_be    = "marta_be"    # NEW
    marta_bu    = "marta_bu"    # NEW
    matteo_c    = "matteo_c"
    nadia_p     = "nadia_p"
    sara_g      = "sara_g"
    sarah_c     = "sarah_c"     # NEW
    veronica_f  = "veronica_f"

class CoachEnum(str, Enum):
    alessandra_d = "alessandra_d"
    claudio_l    = "claudio_l"   # NEW
    federico_d   = "federico_d"
    lorenzo_s    = "lorenzo_s"
    sara_p       = "sara_p"
    simone_l     = "simone_l"

class PsicologaEnum(str, Enum):
    alice_l    = "alice_l"
    barbara_v  = "barbara_v"
    claudia_m  = "claudia_m"
    delia_d    = "delia_d"
    manny_a    = "manny_a"       # NEW
    martina_l  = "martina_l"


class TaskStatusEnum(str, Enum):
    todo        = "todo"
    in_progress = "in_progress"
    done        = "done"
    archived    = "archived"


class TaskPriorityEnum(str, Enum):
    low     = "low"
    medium  = "medium"
    high    = "high"
    urgent  = "urgent"


class TaskCategoryEnum(str, Enum):
    onboarding  = "onboarding"
    check       = "check"
    reminder    = "reminder"
    formazione  = "formazione"
    sollecito   = "sollecito"
    generico    = "generico"




class OKRStatusEnum(str, Enum):
    draft = "draft"
    active = "active"
    completed = "completed"
    archived = "archived"


class OKRPeriodEnum(str, Enum):
    q1 = "q1"
    q2 = "q2"
    q3 = "q3"
    q4 = "q4"
    yearly = "yearly"
    custom = "custom"


# ─────────────────────────── ENUM NUTRITION ─────────────────────────── #
class MealTypeEnum(str, Enum):
    colazione = "colazione"
    spuntino_mattina = "spuntino_mattina"
    pranzo = "pranzo"
    spuntino_pomeriggio = "spuntino_pomeriggio"
    cena = "cena"
    spuntino_sera = "spuntino_sera"


class DietaryPreferenceEnum(str, Enum):
    vegetariano = "vegetariano"
    vegano = "vegano"
    pescetariano = "pescetariano"
    senza_glutine = "senza_glutine"
    senza_lattosio = "senza_lattosio"
    halal = "halal"
    kosher = "kosher"
    paleo = "paleo"
    keto = "keto"
    mediterranea = "mediterranea"


class NutritionalGoalEnum(str, Enum):
    dimagrimento = "dimagrimento"
    mantenimento = "mantenimento"
    aumento_massa = "aumento_massa"
    ricomposizione = "ricomposizione"
    salute_generale = "salute_generale"


class ActivityLevelEnum(str, Enum):
    sedentario = "sedentario"
    leggermente_attivo = "leggermente_attivo"
    moderatamente_attivo = "moderatamente_attivo"
    molto_attivo = "molto_attivo"
    estremamente_attivo = "estremamente_attivo"


class FoodUnitEnum(str, Enum):
    grammi = "g"
    millilitri = "ml"
    cucchiaio = "cucchiaio"
    cucchiaino = "cucchiaino"
    tazza = "tazza"
    pezzo = "pezzo"
    fetta = "fetta"
    porzione = "porzione"




# ─────────────────────────── ENUM TICKET ─────────────────────────── #
class TicketStatusEnum(str, Enum):
    nuovo = "nuovo"
    in_lavorazione = "in_lavorazione"
    in_attesa = "in_attesa"
    chiuso = "chiuso"


class TicketUrgencyEnum(str, Enum):
    alta = "1"  # Entro la giornata
    media = "2"  # Entro 2 giorni
    bassa = "3"  # Entro la settimana


class TicketCategoryEnum(str, Enum):
    problema = "problema"
    upgrade = "upgrade"
    review = "review"


# ─────────────────────────── ENUM FERIE/PERMESSI ─────────────────────────── #
class LeaveTypeEnum(str, Enum):
    ferie = "ferie"
    permesso = "permesso"
    malattia = "malattia"


class LeaveStatusEnum(str, Enum):
    bozza = "bozza"
    richiesta = "richiesta"  # Legacy - mantenuto per retrocompatibilità
    pending_first_approval = "pending_first_approval"  # In attesa prima approvazione (Team Leader/Resp. Dip./CCO/CEO)
    pending_hr = "pending_hr"  # In attesa approvazione HR (fase finale)
    approvata = "approvata"
    rifiutata = "rifiutata"
    cancellata = "cancellata"


# ─────────────────────────── ENUM KNOWLEDGE BASE ─────────────────────────── #
class KBVisibilityEnum(str, Enum):
    """Livelli di visibilità per documenti KB"""
    only_heads = "only_heads"          # Solo HEAD di tutti i dipartimenti
    department = "department"          # Solo membri del dipartimento
    company = "company"                # Tutta l'azienda


class KBDocumentStatusEnum(str, Enum):
    """Stati del documento KB"""
    draft = "draft"                    # Bozza
    published = "published"            # Pubblicato
    archived = "archived"              # Archiviato
    under_review = "under_review"      # In revisione


class KBAlertTypeEnum(str, Enum):
    """Tipi di alert per monitoring KB"""
    storage_limit = "storage_limit"          # Limite storage superato
    outdated_docs = "outdated_docs"          # Documenti obsoleti
    no_activity = "no_activity"              # Nessuna attività recente
    high_searches_no_results = "no_results"  # Troppe ricerche senza risultati
    broken_links = "broken_links"            # Link rotti nei documenti
    pending_reviews = "pending_reviews"      # Documenti da revisionare


class KBActionTypeEnum(str, Enum):
    """Tipi di azioni per activity log KB"""
    view = "view"
    create = "create"
    edit = "edit"
    delete = "delete"
    download = "download"
    share = "share"
    bookmark = "bookmark"
    search = "search"
    upload = "upload"
    comment = "comment"
    acknowledge = "acknowledge"


# ─────────────────────────── ENUM RECRUITING ─────────────────────────── #
class ApplicationStatusEnum(str, Enum):
    """Stati della candidatura."""
    new = "new"
    screening = "screening"
    reviewed = "reviewed"
    interview_scheduled = "interview_scheduled"
    interviewed = "interviewed"
    offer_sent = "offer_sent"
    hired = "hired"
    rejected = "rejected"
    withdrawn = "withdrawn"

class ApplicationSourceEnum(str, Enum):
    """Fonte della candidatura."""
    linkedin = "linkedin"
    facebook = "facebook"
    instagram = "instagram"
    website = "website"
    referral = "referral"
    other = "other"

# ─────────────────────────── ENUM CLIENT CHECKS ─────────────────────────── #
class CheckFormTypeEnum(str, Enum):
    """Tipo di check form."""
    iniziale = "iniziale"
    settimanale = "settimanale"


class CheckFormStatusEnum(str, Enum):
    """Stato del form di controllo."""
    draft = "draft"
    active = "active"
    inactive = "inactive"
    archived = "archived"


class CheckFormFieldTypeEnum(str, Enum):
    """Tipo di campo del form."""
    text = "text"
    number = "number"
    email = "email"
    textarea = "textarea"
    select = "select"
    multiselect = "multiselect"
    radio = "radio"
    checkbox = "checkbox"
    scale = "scale"
    date = "date"
    file = "file"
    rating = "rating"
    yesno = "yesno"


class AssignmentStatusEnum(str, Enum):
    """Stato dell'assegnazione."""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"
    cancelled = "cancelled"


# Registrazione dei tipi Postgres (una sola volta)
for _e in (
    TeamEnum,
    PagamentoEnum,
    GiornoEnum,
    StatoClienteEnum,
    CheckSaltatiEnum,
    LuogoAllenEnum,
    FiguraRifEnum,
    TrasformazioneEnum,
    BonusBandEnum,
    CheckTypeEnum,
    GenereEnum,
    TipologiaClienteEnum,
    CatEnum,
    SalesRoleEnum,
    InfluencerFlagEnum,
    PeriodTypeEnum,
    CenterTypeEnum,
    TransactionTypeEnum,
    CommissionRoleEnum,
    NutrizionistaEnum,
    CoachEnum,
    PsicologaEnum,
    TaskStatusEnum,
    TaskPriorityEnum,
    CampaignPlatformEnum,
    OKRStatusEnum,
    OKRPeriodEnum,
    MealTypeEnum,
    DietaryPreferenceEnum,
    NutritionalGoalEnum,
    ActivityLevelEnum,
    FoodUnitEnum,
    TicketStatusEnum,
    TicketUrgencyEnum,
    LeaveTypeEnum,
    LeaveStatusEnum,
    KBVisibilityEnum,
    KBDocumentStatusEnum,
    KBAlertTypeEnum,
    KBActionTypeEnum,
    ApplicationStatusEnum,
    CheckFormTypeEnum,
    CheckFormStatusEnum,
    CheckFormFieldTypeEnum,
    AssignmentStatusEnum,
    PagamentoInternoStatusEnum,
    TipoPagamentoInternoEnum,
    KPITypeEnum,
):
    _pg_enum(_e)

# ───────────────────────────── Mixins ──────────────────────────── #
class TimestampMixin:
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    
# ───────────────────── 0) USERS & INFLUENCER ───────────────────── #


# ---------------------------------------------------------------------------- #
#  Department
# ---------------------------------------------------------------------------- #
class Department(db.Model):
    __tablename__ = "departments"

    id   = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)

    # capo reparto (opzionale)
    head_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id",
                      name="fk_departments_head_id",
                      ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    
    # ────────────────────────── NUOVI CAMPI DOCUMENTI ───────────────────────── #
    # Linee guida dipartimento (testo o PDF)
    guidelines_text = db.Column(db.Text, nullable=True)
    guidelines_pdf = db.Column(db.String(255), nullable=True)
    
    # Standard Operating Procedures
    sop_members_pdf = db.Column(db.String(255), nullable=True)
    sop_managers_pdf = db.Column(db.String(255), nullable=True)
    
    # Metadata documenti (opzionale ma utile)
    guidelines_updated_at = db.Column(db.DateTime, nullable=True)
    sop_updated_at = db.Column(db.DateTime, nullable=True)

    # ────────────────────────── relazioni ───────────────────────── #
    # NOTA: members relationship rimossa - User.department_id non esiste più

    head    = relationship("User",
                           back_populates="departments_led",
                           lazy="joined",
                           foreign_keys=[head_id])

    # 🔹 nuovo – task del reparto
    tasks   = relationship("Task",
                           back_populates="department",
                           cascade="all, delete-orphan",
                           lazy="selectin")

    # 🔹 NUOVO – OKR del dipartimento
    objectives = relationship(
        "DepartmentObjective", 
        back_populates="department",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DepartmentObjective.order_index"
    )
    
    # 🔹 NUOVO – Email notifiche ticket
    ticket_notification_email = db.Column(
        db.String(255),
        comment="Email per notifiche ticket del dipartimento"
    )

    # 🔹 NUOVO – Teams (sotto-organizzazioni del dipartimento)
    teams = relationship(
        "Team",
        back_populates="department",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Team.name"
    )

    # ────────────────────────── METODI HELPER DOCUMENTI ───────────────────────── #
    @property
    def has_guidelines(self) -> bool:
        """True se ci sono linee guida (testo o PDF)."""
        return bool(self.guidelines_text or self.guidelines_pdf)
    
    @property
    def has_sop_members(self) -> bool:
        """True se c'è SOP per membri."""
        return bool(self.sop_members_pdf)
    
    @property
    def has_sop_managers(self) -> bool:
        """True se c'è SOP per manager."""
        return bool(self.sop_managers_pdf)
    
    @property
    def has_any_documents(self) -> bool:
        """True se c'è almeno un documento."""
        return self.has_guidelines or self.has_sop_members or self.has_sop_managers
    
    def get_document_path(self, doc_type: str) -> str | None:
        """Ritorna il path del documento richiesto."""
        doc_map = {
            'guidelines_pdf': self.guidelines_pdf,
            'sop_members': self.sop_members_pdf,
            'sop_managers': self.sop_managers_pdf
        }
        return doc_map.get(doc_type)
    
    def update_document_timestamp(self, doc_type: str) -> None:
        """Aggiorna il timestamp di modifica del documento."""
        from datetime import datetime
        
        if doc_type in ['guidelines_text', 'guidelines_pdf']:
            self.guidelines_updated_at = datetime.utcnow()
        elif doc_type in ['sop_members_pdf', 'sop_managers_pdf']:
            self.sop_updated_at = datetime.utcnow()
    
    # 🔹 NUOVO – Helper per ticket
    @property
    def notification_email(self) -> str | None:
        """Email per notifiche (priorità: custom email > head email)."""
        if self.ticket_notification_email:
            return self.ticket_notification_email
        if self.head:
            return self.head.email
        return None
    
    @property
    def open_tickets_count(self) -> int:
        """Numero di ticket aperti assegnati al dipartimento."""
        from corposostenibile.models import Ticket, TicketStatusEnum
        return Ticket.query.filter(
            Ticket.department_id == self.id,
            Ticket.status != TicketStatusEnum.chiuso
        ).count()

    # ────────────────────────── METODI HELPER TEAMS ───────────────────────── #
    @property
    def all_members(self):
        """
        Tutti i membri del dipartimento (indipendentemente dal team).
        BACKWARD COMPATIBLE: usa sempre department_id.
        """
        return self.members  # già definito come relationship

    @property
    def team_count(self) -> int:
        """Numero di team nel dipartimento."""
        return len(self.teams)

    @property
    def has_teams(self) -> bool:
        """True se il dipartimento ha almeno un team."""
        return self.team_count > 0

    def get_team_by_name(self, name: str):
        """Trova team per nome (case-insensitive)."""
        name_lower = name.lower()
        return next((t for t in self.teams if t.name.lower() == name_lower), None)

    def get_members_without_team(self):
        """Ritorna lista utenti del dipartimento che non hanno un team assegnato."""
        return [m for m in self.members if m.team_id is None]

    # -------------------------------------------------------------- #
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Department {self.name!r}>"


# ---------------------------------------------------------------------------- #
#  Team - Team per specializzazione (Nutrizione, Coach, Psicologia)
# ---------------------------------------------------------------------------- #
class Team(TimestampMixin, db.Model):
    """
    Team organizzato per specializzazione.

    Ogni team ha:
    - Un tipo (nutrizione, coach, psicologia)
    - Un team leader (utente con ruolo team_leader e specialty compatibile)
    - Membri (professionisti con specialty compatibile)

    I team sono indipendenti dai dipartimenti e un professionista
    può appartenere a più team.
    """
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)

    # Nome del team (es. "Team Nutrizione Alpha", "Team Coach Beta")
    name = db.Column(db.String(120), nullable=False)

    # Descrizione opzionale
    description = db.Column(db.Text, nullable=True)

    # Tipo di team (nutrizione, coach, psicologia)
    team_type = db.Column(
        _def(TeamTypeEnum),
        nullable=False,
        index=True,
        comment="Tipo di team: nutrizione, coach, psicologia"
    )

    # FK al dipartimento (opzionale per backward compatibility)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id",
                      name="fk_teams_department_id",
                      ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Team leader (head del team)
    head_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id",
                      name="fk_teams_head_id",
                      ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Stato attivo/inattivo
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ────────────────────────── Relationships ───────────────────────── #
    department = relationship(
        "Department",
        back_populates="teams"
    )

    head = relationship(
        "User",
        foreign_keys=[head_id],
        back_populates="teams_led"
    )

    # Membri del team (many-to-many via team_members)
    members = relationship(
        "User",
        secondary="team_members",
        back_populates="teams",
        lazy="selectin"
    )

    # ────────────────────────── Constraints ───────────────────────── #
    __table_args__ = (
        # Nome team unico per tipo
        db.UniqueConstraint(
            'team_type',
            'name',
            name='uq_teams_type_name'
        ),
    )

    # ────────────────────────── Helper Methods ───────────────────────── #
    @property
    def member_count(self) -> int:
        """Numero di membri nel team."""
        return len(self.members) if self.members else 0

    @property
    def full_name(self) -> str:
        """Nome completo con tipo."""
        type_label = self.team_type.value.capitalize() if self.team_type else "?"
        return f"{type_label} - {self.name}"

    def is_member(self, user) -> bool:
        """Verifica se l'utente è membro del team."""
        return user in self.members if self.members else False

    def is_head(self, user) -> bool:
        """Verifica se l'utente è il team leader."""
        return self.head_id == user.id

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Team {self.name!r} (type={self.team_type.value if self.team_type else None})>"


# ---------------------------------------------------------------------------- #
#  Certification  (file upload)
# ---------------------------------------------------------------------------- #
class Certification(db.Model):
    """File che attesta una certificazione professionale di un utente."""

    __tablename__ = "certifications"

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(255), nullable=False)
    file_path   = db.Column(db.String(255), nullable=False)  # es. "certs/123456.pdf"
    content_type = db.Column(db.String(120), nullable=False)  # es. "application/pdf"
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # relazioni --------------------------------------------------------------- #
    users = db.relationship(
        "User",
        secondary="user_certification",
        back_populates="certifications",
        lazy="selectin",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Certification {self.title!r}>"


# ---------------------------------------------------------------------------- #
#  Tabella ponte User ⇄ Certification (M2M)
# ---------------------------------------------------------------------------- #
user_certification = db.Table(
    "user_certification",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column(
        "certification_id", db.Integer, db.ForeignKey("certifications.id"), primary_key=True
    ),
    db.Column("granted_at", db.DateTime, default=datetime.utcnow, nullable=False),
)

# ---------------------------------------------------------------------------- #
#  Tabella ponte Trial User ⇄ Cliente (M2M)
# ---------------------------------------------------------------------------- #
trial_user_clients = db.Table(
    "trial_user_clients",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("cliente_id", db.BigInteger, db.ForeignKey("clienti.cliente_id"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column("assigned_by", db.Integer, db.ForeignKey("users.id")),  # Chi ha assegnato
    db.Column("notes", db.Text),  # Note sull'assegnazione
)

# ---------------------------------------------------------------------------- #
#  Tabella ponte Team ⇄ User (M2M) - Membri del team
# ---------------------------------------------------------------------------- #
team_members = db.Table(
    "team_members",
    db.Column("team_id", db.Integer, db.ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("joined_at", db.DateTime, default=datetime.utcnow, nullable=False),
)


# ────────────────────────────── CALENDARIO ──────────────────────────────
class GoogleAuth(TimestampMixin, db.Model):
    """
    OAuth-store one-to-one con l'utente.

    • **user_id** PK = FK → users.id
    • **token_json**  blob serializzato restituito da google-auth-oauthlib
    • **expires_at**  timestamp di scadenza (UTC)
    • **refresh_token** token per rinnovare l'access_token (persistente)
    • **token_expires_at** scadenza precisa dell'access_token
    """
    __tablename__ = "google_auth"

    user_id: int = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    token_json: dict = db.Column(JSONB, nullable=False)
    expires_at: datetime = db.Column(db.DateTime, nullable=False, index=True)

    # Campi per autenticazione persistente
    refresh_token: str = db.Column(db.Text, nullable=True)
    token_expires_at: datetime = db.Column(db.DateTime, nullable=True, index=True)
    last_refresh_at: datetime = db.Column(db.DateTime, nullable=True)

    # relazione 1-1 verso User
    user = db.relationship("User", back_populates="google_auth", uselist=False)

    def is_token_expired(self) -> bool:
        """Verifica se il token di accesso è scaduto."""
        check_time = self.token_expires_at or self.expires_at
        if not check_time:
            return True
        return datetime.utcnow() >= check_time

    def is_expiring_soon(self, minutes: int = 5) -> bool:
        """Verifica se il token scade entro N minuti."""
        check_time = self.token_expires_at or self.expires_at
        if not check_time:
            return True
        return datetime.utcnow() >= (check_time - timedelta(minutes=minutes))

    def has_refresh_token(self) -> bool:
        """Verifica se è disponibile un refresh token."""
        # Prima controlla il campo dedicato
        if self.refresh_token and self.refresh_token.strip():
            return True
        # Fallback: controlla in token_json
        if self.token_json and self.token_json.get('refresh_token'):
            return True
        return False

    def get_refresh_token(self) -> str | None:
        """Ottiene il refresh token da dove disponibile."""
        if self.refresh_token and self.refresh_token.strip():
            return self.refresh_token
        if self.token_json and self.token_json.get('refresh_token'):
            return self.token_json.get('refresh_token')
        return None

    def can_auto_refresh(self) -> bool:
        """Verifica se è possibile rinnovare automaticamente il token."""
        return self.has_refresh_token()

    def update_tokens(self, token_data: dict) -> None:
        """Aggiorna i token con i nuovi dati ricevuti da Google."""
        # Aggiorna il token JSON completo
        self.token_json = token_data

        # Estrai e salva il refresh token se presente (NON sovrascrivere con None)
        if token_data.get('refresh_token'):
            self.refresh_token = token_data['refresh_token']

        # Calcola la scadenza del token di accesso
        if token_data.get('expires_at'):
            # expires_at potrebbe essere un timestamp Unix
            try:
                if isinstance(token_data['expires_at'], (int, float)):
                    self.token_expires_at = datetime.fromtimestamp(token_data['expires_at'])
                else:
                    self.token_expires_at = token_data['expires_at']
            except (TypeError, ValueError, OSError):
                self.token_expires_at = datetime.utcnow() + timedelta(hours=1)
        elif token_data.get('expires_in'):
            expires_in = int(token_data['expires_in'])
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        else:
            # Default: 1 ora (standard Google)
            self.token_expires_at = datetime.utcnow() + timedelta(hours=1)

        # Mantieni compatibilità con il campo esistente
        self.expires_at = self.token_expires_at
        self.last_refresh_at = datetime.utcnow()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<GoogleAuth user_id={self.user_id} expires_at={self.expires_at} has_refresh={self.has_refresh_token()}>"

# ---------------------------------------------------------------------------- #
#  Origine  (per Influencer/Campaigns)
# ---------------------------------------------------------------------------- #
class Origine(TimestampMixin, db.Model):
    """
    Origine dei clienti (es. campagne marketing, influencer, etc).
    Utilizzata per filtrare i clienti visibili agli Influencer.
    """
    __tablename__ = "origins"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    active = db.Column(db.Boolean, default=True, nullable=False)

    influencer_id = db.Column(db.Integer, db.ForeignKey("users.id"), unique=True)
    influencer = db.relationship("User", back_populates="influencer_origin")

    def __repr__(self) -> str:
        return f"<Origine {self.name!r}>"


# ---------------------------------------------------------------------------- #
#  Tabella ponte User (Influencer) ⇄ Origine (M2M)
# ---------------------------------------------------------------------------- #
# user_origins table removed provided 1:1 implementation

# --------------------------------------------------------------------------- #
#  User  (profili interni) – DEFINITIVO
# --------------------------------------------------------------------------- #
# ───────────────────── 4. SOSTITUISCI User ─────────────────────── #
# Estrai solo la parte del modello User da aggiornare

class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = "users"

    # ────────────────────────── PK & credenziali ───────────────────────────
    id            = db.Column(db.Integer, primary_key=True)
    email         = db.Column(db.String(255), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    # ────────────────────────── Profilo base ───────────────────────────────
    first_name   = db.Column(db.String(80),  nullable=False)
    last_name    = db.Column(db.String(80),  nullable=False)
    avatar_path  = db.Column(db.String(255))

    # Limite clienti assegnabili (manuale)
    max_clients = db.Column(db.Integer, nullable=True, default=None)

    # ────────────────────────── AI Notes ───────────────────────────────────
    assignment_ai_notes = db.Column(db.JSON, default=dict, comment="Note strutturate per assegnazione automatica AI")

    # ────────────────────────── Sicurezza ──────────────────────────────────
    last_password_change_at = db.Column(db.DateTime)
    is_admin      = db.Column(db.Boolean, default=False, nullable=False)
    is_active     = db.Column(db.Boolean, default=True , nullable=False)
    last_login_at = db.Column(db.DateTime)
    last_login_ip = db.Column(db.String(45))
    reset_token   = db.Column(db.String(128), unique=True, index=True)
    reset_sent_at = db.Column(db.DateTime)

    # ────────────────────────── Ruolo e Specializzazione (Team System) ──────
    role = db.Column(
        _def(UserRoleEnum),
        default=UserRoleEnum.professionista,
        nullable=False,
        index=True,
        comment="Ruolo utente: admin, team_leader, professionista, team_esterno"
    )
    specialty = db.Column(
        _def(UserSpecialtyEnum),
        nullable=True,
        index=True,
        comment="Specializzazione: nutrizione, psicologia, coach, etc."
    )
    is_external = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="True se l'utente è un collaboratore esterno"
    )

    # ────────────────────────── Trial User System ──────────────────────────────
    is_trial = db.Column(db.Boolean, default=False, nullable=False)
    trial_stage = db.Column(db.Integer, default=1)  # 1=Dashboard+Review, 2=Selected Clients, 3=Full User
    trial_started_at = db.Column(db.DateTime)
    trial_promoted_at = db.Column(db.DateTime)  # Quando è diventato user ufficiale
    trial_supervisor_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # Chi supervisiona questo trial user

    # ────────────────────────── GHL Calendar Integration ─────────────────────────
    ghl_calendar_id = db.Column(db.String(100), index=True, comment="ID calendario GHL associato")
    ghl_user_id = db.Column(db.String(100), index=True, comment="ID utente GHL associato")

    # ────────────────────────── Full-text search ───────────────────────────
    search_vector = db.Column(TSVECTOR)
    __ts_vector__ = TSVectorType(
        "email", "first_name", "last_name",
        regconfig="italian",
        weights={"email": "A", "first_name": "B", "last_name": "B"},
    )

    # ────────────────────────── Relazioni ORM ──────────────────────────────
    departments_led  = relationship("Department", back_populates="head",
                                    lazy="selectin", foreign_keys="Department.head_id")

    teams_led        = relationship("Team", back_populates="head",
                                    lazy="selectin", foreign_keys="Team.head_id")

    # Team di cui l'utente è membro (many-to-many via team_members)
    teams            = relationship("Team", secondary="team_members",
                                    back_populates="members", lazy="selectin")

    certifications   = relationship("Certification", secondary="user_certification",
                                    back_populates="users", lazy="selectin")

    clienti          = relationship("Cliente", 
                                    foreign_keys="Cliente.created_by",
                                    back_populates="created_by_user",
                                    lazy="selectin", cascade="all, delete-orphan")

    # ────────────────────────── Compatibilità / Helpers ────────────────────
    @property
    def department(self):
        """
        Restituisce il dipartimento del primo team dell'utente.
        Helper per compatibilità con codice legacy che si aspetta user.department.
        """
        if self.teams:
            for team in self.teams:
                if team.department:
                    return team.department
        return None

    google_auth      = relationship("GoogleAuth", back_populates="user",
                                    uselist=False, cascade="all, delete-orphan")


    tasks_assigned   = relationship("Task", back_populates="assignee",
                                    lazy="selectin")

    objectives       = relationship(
        "Objective",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Objective.order_index",
    )

    # Nutrition模块
    created_meal_plans = relationship(
        "MealPlan", back_populates="created_by",
        foreign_keys="MealPlan.created_by_id",
        lazy="selectin", cascade="all, delete-orphan",
    )
    created_training_plans = relationship(
        "TrainingPlan", back_populates="created_by",
        foreign_keys="TrainingPlan.created_by_id",
        lazy="selectin", cascade="all, delete-orphan",
    )
    created_training_locations = relationship(
        "TrainingLocation", back_populates="created_by",
        foreign_keys="TrainingLocation.created_by_id",
        lazy="selectin", cascade="all, delete-orphan",
    )
    created_recipes = relationship(
        "Recipe", back_populates="created_by",
        lazy="selectin", cascade="all, delete-orphan",
    )
    nutrition_notes = relationship(
        "NutritionNote", back_populates="nutritionist",
        lazy="selectin", cascade="all, delete-orphan",
    )


    # ───────────────► Relazioni HR estese ◄───────────────
    education = relationship(
        "UserEducation",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="UserEducation.data_conseguimento.desc()",
    )
    
    salary_history = relationship(
        "UserSalaryHistory",
        back_populates="user",
        foreign_keys="UserSalaryHistory.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="UserSalaryHistory.data_effettiva.desc()",
    )
    
    # ───────────────► Relazioni Ferie/Permessi ◄───────────────
    leave_requests = relationship(
        "LeaveRequest",
        back_populates="user",
        foreign_keys="LeaveRequest.user_id",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="LeaveRequest.start_date.desc()",
    )

    # ───────────────► Relazioni Trial System ◄───────────────
    trial_supervisor = relationship(
        "User",
        foreign_keys=[trial_supervisor_id],
        remote_side=[id],
        backref=db.backref("supervised_trial_users", lazy="dynamic")
    )

    # Clienti assegnati per trial users (many-to-many)
    trial_assigned_clients = relationship(
        "Cliente",
        secondary="trial_user_clients",
        primaryjoin="User.id==trial_user_clients.c.user_id",
        secondaryjoin="Cliente.cliente_id==trial_user_clients.c.cliente_id",
        backref="trial_users",
        lazy="selectin"
    )

    # ────────────────────────── Quality Score KPI ──────────────────────────
    quality_score_current_week = db.Column(db.Float)  # Score settimana corrente
    quality_score_current_month = db.Column(db.Float)  # Score mensile (rolling 4 settimane)
    quality_score_current_quarter = db.Column(db.Float)  # Score trimestrale (rolling 12 settimane)
    bonus_band_current = db.Column(db.String(10))  # Banda bonus attuale ('100%', '60%', '30%', '0%')
    quality_last_updated = db.Column(db.DateTime)  # Ultimo aggiornamento Quality Score

    __table_args__ = (
        Index("ix_users_search_vector", "search_vector", postgresql_using="gin"),
    )

    # ────────────────────────── Helper password ────────────────────────────
    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)
        self.last_password_change_at = datetime.utcnow()

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    # ────────────────────────── Proprietà convenience ──────────────────────
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def name(self) -> str:
        """Alias for full_name for compatibility"""
        return self.full_name

    @property
    def avatar_url(self) -> str:
        from flask import url_for
        return (
            url_for("team.serve_avatar", user_id=self.id)
            if self.avatar_path
            else "/static/assets/immagini/logo_user.png"
        )

    @property
    def has_sales_access(self) -> bool:
        """
        Verifica se l'utente ha accesso al sistema Sales Form.
        True se è admin o ha un SalesFormLink attivo.
        """
        if self.is_admin:
            return True

        # Check se ha un SalesFormLink attivo
        from corposostenibile.models import SalesFormLink
        has_link = db.session.query(SalesFormLink).filter(
            SalesFormLink.user_id == self.id,
            SalesFormLink.is_active == True,
            SalesFormLink.lead_id.is_(None)  # Solo link di tipo "sales"
        ).first()

        return has_link is not None

    @property
    def is_nutritionist(self) -> bool:
        """Check if user has nutrition specialty."""
        return self.specialty in [UserSpecialtyEnum.nutrizione, UserSpecialtyEnum.nutrizionista]

    @property
    def role_display(self) -> str:
        """Display name for role."""
        role_labels = {
            'admin': 'Admin',
            'team_leader': 'Team Leader',
            'professionista': 'Professionista',
            'team_esterno': 'Team Esterno',
        }
        role_value = self.role.value if hasattr(self.role, 'value') else str(self.role)
        return role_labels.get(role_value, role_value)

    @property
    def specialty_display(self) -> str:
        """Display name for specialty."""
        if not self.specialty:
            return ""
        specialty_labels = {
            'amministrazione': 'Amministrazione',
            'cco': 'CCO',
            'nutrizione': 'Nutrizione',
            'psicologia': 'Psicologia',
            'coach': 'Coach',
            'nutrizionista': 'Nutrizionista',
            'psicologo': 'Psicologo',
        }
        spec_value = self.specialty.value if hasattr(self.specialty, 'value') else str(self.specialty)
        return specialty_labels.get(spec_value, spec_value)

    # ────────────────────────── Trial User Helpers ─────────────────────────────
    @property
    def trial_stage_description(self) -> str:
        """Descrizione dello stage del trial user."""
        if not self.is_trial:
            return "User Ufficiale"
        stages = {
            1: "Stage 1: Dashboard + Training",
            2: "Stage 2: Clienti Selezionati",
            3: "User Ufficiale"
        }
        return stages.get(self.trial_stage, "Sconosciuto")

    def can_access_section(self, section: str) -> bool:
        """Verifica se un trial user può accedere a una sezione."""
        if not self.is_trial:
            return True  # User normale, accesso completo

        if self.is_admin:
            return True  # Admin ha sempre accesso

        # Stage 1: Solo Dashboard e Training (Review)
        if self.trial_stage == 1:
            allowed_sections = ['dashboard', 'review', 'training', 'auth', 'welcome']
            return section.lower() in allowed_sections

        # Stage 2: Dashboard, Training e Clienti Selezionati
        if self.trial_stage == 2:
            allowed_sections = ['dashboard', 'review', 'training', 'auth', 'welcome', 'customers']
            return section.lower() in allowed_sections

        # Stage 3 o superiore: Accesso completo
        return True

    def can_view_client(self, cliente_id: int) -> bool:
        """Verifica se un trial user può vedere un cliente specifico."""
        if not self.is_trial or self.trial_stage >= 3:
            return True  # User normale o stage 3+

        if self.trial_stage < 2:
            return False  # Stage 1 non può vedere clienti

        # Stage 2: Solo clienti assegnati
        return any(c.cliente_id == cliente_id for c in self.trial_assigned_clients)

    def promote_to_next_stage(self) -> bool:
        """Promuove il trial user allo stage successivo."""
        if not self.is_trial:
            return False

        if self.trial_stage < 3:
            self.trial_stage += 1
            if self.trial_stage == 3:
                # Diventa user ufficiale
                self.is_trial = False
                self.trial_promoted_at = datetime.utcnow()
            db.session.commit()
            return True
        return False

    # ────────────────────────── Flask-Login ────────────────────────────────
    def get_id(self) -> str:             # type: ignore[override]
        return str(self.id)

    def get_roles(self) -> List[str]:
        return ["admin"] if self.is_admin else []

    # ────────────────────────── Influencer Origins ────────────────────────────
    # ────────────────────────── Influencer Origins ────────────────────────────
    influencer_origin = relationship(
        "Origine",
        back_populates="influencer",
        uselist=False,
        lazy="selectin"
    )

    # ────────────────────────── Repr ───────────────────────────────────────
    def __repr__(self) -> str:           # pragma: no cover
        return f"<User {self.email!r}>"
    

class Influencer(TimestampMixin, db.Model):
    __tablename__ = "influencers"

    influencer_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    handle = db.Column(db.String(255))
    note = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True, nullable=False)

    ad_campaigns = relationship("AdCampaign", back_populates="influencer")

# ───────────────────── 1) SALES PERSON ─────────────────────────── #
class SalesPerson(TimestampMixin, db.Model):
    __tablename__ = "sales_person"

    sales_person_id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    role = db.Column(_def(SalesRoleEnum), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)

    # inverse relationships
    # COMMENTATA TEMPORANEAMENTE - da ripristinare quando Cliente avrà personal_consultant_id
    # clienti_personali = relationship("Cliente", back_populates="personal_consultant", cascade="all, delete-orphan")
    
    contratti_venduti = relationship("SubscriptionContract", back_populates="seller", cascade="all, delete-orphan")
    commissions = relationship("Commission", back_populates="recipient", cascade="all, delete-orphan")
    sales_performance = relationship("SalesPerformanceDaily", back_populates="sales_person", cascade="all, delete-orphan")


# ───────────────────── 2) CLIENTI ─────────────────────────────── #

# Tabelle di associazione many-to-many per professionisti multipli
cliente_nutrizionisti = db.Table('cliente_nutrizionisti',
    db.Column('cliente_id', db.Integer, db.ForeignKey('clienti.cliente_id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

cliente_coaches = db.Table('cliente_coaches',
    db.Column('cliente_id', db.Integer, db.ForeignKey('clienti.cliente_id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

cliente_psicologi = db.Table('cliente_psicologi',
    db.Column('cliente_id', db.Integer, db.ForeignKey('clienti.cliente_id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

cliente_consulenti = db.Table('cliente_consulenti',
    db.Column('cliente_id', db.Integer, db.ForeignKey('clienti.cliente_id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

# ─────────────────────────  Storico Stati Servizio  ────────────────────────── #
class StatoServizioLog(TimestampMixin, db.Model):
    """
    Log/Storico dei cambiamenti di stato per i vari servizi del cliente.
    Traccia tutti i cambi di stato per: coaching, nutrizione, psicologia, chat coaching, ecc.
    """
    __tablename__ = "stato_servizio_log"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.cliente_id', ondelete='CASCADE'), nullable=False, index=True)

    # Tipo di servizio: 'coach', 'nutrizione', 'psicologia', 'chat_coaching', 'chat_nutrizione', 'chat_psicologia'
    servizio = db.Column(db.String(50), nullable=False, index=True)

    # Stato del servizio
    stato = db.Column(_def(StatoClienteEnum), nullable=False)

    # Range temporale dello stato
    data_inizio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_fine = db.Column(db.DateTime, nullable=True)  # NULL = ancora in corso

    # Relazione con il cliente
    cliente = db.relationship('Cliente', backref=db.backref('storico_stati', lazy='dynamic', order_by='StatoServizioLog.data_inizio.desc()'))

    def __repr__(self):
        stato_str = "in corso" if self.data_fine is None else f"fino al {self.data_fine.strftime('%d/%m/%Y')}"
        return f"<StatoServizioLog {self.servizio}={self.stato.value} dal {self.data_inizio.strftime('%d/%m/%Y')} {stato_str}>"

    @property
    def is_attivo(self):
        """Ritorna True se questo stato è ancora attivo (data_fine è NULL)"""
        return self.data_fine is None

    @property
    def durata_giorni(self):
        """Calcola la durata in giorni dello stato"""
        fine = self.data_fine or datetime.utcnow()
        return (fine - self.data_inizio).days


class PatologiaLog(TimestampMixin, db.Model):
    """
    Log/Storico delle patologie del cliente.
    Traccia quando una patologia viene aggiunta o rimossa per avere uno storico completo.
    """
    __tablename__ = "patologia_log"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.cliente_id', ondelete='CASCADE'), nullable=False, index=True)

    # Nome della patologia (es: 'ibs', 'dca', 'diabete', ecc.)
    patologia = db.Column(db.String(100), nullable=False, index=True)

    # Nome visualizzato della patologia (es: 'IBS', 'DCA', 'Diabete')
    patologia_nome = db.Column(db.String(200), nullable=False)

    # Azione: 'aggiunta' o 'rimossa'
    azione = db.Column(db.String(20), nullable=False)

    # Range temporale della patologia
    data_inizio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_fine = db.Column(db.DateTime, nullable=True)  # NULL = ancora presente

    # Note opzionali
    note = db.Column(db.Text, nullable=True)

    # Relazione con il cliente
    cliente = db.relationship('Cliente', backref=db.backref('storico_patologie', lazy='dynamic', order_by='PatologiaLog.data_inizio.desc()'))

    def __repr__(self):
        stato_str = "presente" if self.data_fine is None else f"rimossa il {self.data_fine.strftime('%d/%m/%Y')}"
        return f"<PatologiaLog {self.patologia_nome} {self.azione} il {self.data_inizio.strftime('%d/%m/%Y')} - {stato_str}>"

    @property
    def is_attiva(self):
        """Ritorna True se questa patologia è ancora presente (data_fine è NULL)"""
        return self.data_fine is None

    @property
    def durata_giorni(self):
        """Calcola la durata in giorni della patologia"""
        fine = self.data_fine or datetime.utcnow()
        return (fine - self.data_inizio).days


class PatologiaPsicoLog(TimestampMixin, db.Model):
    """
    Log/Storico delle patologie psicologiche del cliente.
    Traccia quando una patologia psicologica viene aggiunta o rimossa per avere uno storico completo.
    """
    __tablename__ = "patologia_psico_log"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.cliente_id', ondelete='CASCADE'), nullable=False, index=True)

    # Nome della patologia psicologica (es: 'dca', 'obesita_psicoemotiva', ecc.)
    patologia = db.Column(db.String(100), nullable=False, index=True)

    # Nome visualizzato della patologia (es: 'Disturbi del comportamento alimentare (DCA)', ecc.)
    patologia_nome = db.Column(db.String(200), nullable=False)

    # Azione: 'aggiunta' o 'rimossa'
    azione = db.Column(db.String(20), nullable=False)

    # Range temporale della patologia
    data_inizio = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    data_fine = db.Column(db.DateTime, nullable=True)  # NULL = ancora presente

    # Note opzionali
    note = db.Column(db.Text, nullable=True)

    # Relazione con il cliente
    cliente = db.relationship('Cliente', backref=db.backref('storico_patologie_psico', lazy='dynamic', order_by='PatologiaPsicoLog.data_inizio.desc()'))

    def __repr__(self):
        stato_str = "presente" if self.data_fine is None else f"rimossa il {self.data_fine.strftime('%d/%m/%Y')}"
        return f"<PatologiaPsicoLog {self.patologia_nome} {self.azione} il {self.data_inizio.strftime('%d/%m/%Y')} - {stato_str}>"

    @property
    def is_attiva(self):
        """Ritorna True se questa patologia è ancora presente (data_fine è NULL)"""
        return self.data_fine is None

    @property
    def durata_giorni(self):
        """Calcola la durata in giorni della patologia"""
        fine = self.data_fine or datetime.utcnow()
        return (fine - self.data_inizio).days


# ─────────────────────────  Cliente  ────────────────────────── #
# ─────────────────────────  Cliente (VERSIONE RIDOTTA COMPLETA) ────────────────────────── #
class Cliente(TimestampMixin, db.Model):
    """
    Anagrafica clienti – **versione ridotta** con i soli campi essenziali
    (quelli effettivamente utilizzati dai blueprint in produzione).

    • Versionata con SQLAlchemy-Continuum ( ``__versioned__ = {}`` ).
    • Compatibilità con il vecchio schema mantenuta tramite alcune *property*
      (ltv, email, numero_tel, …) così da non dover toccare tutto il codice
      legacy in un’unica PR.
    """

    __tablename__  = "clienti"
    __versioned__  = {}                       # ⇦ abilita versioning

    # ─────────────────── CHIAVE PRIMARIA ───────────────────────── #
    cliente_id      = db.Column(db.BigInteger, primary_key=True)

    # ─────────────────── FULL-TEXT SEARCH (PG FTS) ─────────────── #
    search_vector   = db.Column(
        TSVectorType("nome_cognome", "consulente_alimentare")
    )

    # ───────────────────────── CAMPI BASE ───────────────────────── #

    # Anagrafica
    nome_cognome            = db.Column(db.String(255), nullable=False)
    data_di_nascita         = db.Column(db.Date)
    professione             = db.Column(db.Text)
    professione_note        = db.Column(db.Text)  # Note aggiuntive sulla professione

    # Dati aggiuntivi finance (tutti facoltativi)
    origine                 = db.Column(db.String(255))  # Origine del cliente (Legacy/Display)
    origine_id              = db.Column(db.Integer, db.ForeignKey("origins.id"), nullable=True, index=True)
    
    origine_obj             = relationship("Origine", backref="clienti", lazy="joined")

    deposito_iniziale       = db.Column(db.Numeric(10, 2))  # Deposito iniziale
    paese                   = db.Column(db.String(100))  # Paese di residenza
    genere                  = db.Column(db.String(20))   # M/F/Altro
    mail                    = db.Column(db.String(255))  # Email
    numero_telefono         = db.Column(db.String(50))   # Numero di telefono
    indirizzo               = db.Column(db.Text)         # Indirizzo completo

    # Programma
    storico_programma       = db.Column(db.Text)
    programma_attuale       = db.Column(db.Text)
    programma_attuale_dettaglio = db.Column(db.String(100))  # BP, BALANCE PLATE, etc.
    macrocategoria          = db.Column(db.Text)

    # Abbonamento
    data_inizio_abbonamento = db.Column(db.Date)
    durata_programma_giorni = db.Column(db.Integer)
    rate_cliente_sales      = db.Column(NUMERIC)
    rate_cliente_sales_dettaglio = db.Column(db.Text)  # Dettaglio testuale pagamenti

    # Obiettivi / consulenza
    obiettivo_semplicato    = db.Column(db.Text)
    obiettivo_cliente       = db.Column(db.Text)  # Obiettivo dettagliato dall'Excel
    consulente_alimentare   = db.Column(db.Text)

    # Date call iniziali
    data_call_iniziale_nutrizionista = db.Column(db.Date)
    data_call_iniziale_psicologia    = db.Column(db.Date)
    data_call_iniziale_coach         = db.Column(db.Date)

    # Problematiche
    problema                = db.Column(db.Text)
    paure                   = db.Column(db.Text)
    conseguenze             = db.Column(db.Text)
    storia_cliente          = db.Column(db.Text)  # Storia completa del cliente

    # Patologie
    nessuna_patologia                   = db.Column(db.Boolean, default=False)
    patologia_ibs                       = db.Column(db.Boolean, default=False)
    patologia_reflusso                  = db.Column(db.Boolean, default=False)
    patologia_gastrite                  = db.Column(db.Boolean, default=False)
    patologia_dca                       = db.Column(db.Boolean, default=False)
    patologia_insulino_resistenza       = db.Column(db.Boolean, default=False)
    patologia_diabete                   = db.Column(db.Boolean, default=False)
    patologia_dislipidemie              = db.Column(db.Boolean, default=False)
    patologia_steatosi_epatica          = db.Column(db.Boolean, default=False)
    patologia_ipertensione              = db.Column(db.Boolean, default=False)
    patologia_pcos                      = db.Column(db.Boolean, default=False)
    patologia_endometriosi              = db.Column(db.Boolean, default=False)
    patologia_obesita_sindrome          = db.Column(db.Boolean, default=False)
    patologia_osteoporosi               = db.Column(db.Boolean, default=False)
    patologia_diverticolite             = db.Column(db.Boolean, default=False)
    patologia_crohn                     = db.Column(db.Boolean, default=False)
    patologia_stitichezza               = db.Column(db.Boolean, default=False)
    patologia_tiroidee                  = db.Column(db.Boolean, default=False)

    # Patologie Psicologiche
    nessuna_patologia_psico                    = db.Column(db.Boolean, default=False)
    patologia_psico_dca                        = db.Column(db.Boolean, default=False)
    patologia_psico_obesita_psicoemotiva       = db.Column(db.Boolean, default=False)
    patologia_psico_ansia_umore_cibo           = db.Column(db.Boolean, default=False)
    patologia_psico_comportamenti_disfunzionali = db.Column(db.Boolean, default=False)
    patologia_psico_immagine_corporea          = db.Column(db.Boolean, default=False)
    patologia_psico_psicosomatiche             = db.Column(db.Boolean, default=False)
    patologia_psico_relazionali_altro          = db.Column(db.Boolean, default=False)
    
    # Campi testuali per "Altro"
    patologia_altro                     = db.Column(db.Text)  # Campo testuale per "Altro" nutrizione
    patologia_psico_altro               = db.Column(db.Text)  # Campo testuale per "Altro" psicologia

    # Bonus & Alert
    bonus                   = db.Column(db.Boolean)
    alert                   = db.Column(db.Boolean)
    alert_storia            = db.Column(db.Text)

    # Rinnovi
    data_rinnovo            = db.Column(db.Date)
    # giorni_rimanenti rimosso - ora usiamo giorni_rimanenti_calcolati (property)
    in_scadenza             = db.Column(db.String(20))  # Boolean o "Interno"

    # Team / pagamento / tipologia
    di_team                 = db.Column(_def(TeamEnum))
    modalita_pagamento      = db.Column(_def(PagamentoEnum))
    note_rinnovo            = db.Column(db.Text)
    tipologia_cliente       = db.Column(_def(TipologiaClienteEnum))

    # Staff (ora stringhe singole per compatibilità Excel)
    nutrizionista           = db.Column(db.String(255))  # Nome singolo
    coach                   = db.Column(db.String(255))  # Nome singolo
    psicologa               = db.Column(db.String(255))  # Nome singolo
    
    # FK per i professionisti (nuove colonne per associazione con User)
    nutrizionista_id        = db.Column(db.Integer, db.ForeignKey("users.id"))
    coach_id                = db.Column(db.Integer, db.ForeignKey("users.id"))
    psicologa_id            = db.Column(db.Integer, db.ForeignKey("users.id"))
    consulente_alimentare_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    health_manager_id       = db.Column(db.Integer, db.ForeignKey("users.id"))  # NUOVO - Health Manager dal dipartimento 13

    # Call iniziali (flag)
    call_iniziale_nutrizionista = db.Column(db.Boolean)
    call_iniziale_coach         = db.Column(db.Boolean)
    call_iniziale_psicologa     = db.Column(db.Boolean)

    # Test & piani
    data_test_alim          = db.Column(db.Date)
    tipo_iniziale           = db.Column(db.Text)
    tipo_attuale            = db.Column(db.Text)
    piano_alimentare        = db.Column(db.Text)

    # Check & stati
    check_day               = db.Column(_def(GiornoEnum))
    stato_cliente           = db.Column(_def(StatoClienteEnum))
    check_saltati           = db.Column(_def(CheckSaltatiEnum))
    stato_cliente_chat      = db.Column(_def(StatoClienteEnum))  # Campo legacy generale
    stato_cliente_chat_nutrizione  = db.Column(_def(StatoClienteEnum))  # Stato chat specifico per servizio nutrizione
    stato_cliente_chat_coaching    = db.Column(_def(StatoClienteEnum))  # Stato chat specifico per servizio coaching
    stato_cliente_chat_psicologia  = db.Column(_def(StatoClienteEnum))  # Stato chat specifico per servizio psicologia

    # Stati servizi (rinominato e aggiunti nuovi)
    stato_psicologia        = db.Column(_def(StatoClienteEnum))  # Rinominato da stato_cliente_sedute_psico
    stato_nutrizione        = db.Column(_def(StatoClienteEnum))  # NUOVO
    stato_coach             = db.Column(_def(StatoClienteEnum))  # NUOVO
    
    # Date cambio stato servizi (per tracciabilità)
    stato_psicologia_data   = db.Column(db.DateTime)  # NUOVO - quando è cambiato lo stato
    stato_nutrizione_data   = db.Column(db.DateTime)  # NUOVO - quando è cambiato lo stato
    stato_coach_data        = db.Column(db.DateTime)  # NUOVO - quando è cambiato lo stato
    stato_cliente_data      = db.Column(db.DateTime)  # NUOVO - quando è cambiato lo stato globale

    # ========== VALUTAZIONE OBIETTIVI ARR ==========
    # Usato per calcolo ARR: cliente con obiettivi residui conta nel denominatore
    has_goals_left = db.Column(db.Boolean, nullable=True, comment="Se cliente ha ancora obiettivi da raggiungere")
    goals_evaluation_date = db.Column(db.DateTime, nullable=True, comment="Data ultima valutazione obiettivi")
    evaluated_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, comment="Chi ha valutato gli obiettivi")

    # Storie specialisti
    storia_coach            = db.Column(db.Text)
    note_extra_coach        = db.Column(db.Text)  # Note aggiuntive coach
    storia_nutrizione       = db.Column(db.Text)
    note_extra_nutrizione   = db.Column(db.Text)
    storia_psicologica      = db.Column(db.Text)
    note_extra_psicologa    = db.Column(db.Text)  # Note aggiuntive psicologa

    # Note Alert / Criticità per servizio
    alert_nutrizione        = db.Column(db.Text)  # Note critiche nutrizione
    alert_coaching          = db.Column(db.Text)  # Note critiche coaching
    alert_psicologia        = db.Column(db.Text)  # Note critiche psicologia

    # Reach-out / social
    reach_out               = db.Column(_def(GiornoEnum))  # Giorno della settimana (campo legacy generale)
    reach_out_nutrizione    = db.Column(_def(GiornoEnum))  # Reach out specifico per servizio nutrizione
    reach_out_coaching      = db.Column(_def(GiornoEnum))  # Reach out specifico per servizio coaching
    reach_out_psicologia    = db.Column(_def(GiornoEnum))  # Reach out specifico per servizio psicologia

    # Allenamento / dieta
    allenamento_dal         = db.Column(db.Date)
    nuovo_allenamento_il    = db.Column(db.Date)
    luogo_di_allenamento    = db.Column(_def(LuogoAllenEnum))

    dieta_dal               = db.Column(db.Date)
    nuova_dieta_dal         = db.Column(db.Date)

    # Figura di riferimento
    figura_di_riferimento   = db.Column(_def(FiguraRifEnum))

    # Social & media flags
    no_social               = db.Column(db.Boolean)  # Richiede di non condividere
    social_oscurato         = db.Column(db.Boolean)  # Solo da oscurato
    video_feedback          = db.Column(db.Boolean)
    proposta_live_training  = db.Column(db.Boolean)
    live_training_proposte  = db.Column(db.Boolean)
    live_training_bonus_prenotata = db.Column(db.Boolean)  # Da Excel
    video_feedback_richiesto = db.Column(db.Boolean)
    video_feedback_svolto    = db.Column(db.Boolean)
    video_feedback_condiviso = db.Column(db.Boolean)

    # Trasformazione
    trasformazione_fisica            = db.Column(db.Boolean)
    trasformazione_fisica_condivisa  = db.Column(db.Boolean)
    trasformazione                   = db.Column(_def(TrasformazioneEnum))

    # Exit-call
    exit_call_richiesta   = db.Column(db.Boolean)
    exit_call_svolta      = db.Column(db.Boolean)
    exit_call_condivisa   = db.Column(db.Boolean)
    exit_call_note        = db.Column(db.Text)  # Note per richiesta/rifiuto/ricezione

    # ───────────────────── HEALTH MANAGER FEATURES ──────────────────── #

    # Consenso Social
    consenso_social_richiesto = db.Column(db.Boolean)
    consenso_social_accettato = db.Column(db.Boolean)
    consenso_social_note      = db.Column(db.Text)  # Note per richiesta/rifiuto/ricezione
    consenso_social_documento = db.Column(db.String(500))  # Path al documento firmato

    # Recensione Scritta
    recensione_richiesta  = db.Column(db.Boolean)
    recensione_accettata  = db.Column(db.Boolean)
    recensione_stelle     = db.Column(db.Integer)  # Rating 1-5 stelle
    recensione_testo      = db.Column(db.Text)  # Testo della recensione
    recensione_risposta   = db.Column(db.Boolean)  # Risposto alla recensione

    # Quality Score tracking (estensioni)
    ultima_recensione_trustpilot_data = db.Column(db.DateTime)  # Data ultima recensione Trustpilot applicata
    recensioni_lifetime_count = db.Column(db.Integer, default=0)  # Numero totale recensioni ricevute (lifetime)

    # Videofeedback (enhancement degli esistenti)
    videofeedback_note    = db.Column(db.Text)  # Note per richiesta/rifiuto/ricezione
    videofeedback_file    = db.Column(db.String(500))  # Path al file video

    # Referral Richiesti
    referral_richiesti_note = db.Column(db.Text)  # Note per richiesta/rifiuto/ricezione

    # Sedute psicologia
    sedute_psicologia_comprate = db.Column(db.Integer)  # Numero sedute acquistate
    sedute_psicologia_svolte = db.Column(db.Integer)    # Numero sedute effettuate

    # ───────────────────── FREEZE MANAGEMENT ─────────────────────── #
    # Campi per gestione stato FREEZE
    is_frozen = db.Column(db.Boolean, default=False)  # Flag rapido per verificare se è in freeze
    freeze_date = db.Column(db.DateTime)  # Quando è stato messo in freeze
    freeze_reason = db.Column(db.Text)  # Motivazione del freeze (opzionale)
    freeze_resolution = db.Column(db.Text)  # Storia/risoluzione quando viene rimosso il freeze
    frozen_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # Chi ha messo in freeze
    unfrozen_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # Chi ha rimosso il freeze

    # ───────────────────── ONBOARDING (HEALTH MANAGER) ────────────── #
    # Campi per gestione onboarding iniziale
    onboarding_date = db.Column(db.Date)  # Data di onboarding del cliente
    note_criticita_iniziali = db.Column(db.Text)  # Note sulle criticità iniziali rilevate durante onboarding

    # ───────────────────── RELAZIONI "CORE" ─────────────────────── #

    # FK → User che ha creato il cliente
    created_by            = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_user       = relationship("User", foreign_keys=[created_by], back_populates="clienti")
    
    # Relazioni con i professionisti (singoli - per retrocompatibilità)
    nutrizionista_user    = relationship("User", foreign_keys=[nutrizionista_id], backref="clienti_nutrizionista_single")
    coach_user            = relationship("User", foreign_keys=[coach_id], backref="clienti_coach_single")
    psicologa_user        = relationship("User", foreign_keys=[psicologa_id], backref="clienti_psicologa_single")
    consulente_user       = relationship("User", foreign_keys=[consulente_alimentare_id], backref="clienti_consulente_single")
    health_manager_user   = relationship("User", foreign_keys=[health_manager_id], backref="clienti_health_manager")  # NUOVO
    
    # Relazioni many-to-many per professionisti multipli
    nutrizionisti_multipli = relationship("User", secondary=cliente_nutrizionisti, 
                                          backref="clienti_nutrizionista_multi",
                                          lazy="selectin")
    coaches_multipli       = relationship("User", secondary=cliente_coaches,
                                          backref="clienti_coach_multi",
                                          lazy="selectin")
    psicologi_multipli     = relationship("User", secondary=cliente_psicologi,
                                          backref="clienti_psicologa_multi",
                                          lazy="selectin")
    consulenti_multipli    = relationship("User", secondary=cliente_consulenti,
                                          backref="clienti_consulente_multi",
                                          lazy="selectin")

    # Cartelle cliniche & allegati
    cartelle              = relationship(
        "CartellaClinica",
        back_populates="cliente",
        cascade="all, delete-orphan",
    )


    # Task Kanban
    tasks                 = relationship(
        "Task",
        back_populates="client",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    
    # TypeForm responses
    typeform_responses    = relationship(
        "TypeFormResponse",
        back_populates="cliente",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # ───────────────────── RELAZIONI NUTRITION ──────────────────── #

    nutritional_profile   = relationship(
        "NutritionalProfile",
        back_populates="cliente",
        uselist=False,
        cascade="all, delete-orphan",
    )

    health_assessments    = relationship(
        "HealthAssessment",
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="HealthAssessment.assessment_date.desc()",
    )

    biometric_data        = relationship(
        "BiometricData",
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="BiometricData.measurement_date.desc()",
    )

    meal_plans            = relationship(
        "MealPlan",
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="MealPlan.start_date.desc()",
    )

    training_plans        = relationship(
        "TrainingPlan",
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="TrainingPlan.start_date.desc()",
    )

    training_locations    = relationship(
        "TrainingLocation",
        back_populates="cliente",
        cascade="all, delete-orphan",
        order_by="TrainingLocation.start_date.desc()",
    )

    dietary_preferences   = relationship(
        "DietaryPreference",
        secondary="cliente_dietary_preference",
        back_populates="clienti",
    )

    food_intolerances     = relationship(
        "FoodIntolerance",
        secondary="cliente_food_intolerance",
        back_populates="clienti",
    )


    # ───────────────── PROPERTY DI COMPATIBILITÀ ────────────────── #

    @property
    def ltv(self) -> float:
        """Proxy LTV totale (usa *rate_cliente_sales* finché non c’è la tabella payments)."""
        return float(self.rate_cliente_sales or 0)

    @property
    def ltv_90_gg(self) -> float:
        """Proxy LTV 90 gg – idem sopra."""
        return float(self.rate_cliente_sales or 0)

    @property
    def email(self) -> str:
        """Compat: restituisce *consulente_alimentare* come “email” placeholder."""
        return self.consulente_alimentare or ""

    @property
    def numero_tel(self) -> str:
        """Compat placeholder – non esiste ancora campo telefono nel nuovo schema."""
        return ""

    # ───────────────── PROPERTY CALCOLATE ────────────────────────── #

    @property
    def giorni_rimanenti_calcolati(self) -> Optional[int]:
        """Giorni rimanenti al rinnovo (calcolati dinamicamente)."""
        if not self.data_rinnovo:
            return None
        delta = self.data_rinnovo - date.today()
        return delta.days
    
    @property
    def mesi_come_cliente(self) -> int:
        """Mesi trascorsi da *data_inizio_abbonamento*."""
        if not self.data_inizio_abbonamento:
            return 0
        delta = date.today() - self.data_inizio_abbonamento
        return max(0, delta.days // 30)

    @property
    def age(self) -> Optional[int]:
        """Età in anni basata su *data_di_nascita* (None se mancante)."""
        if not self.data_di_nascita:
            return None
        today = date.today()
        return (
            today.year
            - self.data_di_nascita.year
            - (
                (today.month, today.day)
                < (self.data_di_nascita.month, self.data_di_nascita.day)
            )
        )

    # Nutri-helpers
    @property
    def current_bmr(self) -> Optional[float]:
        """Basal Metabolic Rate – formula Harris-Benedict."""
        latest = self.biometric_data.first() if self.biometric_data else None
        if not latest or not self.nutritional_profile or self.age is None:
            return None

        if self.genere == GenereEnum.uomo:
            bmr = 88.362 + 13.397 * latest.weight + 4.799 * latest.height - 5.677 * self.age
        else:
            bmr = 447.593 + 9.247 * latest.weight + 3.098 * latest.height - 4.330 * self.age
        return round(bmr, 2)

    @property
    def current_tdee(self) -> Optional[float]:
        """Total Daily Energy Expenditure basato su BMR × livello attività."""
        if self.current_bmr is None or not self.nutritional_profile:
            return None

        multipliers = {
            ActivityLevelEnum.sedentario: 1.2,
            ActivityLevelEnum.leggermente_attivo: 1.375,
            ActivityLevelEnum.moderatamente_attivo: 1.55,
            ActivityLevelEnum.molto_attivo: 1.725,
            ActivityLevelEnum.estremamente_attivo: 1.9,
        }
        mult = multipliers.get(self.nutritional_profile.activity_level, 1.2)
        return round(self.current_bmr * mult, 2)

    @property
    def genere_from_profile(self) -> Optional[GenereEnum]:
        """Genero letto dal profilo nutrizionale (se presente)."""
        if self.nutritional_profile:
            return self.nutritional_profile.gender
        return None


    # ───────────────────────── PROPERTY COMPATIBILITÀ ──────────────────────── #
    @property
    def stato_cliente_sedute_psico(self):
        """Compatibilità con vecchio nome campo."""
        return self.stato_psicologia
    
    @stato_cliente_sedute_psico.setter
    def stato_cliente_sedute_psico(self, value):
        """Compatibilità con vecchio nome campo - aggiorna anche la data."""
        if self.stato_psicologia != value:
            self.stato_psicologia = value
            self.stato_psicologia_data = datetime.utcnow()
    
    # ───────────────────────── METODI STATO ──────────────────────── #
    def update_stato_servizio(self, servizio: str, nuovo_stato: StatoClienteEnum):
        """Aggiorna lo stato di un servizio e la relativa data."""
        from datetime import datetime

        vecchio_stato = None
        stato_cambiato = False

        if servizio == 'nutrizione':
            vecchio_stato = self.stato_nutrizione
            if self.stato_nutrizione != nuovo_stato:
                self.stato_nutrizione = nuovo_stato
                self.stato_nutrizione_data = datetime.utcnow()
                stato_cambiato = True
        elif servizio == 'coach':
            vecchio_stato = self.stato_coach
            if self.stato_coach != nuovo_stato:
                self.stato_coach = nuovo_stato
                self.stato_coach_data = datetime.utcnow()
                stato_cambiato = True
        elif servizio == 'psicologia':
            vecchio_stato = self.stato_psicologia
            if self.stato_psicologia != nuovo_stato:
                self.stato_psicologia = nuovo_stato
                self.stato_psicologia_data = datetime.utcnow()
                stato_cambiato = True

        # Registra il cambio di stato nello storico
        if stato_cambiato:
            self._registra_cambio_stato_storico(servizio, nuovo_stato)

        # Se lo stato è cambiato in ghost, notifica gli altri professionisti
        if vecchio_stato != nuovo_stato and nuovo_stato == StatoClienteEnum.ghost:
            self.notify_service_ghost_status(servizio)

        # Dopo ogni cambio, verifica se deve cambiare lo stato globale
        self.check_stato_globale_ghost()

    def _registra_cambio_stato_storico(self, servizio: str, nuovo_stato: StatoClienteEnum):
        """
        Registra il cambio di stato nello storico.
        Chiude lo stato precedente e crea un nuovo record per il nuovo stato.
        """
        from datetime import datetime

        # Chiudi lo stato precedente (se esiste)
        stato_attuale = StatoServizioLog.query.filter_by(
            cliente_id=self.cliente_id,
            servizio=servizio,
            data_fine=None
        ).first()

        if stato_attuale:
            stato_attuale.data_fine = datetime.utcnow()

        # Crea il nuovo record per il nuovo stato
        nuovo_log = StatoServizioLog(
            cliente_id=self.cliente_id,
            servizio=servizio,
            stato=nuovo_stato,
            data_inizio=datetime.utcnow()
        )
        db.session.add(nuovo_log)

    def update_stato_chat(self, servizio: str, nuovo_stato: StatoClienteEnum):
        """
        Aggiorna lo stato della chat per un servizio specifico e registra nello storico.
        servizio: 'coaching', 'nutrizione', 'psicologia'
        """
        from datetime import datetime

        vecchio_stato = None
        stato_cambiato = False
        nome_servizio_log = f"chat_{servizio}"

        if servizio == 'coaching':
            vecchio_stato = self.stato_cliente_chat_coaching
            if self.stato_cliente_chat_coaching != nuovo_stato:
                self.stato_cliente_chat_coaching = nuovo_stato
                stato_cambiato = True
        elif servizio == 'nutrizione':
            vecchio_stato = self.stato_cliente_chat_nutrizione
            if self.stato_cliente_chat_nutrizione != nuovo_stato:
                self.stato_cliente_chat_nutrizione = nuovo_stato
                stato_cambiato = True
        elif servizio == 'psicologia':
            vecchio_stato = self.stato_cliente_chat_psicologia
            if self.stato_cliente_chat_psicologia != nuovo_stato:
                self.stato_cliente_chat_psicologia = nuovo_stato
                stato_cambiato = True

        # Registra il cambio di stato nello storico
        if stato_cambiato:
            self._registra_cambio_stato_storico(nome_servizio_log, nuovo_stato)
    
    def check_stato_globale_ghost(self):
        """
        Verifica se il cliente deve andare in ghost globale.
        Il cliente va in ghost se TUTTI i servizi che ha sono in ghost.
        """
        from datetime import datetime
        
        # Raccogli gli stati dei servizi che il cliente ha effettivamente
        stati_attivi = []
        
        # Nutrizione: verifica se ha nutrizionisti
        if self.nutrizionisti_multipli or self.nutrizionista_id or self.nutrizionista:
            if self.stato_nutrizione:
                stati_attivi.append(self.stato_nutrizione)
        
        # Coach: verifica se ha coach
        if self.coaches_multipli or self.coach_id or self.coach:
            if self.stato_coach:
                stati_attivi.append(self.stato_coach)
        
        # Psicologia: verifica se ha psicologi
        if self.psicologi_multipli or self.psicologa_id or self.psicologa:
            if self.stato_psicologia:
                stati_attivi.append(self.stato_psicologia)
        
        # Se non ha servizi o non ha stati, non fare nulla
        if not stati_attivi:
            return
        
        # Se TUTTI gli stati attivi sono ghost, metti il cliente in ghost
        if all(stato == StatoClienteEnum.ghost for stato in stati_attivi):
            if self.stato_cliente != StatoClienteEnum.ghost:
                old_stato = self.stato_cliente
                self.stato_cliente = StatoClienteEnum.ghost
                self.stato_cliente_data = datetime.utcnow()
                
                # Invia notifiche ai professionisti
                self.notify_professionals_ghost_status(old_stato)
        # Se almeno uno non è ghost e il cliente è ghost, riattiva
        elif self.stato_cliente == StatoClienteEnum.ghost:
            if any(stato != StatoClienteEnum.ghost for stato in stati_attivi):
                self.stato_cliente = StatoClienteEnum.attivo
                self.stato_cliente_data = datetime.utcnow()
    
    def notify_service_ghost_status(self, servizio: str):
        """Invia email di notifica quando un singolo servizio va in ghost."""
        from corposostenibile.blueprints.customers.notifications import notify_service_ghost
        notify_service_ghost(self, servizio)
    
    def notify_professionals_ghost_status(self, old_stato):
        """Invia email di notifica ai professionisti quando un cliente va in ghost globale."""
        from corposostenibile.blueprints.customers.notifications import (
            notify_professionals_on_ghost,
            notify_client_reactivation
        )
        
        if self.stato_cliente == StatoClienteEnum.ghost:
            # Cliente è andato in ghost globale
            notify_professionals_on_ghost(self)
        elif old_stato == StatoClienteEnum.ghost:
            # Cliente è uscito dallo stato ghost
            notify_client_reactivation(self)
    
    def get_stato_data_display(self, servizio: str) -> str:
        """
        Ritorna la data di cambio stato formattata o il messaggio default.
        """
        data = None
        if servizio == 'nutrizione':
            data = self.stato_nutrizione_data
        elif servizio == 'coach':
            data = self.stato_coach_data
        elif servizio == 'psicologia':
            data = self.stato_psicologia_data
        elif servizio == 'cliente':
            data = self.stato_cliente_data

        if data:
            return data.strftime('%d/%m/%Y %H:%M')
        return "Data non presente, vecchia procedura"

    # ===== NUOVI CAMPI PER INTEGRAZIONE GHL =====

    # Tracking GHL
    ghl_contact_id = db.Column(db.String(100), unique=True, index=True)
    ghl_last_sync = db.Column(db.DateTime)

    # Stato pagamento dettagliato
    payment_status = db.Column(db.String(50), default='pending', index=True)
    # Valori: 'pending', 'partial_paid', 'fully_paid', 'verified', 'refunded'
    payment_verified_at = db.Column(db.DateTime)
    payment_verified_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Stato servizio dettagliato
    service_status = db.Column(db.String(50), default='unassigned', index=True)
    # Valori: 'unassigned', 'assigning', 'partially_assigned', 'fully_assigned', 'active', 'paused', 'completed'
    service_activated_at = db.Column(db.DateTime)

    # Tracking acquisizione
    acquisition_source = db.Column(db.String(100))  # 'ghl_webhook', 'manual_entry', 'excel_import', 'website_form'
    acquisition_channel = db.Column(db.String(100))  # 'instagram', 'facebook', 'google', 'referral', 'direct'
    acquisition_campaign = db.Column(db.String(200))  # Nome campagna marketing
    acquisition_date = db.Column(db.DateTime, default=datetime.utcnow)
    first_contact_date = db.Column(db.DateTime)

    # Servizio clienti assignment
    assigned_service_rep = db.Column(db.Integer, db.ForeignKey('users.id'))
    service_assignment_date = db.Column(db.DateTime)
    service_assignment_method = db.Column(db.String(50))  # 'auto_calendar', 'manual', 'ai_suggested'

    # Tracking ultima modifica da GHL
    ghl_last_modified = db.Column(db.DateTime)
    ghl_modification_count = db.Column(db.Integer, default=0)

    # ===== RELAZIONI AGGIUNTIVE PER GHL =====
    payment_verifier = db.relationship('User', foreign_keys=[payment_verified_by], backref='verified_payments')
    service_rep = db.relationship('User', foreign_keys=[assigned_service_rep], backref='serviced_clients')

    # ===== RELAZIONI FREEZE =====
    frozen_by_user = db.relationship('User', foreign_keys=[frozen_by_id], backref='clients_frozen')
    unfrozen_by_user = db.relationship('User', foreign_keys=[unfrozen_by_id], backref='clients_unfrozen')
    freeze_history = db.relationship('ClienteFreezeHistory', back_populates='cliente',
                                    cascade='all, delete-orphan', order_by='ClienteFreezeHistory.freeze_date.desc()')

    # ===== RELAZIONI CUSTOMER CARE =====
    customer_care_interventions = db.relationship('CustomerCareIntervention', back_populates='cliente',
                                                  cascade='all, delete-orphan', order_by='CustomerCareIntervention.intervention_date.desc()')

    # ───────────────────────── DEBUG / REPR ──────────────────────── #
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Cliente {self.cliente_id} – {self.nome_cognome!r}>"


# ───────────────── CUSTOMER CARE INTERVENTIONS ──────────────────── #
class CustomerCareIntervention(TimestampMixin, db.Model):
    """
    Interventi di Customer Care per un cliente.

    Registra gli interventi effettuati dal team Customer Care con:
    - Data dell'intervento
    - Note testuali descrittive
    - Link opzionale a video Loom
    """
    __tablename__ = "customer_care_interventions"
    __versioned__ = {}  # Abilita versioning

    id = db.Column(db.Integer, primary_key=True)

    # ── Relazione con Cliente ────────────────────────────────────────
    cliente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("clienti.cliente_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Dati intervento ──────────────────────────────────────────────
    intervention_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    notes = db.Column(db.Text, nullable=False)
    loom_link = db.Column(db.String(500))

    # ── Audit trail ──────────────────────────────────────────────────
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )

    # ── Relationships ────────────────────────────────────────────────
    cliente = db.relationship("Cliente", back_populates="customer_care_interventions")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return (
            f"<CustomerCareIntervention #{self.id} "
            f"cliente={self.cliente_id} date={self.intervention_date}>"
        )

    def to_dict(self) -> dict:
        """Serializza per API JSON."""
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "intervention_date": self.intervention_date.isoformat() if self.intervention_date else None,
            "notes": self.notes,
            "loom_link": self.loom_link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": {
                "id": self.created_by.id,
                "full_name": self.created_by.full_name or self.created_by.email,
                "avatar_url": self.created_by.avatar_url
            } if self.created_by else None
        }


# ───────────────── CHECK IN INTERVENTIONS ──────────────────────── #
class CheckInIntervention(TimestampMixin, db.Model):
    """
    Interventi di Check In per un cliente.

    Registra i check-in periodici con il cliente con:
    - Data dell'intervento
    - Note testuali descrittive
    - Link opzionale a video Loom
    """
    __tablename__ = "check_in_interventions"
    __versioned__ = {}  # Abilita versioning

    id = db.Column(db.Integer, primary_key=True)

    # ── Relazione con Cliente ────────────────────────────────────────
    cliente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("clienti.cliente_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Dati intervento ──────────────────────────────────────────────
    intervention_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    notes = db.Column(db.Text, nullable=False)
    loom_link = db.Column(db.String(500))

    # ── Audit trail ──────────────────────────────────────────────────
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )

    # ── Relationships ────────────────────────────────────────────────
    cliente = db.relationship("Cliente", backref="check_in_interventions")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return (
            f"<CheckInIntervention #{self.id} "
            f"cliente={self.cliente_id} date={self.intervention_date}>"
        )

    def to_dict(self) -> dict:
        """Serializza per API JSON."""
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "intervention_date": self.intervention_date.isoformat() if self.intervention_date else None,
            "notes": self.notes,
            "loom_link": self.loom_link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": {
                "id": self.created_by.id,
                "full_name": self.created_by.full_name or self.created_by.email,
                "avatar_url": self.created_by.avatar_url
            } if self.created_by else None
        }


# ───────────────── CONTINUITY CALL INTERVENTIONS ────────────────── #
class ContinuityCallIntervention(TimestampMixin, db.Model):
    """
    Interventi di Continuity Call per un cliente.

    Registra le chiamate di continuità con il cliente con:
    - Data dell'intervento
    - Note testuali descrittive
    - Link opzionale a video Loom
    """
    __tablename__ = "continuity_call_interventions"
    __versioned__ = {}  # Abilita versioning

    id = db.Column(db.Integer, primary_key=True)

    # ── Relazione con Cliente ────────────────────────────────────────
    cliente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("clienti.cliente_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # ── Dati intervento ──────────────────────────────────────────────
    intervention_date = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    notes = db.Column(db.Text, nullable=False)
    loom_link = db.Column(db.String(500))

    # ── Audit trail ──────────────────────────────────────────────────
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )

    # ── Relationships ────────────────────────────────────────────────
    cliente = db.relationship("Cliente", backref="continuity_call_interventions")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self) -> str:
        return (
            f"<ContinuityCallIntervention #{self.id} "
            f"cliente={self.cliente_id} date={self.intervention_date}>"
        )

    def to_dict(self) -> dict:
        """Serializza per API JSON."""
        return {
            "id": self.id,
            "cliente_id": self.cliente_id,
            "intervention_date": self.intervention_date.isoformat() if self.intervention_date else None,
            "notes": self.notes,
            "loom_link": self.loom_link,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "created_by": {
                "id": self.created_by.id,
                "full_name": self.created_by.full_name or self.created_by.email,
                "avatar_url": self.created_by.avatar_url
            } if self.created_by else None
        }


# ───────────────── 3) CARTELLA CLINICA & ALLEGATI ───────────────── #
class CartellaClinica(TimestampMixin, db.Model):
    __tablename__ = "cartelle_cliniche"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("cartelle_cliniche.id"))

    nome = db.Column(db.String(255), nullable=False)
    note = db.Column(db.Text)

    cliente = relationship("Cliente", back_populates="cartelle")
    allegati = relationship("Allegato", back_populates="cartella", cascade="all, delete-orphan")


class Allegato(db.Model):
    __tablename__ = "allegati"

    id = db.Column(db.Integer, primary_key=True)
    cartella_id = db.Column(db.Integer, db.ForeignKey("cartelle_cliniche.id"), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_type = db.Column(db.String(128))
    note = db.Column(db.Text)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)

    cartella = relationship("CartellaClinica", back_populates="allegati")

# ─────────────── 4) CONTRATTI, PAGAMENTI, COMMISSIONI ───────────── #
class SubscriptionContract(TimestampMixin, db.Model):
    __tablename__ = "subscription_contracts"
    __versioned__ = {}

    subscription_id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False
    )

    __table_args__ = (
        Index("ix_subscription_contracts_cliente_id", "cliente_id"),
    )

    # --- date principali
    sale_date = db.Column(db.Date)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    duration_days = db.Column(db.Integer)

    # --- valori economici
    initial_deposit = db.Column(NUMERIC)
    service_type = db.Column(db.Text)
    team_vendita = db.Column(db.Text)
    plusvalenze = db.Column(NUMERIC)
    sedute_psicologia = db.Column(db.Integer)
    rate_cliente_sales = db.Column(NUMERIC)

    # --- seller
    seller_id = db.Column(db.Integer, db.ForeignKey("sales_person.sales_person_id"))

    # --- relazioni
    # COMMENTATA TEMPORANEAMENTE - da ripristinare quando Cliente avrà subscriptions
    # cliente = relationship("Cliente", back_populates="subscriptions")
    
    payments = relationship(
        "PaymentTransaction", back_populates="subscription", cascade="all, delete-orphan"
    )
    renewals = relationship(
        "SubscriptionRenewal", back_populates="subscription", cascade="all, delete-orphan"
    )
    seller = relationship("SalesPerson", back_populates="contratti_venduti")

class SubscriptionRenewal(TimestampMixin, db.Model):
    __tablename__ = "subscription_renewals"
    __versioned__ = {}  # ← versioning abilitato

    renewal_id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(db.Integer, db.ForeignKey("subscription_contracts.subscription_id"), nullable=False)

    renewal_payment_date = db.Column(db.Date)
    renewal_amount = db.Column(NUMERIC)
    renewal_duration_days = db.Column(db.Integer)
    renewal_responsible = db.Column(db.Text)
    payment_method = db.Column(_def(PagamentoEnum))
    note = db.Column(db.Text)

    subscription = relationship("SubscriptionContract", back_populates="renewals")


class PaymentTransaction(TimestampMixin, db.Model):
    __tablename__ = "payment_transactions"
    __versioned__ = {}

    payment_id = db.Column(db.Integer, primary_key=True)
    subscription_id = db.Column(
        db.Integer, db.ForeignKey("subscription_contracts.subscription_id"), nullable=False
    )
    cliente_id = db.Column(
        db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False
    )

    __table_args__ = (
        Index("ix_payment_transactions_cliente_id", "cliente_id"),
    )

    payment_date = db.Column(db.Date)
    amount = db.Column(NUMERIC)
    payment_method = db.Column(_def(PagamentoEnum))
    transaction_type = db.Column(_def(TransactionTypeEnum))
    refund_amount = db.Column(NUMERIC)
    commission_split = db.Column(JSONB)
    note = db.Column(db.Text)
    website_sale = db.Column(db.Boolean)

    subscription = relationship("SubscriptionContract", back_populates="payments")
    # COMMENTATA TEMPORANEAMENTE - da ripristinare quando Cliente avrà payments
    # cliente = relationship("Cliente", back_populates="payments")
    commissions = relationship(
        "Commission", back_populates="payment", cascade="all, delete-orphan"
    )

class Commission(db.Model):
    __tablename__ = "commissions"

    commission_id = db.Column(db.Integer, primary_key=True)
    payment_id = db.Column(
        db.Integer,
        db.ForeignKey("payment_transactions.payment_id"),
        nullable=False,
    )

    role = db.Column(_def(CommissionRoleEnum), nullable=False)

    # ------------------------------------------------------------------ #
    #  Fix:  ripristiniamo la ForeignKey verso sales_person              #
    # ------------------------------------------------------------------ #
    recipient_id = db.Column(
        db.Integer,
        db.ForeignKey("sales_person.sales_person_id"),
        nullable=True,          # può restare NULL se un giorno userai altri target
        comment="ID del destinatario della commissione (Sales, Setter, Coach, …)",
    )

    importo = db.Column(NUMERIC)
    note = db.Column(db.Text)

    # ----------------------------- relazioni --------------------------- #
    payment = relationship("PaymentTransaction", back_populates="commissions")
    recipient = relationship("SalesPerson", back_populates="commissions")



# ─────────────── 7) MARKETING / ADS ────────────────────────── #
class AdCampaign(TimestampMixin, db.Model):
    __tablename__ = "ad_campaigns"

    campaign_id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(255))
    campaign_name = db.Column(db.String(255))
    platform = db.Column(db.String(255))
    objective_type = db.Column(db.String(255))
    influencer_flag = db.Column(_def(InfluencerFlagEnum))
    active = db.Column(db.Boolean, default=True)

    influencer_id = db.Column(db.Integer, db.ForeignKey("influencers.influencer_id"))
    influencer = relationship("Influencer", back_populates="ad_campaigns")

    ad_metrics = relationship("AdMetricsDaily", back_populates="campaign", cascade="all, delete-orphan")


class AdMetricsDaily(db.Model):
    __tablename__ = "ad_metrics_daily"

    ad_metric_id = db.Column(db.Integer, primary_key=True)
    campaign_id = db.Column(db.Integer, db.ForeignKey("ad_campaigns.campaign_id"), nullable=False)

    spesa = db.Column(NUMERIC)
    cpv = db.Column(NUMERIC)
    cpft = db.Column(NUMERIC)
    cpfa = db.Column(NUMERIC)
    cpch = db.Column(NUMERIC)
    cpcb = db.Column(NUMERIC)
    cac = db.Column(NUMERIC)
    chat = db.Column(db.Integer)
    cb = db.Column(db.Integer)
    n_sales = db.Column(db.Integer)
    sales = db.Column(NUMERIC)
    roas = db.Column(NUMERIC)
    roas_totale = db.Column(NUMERIC)
    tgp = db.Column(NUMERIC)
    tgp_cac = db.Column(NUMERIC)
    visite = db.Column(db.Integer)
    followers = db.Column(db.Integer)
    followers_adjusted = db.Column(db.Integer)

    campaign = relationship("AdCampaign", back_populates="ad_metrics")


class TrafficSource(db.Model):
    __tablename__ = "traffic_sources"

    source_id = db.Column(db.Integer, primary_key=True)
    source_name = db.Column(db.String(255))
    medium = db.Column(db.String(255))
    paid_flag = db.Column(db.Boolean)

    metrics = relationship("TrafficMetricsDaily", back_populates="source", cascade="all, delete-orphan")


class TrafficMetricsDaily(db.Model):
    __tablename__ = "traffic_metrics_daily"

    traffic_metric_id = db.Column(db.Integer, primary_key=True)
    source_id = db.Column(db.Integer, db.ForeignKey("traffic_sources.source_id"), nullable=False)
    visite = db.Column(db.Integer)
    leads_da_chiamare = db.Column(db.Integer)

    source = relationship("TrafficSource", back_populates="metrics")


class Setter(db.Model):
    __tablename__ = "setter"

    setter_id = db.Column(db.Integer, primary_key=True)
    setter_name = db.Column(db.String(255))
    active = db.Column(db.Boolean, default=True)

    metrics = relationship("CallbackMetricsDaily", back_populates="setter", cascade="all, delete-orphan")


class CallbackMetricsDaily(db.Model):
    __tablename__ = "callback_metrics_daily"

    cb_metric_id = db.Column(db.Integer, primary_key=True)
    setter_id = db.Column(db.Integer, db.ForeignKey("setter.setter_id"), nullable=False)

    cb_totali = db.Column(db.Integer)
    cb_daily_avg = db.Column(NUMERIC)
    cb_chatting = db.Column(db.Integer)
    cb_setting = db.Column(db.Integer)
    cb_org = db.Column(db.Integer)
    cb_ads = db.Column(db.Integer)
    links_mandati = db.Column(db.Integer)
    chat_org = db.Column(db.Integer)
    chat_ads = db.Column(db.Integer)
    nuovi_important = db.Column(db.Integer)
    perc_cb_risposte = db.Column(NUMERIC)
    perc_cb_leads = db.Column(NUMERIC)
    perc_cb_links = db.Column(NUMERIC)
    perc_cb_nuovi = db.Column(NUMERIC)
    cpcb = db.Column(NUMERIC)
    cpcb_setting = db.Column(NUMERIC)
    cpcb_chatting = db.Column(NUMERIC)
    cb_vs_venditori_svolte = db.Column(db.Integer)

    setter = relationship("Setter", back_populates="metrics")

# ─────────────── 8) SALES PERFORMANCE & HR ─────────────────────── #
class SalesPerformanceDaily(db.Model):
    __tablename__ = "sales_performance_daily"

    sales_perf_id = db.Column(db.Integer, primary_key=True)
    sales_person_id = db.Column(db.Integer, db.ForeignKey("sales_person.sales_person_id"), nullable=False)

    cb1_prenotate = db.Column(db.Integer)
    cb1_confermate = db.Column(db.Integer)
    not_cancelled_rate_pct = db.Column(NUMERIC)
    call1_fatte = db.Column(db.Integer)
    no_show1 = db.Column(db.Integer)
    show_up1_rate = db.Column(NUMERIC)
    cb2 = db.Column(db.Integer)
    call2_fatte = db.Column(db.Integer)
    no_show2 = db.Column(db.Integer)
    show_up2_rate = db.Column(NUMERIC)
    av_calls_day = db.Column(NUMERIC)
    opportunita = db.Column(db.Integer)
    chiuso_won = db.Column(db.Integer)
    chiuso_lost = db.Column(db.Integer)
    pending = db.Column(db.Integer)
    cr = db.Column(NUMERIC)
    cash_collected = db.Column(NUMERIC)
    rate_incassate = db.Column(NUMERIC)
    cpct = db.Column(NUMERIC)
    ipcb = db.Column(NUMERIC)
    avds = db.Column(NUMERIC)
    perc_cr_cb1_prenotate = db.Column(NUMERIC)

    sales_person = relationship("SalesPerson", back_populates="sales_performance")


class HRRecruitingMetrics(db.Model):
    __tablename__ = "hr_recruiting_metrics"

    hr_metric_id = db.Column(db.Integer, primary_key=True)

    cphrc = db.Column(NUMERIC)
    cpp = db.Column(NUMERIC)
    cpe = db.Column(NUMERIC)
    ads_name = db.Column(db.String(255))
    costo = db.Column(NUMERIC)
    cv_ricevuti = db.Column(db.Integer)
    hr_call = db.Column(db.Integer)
    prove = db.Column(db.Integer)
    assunti = db.Column(db.Integer)




# ─────────────────────────── ENUM Recruiting ────────────────────────────
# ──────────────────────── 2. MODELLO Task ─────────────────────── #
# ───────────────────────────  Task  ──────────────────────────────── #
class Task(TimestampMixin, db.Model):
    """
    Task Kanban di reparto, associabile (opzionalmente) a un cliente
    e assegnabile a un membro del dipartimento.
    """
    __tablename__ = "tasks"

    id           = db.Column(db.Integer, primary_key=True)
    title        = db.Column(db.String(255), nullable=False)
    description  = db.Column(db.Text)
    status       = db.Column(_def(TaskStatusEnum),
                             default=TaskStatusEnum.todo,
                             nullable=False)
    priority     = db.Column(_def(TaskPriorityEnum),
                             default=TaskPriorityEnum.medium,
                             nullable=False)
    category     = db.Column(_def(TaskCategoryEnum),
                             default=TaskCategoryEnum.generico,
                             nullable=False)
    payload      = db.Column(db.JSON, default=dict)  # Dati contestuali (es. cliente_id, check_id)
    
    due_date     = db.Column(db.Date)

    # FK principali
    # department_id reso Nullable per task di sistema (es. solleciti automatici)
    department_id = db.Column(db.Integer,
                              db.ForeignKey("departments.id"),
                              nullable=True,
                              index=True)
    assignee_id   = db.Column(db.Integer,
                              db.ForeignKey("users.id"),
                              index=True)
    client_id     = db.Column(db.BigInteger,
                              db.ForeignKey("clienti.cliente_id"),
                              index=True)

    # ─────────────── relazioni ─────────────────────────── #
    department = relationship("Department", back_populates="tasks")
    assignee   = relationship("User",        back_populates="tasks_assigned")
    client     = relationship("Cliente",     back_populates="tasks")

    # ----------------------------------------------------- #
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Task {self.id} – {self.title!r}>"



# ──────────────────────── MODELLI OKR ─────────────────────── #
class Objective(TimestampMixin, db.Model):
    """
    Obiettivi OKR per utente.
    Ogni utente può avere 1-3 obiettivi attivi per periodo.
    """
    __tablename__ = "objectives"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Dati obiettivo - SEMPLIFICATO come DepartmentObjective
    title = db.Column(db.Text, nullable=False)
    status = db.Column(
        _def(OKRStatusEnum), 
        default=OKRStatusEnum.active,
        nullable=False,
        index=True
    )
    
    # Tipo OKR (concreto o aspirazionale)
    okr_type = db.Column(db.String(20), default='concreto', nullable=False)
    
    # Trimestri selezionati (es: "q1,q2,q3") - allineato con dipartimento
    period = db.Column(
        db.String(50), 
        default="yearly",
        nullable=False
    )
    
    # Ordinamento (per drag & drop)
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # ─────────────── Relazioni ─────────────────────────── #
    user = relationship("User", back_populates="objectives")
    key_results = relationship(
        "KeyResult", 
        back_populates="objective", 
        cascade="all, delete-orphan",
        order_by="KeyResult.order_index"
    )
    updates = relationship(
        "OKRUpdate", 
        back_populates="objective",
        cascade="all, delete-orphan",
        order_by="OKRUpdate.created_at.desc()"
    )
    
    # ─────────────── Proprietà helper ─────────────────────────── #
    @property
    def is_active(self) -> bool:
        """True se l'obiettivo è attivo."""
        return self.status == OKRStatusEnum.active
    
    def __repr__(self) -> str:
        return f"<Objective {self.id} - {self.title!r}>"


class KeyResult(TimestampMixin, db.Model):
    """
    Key Results misurabili per ogni obiettivo.
    Ogni obiettivo può avere 1-5 key results.
    """
    __tablename__ = "key_results"
    
    id = db.Column(db.Integer, primary_key=True)
    objective_id = db.Column(
        db.Integer, 
        db.ForeignKey("objectives.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Dati key result - SEMPLIFICATO come DepartmentKeyResult
    title = db.Column(db.Text, nullable=False)
    
    # Ordinamento
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # ─────────────── Relazioni ─────────────────────────── #
    objective = relationship("Objective", back_populates="key_results")
    
    def __repr__(self) -> str:
        return f"<KeyResult {self.id} - {self.title!r}>"


class OKRUpdate(TimestampMixin, db.Model):
    """
    Storico aggiornamenti settimanali degli OKR.
    Traccia progressi, note, blocchi e achievements.
    """
    __tablename__ = "okr_updates"
    
    id = db.Column(db.Integer, primary_key=True)
    objective_id = db.Column(
        db.Integer, 
        db.ForeignKey("objectives.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Periodo di riferimento
    week_number = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    update_date = db.Column(db.Date, default=lambda: datetime.utcnow().date(), nullable=False)
    
    # Contenuto update
    notes = db.Column(db.Text)  # Note generali
    blockers = db.Column(db.Text)  # Ostacoli/problemi
    achievements = db.Column(db.Text)  # Risultati ottenuti
    next_steps = db.Column(db.Text)  # Prossimi passi
    
    # Personal sentiment (allineato con dipartimento)
    personal_morale = db.Column(db.Integer)  # 1-5, morale personale
    confidence_level = db.Column(db.Integer)  # 1-5, quanto sei fiducioso
    
    # Snapshot dei progressi al momento dell'update
    objective_progress = db.Column(db.Integer, nullable=False)
    key_results_snapshot = db.Column(JSONB, default=dict)  # {kr_id: {title}}
    
    # Metriche personali (opzionale) - allineato con team_metrics
    personal_metrics = db.Column(JSONB, default=dict)  # {metric_name: value}
    
    # ─────────────── Relazioni ─────────────────────────── #
    objective = relationship("Objective", back_populates="updates")
    user = relationship("User")
    
    # ─────────────── Proprietà helper ─────────────────────────── #
    @property
    def week_label(self) -> str:
        """Etichetta settimana (es: 'W45 2024')."""
        return f"W{self.week_number} {self.year}"
    
    @property
    def has_blockers(self) -> bool:
        """True se ci sono blockers."""
        return bool(self.blockers and self.blockers.strip())
    
    @property
    def confidence_emoji(self) -> str:
        """Emoji basata sul livello di confidenza."""
        if not self.confidence_level:
            return "😐"
        emojis = {1: "😟", 2: "😕", 3: "😐", 4: "😊", 5: "😎"}
        return emojis.get(self.confidence_level, "😐")
    
    @property
    def morale_emoji(self) -> str:
        """Emoji basata sul morale personale."""
        if not self.personal_morale:
            return "😐"
        emojis = {1: "😞", 2: "😔", 3: "😐", 4: "😊", 5: "🚀"}
        return emojis.get(self.personal_morale, "😐")
    
    def __repr__(self) -> str:
        return f"<OKRUpdate {self.id} - Week {self.week_number}/{self.year}>"
    


# ──────────────────────── MODELLI HR ESTESI ─────────────────────── #
class UserEducation(TimestampMixin, db.Model):
    """
    Titoli di studio e certificazioni formative degli utenti.
    """
    __tablename__ = "user_education"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Tipo di titolo
    titolo_tipo = db.Column(db.String(50), nullable=False)  # diploma, laurea_triennale, laurea_magistrale, master, dottorato, certificazione
    titolo_nome = db.Column(db.String(255), nullable=False)  # Nome del titolo conseguito
    istituto = db.Column(db.String(255), nullable=False)  # Università/Scuola
    
    # Dettagli
    voto = db.Column(db.String(20))  # es: "110/110", "110L", "18/30"
    data_conseguimento = db.Column(db.Date, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relazioni
    user = relationship("User", back_populates="education")
    
    # Indice su user_id per queries efficienti
    __table_args__ = (
        Index("idx_user_education_user_id", "user_id"),
    )
    
    def __repr__(self) -> str:
        return f"<UserEducation {self.id} - {self.titolo_nome} ({self.titolo_tipo})>"


class UserSalaryHistory(TimestampMixin, db.Model):
    """
    Storico retributivo e variazioni salariali degli utenti.
    """
    __tablename__ = "user_salary_history"
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Tipo e importi
    tipo_variazione = db.Column(db.String(50), nullable=False)  # aumento, bonus, premio, rimborso, promozione
    importo_precedente = db.Column(db.Numeric(12, 2))  # Per aumenti
    importo_nuovo = db.Column(db.Numeric(12, 2), nullable=False)
    valuta = db.Column(db.String(3), default="EUR", nullable=False)
    
    # Date
    data_effettiva = db.Column(db.Date, nullable=False)
    data_delibera = db.Column(db.Date)
    
    # Dettagli
    note = db.Column(db.Text)
    approvato_da_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Relazioni
    user = relationship("User", back_populates="salary_history", foreign_keys=[user_id])
    approvato_da = relationship("User", foreign_keys=[approvato_da_id])
    
    # Indice su user_id per queries efficienti
    __table_args__ = (
        Index("idx_user_salary_history_user_id", "user_id"),
    )
    
    @property
    def variazione_percentuale(self) -> Optional[float]:
        """Calcola la variazione percentuale se disponibile."""
        if self.importo_precedente and self.importo_precedente > 0:
            return round(((self.importo_nuovo - self.importo_precedente) / self.importo_precedente) * 100, 2)
        return None
    
    def __repr__(self) -> str:
        return f"<UserSalaryHistory {self.id} - {self.tipo_variazione} {self.importo_nuovo} {self.valuta}>"


# ──────────────────────── MODELLI OKR DIPARTIMENTO ─────────────────────── #
class DepartmentObjective(TimestampMixin, db.Model):
    """
    Obiettivi OKR per dipartimento.
    Ogni dipartimento può avere multiple obiettivi attivi.
    """
    __tablename__ = "department_objectives"
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer, 
        db.ForeignKey("departments.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Chi ha creato l'obiettivo (tipicamente head o admin)
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    
    # Dati obiettivo - SEMPLIFICATO
    title = db.Column(db.Text, nullable=False)
    status = db.Column(
        _def(OKRStatusEnum), 
        default=OKRStatusEnum.active,
        nullable=False,
        index=True
    )
    
    # Tipo OKR (concreto o aspirazionale)
    okr_type = db.Column(db.String(20), default='concreto', nullable=False)
    
    # Trimestri selezionati (es: "q1,q2,q3")
    period = db.Column(
        db.String(50), 
        default="yearly",
        nullable=False
    )
    
    # Ordinamento (per drag & drop)
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # ─────────────── Relazioni ─────────────────────────── #
    department = relationship("Department", back_populates="objectives")
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    key_results = relationship(
        "DepartmentKeyResult", 
        back_populates="objective", 
        cascade="all, delete-orphan",
        order_by="DepartmentKeyResult.order_index"
    )
    
    updates = relationship(
        "DepartmentOKRUpdate", 
        back_populates="objective",
        cascade="all, delete-orphan",
        order_by="DepartmentOKRUpdate.created_at.desc()"
    )
    
    # Link con OKR personali dei membri (opzionale)
    linked_personal_objectives = relationship(
        "Objective",
        secondary="dept_personal_okr_link",
        backref="linked_department_objectives"
    )
    
    # ─────────────── Proprietà helper ─────────────────────────── #
    @property
    def is_active(self) -> bool:
        """True se l'obiettivo è attivo."""
        return self.status == OKRStatusEnum.active
    
    def __repr__(self) -> str:
        return f"<DepartmentObjective {self.id} - {self.title!r}>"


class DepartmentKeyResult(TimestampMixin, db.Model):
    """
    Key Results misurabili per obiettivi di dipartimento.
    Possono essere assegnati a membri specifici del team.
    """
    __tablename__ = "department_key_results"
    
    id = db.Column(db.Integer, primary_key=True)
    objective_id = db.Column(
        db.Integer, 
        db.ForeignKey("department_objectives.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Dati key result - SEMPLIFICATO  
    title = db.Column(db.Text, nullable=False)
    
    # Ordinamento
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # ─────────────── Relazioni ─────────────────────────── #
    objective = relationship("DepartmentObjective", back_populates="key_results")
    
    def __repr__(self) -> str:
        return f"<DepartmentKeyResult {self.id} - {self.title!r}>"


class DepartmentOKRUpdate(TimestampMixin, db.Model):
    """
    Storico aggiornamenti settimanali degli OKR di dipartimento.
    Traccia progressi del team, note, blocchi e achievements.
    """
    __tablename__ = "department_okr_updates"
    
    id = db.Column(db.Integer, primary_key=True)
    objective_id = db.Column(
        db.Integer, 
        db.ForeignKey("department_objectives.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Chi ha fatto l'update (tipicamente head o membro del team)
    user_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Periodo di riferimento
    week_number = db.Column(db.Integer, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    update_date = db.Column(db.Date, default=lambda: datetime.utcnow().date(), nullable=False)
    
    # Contenuto update
    notes = db.Column(db.Text)  # Note generali
    blockers = db.Column(db.Text)  # Ostacoli/problemi del team
    achievements = db.Column(db.Text)  # Risultati ottenuti dal team
    next_steps = db.Column(db.Text)  # Prossimi passi
    
    # Team sentiment (opzionale)
    team_morale = db.Column(db.Integer)  # 1-5, morale del team
    confidence_level = db.Column(db.Integer)  # 1-5, quanto il team è fiducioso
    
    # Snapshot dei progressi al momento dell'update
    objective_progress = db.Column(db.Integer, nullable=False)
    key_results_snapshot = db.Column(JSONB, default=dict)  # {kr_id: {title, progress, current_value, assignee}}
    
    # Metriche aggiuntive del team (opzionale)
    team_metrics = db.Column(JSONB, default=dict)  # {metric_name: value}
    
    # ─────────────── Relazioni ─────────────────────────── #
    objective = relationship("DepartmentObjective", back_populates="updates")
    user = relationship("User")
    
    # ─────────────── Proprietà helper ─────────────────────────── #
    @property
    def week_label(self) -> str:
        """Etichetta settimana (es: 'W45 2024')."""
        return f"W{self.week_number} {self.year}"
    
    @property
    def has_blockers(self) -> bool:
        """True se ci sono blockers."""
        return bool(self.blockers and self.blockers.strip())
    
    @property
    def confidence_emoji(self) -> str:
        """Emoji basata sul livello di confidenza."""
        if not self.confidence_level:
            return "😐"
        emojis = {1: "😟", 2: "😕", 3: "😐", 4: "😊", 5: "😎"}
        return emojis.get(self.confidence_level, "😐")
    
    @property
    def morale_emoji(self) -> str:
        """Emoji basata sul morale del team."""
        if not self.team_morale:
            return "😐"
        emojis = {1: "😞", 2: "😔", 3: "😐", 4: "😊", 5: "🚀"}
        return emojis.get(self.team_morale, "😐")
    
    def __repr__(self) -> str:
        return f"<DepartmentOKRUpdate {self.id} - Week {self.week_number}/{self.year}>"


# ──────────────────────── TABELLA DI LINK (OPZIONALE) ─────────────────────── #
# Tabella ponte per collegare OKR dipartimento con OKR personali
dept_personal_okr_link = db.Table(
    "dept_personal_okr_link",
    db.Column("dept_objective_id", db.Integer, db.ForeignKey("department_objectives.id"), primary_key=True),
    db.Column("personal_objective_id", db.Integer, db.ForeignKey("objectives.id"), primary_key=True),
    db.Column("linked_at", db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column("linked_by", db.Integer, db.ForeignKey("users.id"))
)



# ──────────────────────── NUTRITION MODELS ─────────────────────── #

# ──────────────────────── 1. FOOD & CATEGORIES ─────────────────────── #
class FoodCategory(TimestampMixin, db.Model):
    """Categorie alimenti (es: Cereali, Proteine, Verdure, etc.)"""
    __tablename__ = "food_categories"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("food_categories.id"))
    icon = db.Column(db.String(50))  # Per UI (es: icon name)
    color = db.Column(db.String(7))  # Hex color per UI
    
    # Relazioni
    parent = relationship("FoodCategory", remote_side=[id])
    foods = relationship("Food", back_populates="category", lazy="selectin")
    
    def __repr__(self):
        return f"<FoodCategory {self.name!r}>"


class Food(TimestampMixin, db.Model):
    """Database alimenti con valori nutrizionali per 100 g."""
    __tablename__ = "foods"
    __versioned__ = {}          # versioning con SQLAlchemy-Continuum

    # ─────────────────── chiave primaria & riferimenti ─────────────────── #
    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(255), nullable=False, index=True)
    brand       = db.Column(db.String(100))
    barcode     = db.Column(db.String(50), index=True)
    category_id = db.Column(db.Integer, db.ForeignKey("food_categories.id"))

    # ───────────── valori nutrizionali (per 100 g di parte edibile) ─────── #
    calories       = db.Column(db.Float, nullable=False)   # kcal
    proteins       = db.Column(db.Float, nullable=False)   # g
    carbohydrates  = db.Column(db.Float, nullable=False)   # g
    fats           = db.Column(db.Float, nullable=False)   # g
    fibers         = db.Column(db.Float, default=0)        # g
    sugars         = db.Column(db.Float, default=0)        # g
    saturated_fats = db.Column(db.Float, default=0)        # g
    sodium         = db.Column(db.Float, default=0)        # mg
    micronutrients = db.Column(JSONB, default=dict)        # es. {"vitamina_c": 12}

    # ───────────────────────────── metadati ────────────────────────────── #
    source      = db.Column(db.String(50))     # "usda", "custom", "user", …
    external_id = db.Column(db.String(100))    # id nel DB esterno
    verified    = db.Column(db.Boolean, default=False)

    # ────────────────────────── Metodi di utilità ────────────────────────── #
    search_vector = db.Column(
        TSVectorType(
            "name",
            "brand",
            regconfig="italian",
            create_index=True         # crea *una sola* volta il GIN index
        )
    )

    # ───────────────────────────── relazioni ───────────────────────────── #
    category = relationship("FoodCategory", back_populates="foods")

    # ───────────────────────────── indici extra ────────────────────────── #
    __table_args__ = (
        Index("ix_foods_name_brand", "name", "brand"),
    )

    # --------------------------------------------------------------------- #
    def __repr__(self) -> str:  # pragma: no cover
        return f"<Food {self.name!r}>"


# ──────────────────────── 2. RECIPES ─────────────────────── #
class Recipe(TimestampMixin, db.Model):
    """Ricette create dalle nutrizioniste"""
    __tablename__ = "recipes"
    __versioned__ = {}
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    preparation_time = db.Column(db.Integer)  # minuti
    cooking_time = db.Column(db.Integer)  # minuti
    servings = db.Column(db.Integer, default=1)
    difficulty = db.Column(db.String(20))  # facile, medio, difficile
    
    # Istruzioni
    instructions = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_public = db.Column(db.Boolean, default=False)
    tags = db.Column(ARRAY(db.String(50)))  # ["veloce", "vegano", "senza glutine"]
    
    # Relazioni
    created_by = relationship("User", back_populates="created_recipes")
    ingredients = relationship(
        "RecipeIngredient",
        back_populates="recipe",
        cascade="all, delete-orphan",
        order_by="RecipeIngredient.order_index"
    )
    
    # Proprietà calcolate
    @property
    def total_calories(self):
        """Calorie totali della ricetta"""
        return sum(ing.calories for ing in self.ingredients)
    
    @property
    def calories_per_serving(self):
        """Calorie per porzione"""
        return self.total_calories / self.servings if self.servings > 0 else 0
    
    @property
    def macros(self):
        """Macronutrienti totali"""
        return {
            "proteins": sum(ing.proteins for ing in self.ingredients),
            "carbohydrates": sum(ing.carbohydrates for ing in self.ingredients),
            "fats": sum(ing.fats for ing in self.ingredients),
            "fibers": sum(ing.fibers for ing in self.ingredients)
        }
    
    def __repr__(self):
        return f"<Recipe {self.name!r}>"


class RecipeIngredient(db.Model):
    """Ingredienti di una ricetta con quantità"""
    __tablename__ = "recipe_ingredients"
    
    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"), nullable=False)
    food_id = db.Column(db.Integer, db.ForeignKey("foods.id"), nullable=False)
    
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(_def(FoodUnitEnum), nullable=False)
    notes = db.Column(db.String(255))  # "tritato finemente", "a cubetti"
    order_index = db.Column(db.Integer, default=0)
    
    # Relazioni
    recipe = relationship("Recipe", back_populates="ingredients")
    food = relationship("Food")
    
    # Proprietà calcolate
    @property
    def grams(self):
        """Converte la quantità in grammi"""
        conversions = {
            FoodUnitEnum.grammi: 1,
            FoodUnitEnum.millilitri: 1,  # Assumendo densità 1
            FoodUnitEnum.cucchiaio: 15,
            FoodUnitEnum.cucchiaino: 5,
            FoodUnitEnum.tazza: 240,
            FoodUnitEnum.pezzo: 100,  # Default, va personalizzato
            FoodUnitEnum.fetta: 30,   # Default, va personalizzato
            FoodUnitEnum.porzione: 100  # Default, va personalizzato
        }
        return self.quantity * conversions.get(self.unit, 100)
    
    @property
    def calories(self):
        """Calorie per questa quantità di ingrediente"""
        return (self.food.calories * self.grams) / 100
    
    @property
    def proteins(self):
        return (self.food.proteins * self.grams) / 100
    
    @property
    def carbohydrates(self):
        return (self.food.carbohydrates * self.grams) / 100
    
    @property
    def fats(self):
        return (self.food.fats * self.grams) / 100
    
    @property
    def fibers(self):
        return (self.food.fibers * self.grams) / 100
    
    def __repr__(self):
        return f"<RecipeIngredient {self.quantity} {self.unit.value} {self.food.name}>"


# ──────────────────────── 3. MEAL PLANS ─────────────────────── #
class MealPlan(TimestampMixin, db.Model):
    """Piano alimentare per un cliente"""
    __tablename__ = "meal_plans"
    __versioned__ = {}
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    name = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Target nutrizionali
    target_calories = db.Column(db.Float)
    target_proteins = db.Column(db.Float)  # g
    target_carbohydrates = db.Column(db.Float)  # g
    target_fats = db.Column(db.Float)  # g
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

    # Campi per gestione dieta/storico
    piano_alimentare = db.Column(db.Text)     # Dettagli piano alimentare (deprecato, mantenuto per compatibilità)
    piano_alimentare_file_path = db.Column(db.String(500), nullable=True)  # Path al file PDF del piano alimentare
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Ultimo utente che ha modificato
    change_reason = db.Column(db.Text)        # Motivazione cambio (per "Cambia Dieta")

    # Relazioni
    cliente = relationship("Cliente", back_populates="meal_plans")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_meal_plans")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    days = relationship(
        "MealPlanDay",
        back_populates="meal_plan",
        cascade="all, delete-orphan",
        order_by="MealPlanDay.day_date"
    )
    extra_files = relationship(
        "PlanExtraFile",
        primaryjoin="and_(PlanExtraFile.plan_type == 'meal_plan', PlanExtraFile.plan_id == MealPlan.id)",
        foreign_keys="[PlanExtraFile.plan_id]",
        viewonly=True,
        order_by="PlanExtraFile.created_at"
    )

    # Proprietà
    @property
    def duration_days(self):
        """Durata del piano in giorni"""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    # Metodi di validazione
    def validate_no_overlap(self, exclude_id=None):
        """Valida che non ci siano sovrapposizioni con altri piani dello stesso cliente."""
        from sqlalchemy import and_, or_

        query = MealPlan.query.filter_by(cliente_id=self.cliente_id)

        if exclude_id:
            query = query.filter(MealPlan.id != exclude_id)

        # Verifica sovrapposizioni: un periodo si sovrappone se:
        # - start_date è dentro un altro periodo: start_date >= other.start_date AND start_date <= other.end_date
        # - end_date è dentro un altro periodo: end_date >= other.start_date AND end_date <= other.end_date
        # - periodo contiene completamente un altro: start_date <= other.start_date AND end_date >= other.end_date

        overlapping = query.filter(
            or_(
                and_(
                    self.start_date >= MealPlan.start_date,
                    self.start_date <= MealPlan.end_date
                ),
                and_(
                    self.end_date >= MealPlan.start_date,
                    self.end_date <= MealPlan.end_date
                ),
                and_(
                    self.start_date <= MealPlan.start_date,
                    self.end_date >= MealPlan.end_date
                )
            )
        ).first()

        if overlapping:
            raise ValueError(
                f"Il periodo {self.start_date} - {self.end_date} si sovrappone con un piano esistente "
                f"({overlapping.name}: {overlapping.start_date} - {overlapping.end_date})"
            )

        return True

    @classmethod
    def calculate_next_start_date(cls, cliente_id):
        """Calcola la data di inizio default per il prossimo piano (end_date ultimo + 1 giorno)."""
        from datetime import date, timedelta

        last_plan = (
            cls.query.filter_by(cliente_id=cliente_id, is_active=True)
            .order_by(cls.start_date.desc())
            .first()
        )

        if not last_plan:
            return date.today()

        if not last_plan.end_date:
            return None  # Richiede impostazione manuale

        return last_plan.end_date + timedelta(days=1)

    def __repr__(self):
        return f"<MealPlan {self.name!r} for Cliente {self.cliente_id}>"


class TrainingPlan(TimestampMixin, db.Model):
    """Piano allenamento con storico e versioning (analogo a MealPlan)"""
    __tablename__ = "training_plans"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clienti.cliente_id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Identificazione
    name = db.Column(db.String(255), nullable=True)

    # Periodo
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)

    # Campi per gestione allenamento/storico
    piano_allenamento = db.Column(db.Text)     # Dettagli piano allenamento (deprecato, mantenuto per compatibilità)
    piano_allenamento_file_path = db.Column(db.String(500), nullable=True)  # Path al file PDF del piano allenamento
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    change_reason = db.Column(db.Text)         # Motivazione cambio

    # Relazioni
    cliente = relationship("Cliente", back_populates="training_plans")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_training_plans")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
    extra_files = relationship(
        "PlanExtraFile",
        primaryjoin="and_(PlanExtraFile.plan_type == 'training_plan', PlanExtraFile.plan_id == TrainingPlan.id)",
        foreign_keys="[PlanExtraFile.plan_id]",
        viewonly=True,
        order_by="PlanExtraFile.created_at"
    )

    @property
    def duration_days(self):
        """Calcola durata in giorni."""
        if not self.end_date:
            return None
        return (self.end_date - self.start_date).days + 1

    # Metodi di validazione
    def validate_no_overlap(self, exclude_id=None):
        """Valida che non ci siano sovrapposizioni con altri piani dello stesso cliente."""
        from sqlalchemy import and_, or_

        query = TrainingPlan.query.filter_by(cliente_id=self.cliente_id)

        if exclude_id:
            query = query.filter(TrainingPlan.id != exclude_id)

        overlapping = query.filter(
            or_(
                and_(
                    self.start_date >= TrainingPlan.start_date,
                    self.start_date <= TrainingPlan.end_date
                ),
                and_(
                    self.end_date >= TrainingPlan.start_date,
                    self.end_date <= TrainingPlan.end_date
                ),
                and_(
                    self.start_date <= TrainingPlan.start_date,
                    self.end_date >= TrainingPlan.end_date
                )
            )
        ).first()

        if overlapping:
            raise ValueError(
                f"Il periodo {self.start_date} - {self.end_date} si sovrappone con un piano esistente "
                f"({overlapping.name}: {overlapping.start_date} - {overlapping.end_date})"
            )

        return True

    @classmethod
    def calculate_next_start_date(cls, cliente_id):
        """Calcola la data di inizio default per il prossimo piano (end_date ultimo + 1 giorno)."""
        from datetime import date, timedelta

        last_plan = (
            cls.query.filter_by(cliente_id=cliente_id, is_active=True)
            .order_by(cls.start_date.desc())
            .first()
        )

        if not last_plan:
            return date.today()

        if not last_plan.end_date:
            return None  # Richiede impostazione manuale

        return last_plan.end_date + timedelta(days=1)

    def __repr__(self):
        return f"<TrainingPlan {self.name!r} for Cliente {self.cliente_id}>"


class PlanExtraFile(TimestampMixin, db.Model):
    """File extra allegati ai piani alimentari o di allenamento"""
    __tablename__ = "plan_extra_files"

    id = db.Column(db.Integer, primary_key=True)
    plan_type = db.Column(_def(PlanTypeEnum), nullable=False)  # 'meal_plan' o 'training_plan'
    plan_id = db.Column(db.Integer, nullable=False)  # ID del piano (MealPlan o TrainingPlan)
    file_path = db.Column(db.String(500), nullable=False)  # Path relativo al file
    file_name = db.Column(db.String(255), nullable=False)  # Nome originale del file
    file_size = db.Column(db.Integer, nullable=False)  # Dimensione in bytes
    uploaded_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relazioni
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])

    # Indici per performance
    __table_args__ = (
        Index('ix_plan_extra_files_plan_type_id', 'plan_type', 'plan_id'),
    )

    def __repr__(self):
        return f"<PlanExtraFile {self.file_name!r} for {self.plan_type} {self.plan_id}>"


class TrainingLocation(TimestampMixin, db.Model):
    """Storico luogo di allenamento del cliente"""
    __tablename__ = "training_locations"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey("clienti.cliente_id"), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Periodo
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=True)

    # Luogo
    location = db.Column(db.String(50), nullable=False)  # casa, palestra, ibrido

    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    notes = db.Column(db.Text)
    changed_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    change_reason = db.Column(db.Text)

    # Relazioni
    cliente = relationship("Cliente", back_populates="training_locations")
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_training_locations")
    changed_by = relationship("User", foreign_keys=[changed_by_id])

    @property
    def duration_days(self):
        """Calcola durata in giorni."""
        if not self.end_date:
            return None
        return (self.end_date - self.start_date).days + 1

    def validate_no_overlap(self, exclude_id=None):
        """Valida che non ci siano sovrapposizioni (gestisce end_date=None per periodi aperti)."""
        from sqlalchemy import and_, or_

        query = TrainingLocation.query.filter_by(cliente_id=self.cliente_id)
        if exclude_id:
            query = query.filter(TrainingLocation.id != exclude_id)

        # Formula standard sovrapposizione: A_start <= B_end AND A_end >= B_start
        # Con end_date=None che rappresenta "infinito" (periodo aperto)

        # Per ogni location esistente nel DB, verifica se si sovrappone con il nuovo periodo
        for existing in query.all():
            # Determina gli end_date effettivi (None = infinito futuro)
            new_end = self.end_date  # None o una data
            existing_end = existing.end_date  # None o una data

            # Sovrapposizione: new_start <= existing_end AND new_end >= existing_start
            # Gestendo None come infinito:

            # Condizione 1: new_start <= existing_end (se existing_end è None, sempre vero)
            if existing_end is None:
                cond1_ok = True
            else:
                cond1_ok = self.start_date <= existing_end

            # Condizione 2: new_end >= existing_start (se new_end è None, sempre vero)
            if new_end is None:
                cond2_ok = True
            else:
                cond2_ok = new_end >= existing.start_date

            # Se entrambe le condizioni sono vere, c'è sovrapposizione
            if cond1_ok and cond2_ok:
                overlap_end = existing_end.strftime('%Y-%m-%d') if existing_end else 'in corso'
                raise ValueError(
                    f"Il periodo {self.start_date} - {new_end or 'in corso'} si sovrappone con un periodo esistente "
                    f"({existing.start_date} - {overlap_end})"
                )

        return True

    @classmethod
    def calculate_next_start_date(cls, cliente_id):
        """Calcola la data di inizio default."""
        from datetime import date, timedelta
        last_loc = cls.query.filter_by(cliente_id=cliente_id, is_active=True).order_by(cls.start_date.desc()).first()
        if not last_loc:
            return date.today()
        if not last_loc.end_date:
            return None
        return last_loc.end_date + timedelta(days=1)

    def __repr__(self):
        return f"<TrainingLocation {self.location!r} for Cliente {self.cliente_id}>"


class MealPlanDay(TimestampMixin, db.Model):
    """Giorno specifico del piano alimentare"""
    __tablename__ = "meal_plan_days"
    
    id = db.Column(db.Integer, primary_key=True)
    meal_plan_id = db.Column(db.Integer, db.ForeignKey("meal_plans.id"), nullable=False)
    day_date = db.Column(db.Date, nullable=False)
    day_number = db.Column(db.Integer)  # 1, 2, 3... per piani ciclici
    
    # Note giornaliere
    notes = db.Column(db.Text)
    
    # Relazioni
    meal_plan = relationship("MealPlan", back_populates="days")
    meals = relationship(
        "Meal",
        back_populates="meal_plan_day",
        cascade="all, delete-orphan",
        order_by="Meal.meal_type"
    )
    
    # Proprietà
    @property
    def total_calories(self):
        """Calorie totali del giorno"""
        return sum(meal.total_calories for meal in self.meals)
    
    @property
    def total_macros(self):
        """Macronutrienti totali del giorno"""
        return {
            "proteins": sum(meal.total_proteins for meal in self.meals),
            "carbohydrates": sum(meal.total_carbohydrates for meal in self.meals),
            "fats": sum(meal.total_fats for meal in self.meals)
        }
    
    def __repr__(self):
        return f"<MealPlanDay {self.day_date}>"


class Meal(TimestampMixin, db.Model):
    """Singolo pasto del piano"""
    __tablename__ = "meals"
    
    id = db.Column(db.Integer, primary_key=True)
    meal_plan_day_id = db.Column(db.Integer, db.ForeignKey("meal_plan_days.id"), nullable=False)
    meal_type = db.Column(_def(MealTypeEnum), nullable=False)
    
    name = db.Column(db.String(255))  # Nome opzionale del pasto
    notes = db.Column(db.Text)
    
    # Relazioni
    meal_plan_day = relationship("MealPlanDay", back_populates="meals")
    foods = relationship(
        "MealFood",
        back_populates="meal",
        cascade="all, delete-orphan"
    )
    
    # Proprietà
    @property
    def total_calories(self):
        return sum(mf.calories for mf in self.foods)
    
    @property
    def total_proteins(self):
        return sum(mf.proteins for mf in self.foods)
    
    @property
    def total_carbohydrates(self):
        return sum(mf.carbohydrates for mf in self.foods)
    
    @property
    def total_fats(self):
        return sum(mf.fats for mf in self.foods)
    
    def __repr__(self):
        return f"<Meal {self.meal_type.value}>"


class MealFood(db.Model):
    """Alimento in un pasto con quantità specifica"""
    __tablename__ = "meal_foods"
    
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.Integer, db.ForeignKey("meals.id"), nullable=False)
    
    # Può essere un alimento O una ricetta
    food_id = db.Column(db.Integer, db.ForeignKey("foods.id"))
    recipe_id = db.Column(db.Integer, db.ForeignKey("recipes.id"))
    
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(_def(FoodUnitEnum), nullable=False)
    notes = db.Column(db.Text)
    
    # Relazioni
    meal = relationship("Meal", back_populates="foods")
    food = relationship("Food")
    recipe = relationship("Recipe")
    
    # Constraint
    __table_args__ = (
        db.CheckConstraint(
            "(food_id IS NOT NULL AND recipe_id IS NULL) OR (food_id IS NULL AND recipe_id IS NOT NULL)",
            name="meal_food_xor_recipe"
        ),
    )
    
    # Proprietà
    @property
    def grams(self):
        """Converte in grammi"""
        conversions = {
            FoodUnitEnum.grammi: 1,
            FoodUnitEnum.millilitri: 1,
            FoodUnitEnum.cucchiaio: 15,
            FoodUnitEnum.cucchiaino: 5,
            FoodUnitEnum.tazza: 240,
            FoodUnitEnum.pezzo: 100,
            FoodUnitEnum.fetta: 30,
            FoodUnitEnum.porzione: 100
        }
        return self.quantity * conversions.get(self.unit, 100)
    
    @property
    def calories(self):
        if self.food:
            return (self.food.calories * self.grams) / 100
        elif self.recipe:
            # Per ricette, quantity rappresenta il numero di porzioni
            return self.recipe.calories_per_serving * self.quantity
        return 0
    
    @property
    def proteins(self):
        if self.food:
            return (self.food.proteins * self.grams) / 100
        elif self.recipe:
            macros = self.recipe.macros
            return (macros["proteins"] / self.recipe.servings) * self.quantity
        return 0
    
    @property
    def carbohydrates(self):
        if self.food:
            return (self.food.carbohydrates * self.grams) / 100
        elif self.recipe:
            macros = self.recipe.macros
            return (macros["carbohydrates"] / self.recipe.servings) * self.quantity
        return 0
    
    @property
    def fats(self):
        if self.food:
            return (self.food.fats * self.grams) / 100
        elif self.recipe:
            macros = self.recipe.macros
            return (macros["fats"] / self.recipe.servings) * self.quantity
        return 0
    
    def __repr__(self):
        item = self.food.name if self.food else self.recipe.name
        return f"<MealFood {self.quantity} {self.unit.value} {item}>"


# ──────────────────────── 4. TEMPLATES ─────────────────────── #
class MealPlanTemplate(TimestampMixin, db.Model):
    """Template di piani riutilizzabili"""
    __tablename__ = "meal_plan_templates"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    duration_days = db.Column(db.Integer, nullable=False)
    
    # Categorie target
    tags = db.Column(ARRAY(db.String(50)))  # ["dimagrimento", "vegano", "sportivo"]
    
    # Target nutrizionali di riferimento
    target_calories = db.Column(db.Float)
    target_proteins = db.Column(db.Float)
    target_carbohydrates = db.Column(db.Float)
    target_fats = db.Column(db.Float)
    
    # Metadata
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_public = db.Column(db.Boolean, default=False)
    
    # JSON con la struttura completa del template
    template_data = db.Column(JSONB, nullable=False)
    
    # Relazioni
    created_by = relationship("User")
    
    def __repr__(self):
        return f"<MealPlanTemplate {self.name!r}>"


# ═══════════════════════════════════════════════════════════════════════════════
#                            RESPOND.IO INTEGRATION
# ═══════════════════════════════════════════════════════════════════════════════

class RespondIOLifecycleChange(TimestampMixin, db.Model):
    """
    Tracking di ogni cambio lifecycle per funnel analysis.
    NON salviamo i dati dei contatti, solo le transizioni per le metriche.
    """
    __tablename__ = 'respond_io_lifecycle_changes'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ID del contatto da Respond.io (solo per reference, non salviamo dati personali)
    contact_id = db.Column(db.String(100), nullable=False, index=True)
    
    # Transizione
    from_lifecycle = db.Column(db.String(50))  # Stato precedente
    to_lifecycle = db.Column(db.String(50), nullable=False)  # Nuovo stato
    
    # Canale WhatsApp al momento del cambio
    channel_source = db.Column(db.String(50), index=True)  # Numero WhatsApp
    channel_name = db.Column(db.String(100))  # Nome operatore
    
    # Timestamp del cambio
    changed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # Indici compositi per query performance
    __table_args__ = (
        Index('idx_respondio_channel_time', 'channel_source', 'changed_at'),
        Index('idx_respondio_transition', 'from_lifecycle', 'to_lifecycle', 'changed_at'),
    )
    
    def __repr__(self):
        return f'<RespondIOChange {self.contact_id}: {self.from_lifecycle} → {self.to_lifecycle}>'


class RespondIODailyMetrics(db.Model):
    """
    Metriche aggregate giornaliere per dashboard.
    Pre-calcolate per performance ottimali.
    """
    __tablename__ = 'respond_io_daily_metrics'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Data e canale
    date = db.Column(db.Date, nullable=False, index=True)
    channel_source = db.Column(db.String(50), nullable=False)
    channel_name = db.Column(db.String(100))
    
    # Metriche funnel - conteggi assoluti del giorno
    new_contacts = db.Column(db.Integer, default=0)
    new_leads = db.Column(db.Integer, default=0)
    
    # NUOVO: Conteggi totali per ogni stato (quante volte un contatto è stato messo in quello stato)
    total_contrassegnato = db.Column(db.Integer, default=0)
    total_in_target = db.Column(db.Integer, default=0)
    total_link_da_inviare = db.Column(db.Integer, default=0)
    total_link_inviato = db.Column(db.Integer, default=0)
    total_prenotato = db.Column(db.Integer, default=0)
    
    # Conversioni nel giorno (da → a) - MANTENIAMO per analisi del flusso
    lead_to_contrassegnato = db.Column(db.Integer, default=0)
    contrassegnato_to_target = db.Column(db.Integer, default=0)
    target_to_link_da_inviare = db.Column(db.Integer, default=0)  # In Target → Link Da Inviare
    link_da_inviare_to_link_inviato = db.Column(db.Integer, default=0)  # Link Da Inviare → Link Inviato
    target_to_link = db.Column(db.Integer, default=0)  # Compatibilità: In Target → Link Inviato diretto
    link_to_prenotato = db.Column(db.Integer, default=0)
    
    # Altri stati
    to_under = db.Column(db.Integer, default=0)
    to_non_target = db.Column(db.Integer, default=0)
    to_prenotato_non_target = db.Column(db.Integer, default=0)
    
    # Tempo medio tra stages (in minuti) - opzionale
    avg_time_lead_to_contrassegnato = db.Column(db.Float)
    avg_time_contrassegnato_to_target = db.Column(db.Float)
    avg_time_target_to_link = db.Column(db.Float)
    avg_time_link_to_prenotato = db.Column(db.Float)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Constraint per evitare duplicati
    __table_args__ = (
        db.UniqueConstraint('date', 'channel_name', name='uq_respondio_daily_channel_name'),
    )
    
    def __repr__(self):
        return f'<RespondIOMetrics {self.date} - {self.channel_name}>'


# Costanti per Respond.io
RESPOND_IO_LIFECYCLE_STAGES = [
    'Nuova Lead',
    'Contrassegnato',
    'In Target',
    'Link Inviato',
    'Prenotato',
    'Under',
    'Prenotato Non In Target',
    'Non in Target'
]

RESPOND_IO_CHANNELS = {
    '393482924893': 'Sciaudone Matteo',
    '393482933823': 'Celestino Breccione Mattucci',
    '393482942444': 'Lorenzo Lari',
    '393455234135': 'Cristiano Fallai'
}


class RespondIOContactChannel(db.Model):
    """
    Cache del mapping contact-channel dai webhook dei messaggi.
    Auto-pulizia dopo 7 giorni di inattività.
    """
    __tablename__ = 'respond_io_contact_channels'
    
    contact_id = db.Column(db.String(100), primary_key=True)
    channel_name = db.Column(db.String(200), nullable=False)
    channel_source = db.Column(db.String(100))
    channel_id = db.Column(db.String(100))
    last_updated = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    @classmethod
    def update_mapping(cls, contact_id, channel_name, channel_source=None, channel_id=None):
        """Aggiorna o crea il mapping contact-channel"""
        mapping = cls.query.get(str(contact_id))
        if mapping:
            mapping.channel_name = channel_name
            mapping.channel_source = channel_source
            mapping.channel_id = channel_id
            mapping.last_updated = datetime.utcnow()
        else:
            mapping = cls(
                contact_id=str(contact_id),
                channel_name=channel_name,
                channel_source=channel_source,
                channel_id=channel_id
            )
            db.session.add(mapping)
        return mapping
    
    @classmethod
    def get_channel(cls, contact_id):
        """Recupera il canale per un contact_id"""
        mapping = cls.query.get(str(contact_id))
        if mapping:
            return mapping.channel_name, mapping.channel_source or mapping.channel_name
        return None, None
    
    @classmethod
    def cleanup_old_records(cls, days=2):
        """Rimuove record più vecchi di N giorni (default: 48 ore)"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        old_records = cls.query.filter(cls.last_updated < cutoff_date).delete()
        db.session.commit()
        return old_records


# ──────────────────────── 5. CLIENT PROFILES ─────────────────────── #
class NutritionalProfile(TimestampMixin, db.Model):
    """Profilo nutrizionale del cliente"""
    __tablename__ = "nutritional_profiles"
    __versioned__ = {}
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("clienti.cliente_id"),
        unique=True,
        nullable=False
    )
    
    # Obiettivi
    nutritional_goal = db.Column(_def(NutritionalGoalEnum), nullable=False)
    target_weight = db.Column(db.Float)  # kg
    target_date = db.Column(db.Date)
    
    # Livello attività
    activity_level = db.Column(_def(ActivityLevelEnum), nullable=False)
    training_frequency = db.Column(db.Integer)  # volte/settimana
    training_type = db.Column(db.String(255))  # "cardio", "pesi", "misto"
    
    # Dati fisici base
    gender = db.Column(_def(GenereEnum), nullable=False)
    
    # Note mediche
    medical_conditions = db.Column(db.Text)
    medications = db.Column(db.Text)
    supplements = db.Column(db.Text)
    
    # Relazioni
    cliente = relationship("Cliente", back_populates="nutritional_profile")
    
    def __repr__(self):
        return f"<NutritionalProfile for Cliente {self.cliente_id}>"


class HealthAssessment(TimestampMixin, db.Model):
    """Anamnesi e valutazione salute periodica"""
    __tablename__ = "health_assessments"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    assessment_date = db.Column(db.Date, nullable=False)
    
    # Anamnesi familiare
    family_history = db.Column(JSONB, default=dict)  # {"diabete": true, "ipertensione": false}
    
    # Stile di vita
    sleep_hours = db.Column(db.Float)
    sleep_quality = db.Column(db.String(20))  # "scarsa", "sufficiente", "buona", "ottima"
    stress_level = db.Column(db.Integer)  # 1-10
    smoking = db.Column(db.Boolean, default=False)
    alcohol_frequency = db.Column(db.String(50))  # "mai", "occasionale", "moderato", "frequente"
    
    # Sintomi e problematiche
    digestive_issues = db.Column(db.Text)
    energy_levels = db.Column(db.String(20))  # "basso", "normale", "alto"
    
    # Esami del sangue (opzionali)
    blood_tests = db.Column(JSONB, default=dict)  # {"glicemia": 95, "colesterolo_tot": 180}
    
    # Note
    notes = db.Column(db.Text)
    
    # Relazioni
    cliente = relationship("Cliente", back_populates="health_assessments")
    
    def __repr__(self):
        return f"<HealthAssessment {self.assessment_date} for Cliente {self.cliente_id}>"


class BiometricData(TimestampMixin, db.Model):
    """Misurazioni biometriche periodiche"""
    __tablename__ = "biometric_data"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    measurement_date = db.Column(db.Date, nullable=False)
    
    # Misure base
    weight = db.Column(db.Float, nullable=False)  # kg
    height = db.Column(db.Float, nullable=False)  # cm
    
    # Circonferenze (cm)
    waist = db.Column(db.Float)
    hips = db.Column(db.Float)
    chest = db.Column(db.Float)
    arm_left = db.Column(db.Float)
    arm_right = db.Column(db.Float)
    thigh_left = db.Column(db.Float)
    thigh_right = db.Column(db.Float)
    
    # Composizione corporea
    body_fat_percentage = db.Column(db.Float)
    muscle_mass = db.Column(db.Float)  # kg
    bone_mass = db.Column(db.Float)  # kg
    water_percentage = db.Column(db.Float)
    
    # Altro
    blood_pressure_sys = db.Column(db.Integer)
    blood_pressure_dia = db.Column(db.Integer)
    resting_heart_rate = db.Column(db.Integer)
    
    # Note
    notes = db.Column(db.Text)
    
    # Relazioni
    cliente = relationship("Cliente", back_populates="biometric_data")
    
    # Proprietà calcolate
    @property
    def bmi(self):
        """Body Mass Index"""
        if self.height and self.weight:
            height_m = self.height / 100
            return round(self.weight / (height_m ** 2), 2)
        return None
    
    @property
    def waist_hip_ratio(self):
        """Rapporto vita/fianchi"""
        if self.waist and self.hips:
            return round(self.waist / self.hips, 2)
        return None
    
    def __repr__(self):
        return f"<BiometricData {self.measurement_date} for Cliente {self.cliente_id}>"


# ──────────────────────── 6. PREFERENCES & INTOLERANCES ─────────────────────── #
class DietaryPreference(db.Model):
    """Preferenze alimentari disponibili"""
    __tablename__ = "dietary_preferences"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    preference_type = db.Column(_def(DietaryPreferenceEnum), nullable=False)
    description = db.Column(db.Text)
    
    # Relazioni
    clienti = relationship(
        "Cliente",
        secondary="cliente_dietary_preference",
        back_populates="dietary_preferences"
    )
    
    def __repr__(self):
        return f"<DietaryPreference {self.name!r}>"


class FoodIntolerance(db.Model):
    """Intolleranze e allergie alimentari"""
    __tablename__ = "food_intolerances"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    severity = db.Column(db.String(20))  # "lieve", "moderata", "grave", "allergia"
    description = db.Column(db.Text)
    
    # Relazioni
    clienti = relationship(
        "Cliente",
        secondary="cliente_food_intolerance",
        back_populates="food_intolerances"
    )
    
    def __repr__(self):
        return f"<FoodIntolerance {self.name!r}>"


# ──────────────────────── 7. NOTES ─────────────────────── #
class NutritionNote(TimestampMixin, db.Model):
    """Note riservate delle nutrizioniste sui clienti"""
    __tablename__ = "nutrition_notes"
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    nutritionist_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    
    note_date = db.Column(db.Date, nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=True)  # Note solo per la nutrizionista
    
    # Relazioni
    cliente = relationship("Cliente")
    nutritionist = relationship("User", back_populates="nutrition_notes")
    
    def __repr__(self):
        return f"<NutritionNote {self.note_date} by User {self.nutritionist_id}>"


# ──────────────────────── TABELLE PONTE M2M ─────────────────────── #
cliente_dietary_preference = db.Table(
    "cliente_dietary_preference",
    db.Column("cliente_id", db.BigInteger, db.ForeignKey("clienti.cliente_id"), primary_key=True),
    db.Column("preference_id", db.Integer, db.ForeignKey("dietary_preferences.id"), primary_key=True),
    db.Column("added_at", db.DateTime, default=datetime.utcnow, nullable=False)
)

cliente_food_intolerance = db.Table(
    "cliente_food_intolerance",
    db.Column("cliente_id", db.BigInteger, db.ForeignKey("clienti.cliente_id"), primary_key=True),
    db.Column("intolerance_id", db.Integer, db.ForeignKey("food_intolerances.id"), primary_key=True),
    db.Column("added_at", db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column("notes", db.Text)  # Note specifiche per questo cliente
)


    





# ──────────────────────── TICKET SYSTEM ─────────────────────── #

# Tabella ponte M2M per dipartimenti condivisi
ticket_shared_departments = db.Table(
    "ticket_shared_departments",
    db.Column("ticket_id", db.Integer, db.ForeignKey("tickets.id"), primary_key=True),
    db.Column("department_id", db.Integer, db.ForeignKey("departments.id"), primary_key=True),
    db.Column("shared_at", db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column("shared_by_id", db.Integer, db.ForeignKey("users.id"))
)

# Tabella ponte M2M per utenti assegnati ai ticket
ticket_assigned_users = db.Table(
    "ticket_assigned_users",
    db.Column("ticket_id", db.Integer, db.ForeignKey("tickets.id"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column("assigned_by_id", db.Integer, db.ForeignKey("users.id"))
)


class Ticket(TimestampMixin, db.Model):
    """
    Sistema di ticketing per richieste inter-dipartimentali.
    Può essere creato da form pubblico o internamente.
    """
    __tablename__ = "tickets"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dati richiedente (da form pubblico)
    requester_first_name = db.Column(db.String(80), nullable=False)
    requester_last_name = db.Column(db.String(80), nullable=False)
    requester_email = db.Column(db.String(255), nullable=False, index=True)
    requester_department = db.Column(db.String(120))  # Dipartimento di appartenenza del richiedente
    
    # Ticket info
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    urgency = db.Column(_def(TicketUrgencyEnum), nullable=False, index=True)
    status = db.Column(
        _def(TicketStatusEnum),
        nullable=False,
        default=TicketStatusEnum.nuovo,
        index=True
    )

    # Categoria ticket (solo per dipartimento ID=13)
    category = db.Column(
        _def(TicketCategoryEnum),
        nullable=True,
        index=True,
        comment="Categoria ticket: problema/upgrade/review (solo dept 13)"
    )

    # Cliente/Lead collegato (opzionale)
    related_client_name = db.Column(db.String(255))  # Nome cliente/lead indicato nel form
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=True)
    
    # Dipartimento principale assegnato
    department_id = db.Column(
        db.Integer, 
        db.ForeignKey("departments.id"), 
        nullable=False,
        index=True
    )
    
    # Tracking
    ticket_number = db.Column(
        db.String(20), 
        unique=True, 
        nullable=False, 
        index=True,
        comment="Numero ticket progressivo YYYYMMDD-XXXX"
    )
    
    # Date importanti
    due_date = db.Column(db.DateTime, nullable=False)  # Calcolata in base all'urgenza
    closed_at = db.Column(db.DateTime)
    
    # Allegato (opzionale) - PDF o immagine
    attachment_filename = db.Column(
        db.String(255), 
        nullable=True,
        comment="Nome del file allegato (se presente)"
    )
    attachment_path = db.Column(
        db.String(500), 
        nullable=True,
        comment="Percorso relativo del file allegato"
    )
    
    # User interno che ha preso in carico (opzionale)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    
    # User che ha creato il ticket (ora obbligatorio)
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # nullable per compatibilità con vecchi ticket
    
    # Search
    search_vector = db.Column(TSVECTOR)
    __ts_vector__ = TSVectorType(
        "title", "description", "requester_email",
        regconfig="italian",
        weights={"title": "A", "description": "B", "requester_email": "C"}
    )
    
    # ─────────────── Relazioni ─────────────────────────── #
    department = relationship("Department", foreign_keys=[department_id], backref="tickets_assigned")
    cliente = relationship("Cliente", backref="tickets")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], backref="tickets_assigned_to")
    created_by = relationship("User", foreign_keys=[created_by_id], backref="tickets_created")
    
    # Dipartimenti condivisi
    shared_departments = relationship(
        "Department",
        secondary="ticket_shared_departments",
        backref="tickets_shared"
    )
    
    # Utenti assegnati (many-to-many)
    assigned_users = relationship(
        "User",
        secondary="ticket_assigned_users",
        primaryjoin="Ticket.id == ticket_assigned_users.c.ticket_id",
        secondaryjoin="User.id == ticket_assigned_users.c.user_id",
        backref="assigned_tickets"
    )
    
    # Storico e commenti
    status_changes = relationship(
        "TicketStatusChange", 
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketStatusChange.created_at.desc()"
    )
    
    comments = relationship(
        "TicketComment",
        back_populates="ticket", 
        cascade="all, delete-orphan",
        order_by="TicketComment.created_at.desc()"
    )
    
    # Allegati multipli (fino a 5)
    attachments = relationship(
        "TicketAttachment",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketAttachment.created_at.asc()"
    )
    
    # ─────────────── Metodi Helper ─────────────────────────── #
    @property
    def has_attachment(self) -> bool:
        """True se il ticket ha un allegato."""
        return bool(self.attachment_filename and self.attachment_path)
    
    @property
    def attachment_extension(self) -> str:
        """Restituisce l'estensione del file allegato."""
        if self.attachment_filename:
            import os
            return os.path.splitext(self.attachment_filename)[1].lower()
        return ""
    
    @property
    def is_attachment_image(self) -> bool:
        """True se l'allegato è un'immagine."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        return self.attachment_extension in image_extensions
    
    @property
    def is_attachment_pdf(self) -> bool:
        """True se l'allegato è un PDF."""
        return self.attachment_extension == '.pdf'
    
    @property
    def is_overdue(self) -> bool:
        """True se il ticket è scaduto."""
        if self.status == TicketStatusEnum.chiuso:
            return False
        if self.due_date is None:
            return False
        import pytz
        rome_tz = pytz.timezone('Europe/Rome')
        now_rome = datetime.now(rome_tz)
        due_rome = pytz.utc.localize(self.due_date).astimezone(rome_tz)
        return now_rome > due_rome
    
    @property
    def hours_until_due(self) -> float:
        """Ore rimanenti alla scadenza."""
        if self.status == TicketStatusEnum.chiuso:
            return 0
        import pytz
        rome_tz = pytz.timezone('Europe/Rome')
        now_rome = datetime.now(rome_tz)
        due_rome = pytz.utc.localize(self.due_date).astimezone(rome_tz)
        delta = due_rome - now_rome
        return max(0, delta.total_seconds() / 3600)
    
    @property
    def urgency_label(self) -> str:
        """Label testuale per urgenza."""
        labels = {
            TicketUrgencyEnum.alta: "Alta - Entro oggi",
            TicketUrgencyEnum.media: "Media - Entro 2 giorni", 
            TicketUrgencyEnum.bassa: "Bassa - Entro la settimana"
        }
        return labels.get(self.urgency, "")
    
    @property
    def status_badge_class(self) -> str:
        """Classe CSS per il badge dello status."""
        classes = {
            TicketStatusEnum.nuovo: "badge-danger",
            TicketStatusEnum.in_lavorazione: "badge-warning",
            TicketStatusEnum.in_attesa: "badge-info",
            TicketStatusEnum.chiuso: "badge-success"
        }
        return classes.get(self.status, "badge-secondary")
    
    @property
    def all_involved_departments(self) -> List[Department]:
        """Tutti i dipartimenti coinvolti (principale + condivisi)."""
        depts = [self.department]
        depts.extend(self.shared_departments)
        return depts
    
    # Property per ottenere il nome del cliente/lead
    @property
    def client_display_name(self) -> str:
        """
        Restituisce il nome del cliente o lead collegato.
        Priorità: cliente esistente > lead testuale > vuoto
        """
        if self.cliente and self.cliente.nome_cognome:
            return self.cliente.nome_cognome
        elif self.related_client_name:
            return self.related_client_name
        return ""
    
    @classmethod
    def generate_ticket_number(cls) -> str:
        """Genera numero ticket progressivo YYYYMMDD-XXXX."""
        today = date.today()
        prefix = today.strftime("%Y%m%d")
        
        # Trova l'ultimo numero del giorno
        last_ticket = cls.query.filter(
            cls.ticket_number.like(f"{prefix}-%")
        ).order_by(cls.ticket_number.desc()).first()
        
        if last_ticket:
            last_num = int(last_ticket.ticket_number.split("-")[1])
            next_num = last_num + 1
        else:
            next_num = 1
        
        return f"{prefix}-{next_num:04d}"
    
    def calculate_due_date(self) -> datetime:
        """Calcola la scadenza in base all'urgenza."""
        import pytz
        rome_tz = pytz.timezone('Europe/Rome')
        now = datetime.now(rome_tz)
        
        if self.urgency == TicketUrgencyEnum.alta:
            # Entro fine giornata lavorativa (18:00)
            due = now.replace(hour=18, minute=0, second=0, microsecond=0)
            if now.hour >= 18:
                # Se già passate le 18, entro domani alle 18
                due += timedelta(days=1)
        elif self.urgency == TicketUrgencyEnum.media:
            # Entro 2 giorni lavorativi
            due = now + timedelta(days=2)
        else:  # bassa
            # Entro 7 giorni
            due = now + timedelta(days=7)
        
        # Converte in UTC per il salvataggio nel database
        return due.astimezone(pytz.utc).replace(tzinfo=None)
    
    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_number} - {self.title[:30]}>"


class TicketStatusChange(TimestampMixin, db.Model):
    """
    Traccia tutti i cambi di stato di un ticket con messaggio.
    """
    __tablename__ = "ticket_status_changes"
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer, 
        db.ForeignKey("tickets.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    
    # Stati
    from_status = db.Column(_def(TicketStatusEnum), nullable=True)  # NULL per primo stato
    to_status = db.Column(_def(TicketStatusEnum), nullable=False)
    
    # Chi ha fatto il cambio
    changed_by_id = db.Column(
        db.Integer, 
        db.ForeignKey("users.id"), 
        nullable=False,
        index=True
    )
    
    # Messaggio obbligatorio per notifica email
    message = db.Column(db.Text, nullable=False)
    
    # Email inviate
    emails_sent_to = db.Column(
        JSONB, 
        default=list,
        comment="Lista email a cui è stata inviata la notifica"
    )
    
    # ─────────────── Relazioni ─────────────────────────── #
    ticket = relationship("Ticket", back_populates="status_changes")
    changed_by = relationship("User")
    
    def __repr__(self) -> str:
        return f"<TicketStatusChange {self.from_status} → {self.to_status}>"


class TicketComment(TimestampMixin, db.Model):
    """
    Commenti interni sul ticket (non inviati via email).
    """
    __tablename__ = "ticket_comments"
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    content = db.Column(db.Text, nullable=False)
    is_internal = db.Column(db.Boolean, default=True, nullable=False)
    
    # Allegati (opzionale per future implementazioni)
    attachments = db.Column(JSONB, default=list)
    
    # ─────────────── Relazioni ─────────────────────────── #
    ticket = relationship("Ticket", back_populates="comments")
    author = relationship("User")
    
    def __repr__(self) -> str:
        return f"<TicketComment by {self.author_id} on Ticket {self.ticket_id}>"


class TicketAttachment(TimestampMixin, db.Model):
    """
    Gestisce gli allegati multipli per i ticket.
    Ogni ticket può avere fino a 5 allegati.
    """
    __tablename__ = "ticket_attachments"
    
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Info file
    filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)  # in bytes
    mime_type = db.Column(db.String(100), nullable=True)
    
    # Upload info
    uploaded_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    
    # ─────────────── Relazioni ─────────────────────────── #
    ticket = relationship("Ticket", back_populates="attachments")
    uploaded_by = relationship("User")
    
    @property
    def extension(self) -> str:
        """Estensione del file."""
        if self.filename:
            import os
            return os.path.splitext(self.filename)[1].lower()
        return ""
    
    @property
    def is_image(self) -> bool:
        """Controlla se è un'immagine."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
        return self.extension in image_extensions
    
    @property
    def is_pdf(self) -> bool:
        """Controlla se è un PDF."""
        return self.extension == '.pdf'
    
    @property
    def size_formatted(self) -> str:
        """Dimensione formattata in MB/KB."""
        if self.file_size < 1024:
            return f"{self.file_size} B"
        elif self.file_size < 1024 * 1024:
            return f"{self.file_size / 1024:.1f} KB"
        else:
            return f"{self.file_size / (1024 * 1024):.1f} MB"
    
    def __repr__(self) -> str:
        return f"<TicketAttachment {self.filename} for Ticket {self.ticket_id}>"


class TicketMessage(TimestampMixin, db.Model):
    """
    Modello per i messaggi di chat nei ticket.
    Permette conversazioni tra richiedente e tutti i destinatari del ticket.
    """
    __tablename__ = 'ticket_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Ticket a cui appartiene il messaggio
    ticket_id = db.Column(
        db.Integer,
        db.ForeignKey('tickets.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Chi invia il messaggio
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Contenuto del messaggio
    content = db.Column(db.Text, nullable=False)
    
    # Tracciamento lettura
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime)
    read_by = db.Column(JSONB, default=list, comment="Lista ID utenti che hanno letto")
    
    # ─────────────── Relazioni ─────────────────────────── #
    ticket = relationship("Ticket", backref=db.backref("messages", lazy="dynamic", cascade="all, delete-orphan"))
    sender = relationship("User", foreign_keys=[sender_id])
    
    def mark_as_read(self, user_id: int):
        """Marca il messaggio come letto da un utente."""
        read_list = self.read_by or []
        if user_id not in read_list:
            # Crea una nuova lista per forzare l'aggiornamento JSONB
            new_read_list = list(read_list)
            new_read_list.append(user_id)
            self.read_by = new_read_list
            self.read_at = datetime.utcnow()
            self.is_read = True
            # Flag the attribute as modified for SQLAlchemy
            from sqlalchemy.orm.attributes import flag_modified
            flag_modified(self, 'read_by')
            db.session.commit()
    
    def is_read_by(self, user_id: int) -> bool:
        """Verifica se un utente ha letto il messaggio."""
        return user_id in (self.read_by or [])
    
    def __repr__(self) -> str:
        return f"<TicketMessage {self.id} in Ticket {self.ticket_id}>"


# ───────────────────────────── FERIE E PERMESSI ──────────────────────────── #

class LeavePolicy(TimestampMixin, db.Model):
    """Configurazione annuale giorni ferie/permessi per l'azienda."""
    __tablename__ = "leave_policies"
    
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, unique=True, index=True)
    
    # Giorni ferie annuali (uguale per tutti)
    annual_leave_days = db.Column(db.Integer, nullable=False, default=22)
    
    # Ore permessi annuali 
    annual_permission_hours = db.Column(db.Integer, nullable=False, default=32)
    
    # Vincoli giorni consecutivi ferie
    min_consecutive_days = db.Column(db.Integer, nullable=False, default=3)
    max_consecutive_days = db.Column(db.Integer, nullable=False, default=15)
    
    # Note o regole aggiuntive
    notes = db.Column(db.Text, nullable=True)
    
    # Chi ha creato/modificato la policy (solo admin)
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    
    # Relazioni
    created_by = relationship("User", foreign_keys=[created_by_id])
    
    def __repr__(self) -> str:
        return f"<LeavePolicy year={self.year}>"


class ItalianHoliday(db.Model):
    """Calendario festività italiane."""
    __tablename__ = "italian_holidays"
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, unique=True, index=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Se è un ponte aziendale (aggiunto oltre alle festività nazionali)
    is_company_bridge = db.Column(db.Boolean, default=False, nullable=False)
    
    # Anno di riferimento per query più veloci
    year = db.Column(db.Integer, nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<ItalianHoliday {self.date} - {self.name}>"


class LeaveRequest(TimestampMixin, db.Model):
    """
    Richieste di ferie/permessi/malattie.

    WORKFLOW APPROVAZIONE TWO-TIER:
    ===============================

    NUTRIZIONE (con Team):
    - Membro team → Team Leader → HR
    - Team Leader → CCO → HR

    COACH / PSICOLOGIA:
    - Membro → Responsabile Dipartimento → HR
    - Responsabile Dipartimento → CCO → HR

    ALTRI DIPARTIMENTI:
    - Membro → Responsabile Dipartimento → HR
    - Responsabile Dipartimento → CEO → HR
    """
    __tablename__ = "leave_requests"

    id = db.Column(db.Integer, primary_key=True)

    # Chi fa la richiesta
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Tipo e stato
    leave_type = db.Column(
        _def(LeaveTypeEnum),
        nullable=False,
        index=True
    )
    status = db.Column(
        _def(LeaveStatusEnum),
        nullable=False,
        default=LeaveStatusEnum.bozza,
        index=True
    )

    # Date
    start_date = db.Column(db.Date, nullable=False, index=True)
    end_date = db.Column(db.Date, nullable=False)

    # Per i permessi in ore (opzionale)
    hours = db.Column(db.Float, nullable=True)

    # Giorni lavorativi calcolati (escludendo weekend e festivi)
    working_days = db.Column(db.Float, nullable=False, default=0)

    # Note e motivazioni
    notes = db.Column(db.Text, nullable=True)
    rejection_reason = db.Column(db.Text, nullable=True)

    # ────────────────────────── Two-Tier Approval ──────────────────────────
    # Chi deve approvare la prima fase (Team Leader / Resp. Dip. / CCO / CEO)
    first_approver_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Chi deve approvare la prima fase"
    )
    first_approved_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Quando è stata approvata la prima fase"
    )

    # Chi approva la fase HR (finale)
    hr_approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="HR che ha approvato (fase finale)"
    )
    hr_approved_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Quando HR ha approvato"
    )

    # Legacy field - punta all'approvatore finale per retrocompatibilità
    approved_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at = db.Column(db.DateTime, nullable=True)

    # ────────────────────────── Relazioni ──────────────────────────
    user = relationship("User", foreign_keys=[user_id], back_populates="leave_requests")
    first_approver = relationship("User", foreign_keys=[first_approver_id])
    hr_approver = relationship("User", foreign_keys=[hr_approved_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])

    # Indici composti per query frequenti
    __table_args__ = (
        Index('idx_leave_requests_user_year', 'user_id', 'start_date'),
        Index('idx_leave_requests_status_dates', 'status', 'start_date', 'end_date'),
        Index('idx_leave_requests_first_approver', 'first_approver_id'),
    )

    @staticmethod
    def determine_initial_status_and_approver(user: 'User') -> tuple:
        """
        Determina lo stato iniziale e il primo approvatore in base al contesto del dipendente.

        Returns:
            tuple: (LeaveStatusEnum, first_approver_id, approver_description)

        LOGICA:
        =======
        NUTRIZIONE (con Team):
        - Membro team → Team Leader
        - Team Leader → CCO

        COACH / PSICOLOGIA:
        - Membro → Responsabile Dipartimento
        - Responsabile Dipartimento → CCO

        ALTRI DIPARTIMENTI:
        - Membro → Responsabile Dipartimento
        - Responsabile Dipartimento → CEO
        """
        from flask import current_app

        # Caso 1: Utente senza dipartimento - fallback ad admin
        if not user.department:
            current_app.logger.warning(
                f"User {user.id} ({user.full_name}) non ha dipartimento. Richiede approvazione admin."
            )
            # Trova un admin attivo
            admin = User.query.filter_by(is_admin=True, is_active=True).first()
            if admin:
                return (LeaveStatusEnum.pending_first_approval, admin.id, f"Admin ({admin.full_name})")
            return (LeaveStatusEnum.pending_first_approval, None, "Admin")

        dept_name = user.department.name

        # ─────────────────── NUTRIZIONE (con Team) ───────────────────
        if dept_name in ('Nutrizione', 'Nutrizione 2'):
            # Verifica se l'utente è un Team Leader
            is_team_leader = any(t.head_id == user.id for t in user.department.teams) if user.department.teams else False

            if is_team_leader:
                # Team Leader → CCO approva
                cco_dept = Department.query.filter_by(name='CCO').first()
                if cco_dept and cco_dept.head:
                    return (
                        LeaveStatusEnum.pending_first_approval,
                        cco_dept.head.id,
                        f"CCO ({cco_dept.head.full_name})"
                    )
                # Fallback: CEO approva
                ceo_dept = Department.query.filter_by(name='CEO').first()
                if ceo_dept and ceo_dept.head:
                    current_app.logger.warning(f"CCO non trovato per Team Leader {user.id}, fallback a CEO")
                    return (LeaveStatusEnum.pending_first_approval, ceo_dept.head.id, f"CEO ({ceo_dept.head.full_name})")

            # Membro del team → Team Leader approva
            if user.team and user.team.head:
                return (
                    LeaveStatusEnum.pending_first_approval,
                    user.team.head.id,
                    f"Team Leader ({user.team.head.full_name})"
                )

            # Membro senza team assegnato → Responsabile Dipartimento
            if user.department.head and user.department.head.id != user.id:
                return (
                    LeaveStatusEnum.pending_first_approval,
                    user.department.head.id,
                    f"Responsabile Dipartimento ({user.department.head.full_name})"
                )

            # Fallback: CCO o CEO
            cco_dept = Department.query.filter_by(name='CCO').first()
            if cco_dept and cco_dept.head:
                current_app.logger.warning(f"Nutrizione user {user.id} senza team/head valido, fallback a CCO")
                return (LeaveStatusEnum.pending_first_approval, cco_dept.head.id, f"CCO ({cco_dept.head.full_name})")
            ceo_dept = Department.query.filter_by(name='CEO').first()
            if ceo_dept and ceo_dept.head:
                current_app.logger.warning(f"Nutrizione user {user.id} senza team/head/CCO valido, fallback a CEO")
                return (LeaveStatusEnum.pending_first_approval, ceo_dept.head.id, f"CEO ({ceo_dept.head.full_name})")
            return (LeaveStatusEnum.pending_first_approval, None, "Admin")

        # ─────────────────── COACH / PSICOLOGIA ───────────────────
        if dept_name in ('Coach', 'Psicologia'):
            # Verifica se l'utente è il Responsabile Dipartimento
            is_dept_head = user.department.head_id == user.id

            if is_dept_head:
                # Responsabile Dipartimento → CCO approva
                cco_dept = Department.query.filter_by(name='CCO').first()
                if cco_dept and cco_dept.head:
                    return (
                        LeaveStatusEnum.pending_first_approval,
                        cco_dept.head.id,
                        f"CCO ({cco_dept.head.full_name})"
                    )
                # Fallback: CEO approva
                ceo_dept = Department.query.filter_by(name='CEO').first()
                if ceo_dept and ceo_dept.head:
                    current_app.logger.warning(f"CCO non trovato per Dept Head {user.id}, fallback a CEO")
                    return (LeaveStatusEnum.pending_first_approval, ceo_dept.head.id, f"CEO ({ceo_dept.head.full_name})")

            # Membro → Responsabile Dipartimento approva
            if user.department.head:
                return (
                    LeaveStatusEnum.pending_first_approval,
                    user.department.head.id,
                    f"Responsabile Dipartimento ({user.department.head.full_name})"
                )

            # Fallback: CCO o CEO
            cco_dept = Department.query.filter_by(name='CCO').first()
            if cco_dept and cco_dept.head:
                current_app.logger.warning(f"Dept {dept_name} senza head, fallback a CCO")
                return (LeaveStatusEnum.pending_first_approval, cco_dept.head.id, f"CCO ({cco_dept.head.full_name})")
            ceo_dept = Department.query.filter_by(name='CEO').first()
            if ceo_dept and ceo_dept.head:
                current_app.logger.warning(f"Dept {dept_name} senza head/CCO, fallback a CEO")
                return (LeaveStatusEnum.pending_first_approval, ceo_dept.head.id, f"CEO ({ceo_dept.head.full_name})")
            return (LeaveStatusEnum.pending_first_approval, None, "Admin")

        # ─────────────────── ALTRI DIPARTIMENTI ───────────────────
        is_dept_head = user.department.head_id == user.id

        if is_dept_head:
            # Responsabile Dipartimento → CEO approva
            ceo_dept = Department.query.filter_by(name='CEO').first()
            if ceo_dept and ceo_dept.head:
                return (
                    LeaveStatusEnum.pending_first_approval,
                    ceo_dept.head.id,
                    f"CEO ({ceo_dept.head.full_name})"
                )
            # Fallback: trova un admin
            admin = User.query.filter_by(is_admin=True, is_active=True).first()
            if admin:
                current_app.logger.warning(f"CEO non trovato per Dept Head {user.id}, fallback ad admin")
                return (LeaveStatusEnum.pending_first_approval, admin.id, f"Admin ({admin.full_name})")

        # Membro → Responsabile Dipartimento approva
        if user.department.head:
            return (
                LeaveStatusEnum.pending_first_approval,
                user.department.head.id,
                f"Responsabile Dipartimento ({user.department.head.full_name})"
            )

        # Dipartimento senza responsabile → CEO o admin
        ceo_dept = Department.query.filter_by(name='CEO').first()
        if ceo_dept and ceo_dept.head:
            current_app.logger.warning(f"Dept {dept_name} senza head, fallback a CEO")
            return (LeaveStatusEnum.pending_first_approval, ceo_dept.head.id, f"CEO ({ceo_dept.head.full_name})")
        admin = User.query.filter_by(is_admin=True, is_active=True).first()
        if admin:
            current_app.logger.warning(f"Dept {dept_name} senza head/CEO, fallback ad admin")
            return (LeaveStatusEnum.pending_first_approval, admin.id, f"Admin ({admin.full_name})")
        return (LeaveStatusEnum.pending_first_approval, None, "Admin")

    def get_approval_stage(self) -> str:
        """Ritorna una descrizione human-readable dello stato di approvazione."""
        if self.status == LeaveStatusEnum.pending_first_approval:
            if self.first_approver:
                return f"In attesa di approvazione da {self.first_approver.full_name}"
            return "In attesa di approvazione"
        elif self.status == LeaveStatusEnum.pending_hr:
            # Legacy: richieste vecchie ancora in attesa HR
            return "In attesa di approvazione"
        elif self.status == LeaveStatusEnum.approvata:
            return "Approvata"
        elif self.status == LeaveStatusEnum.rifiutata:
            return "Rifiutata"
        elif self.status == LeaveStatusEnum.richiesta:
            return "In attesa di approvazione"
        else:
            return "In bozza"

    def __repr__(self) -> str:
        return f"<LeaveRequest {self.user_id} - {self.leave_type.value} ({self.start_date} to {self.end_date})>"


# ────────────────────────────────────────────────────────────────────
#  Modelli per Comunicazioni
# ────────────────────────────────────────────────────────────────────

# Tabella di associazione per comunicazioni e dipartimenti
communication_departments = db.Table('communication_departments',
    db.Column('communication_id', db.Integer, db.ForeignKey('communications.id', ondelete='CASCADE'), primary_key=True),
    db.Column('department_id', db.Integer, db.ForeignKey('departments.id', ondelete='CASCADE'), primary_key=True)
)


class Communication(TimestampMixin, db.Model):
    """Comunicazioni inviate agli utenti."""
    __tablename__ = "communications"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Titolo e contenuto
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)  # HTML content from editor
    
    # Chi ha creato la comunicazione
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Se è per tutti i dipartimenti
    is_for_all_departments = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relazioni
    author = relationship("User", foreign_keys=[author_id])
    departments = relationship("Department", secondary=communication_departments, 
                             backref=db.backref('communications', lazy='dynamic'))
    reads = relationship("CommunicationRead", back_populates="communication", 
                        cascade="all, delete-orphan")
    
    @property
    def total_recipients(self):
        """Numero totale di destinatari."""
        # NOTA: User.department_id rimosso - ora ritorna sempre tutti gli utenti attivi
        return User.query.filter_by(is_active=True).count()
    
    @property
    def read_count(self):
        """Numero di utenti che hanno letto."""
        return len(self.reads)
    
    @property
    def unread_count(self):
        """Numero di utenti che non hanno letto."""
        return self.total_recipients - self.read_count
    
    def get_recipients(self):
        """Ottiene la lista di tutti i destinatari."""
        # NOTA: User.department_id rimosso - ora ritorna sempre tutti gli utenti attivi
        return User.query.filter_by(is_active=True).all()
    
    def has_read(self, user):
        """Verifica se un utente ha letto la comunicazione."""
        return CommunicationRead.query.filter_by(
            communication_id=self.id,
            user_id=user.id
        ).first() is not None
    
    def get_unread_users(self):
        """Ottiene la lista degli utenti che non hanno letto."""
        read_user_ids = [read.user_id for read in self.reads]
        recipients = self.get_recipients()
        return [user for user in recipients if user.id not in read_user_ids]
    
    def __repr__(self) -> str:
        return f"<Communication {self.id} - {self.title}>"


class CommunicationRead(db.Model):
    """Tracciamento delle letture delle comunicazioni."""
    __tablename__ = "communication_reads"
    
    id = db.Column(db.Integer, primary_key=True)
    
    communication_id = db.Column(
        db.Integer,
        db.ForeignKey("communications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Quando è stata letta
    read_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relazioni
    communication = relationship("Communication", back_populates="reads")
    user = relationship("User")
    
    # Vincolo di unicità per evitare letture duplicate
    __table_args__ = (
        db.UniqueConstraint('communication_id', 'user_id', name='_communication_user_uc'),
        Index('idx_communication_reads_user', 'user_id'),
    )
    
    def __repr__(self) -> str:
        return f"<CommunicationRead comm={self.communication_id} user={self.user_id}>"


# ═══════════════════════════════ NEWS/NOVITÀ ═══════════════════════════════ #

# Tabella associativa M2M per news-categorie
news_categories_association = db.Table(
    'news_categories_association',
    db.Column('news_id', db.Integer, db.ForeignKey('news.id', ondelete='CASCADE'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('news_categories.id', ondelete='CASCADE'), primary_key=True),
    db.Column('created_at', db.DateTime, default=datetime.utcnow, nullable=False)
)


class NewsCategory(db.Model):
    """Categorie per le novità aziendali."""
    __tablename__ = "news_categories"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)  # es: "Azienda", "Risorse Umane"
    slug = db.Column(db.String(50), unique=True, nullable=False)  # es: "azienda", "risorse-umane"
    icon = db.Column(db.String(20), default='📰')  # Emoji o icon class
    color = db.Column(db.String(7), default='#6B7280')  # Hex color per badge
    display_order = db.Column(db.Integer, default=0)  # Ordinamento per UI
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self) -> str:
        return f"<NewsCategory {self.id} - {self.name}>"


class News(TimestampMixin, db.Model):
    """Novità e aggiornamenti della piattaforma Corposostenibile Suite."""
    __tablename__ = "news"

    id = db.Column(db.Integer, primary_key=True)

    # Titolo e contenuto
    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.String(500))  # Breve sommario
    content = db.Column(db.Text, nullable=False)  # HTML content from editor

    # Metadata
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Data di pubblicazione (può essere programmata nel futuro)
    published_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Flag per visibilità
    is_published = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_pinned = db.Column(db.Boolean, default=False, nullable=False)  # Novità in evidenza

    # Categoria/Tag (opzionale) - DEPRECATED: mantenuto per retrocompatibilità migration
    category = db.Column(db.String(50))  # es: "feature", "bugfix", "announcement", "maintenance"

    # Immagine di copertina (opzionale)
    cover_image_url = db.Column(db.String(500))

    # Relazioni
    author = relationship("User", foreign_keys=[author_id])
    categories = relationship(
        "NewsCategory",
        secondary=news_categories_association,
        backref=db.backref('news_items', lazy='dynamic'),
        lazy='select'
    )

    @property
    def is_visible(self):
        """Verifica se la news è visibile (pubblicata e data <= oggi)."""
        return self.is_published and self.published_at <= datetime.utcnow()

    @property
    def total_views(self):
        """Numero totale di visualizzazioni."""
        return NewsRead.query.filter_by(news_id=self.id).count()

    def is_read_by(self, user_id: int) -> bool:
        """Verifica se l'utente ha già letto questa news."""
        return NewsRead.query.filter_by(news_id=self.id, user_id=user_id).first() is not None

    def mark_as_read(self, user_id: int):
        """Segna la news come letta dall'utente."""
        existing = NewsRead.query.filter_by(news_id=self.id, user_id=user_id).first()
        if not existing:
            read = NewsRead(news_id=self.id, user_id=user_id)
            db.session.add(read)

    def __repr__(self) -> str:
        return f"<News {self.id} - {self.title}>"


class NewsRead(db.Model):
    """Tracciamento delle letture delle news."""
    __tablename__ = "news_reads"

    id = db.Column(db.Integer, primary_key=True)

    news_id = db.Column(
        db.Integer,
        db.ForeignKey("news.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Quando è stata letta
    read_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relazioni
    news = relationship("News", backref=db.backref('reads', lazy='dynamic', cascade="all, delete-orphan"))
    user = relationship("User")

    # Vincolo di unicità per evitare letture duplicate
    __table_args__ = (
        db.UniqueConstraint('news_id', 'user_id', name='_news_user_uc'),
        Index('idx_news_reads_user', 'user_id'),
    )

    def __repr__(self) -> str:
        return f"<NewsRead news={self.news_id} user={self.user_id}>"


class NewsComment(TimestampMixin, db.Model):
    """Commenti alle novità."""
    __tablename__ = "news_comments"

    id = db.Column(db.Integer, primary_key=True)

    news_id = db.Column(
        db.Integer,
        db.ForeignKey("news.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Contenuto del commento
    content = db.Column(db.Text, nullable=False)

    # Relazioni
    news = relationship("News", backref=db.backref('comments', lazy='dynamic', cascade="all, delete-orphan", order_by="NewsComment.created_at.desc()"))
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<NewsComment {self.id} by user={self.user_id} on news={self.news_id}>"


class NewsLike(TimestampMixin, db.Model):
    """Like (cuore) alle novità."""
    __tablename__ = "news_likes"

    id = db.Column(db.Integer, primary_key=True)
    news_id = db.Column(db.Integer, db.ForeignKey("news.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Constraint per evitare like multipli dallo stesso utente
    __table_args__ = (
        db.UniqueConstraint('news_id', 'user_id', name='uq_news_user_like'),
    )

    news = relationship("News", backref=db.backref('likes', lazy='dynamic', cascade="all, delete-orphan"))
    user = relationship("User")

    def __repr__(self) -> str:
        return f"<NewsLike {self.id} by user={self.user_id} on news={self.news_id}>"


# ====================== RESPOND.IO FOLLOW-UP SYSTEM ====================== #

class RespondIOFollowupConfig(TimestampMixin, db.Model):
    """
    Configurazione follow-up per lifecycle specifici
    """
    __tablename__ = 'respond_io_followup_config'
    
    id = db.Column(db.Integer, primary_key=True)
    lifecycle = db.Column(db.String(50), nullable=False, unique=True)
    enabled = db.Column(db.Boolean, default=True)
    delay_hours = db.Column(db.Integer, default=12)
    message_text = db.Column(db.Text, default="Ciao 💪 Stai bene?")
    template_name = db.Column(db.String(100), default="followup_generico1")
    tag_waiting = db.Column(db.String(100), default="in_attesa_followup_1")
    tag_sent = db.Column(db.String(100), default="followup_1_inviato")
    
    # Statistiche
    total_scheduled = db.Column(db.Integer, default=0)
    total_sent = db.Column(db.Integer, default=0)
    total_cancelled = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<FollowupConfig {self.lifecycle}>'


class RespondIOFollowupQueue(TimestampMixin, db.Model):
    """
    Coda dei follow-up schedulati
    """
    __tablename__ = 'respond_io_followup_queue'
    
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.String(100), nullable=False, index=True)
    lifecycle = db.Column(db.String(50), nullable=False)
    channel_name = db.Column(db.String(200), nullable=False)
    channel_id = db.Column(db.String(100))
    
    # Scheduling
    scheduled_at = db.Column(db.DateTime, nullable=False, index=True)
    original_scheduled_at = db.Column(db.DateTime)  # Orario originale (prima di quiet hours adjustment)
    celery_task_id = db.Column(db.String(255))
    
    # Status
    status = db.Column(db.String(20), default='pending')  # pending, processing, sent, cancelled, failed
    sent_at = db.Column(db.DateTime)
    cancelled_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    
    # Tracking
    last_message_received_at = db.Column(db.DateTime)
    tag_waiting = db.Column(db.String(100))
    tag_sent = db.Column(db.String(100))
    
    # Message details
    message_type = db.Column(db.String(20))  # 'text' or 'template'
    message_sent = db.Column(db.Text)
    
    # IMPORTANTE: Constraint per prevenire duplicati
    # Un contatto può avere SOLO UN follow-up attivo (pending/processing) alla volta
    # Ma può avere multiple entry con status 'sent', 'cancelled', 'failed'
    __table_args__ = (
        # Unique constraint parziale: solo uno pending/processing per contact
        db.Index('idx_unique_active_followup', 'contact_id', 'status',
                unique=True,
                postgresql_where=(db.text("status IN ('pending', 'processing')"))),
    )
    
    def __repr__(self):
        return f'<FollowupQueue {self.contact_id} - {self.lifecycle} - {self.status}>'
    
    @classmethod
    def cancel_pending(cls, contact_id, lifecycle=None):
        """Cancella follow-up pending o processing per un contatto"""
        from flask import current_app
        from corposostenibile.celery_app import celery
        
        query = cls.query.filter(
            cls.contact_id == str(contact_id),  # Assicura che sia stringa
            cls.status.in_(['pending', 'processing'])  # Cancella anche quelli in processing
        )
        if lifecycle:
            query = query.filter_by(lifecycle=lifecycle)
        
        count = 0
        for item in query.all():
            item.status = 'cancelled'
            item.cancelled_at = datetime.utcnow()
            
            # Cancella anche il task Celery se esiste
            if item.celery_task_id:
                try:
                    celery.control.revoke(item.celery_task_id, terminate=True)
                    if current_app:
                        current_app.logger.info(f"Revoked Celery task {item.celery_task_id}")
                except Exception as e:
                    if current_app:
                        current_app.logger.warning(f"Could not revoke task {item.celery_task_id}: {e}")
            
            count += 1
        
        # NON fare commit qui - lascia che lo faccia il chiamante
        # db.session.commit() rimosso intenzionalmente
        return count


class RespondIOMessageHistory(TimestampMixin, db.Model):
    """
    Storico messaggi per tracking finestra 24h
    """
    __tablename__ = 'respond_io_message_history'
    
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.String(100), nullable=False, index=True)
    channel_id = db.Column(db.String(100))
    message_type = db.Column(db.String(20))  # 'incoming' or 'outgoing'
    message_id = db.Column(db.String(100))
    
    # Per calcolare finestra 24h
    message_timestamp = db.Column(db.DateTime, nullable=False, index=True)
    
    # Cleanup automatico dopo 48h
    __table_args__ = (
        db.Index('ix_message_history_cleanup', 'message_timestamp'),
    )
    
    @classmethod
    def get_last_incoming(cls, contact_id):
        """Ottiene ultimo messaggio ricevuto dal contatto"""
        return cls.query.filter_by(
            contact_id=contact_id,
            message_type='incoming'
        ).order_by(cls.message_timestamp.desc()).first()
    
    @classmethod
    def is_within_24h_window(cls, contact_id):
        """
        Verifica se siamo dentro la finestra 24h.
        
        Returns:
            True solo se siamo CERTI di essere dentro le 24h
            False se non abbiamo dati o siamo fuori dalla finestra (approccio conservativo)
        """
        last_incoming = cls.get_last_incoming(contact_id)
        if not last_incoming:
            # Nessun dato = usiamo template per sicurezza
            return False
        
        time_diff = datetime.utcnow() - last_incoming.message_timestamp
        return time_diff < timedelta(hours=24)
    
    @classmethod
    def cleanup_old_records(cls, days=2):
        """Rimuove record più vecchi di N giorni"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        deleted = cls.query.filter(cls.message_timestamp < cutoff).delete()
        db.session.commit()
        return deleted


# Lifecycle abilitati per follow-up
FOLLOWUP_ENABLED_LIFECYCLES = [
    'Contrassegnato',
    'In Target', 
    'Link Da Inviare',
    'Link Inviato'
]


# ════════════════════════════════════════════════════════════════════════════
#                               TYPEFORM RESPONSES
# ════════════════════════════════════════════════════════════════════════════

class TypeFormResponse(TimestampMixin, db.Model):
    """
    Model to store TypeForm weekly check-in responses from customers.
    
    This model stores the responses received from TypeForm's webhook
    or imported from CSV files.
    """
    __tablename__ = "typeform_responses"

    # Primary Key
    id = db.Column(db.Integer, primary_key=True)

    # TypeForm Metadata
    typeform_id = db.Column(db.String(255), nullable=False, unique=True, index=True)
    first_name = db.Column(db.String(255))
    last_name = db.Column(db.String(255))

    # Photo URLs
    photo_front = db.Column(db.String(1024))
    photo_side = db.Column(db.String(1024))
    photo_back = db.Column(db.String(1024))

    # Weekly Reflection Questions
    what_worked = db.Column(db.Text)
    what_didnt_work = db.Column(db.Text)
    what_learned = db.Column(db.Text)
    what_focus_next = db.Column(db.Text)
    injuries_notes = db.Column(db.Text)

    # Ratings (1-10)
    digestion_rating = db.Column(db.Integer)
    energy_rating = db.Column(db.Integer)
    strength_rating = db.Column(db.Integer)
    hunger_rating = db.Column(db.Integer)
    sleep_rating = db.Column(db.Integer)
    mood_rating = db.Column(db.Integer)
    motivation_rating = db.Column(db.Integer)

    # Physical Metrics
    weight = db.Column(db.Float)

    # Program Adherence
    nutrition_program_adherence = db.Column(db.Text)
    training_program_adherence = db.Column(db.Text)
    exercise_modifications = db.Column(db.Text)
    daily_steps = db.Column(db.Text)
    completed_training_weeks = db.Column(db.Text)
    planned_training_days = db.Column(db.Text)

    # Specific Topics
    live_session_topics = db.Column(db.Text)

    # Satisfaction Ratings
    nutritionist_rating = db.Column(db.Integer)
    nutritionist_feedback = db.Column(db.Text)
    psychologist_rating = db.Column(db.Integer)
    psychologist_feedback = db.Column(db.Text)
    coach_rating = db.Column(db.Integer)
    coach_feedback = db.Column(db.Text)

    # Progress Rating
    progress_rating = db.Column(db.Integer)

    # Coordinator Rating (sostituisce progress_rating nel calcolo Quality se presente)
    coordinator_rating = db.Column(db.Integer)
    coordinator_notes = db.Column(db.Text)

    # Additional Info
    referral = db.Column(db.Text)
    extra_comments = db.Column(db.Text)

    submit_date = db.Column(db.DateTime)

    # Full response data (for future fields)
    raw_response_data = db.Column(JSONB)

    # Relationship to Cliente
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=True)
    cliente = relationship("Cliente", back_populates="typeform_responses")

    # Match status (for manually associating responses to customers)
    is_matched = db.Column(db.Boolean, default=False)
    
    # Associations to User (professionals)
    nutritionist_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    coach_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    psychologist_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    
    # Relationships to User
    nutritionist_user = relationship("User", foreign_keys=[nutritionist_user_id], backref="feedback_as_nutritionist")
    coach_user = relationship("User", foreign_keys=[coach_user_id], backref="feedback_as_coach")
    psychologist_user = relationship("User", foreign_keys=[psychologist_user_id], backref="feedback_as_psychologist")

    def __repr__(self):
        return f"<TypeFormResponse {self.id} - {self.first_name} {self.last_name} - {self.submit_date}>"


# ---------------------------------------------------------------------------- #
#  Review System Models
# ---------------------------------------------------------------------------- #

class Review(TimestampMixin, db.Model):
    """
    Modello per le recensioni/valutazioni dei membri del team.
    """
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Chi scrive la review (il responsabile)
    reviewer_id = db.Column(
        db.Integer, 
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Chi riceve la review (il membro del team)
    reviewee_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Contenuto della review
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Tipo di review (opzionale, per categorizzare)
    review_type = db.Column(
        db.String(50),
        default='general',
        nullable=False
    )  # general, performance, monthly, annual, etc.
    
    # Rating (opzionale, scala 1-5)
    rating = db.Column(db.Integer)
    
    # Periodo di riferimento (opzionale)
    period_start = db.Column(db.Date)
    period_end = db.Column(db.Date)
    
    # Obiettivi e aree di miglioramento
    strengths = db.Column(db.Text)
    improvements = db.Column(db.Text)
    goals = db.Column(db.Text)
    
    # Stato della review
    is_draft = db.Column(db.Boolean, default=False, nullable=False)
    is_private = db.Column(db.Boolean, default=False, nullable=False)  # Se true, solo admin e reviewer possono vedere
    
    # Soft delete
    deleted_at = db.Column(db.DateTime)
    
    # Relazioni
    reviewer = db.relationship(
        'User',
        foreign_keys=[reviewer_id],
        backref=db.backref('reviews_given', lazy='dynamic')
    )
    
    reviewee = db.relationship(
        'User',
        foreign_keys=[reviewee_id],
        backref=db.backref('reviews_received', lazy='dynamic')
    )
    
    # Relazione con acknowledgment
    acknowledgment = db.relationship(
        'ReviewAcknowledgment',
        back_populates='review',
        uselist=False,
        cascade='all, delete-orphan'
    )
    
    @property
    def is_acknowledged(self):
        """Verifica se la review è stata confermata."""
        return self.acknowledgment is not None
    
    @property
    def acknowledged_at(self):
        """Data di conferma lettura."""
        if self.acknowledgment:
            return self.acknowledgment.acknowledged_at
        return None
    
    @property
    def rating_stars(self):
        """Restituisce il rating come stelle HTML."""
        if not self.rating:
            return ''
        
        full_stars = '★' * self.rating
        empty_stars = '☆' * (5 - self.rating)
        return full_stars + empty_stars
    
    def __repr__(self):
        return f'<Review {self.id}: {self.reviewer.first_name} -> {self.reviewee.first_name}>'


class ReviewAcknowledgment(db.Model):
    """
    Modello per tracciare la conferma di lettura delle review.
    """
    __tablename__ = 'review_acknowledgments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    review_id = db.Column(
        db.Integer,
        db.ForeignKey('reviews.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Chi conferma (dovrebbe essere sempre reviewee_id della review)
    acknowledged_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Timestamp della conferma
    acknowledged_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Note opzionali del membro alla conferma
    notes = db.Column(db.Text)
    
    # IP address per tracking
    ip_address = db.Column(db.String(45))
    
    # Relazioni
    review = db.relationship(
        'Review',
        back_populates='acknowledgment'
    )
    
    user = db.relationship(
        'User',
        foreign_keys=[acknowledged_by],
        backref=db.backref('review_acknowledgments', lazy='dynamic')
    )
    
    def __repr__(self):
        return f'<ReviewAcknowledgment {self.id}: Review {self.review_id}>'


class ReviewRequest(TimestampMixin, db.Model):
    """
    Modello per le richieste di training/review.
    Gli utenti possono richiedere training al loro responsabile.
    """
    __tablename__ = 'review_requests'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Chi richiede il training
    requester_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # A chi è indirizzata la richiesta (il responsabile)
    requested_to_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Argomento/Titolo della richiesta
    subject = db.Column(db.String(200), nullable=False)
    
    # Descrizione dettagliata (opzionale)
    description = db.Column(db.Text)
    
    # Stato della richiesta
    status = db.Column(
        db.String(20),
        default='pending',
        nullable=False
    )  # pending, accepted, rejected, completed
    
    # Note del responsabile (es. motivo rifiuto)
    response_notes = db.Column(db.Text)
    
    # Data risposta
    responded_at = db.Column(db.DateTime)
    
    # Review creata dalla richiesta (se accettata e completata)
    review_id = db.Column(
        db.Integer,
        db.ForeignKey('reviews.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Urgenza (opzionale)
    priority = db.Column(
        db.String(10),
        default='normal'
    )  # low, normal, high, urgent
    
    # Relazioni
    requester = db.relationship(
        'User',
        foreign_keys=[requester_id],
        backref=db.backref('review_requests_sent', lazy='dynamic')
    )
    
    requested_to = db.relationship(
        'User',
        foreign_keys=[requested_to_id],
        backref=db.backref('review_requests_received', lazy='dynamic')
    )
    
    review = db.relationship(
        'Review',
        backref=db.backref('request', uselist=False)
    )
    
    @property
    def is_pending(self):
        return self.status == 'pending'
    
    @property
    def is_accepted(self):
        return self.status == 'accepted'
    
    @property
    def is_completed(self):
        return self.status == 'completed'
    
    def __repr__(self):
        return f'<ReviewRequest {self.id}: {self.subject}>'


class ReviewMessage(TimestampMixin, db.Model):
    """
    Modello per i messaggi di chat nelle review/training.
    Permette conversazioni bidirezionali tra reviewer e reviewee.
    """
    __tablename__ = 'review_messages'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Review a cui appartiene il messaggio
    review_id = db.Column(
        db.Integer,
        db.ForeignKey('reviews.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Chi invia il messaggio
    sender_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Contenuto del messaggio
    content = db.Column(db.Text, nullable=False)
    
    # Tracciamento lettura
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime)
    read_by = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Soft delete (per mantenere storico)
    deleted_at = db.Column(db.DateTime)
    
    # IP address per tracking
    ip_address = db.Column(db.String(45))
    
    # Relazioni
    review = db.relationship(
        'Review',
        backref=db.backref('messages', lazy='dynamic', cascade='all, delete-orphan')
    )
    
    sender = db.relationship(
        'User',
        foreign_keys=[sender_id],
        backref=db.backref('sent_review_messages', lazy='dynamic')
    )
    
    reader = db.relationship(
        'User',
        foreign_keys=[read_by],
        backref=db.backref('read_review_messages', lazy='dynamic')
    )
    
    def mark_as_read(self, user_id):
        """Marca il messaggio come letto da un utente specifico."""
        if not self.is_read:
            self.is_read = True
            self.read_at = datetime.utcnow()
            self.read_by = user_id
            return True
        return False
    
    @property
    def is_from_reviewer(self):
        """Verifica se il messaggio è dal reviewer originale."""
        return self.sender_id == self.review.reviewer_id
    
    @property
    def is_from_reviewee(self):
        """Verifica se il messaggio è dal destinatario della review."""
        return self.sender_id == self.review.reviewee_id
    
    def __repr__(self):
        return f'<ReviewMessage {self.id}: Review {self.review_id} by User {self.sender_id}>'


class RespondIOUser(TimestampMixin, db.Model):
    """
    Utenti del workspace Respond.io sincronizzati via API.
    Questi sono gli utenti a cui possono essere assegnate le conversazioni.
    """
    __tablename__ = 'respond_io_users'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # ID dell'utente in Respond.io
    respond_io_id = db.Column(db.Integer, unique=True, nullable=False, index=True)
    
    # NUOVO: Associazione con User del gestionale
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True)
    user = db.relationship('User', backref=db.backref('respond_io_profile', uselist=False))
    
    # Dati utente da Respond.io
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    role = db.Column(db.String(50))  # agent, manager, owner
    
    # Team in Respond.io (opzionale)
    team_id = db.Column(db.Integer)
    team_name = db.Column(db.String(100))
    
    # Restrizioni (JSON array)
    restrictions = db.Column(db.JSON)
    
    # Stato
    is_active = db.Column(db.Boolean, default=True)
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relazioni
    work_schedules = db.relationship(
        'RespondIOUserWorkSchedule',
        back_populates='user',
        cascade='all, delete-orphan'
    )
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<RespondIOUser {self.email}>'


class RespondIOUserWorkSchedule(TimestampMixin, db.Model):
    """
    Modello per gestire gli orari di lavoro settimanali degli utenti Respond.io.
    Utilizzato per l'assegnazione automatica dei contatti.
    """
    __tablename__ = 'respond_io_user_work_schedules'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Utente Respond.io
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('respond_io_users.id', ondelete='CASCADE'),
        nullable=False
    )
    
    # Giorno della settimana (0=Lunedì, 6=Domenica)
    day_of_week = db.Column(db.Integer, nullable=False)
    
    # Orari di lavoro
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    
    # Flag per attivare/disattivare il turno
    is_active = db.Column(db.Boolean, default=True)
    
    # Note opzionali (es. "Pausa pranzo 13-14")
    notes = db.Column(db.String(200))
    
    # Timezone dell'utente (default Europe/Rome)
    timezone = db.Column(db.String(50), default='Europe/Rome')
    
    # Relazioni
    user = db.relationship(
        'RespondIOUser',
        back_populates='work_schedules'
    )
    
    # Indici e constraints
    __table_args__ = (
        db.UniqueConstraint('user_id', 'day_of_week', name='unique_respond_io_user_day'),
        db.Index('ix_respond_io_user_work_schedules_user_day', 'user_id', 'day_of_week'),
        db.Index('ix_respond_io_user_work_schedules_day_active', 'day_of_week', 'is_active'),
        db.CheckConstraint('day_of_week >= 0 AND day_of_week <= 6', name='check_respond_io_day_of_week'),
    )
    
    @property
    def day_name(self):
        """Ritorna il nome del giorno in italiano"""
        days = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']
        return days[self.day_of_week]
    
    def is_currently_working(self, check_time=None):
        """
        Verifica se l'utente è attualmente in turno.
        
        Args:
            check_time: datetime da verificare (default: now)
            
        Returns:
            bool: True se l'utente è in turno
        """
        from datetime import datetime
        import pytz
        
        if not self.is_active:
            return False
        
        # Usa il tempo fornito o l'orario attuale
        if check_time is None:
            tz = pytz.timezone(self.timezone)
            check_time = datetime.now(tz)
        elif check_time.tzinfo is None:
            # Se non ha timezone, assumiamo sia nel timezone dell'utente
            tz = pytz.timezone(self.timezone)
            check_time = tz.localize(check_time)
        
        # Verifica il giorno della settimana
        if check_time.weekday() != self.day_of_week:
            return False
        
        # Verifica l'orario
        current_time = check_time.time()
        return self.start_time <= current_time <= self.end_time
    
    def __repr__(self):
        return f'<RespondIOUserWorkSchedule {self.user_id}: {self.day_name} {self.start_time}-{self.end_time}>'


class RespondIOAssignmentLog(TimestampMixin, db.Model):
    """
    Log delle assegnazioni automatiche dei contatti Respond.io.
    Traccia chi ha assegnato cosa e quando per audit e analytics.
    """
    __tablename__ = 'respond_io_assignment_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Chi ha eseguito l'assegnazione
    executed_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Tipo di assegnazione
    assignment_type = db.Column(db.String(50), nullable=False, default='manual')  # manual, automatic, scheduled
    
    # Statistiche dell'assegnazione
    total_contacts = db.Column(db.Integer, default=0)
    contacts_assigned = db.Column(db.Integer, default=0)
    contacts_failed = db.Column(db.Integer, default=0)
    contacts_skipped = db.Column(db.Integer, default=0)
    
    # Utenti coinvolti (JSON array di user_ids)
    assigned_to_users = db.Column(db.JSON)  # [{"user_id": 1, "count": 25}, ...]
    
    # Lifecycle processati
    lifecycles_processed = db.Column(db.JSON)  # ["Nuova Lead", "Contrassegnato", ...]
    
    # Durata dell'operazione
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Stato
    status = db.Column(db.String(20), default='in_progress')  # in_progress, completed, failed, partial
    
    # Eventuali errori
    error_message = db.Column(db.Text)
    
    # Dettagli aggiuntivi (JSON)
    details = db.Column(db.JSON)  # Per info extra come filtri applicati, etc.
    
    # Relazioni
    executed_by = db.relationship(
        'User',
        foreign_keys=[executed_by_id],
        backref=db.backref('assignment_logs', lazy='dynamic')
    )
    
    @property
    def duration_seconds(self):
        """Calcola la durata in secondi"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def success_rate(self):
        """Calcola il tasso di successo"""
        if self.total_contacts > 0:
            return (self.contacts_assigned / self.total_contacts) * 100
        return 0
    
    def __repr__(self):
        return f'<RespondIOAssignmentLog {self.id}: {self.status} - {self.contacts_assigned}/{self.total_contacts}>'


class RespondIOCalendarEvent(TimestampMixin, db.Model):
    """Eventi calendario per gestione turni lavorativi stile Google Calendar"""
    __tablename__ = 'respond_io_calendar_events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('respond_io_users.id', ondelete='CASCADE'), nullable=False)
    
    # Informazioni evento
    title = db.Column(db.String(200), nullable=False)
    start_datetime = db.Column(db.DateTime(timezone=True), nullable=False)
    end_datetime = db.Column(db.DateTime(timezone=True), nullable=False)
    all_day = db.Column(db.Boolean, default=False)
    color = db.Column(db.String(7))  # Colore hex per visualizzazione
    
    # Tipo e stato
    event_type = db.Column(db.String(50), default='work')  # work, break, meeting, holiday
    status = db.Column(db.String(50), default='scheduled')  # scheduled, completed, cancelled
    
    # Note e dettagli
    notes = db.Column(db.Text)
    location = db.Column(db.String(200))
    
    # Ricorrenza
    is_recurring = db.Column(db.Boolean, default=False)
    recurrence_rule = db.Column(db.JSON)  # Regole ricorrenza RRULE compatibili
    parent_event_id = db.Column(db.Integer, db.ForeignKey('respond_io_calendar_events.id', ondelete='SET NULL'))
    
    # Metadati
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    updated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Relazioni
    user = db.relationship('RespondIOUser', backref=db.backref('calendar_events', lazy='dynamic', cascade='all, delete-orphan'))
    parent_event = db.relationship('RespondIOCalendarEvent', remote_side=[id], backref='recurring_instances')
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    updated_by = db.relationship('User', foreign_keys=[updated_by_id])
    breaks = db.relationship('RespondIOCalendarBreak', backref='event', cascade='all, delete-orphan', lazy='dynamic')
    
    def to_fullcalendar_dict(self):
        """Converte l'evento in formato FullCalendar"""
        # Ottieni le pause associate
        breaks_list = []
        for break_item in self.breaks:
            breaks_list.append({
                'id': break_item.id,
                'start': break_item.start_time.isoformat(),
                'end': break_item.end_time.isoformat(),
                'notes': break_item.notes
            })
        
        return {
            'id': self.id,
            'title': self.title,
            'start': self.start_datetime.isoformat(),
            'end': self.end_datetime.isoformat(),
            'allDay': self.all_day,
            'color': self.color or '#3788d8',
            'extendedProps': {
                'event_type': self.event_type,
                'status': self.status,
                'notes': self.notes,
                'location': self.location,
                'user_id': self.user_id,
                'user_name': self.user.full_name if self.user else None,
                'is_recurring': self.is_recurring,
                'breaks': breaks_list  # Include pause nel payload
            }
        }
    
    def generate_recurring_events(self, start_date, end_date):
        """Genera eventi ricorrenti basati sulla regola RRULE"""
        if not self.is_recurring or not self.recurrence_rule:
            return []
        
        from dateutil import rrule
        import pytz
        
        events = []
        # Implementazione della logica RRULE
        # TODO: Implementare parsing completo RRULE
        
        return events
    
    def __repr__(self):
        return f'<CalendarEvent {self.id}: {self.title} ({self.start_datetime})>'


class RespondIOScheduleTemplate(TimestampMixin, db.Model):
    """Template di orari predefiniti per configurazione rapida"""
    __tablename__ = 'respond_io_schedule_templates'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Configurazione orari (JSON)
    # Formato: {
    #   "monday": {"start": "09:00", "end": "18:00", "breaks": [{"start": "13:00", "end": "14:00"}]},
    #   "tuesday": {...},
    #   ...
    # }
    schedule_data = db.Column(db.JSON, nullable=False)
    
    # Colore per visualizzazione
    color = db.Column(db.String(7), default='#3788d8')
    
    # Chi ha creato il template
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', backref=db.backref('schedule_templates', lazy='dynamic'))
    
    def apply_to_user(self, user_id, start_date, end_date=None):
        """Applica il template a un utente per un periodo specifico"""
        events = []
        # Logica per creare eventi basati sul template
        return events
    
    def __repr__(self):
        return f'<ScheduleTemplate {self.id}: {self.name}>'


class RespondIOWorkHistory(TimestampMixin, db.Model):
    """Storico dei turni effettivamente lavorati"""
    __tablename__ = 'respond_io_work_history'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('respond_io_users.id', ondelete='CASCADE'), nullable=False)
    calendar_event_id = db.Column(db.Integer, db.ForeignKey('respond_io_calendar_events.id', ondelete='SET NULL'))
    
    # Orari effettivi
    actual_start = db.Column(db.DateTime(timezone=True), nullable=False)
    actual_end = db.Column(db.DateTime(timezone=True))
    
    # Orari pianificati (per confronto)
    scheduled_start = db.Column(db.DateTime(timezone=True))
    scheduled_end = db.Column(db.DateTime(timezone=True))
    
    # Metriche di lavoro
    work_duration_minutes = db.Column(db.Integer)
    break_duration_minutes = db.Column(db.Integer, default=0)
    overtime_minutes = db.Column(db.Integer, default=0)
    
    # Statistiche conversazioni
    conversations_handled = db.Column(db.Integer, default=0)
    messages_sent = db.Column(db.Integer, default=0)
    messages_received = db.Column(db.Integer, default=0)
    avg_response_time_seconds = db.Column(db.Float)
    
    # Note e valutazioni
    notes = db.Column(db.Text)
    performance_rating = db.Column(db.Integer)  # 1-5 stelle
    
    # Relazioni
    user = db.relationship('RespondIOUser', backref=db.backref('work_history', lazy='dynamic', cascade='all, delete-orphan'))
    calendar_event = db.relationship('RespondIOCalendarEvent', backref=db.backref('work_records', lazy='dynamic'))
    
    @property
    def actual_duration_minutes(self):
        """Calcola la durata effettiva in minuti"""
        if self.actual_end and self.actual_start:
            return int((self.actual_end - self.actual_start).total_seconds() / 60)
        return 0
    
    @property
    def efficiency_score(self):
        """Calcola un punteggio di efficienza"""
        if self.conversations_handled > 0 and self.actual_duration_minutes > 0:
            return round(self.conversations_handled / (self.actual_duration_minutes / 60), 2)
        return 0
    
    def __repr__(self):
        return f'<WorkHistory {self.id}: {self.user_id} on {self.actual_start}>'


class RespondIOTimeOff(TimestampMixin, db.Model):
    """Gestione ferie e assenze"""
    __tablename__ = 'respond_io_time_off'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('respond_io_users.id', ondelete='CASCADE'), nullable=False)
    
    # Periodo
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Tipo e stato
    type = db.Column(db.String(50), nullable=False)  # holiday, sick, personal, training
    status = db.Column(db.String(50), default='pending')  # pending, approved, rejected, cancelled
    
    # Dettagli
    reason = db.Column(db.Text)
    notes = db.Column(db.Text)
    
    # Approvazione
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime(timezone=True))
    approval_notes = db.Column(db.Text)
    
    # Relazioni
    user = db.relationship('RespondIOUser', backref=db.backref('time_offs', lazy='dynamic', cascade='all, delete-orphan'))
    approved_by = db.relationship('User', backref=db.backref('approved_time_offs', lazy='dynamic'))
    
    @property
    def total_days(self):
        """Calcola i giorni totali di assenza"""
        if self.end_date and self.start_date:
            return (self.end_date - self.start_date).days + 1
        return 0
    
    @property
    def is_active(self):
        """Verifica se l'assenza è attiva oggi"""
        from datetime import date
        today = date.today()
        return self.status == 'approved' and self.start_date <= today <= self.end_date
    
    def overlaps_with(self, start_date, end_date):
        """Verifica se c'è sovrapposizione con un altro periodo"""
        return not (end_date < self.start_date or start_date > self.end_date)
    
    def __repr__(self):
        return f'<TimeOff {self.id}: {self.user_id} {self.type} ({self.start_date} - {self.end_date})>'


class RespondIOWorkTimestamp(TimestampMixin, db.Model):
    """Timbrature dei turni di lavoro"""
    __tablename__ = 'respond_io_work_timestamps'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    user = db.relationship('User', backref=db.backref('work_timestamps', lazy='dynamic'))
    
    # Tipo di timbratura
    timestamp_type = db.Column(db.String(20), nullable=False)  # 'start', 'pause_start', 'pause_end', 'end'
    timestamp = db.Column(db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(pytz.timezone('Europe/Rome')))
    
    # Riferimento all'evento calendario (opzionale)
    calendar_event_id = db.Column(db.Integer, db.ForeignKey('respond_io_calendar_events.id', ondelete='SET NULL'))
    calendar_event = db.relationship('RespondIOCalendarEvent', backref=db.backref('timestamps', lazy='dynamic'))
    
    # Stato attuale del turno
    current_status = db.Column(db.String(20))  # 'working', 'paused', 'ended'
    
    # Note opzionali
    notes = db.Column(db.Text)
    
    @classmethod
    def get_current_status(cls, user_id):
        """Ottiene lo stato attuale del turno per un utente"""
        last_timestamp = cls.query.filter_by(user_id=user_id).filter(
            func.date(cls.timestamp) == date.today()
        ).order_by(cls.timestamp.desc()).first()
        
        if not last_timestamp:
            return 'not_started'
        
        if last_timestamp.timestamp_type == 'end':
            return 'ended'
        elif last_timestamp.timestamp_type == 'pause_start':
            return 'paused'
        elif last_timestamp.timestamp_type in ['start', 'pause_end']:
            return 'working'
        
        return 'not_started'


class RespondIOCalendarBreak(TimestampMixin, db.Model):
    """Pause all'interno dei turni di lavoro"""
    __tablename__ = 'respond_io_calendar_breaks'
    
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey('respond_io_calendar_events.id', ondelete='CASCADE'), nullable=False)
    
    # Orari della pausa
    start_time = db.Column(db.DateTime(timezone=True), nullable=False)
    end_time = db.Column(db.DateTime(timezone=True), nullable=False)
    
    # Note opzionali
    notes = db.Column(db.Text)
    
    # Chi ha creato la pausa
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_by = db.relationship('User', backref=db.backref('created_breaks', lazy='dynamic'))
    
    @property
    def duration_minutes(self):
        """Calcola la durata della pausa in minuti"""
        if self.end_time and self.start_time:
            return int((self.end_time - self.start_time).total_seconds() / 60)
        return 0
    
    def overlaps_with(self, start, end):
        """Verifica se la pausa si sovrappone con un altro periodo"""
        return not (end <= self.start_time or start >= self.end_time)
    
    def is_within_event(self):
        """Verifica se la pausa è all'interno del turno di lavoro"""
        if self.event:
            return (self.start_time >= self.event.start_datetime and 
                    self.end_time <= self.event.end_datetime)
        return False
    
    def to_dict(self):
        """Converte la pausa in dizionario"""
        return {
            'id': self.id,
            'event_id': self.event_id,
            'start': self.start_time.isoformat(),
            'end': self.end_time.isoformat(),
            'duration_minutes': self.duration_minutes,
            'notes': self.notes
        }
    
    def __repr__(self):
        return f'<CalendarBreak {self.id}: {self.start_time} - {self.end_time}>'


# ════════════════════════════════════════════════════════════════════════════
#                          DEVELOPMENT PROJECTS SYSTEM
# ════════════════════════════════════════════════════════════════════════════

class ProjectStatusEnum(str, Enum):
    """Stati del progetto di sviluppo"""
    planning = "planning"           # In fase di pianificazione
    in_progress = "in_progress"     # In sviluppo
    testing = "testing"             # In fase di test
    review = "review"               # In revisione
    completed = "completed"         # Completato
    on_hold = "on_hold"            # In pausa
    cancelled = "cancelled"         # Cancellato


class ProjectPriorityEnum(str, Enum):
    """Priorità del progetto"""
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class MilestoneStatusEnum(str, Enum):
    """Stati delle milestone del progetto"""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    delayed = "delayed"
    cancelled = "cancelled"


class ProjectTypeEnum(str, Enum):
    """Tipologia di progetto"""
    feature = "feature"             # Nuova funzionalità
    improvement = "improvement"     # Miglioramento esistente
    bugfix = "bugfix"              # Correzione bug
    infrastructure = "infrastructure" # Infrastruttura
    integration = "integration"     # Integrazione esterna
    optimization = "optimization"   # Ottimizzazione
    migration = "migration"         # Migrazione


# Registrazione ENUM PostgreSQL per i progetti
for _e in (ProjectStatusEnum, ProjectPriorityEnum, MilestoneStatusEnum, ProjectTypeEnum):
    _pg_enum(_e)


class DevelopmentProject(TimestampMixin, db.Model):
    """
    Progetto di sviluppo aziendale visibile agli admin.
    """
    __tablename__ = "development_projects"
    __versioned__ = {}  # Abilita versioning per tracciare modifiche
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informazioni base
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    objective = db.Column(db.Text, nullable=False)
    
    # Classificazione
    project_type = db.Column(
        _def(ProjectTypeEnum),
        nullable=False,
        default=ProjectTypeEnum.feature
    )
    status = db.Column(
        _def(ProjectStatusEnum),
        nullable=False,
        default=ProjectStatusEnum.planning,
        index=True
    )
    priority = db.Column(
        _def(ProjectPriorityEnum),
        nullable=False,
        default=ProjectPriorityEnum.medium,
        index=True
    )
    
    # Timeline - rimosso, gestito tramite milestone
    
    # Progresso (calcolato dalle milestone)
    progress_percentage = db.Column(
        db.Integer,
        default=0,
        nullable=False,
        server_default="0"
    )
    
    # Assegnazioni
    project_manager_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Dipartimento target
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id"),
        nullable=True,  # NULL = per tutta l'azienda
        index=True
    )
    is_company_wide = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment="True se il progetto è per tutta l'azienda"
    )
    
    # Repository e documentazione
    repository_url = db.Column(db.String(512))
    
    # Metriche - rimosse
    
    # Configurazioni extra
    settings = db.Column(JSONB, default=dict)
    # Tags - rimossi
    
    # Flag
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_visible = db.Column(db.Boolean, default=True, nullable=False)
    requires_approval = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relazioni
    project_manager = db.relationship(
        "User",
        foreign_keys=[project_manager_id],
        backref="managed_dev_projects"
    )
    department = db.relationship(
        "Department",
        backref="development_projects"
    )
    milestones = db.relationship(
        "ProjectMilestone",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectMilestone.order_index, ProjectMilestone.due_date"
    )
    team_members = db.relationship(
        "ProjectTeamMember",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    updates = db.relationship(
        "ProjectUpdate",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="ProjectUpdate.created_at.desc()"
    )
    
    @property
    def is_overdue(self) -> bool:
        """True se il progetto ha milestone in ritardo"""
        if self.status == ProjectStatusEnum.completed:
            return False
        # Controlla se ci sono milestone in ritardo
        for milestone in self.milestones:
            if milestone.is_overdue:
                return True
        return False

    @property
    def days_remaining(self) -> Optional[int]:
        """Giorni rimanenti alla prossima milestone"""
        if self.status == ProjectStatusEnum.completed:
            return None
        # Trova la prossima milestone non completata
        next_milestone = None
        for milestone in self.milestones:
            if milestone.status != MilestoneStatusEnum.completed:
                if not next_milestone or milestone.due_date < next_milestone.due_date:
                    next_milestone = milestone
        if next_milestone:
            delta = next_milestone.due_date - date.today()
            return delta.days
        return None
    
    @property
    def all_milestones_completed(self) -> bool:
        """True se tutte le milestone sono completate"""
        if not self.milestones:
            return False
        for milestone in self.milestones:
            if milestone.status != MilestoneStatusEnum.completed:
                return False
        return True

    @property
    def review_request(self) -> Optional[dict]:
        """Ritorna l'ultima richiesta di review se presente"""
        if self.settings and 'reviews' in self.settings:
            # Trova l'ultima richiesta
            for review in reversed(self.settings['reviews']):
                if review.get('type') == 'request':
                    return review
        # Fallback per compatibilità
        if self.settings and 'review_request' in self.settings:
            return self.settings['review_request']
        return None

    @property
    def review_response(self) -> Optional[dict]:
        """Ritorna l'ultima risposta di review se presente"""
        if self.settings and 'reviews' in self.settings:
            # Trova l'ultima response
            for review in reversed(self.settings['reviews']):
                if review.get('type') == 'response':
                    return review
        # Fallback per compatibilità
        if self.settings and 'review_response' in self.settings:
            return self.settings['review_response']
        return None

    @property
    def has_pending_review(self) -> bool:
        """True se c'è una review in attesa di risposta"""
        if not self.settings or 'reviews' not in self.settings:
            return False

        # Conta richieste e risposte
        requests = sum(1 for r in self.settings['reviews'] if r.get('type') == 'request')
        responses = sum(1 for r in self.settings['reviews'] if r.get('type') == 'response')

        return requests > responses

    @property
    def last_review_approved(self) -> Optional[bool]:
        """Ritorna True se l'ultima review è stata approvata, False se richieste modifiche, None se non c'è review"""
        last_response = self.review_response
        if last_response:
            return last_response.get('approved', False)
        return None

    @property
    def all_reviews(self) -> list:
        """Ritorna tutte le review in ordine cronologico"""
        if self.settings and 'reviews' in self.settings:
            return self.settings['reviews']
        return []

    @property
    def is_on_track(self) -> bool:
        """True se il progetto è nei tempi previsti"""
        if not self.milestones:
            return True
        delayed_milestones = [m for m in self.milestones if m.status == MilestoneStatusEnum.delayed]
        return len(delayed_milestones) == 0
    
    @property
    def completed_milestones_count(self) -> int:
        """Numero di milestone completate"""
        return len([m for m in self.milestones if m.status == MilestoneStatusEnum.completed])
    
    @property
    def total_milestones_count(self) -> int:
        """Numero totale di milestone"""
        return len(self.milestones)
    
    def calculate_progress(self) -> int:
        """Calcola il progresso basato sulle milestone"""
        if not self.milestones:
            return 0
        completed = self.completed_milestones_count
        total = self.total_milestones_count
        return int((completed / total) * 100) if total > 0 else 0
    
    def __repr__(self):
        return f"<DevelopmentProject {self.name!r} ({self.status.value})>"


class ProjectMilestone(TimestampMixin, db.Model):
    """
    Milestone/Step di un progetto di sviluppo.
    """
    __tablename__ = "project_milestones"
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("development_projects.id"),
        nullable=False,
        index=True
    )
    
    # Informazioni milestone
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    
    # Timeline
    due_date = db.Column(db.Date, nullable=False)
    completed_date = db.Column(db.Date)
    
    # Stato e progresso
    status = db.Column(
        _def(MilestoneStatusEnum),
        nullable=False,
        default=MilestoneStatusEnum.pending
    )
    progress_percentage = db.Column(db.Integer, default=0, nullable=False)
    
    # Ordinamento
    order_index = db.Column(db.Integer, default=0, nullable=False)
    
    # Responsabile
    assignee_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )
    
    # Deliverables e criteri di successo
    deliverables = db.Column(JSONB, default=list)  # ["API completata", "Documentazione"]
    success_criteria = db.Column(JSONB, default=list)  # ["Test superati", "Code review"]
    
    # Note e blockers
    notes = db.Column(db.Text)
    blockers = db.Column(JSONB, default=list)  # ["In attesa approvazione", "Dipende da X"]
    
    # Relazioni
    project = db.relationship("DevelopmentProject", back_populates="milestones")
    assignee = db.relationship("User", backref="assigned_project_milestones")
    
    @property
    def is_overdue(self) -> bool:
        """True se la milestone è in ritardo"""
        if self.status == MilestoneStatusEnum.completed:
            return False
        return date.today() > self.due_date
    
    @property
    def days_until_due(self) -> Optional[int]:
        """Giorni alla scadenza"""
        if self.status == MilestoneStatusEnum.completed:
            return None
        delta = self.due_date - date.today()
        return delta.days
    
    def __repr__(self):
        return f"<ProjectMilestone {self.name!r} ({self.status.value})>"


class ProjectTeamMember(TimestampMixin, db.Model):
    """
    Membro del team di progetto.
    """
    __tablename__ = "project_team_members"
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("development_projects.id"),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Ruolo nel progetto
    role = db.Column(
        db.String(100),
        nullable=False,
        default="Developer"
    )  # "Lead Developer", "Backend", "Frontend", "Tester", "Designer"
    
    # Allocazione
    allocation_percentage = db.Column(
        db.Integer,
        default=100,
        nullable=False,
        comment="Percentuale di tempo allocata al progetto"
    )
    
    # Date partecipazione
    joined_date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    left_date = db.Column(db.Date)
    
    # Performance
    tasks_assigned = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    hours_logged = db.Column(db.Integer, default=0)
    
    # Flag
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relazioni
    project = db.relationship("DevelopmentProject", back_populates="team_members")
    user = db.relationship("User", backref="dev_project_memberships")
    
    __table_args__ = (
        db.UniqueConstraint('project_id', 'user_id', name='_dev_project_user_uc'),
    )
    
    def __repr__(self):
        return f"<ProjectTeamMember {self.user_id} in {self.project_id}>"


class ProjectUpdate(TimestampMixin, db.Model):
    """
    Aggiornamento/Log di un progetto di sviluppo.
    """
    __tablename__ = "project_updates"
    
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(
        db.Integer,
        db.ForeignKey("development_projects.id"),
        nullable=False,
        index=True
    )
    
    # Autore dell'aggiornamento
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Tipo di aggiornamento
    update_type = db.Column(
        db.String(50),
        nullable=False,
        default="progress"
    )  # "progress", "milestone", "blocker", "completion", "status_change"
    
    # Contenuto
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    
    # Dati strutturati (per automazioni)
    data = db.Column(JSONB, default=dict)
    # Es: {"old_status": "planning", "new_status": "in_progress"}
    #     {"milestone_id": 5, "milestone_name": "API Complete"}
    
    # Visibilità
    is_public = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        comment="False per aggiornamenti solo per admin"
    )
    
    # Flag importante
    is_important = db.Column(db.Boolean, default=False, nullable=False)
    
    # Relazioni
    project = db.relationship("DevelopmentProject", back_populates="updates")
    author = db.relationship("User", backref="project_updates_authored")
    
    def __repr__(self):
        return f"<ProjectUpdate {self.title!r} by {self.author_id}>"



# ═══════════════════════════════════════════════════════════════════════════
#                           KNOWLEDGE BASE MODELS
# ═══════════════════════════════════════════════════════════════════════════

class KBCategory(TimestampMixin, db.Model):
    """
    Categorie gerarchiche per organizzare documenti per dipartimento.
    Supporta sottocategorie infinite con struttura ad albero.
    """
    __tablename__ = 'kb_categories'
    __table_args__ = (
        Index('ix_kb_categories_dept_parent', 'department_id', 'parent_id'),
        Index('ix_kb_categories_slug', 'slug'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer, 
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Gerarchia
    parent_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_categories.id', ondelete='CASCADE'),
        nullable=True
    )
    
    # Dati categoria
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Icona FontAwesome o simile
    color = db.Column(db.String(7))  # Colore HEX
    
    # Ordinamento
    order_index = db.Column(db.Integer, default=0)
    
    # Metadata
    is_active = db.Column(db.Boolean, default=True)
    articles_count = db.Column(db.Integer, default=0)  # Cache conteggio articoli
    
    # Relazioni
    department = db.relationship('Department', backref='kb_categories')
    parent = db.relationship('KBCategory', remote_side=[id], backref='subcategories')
    articles = db.relationship(
        'KBArticle', 
        back_populates='category',
        cascade='all, delete-orphan'
    )
    
    @property
    def full_path(self) -> str:
        """Ritorna il percorso completo della categoria"""
        if self.parent:
            return f"{self.parent.full_path} / {self.name}"
        return self.name
    
    @property
    def level(self) -> int:
        """Ritorna il livello di profondità nella gerarchia"""
        if self.parent:
            return self.parent.level + 1
        return 0
    
    def __repr__(self):
        return f'<KBCategory {self.name} - Dept: {self.department_id}>'


class KBArticle(TimestampMixin, db.Model):
    """
    Articoli/Documenti della Knowledge Base.
    Supporta versioning, rich content, allegati multipli.
    """
    __tablename__ = 'kb_articles'
    __versioned__ = {}  # Abilita versioning SQLAlchemy-Continuum
    # Gli indici sono definiti nella migrazione 450fc9906d6f_aggiunta_modulo_knowledge_base.py
    # Non duplicarli qui per evitare conflitti durante il setup
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_categories.id', ondelete='SET NULL'),
        nullable=True
    )
    
    # Autore
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False
    )
    last_editor_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Contenuto
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(300), nullable=False, unique=True)
    summary = db.Column(db.Text)  # Breve descrizione
    content = db.Column(db.Text, nullable=False)  # HTML content dal WYSIWYG
    
    # Metadata
    status = db.Column(
        _def(KBDocumentStatusEnum),
        default=KBDocumentStatusEnum.draft,
        nullable=False,
        index=True
    )
    visibility = db.Column(
        _def(KBVisibilityEnum),
        default=KBVisibilityEnum.department,
        nullable=False,
        index=True
    )
    
    # SEO & Search
    meta_keywords = db.Column(db.String(255))
    tags = db.Column(JSONB, default=list)  # ["tag1", "tag2", ...]
    
    # Statistiche
    views_count = db.Column(db.Integer, default=0)
    likes_count = db.Column(db.Integer, default=0)
    downloads_count = db.Column(db.Integer, default=0)
    
    # Date importanti
    published_at = db.Column(db.DateTime)
    last_reviewed_at = db.Column(db.DateTime)
    expires_at = db.Column(db.DateTime)  # Data scadenza contenuto
    
    # Opzioni
    is_featured = db.Column(db.Boolean, default=False)  # In evidenza
    is_pinned = db.Column(db.Boolean, default=False)    # Fissato in alto
    allow_comments = db.Column(db.Boolean, default=True)
    require_acknowledgment = db.Column(db.Boolean, default=False)  # Richiede conferma lettura
    
    # Template custom (per documenti speciali)
    template_type = db.Column(db.String(50))  # 'standard', 'faq', 'guide', 'policy'
    
    # Full-text search
    search_vector = db.Column(TSVECTOR)
    __ts_vector__ = TSVectorType(
        'title', 'summary', 'content',
        regconfig='italian',
        weights={'title': 'A', 'summary': 'B', 'content': 'C'}
    )
    
    # Relazioni
    department = db.relationship('Department', backref='kb_articles')
    category = db.relationship('KBCategory', back_populates='articles')
    author = db.relationship('User', foreign_keys=[author_id], backref='kb_articles_created')
    last_editor = db.relationship('User', foreign_keys=[last_editor_id])
    
    attachments = db.relationship(
        'KBAttachment',
        back_populates='article',
        cascade='all, delete-orphan',
        order_by='KBAttachment.order_index'
    )
    
    analytics = db.relationship(
        'KBAnalytics',
        back_populates='article',
        uselist=False,
        cascade='all, delete-orphan'
    )
    
    comments = db.relationship(
        'KBComment',
        back_populates='article',
        cascade='all, delete-orphan',
        order_by='KBComment.created_at.desc()'
    )
    
    @property
    def is_outdated(self) -> bool:
        """Verifica se il documento è obsoleto (>6 mesi dall'ultimo aggiornamento)"""
        if not self.updated_at:
            return False
        return (datetime.utcnow() - self.updated_at).days > 180
    
    @property
    def read_time_minutes(self) -> int:
        """Stima tempo di lettura in minuti"""
        if not self.content:
            return 0
        word_count = len(self.content.split())
        return max(1, word_count // 200)  # ~200 parole al minuto
    
    def can_view(self, user: User) -> bool:
        """Verifica se un utente può vedere questo articolo"""
        if user.is_admin:
            return True

        if self.status != KBDocumentStatusEnum.published:
            # Solo autore può vedere articoli non pubblicati
            return user.id == self.author_id

        # NOTA: department-based visibility semplificata - ora tutti vedono
        if self.visibility == KBVisibilityEnum.company:
            return True
        elif self.visibility == KBVisibilityEnum.department:
            # Senza department_id su User, permettiamo a tutti
            return True
        elif self.visibility == KBVisibilityEnum.only_heads:
            # Controlla se utente guida un department
            return len(user.departments_led) > 0

        return False

    def can_edit(self, user: User) -> bool:
        """Verifica se un utente può modificare questo articolo"""
        if user.is_admin:
            return True

        # L'autore può sempre modificare
        if user.id == self.author_id:
            return True

        return False
    
    def __repr__(self):
        return f'<KBArticle {self.title} - Status: {self.status}>'


class KBAttachment(TimestampMixin, db.Model):
    """
    Allegati per articoli KB (immagini, PDF, audio, video).
    Gestisce upload sicuri e quota storage.
    """
    __tablename__ = 'kb_attachments'
    __table_args__ = (
        CheckConstraint('file_size > 0', name='check_positive_file_size'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # File info
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(512), nullable=False, unique=True)
    file_size = db.Column(db.BigInteger, nullable=False)  # in bytes
    mime_type = db.Column(db.String(100), nullable=False)
    
    # Metadata
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    alt_text = db.Column(db.String(255))  # Per accessibilità immagini
    
    # Tipo e ordinamento
    attachment_type = db.Column(db.String(50))  # 'image', 'document', 'video', 'audio'
    order_index = db.Column(db.Integer, default=0)
    
    # Thumbnail (per immagini/video)
    thumbnail_path = db.Column(db.String(512))
    
    # Upload info
    uploaded_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Download tracking
    downloads_count = db.Column(db.Integer, default=0)
    
    # Relazioni
    article = db.relationship('KBArticle', back_populates='attachments')
    uploaded_by = db.relationship('User')
    
    @property
    def file_extension(self) -> str:
        """Estensione del file"""
        return os.path.splitext(self.filename)[1].lower()
    
    @property
    def is_image(self) -> bool:
        """Verifica se è un'immagine"""
        return self.file_extension in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg']
    
    @property
    def is_document(self) -> bool:
        """Verifica se è un documento"""
        return self.file_extension in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']
    
    @property
    def size_formatted(self) -> str:
        """Dimensione formattata human-readable"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def __repr__(self):
        return f'<KBAttachment {self.filename} - Article: {self.article_id}>'


class KBDepartmentQuota(TimestampMixin, db.Model):
    """
    Gestione quota storage per dipartimento (2GB default).
    Traccia utilizzo e limiti.
    """
    __tablename__ = 'kb_department_quotas'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Quota (in bytes)
    quota_bytes = db.Column(db.BigInteger, nullable=False, default=2147483648)  # 2GB default
    used_bytes = db.Column(db.BigInteger, nullable=False, default=0)
    
    # Alert thresholds
    warning_threshold = db.Column(db.Integer, default=80)  # Alert a 80%
    critical_threshold = db.Column(db.Integer, default=95)  # Critical a 95%
    
    # Statistiche
    files_count = db.Column(db.Integer, default=0)
    last_cleanup_at = db.Column(db.DateTime)
    
    # Relazioni
    department = db.relationship('Department', backref=db.backref('kb_quota', uselist=False))
    
    @property
    def quota_gb(self) -> float:
        """Quota in GB"""
        return self.quota_bytes / (1024 ** 3)
    
    @property
    def used_gb(self) -> float:
        """Spazio usato in GB"""
        return self.used_bytes / (1024 ** 3)
    
    @property
    def available_bytes(self) -> int:
        """Spazio disponibile in bytes"""
        return max(0, self.quota_bytes - self.used_bytes)
    
    @property
    def usage_percentage(self) -> float:
        """Percentuale di utilizzo"""
        if self.quota_bytes == 0:
            return 0
        return (self.used_bytes / self.quota_bytes) * 100
    
    @property
    def is_warning(self) -> bool:
        """True se superata soglia warning"""
        return self.usage_percentage >= self.warning_threshold
    
    @property
    def is_critical(self) -> bool:
        """True se superata soglia critica"""
        return self.usage_percentage >= self.critical_threshold
    
    def can_upload(self, file_size: int) -> bool:
        """Verifica se c'è spazio per un nuovo upload"""
        return (self.used_bytes + file_size) <= self.quota_bytes
    
    def update_usage(self, delta_bytes: int):
        """Aggiorna l'utilizzo dello storage"""
        self.used_bytes = max(0, self.used_bytes + delta_bytes)
        if delta_bytes > 0:
            self.files_count += 1
        elif delta_bytes < 0:
            self.files_count = max(0, self.files_count - 1)
    
    def __repr__(self):
        return f'<KBDepartmentQuota Dept: {self.department_id} - Used: {self.used_gb:.2f}/{self.quota_gb:.2f}GB>'


class KBAnalytics(TimestampMixin, db.Model):
    """
    Analytics dettagliati per ogni articolo.
    Aggiornati in real-time per dashboard HEAD.
    """
    __tablename__ = 'kb_analytics'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True
    )
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Metriche visualizzazioni
    views_count = db.Column(db.Integer, default=0)
    unique_viewers = db.Column(db.Integer, default=0)
    avg_read_time = db.Column(db.Integer, default=0)  # secondi
    completion_rate = db.Column(db.Float, default=0)  # % di lettura completa
    
    # Metriche engagement
    downloads_count = db.Column(db.Integer, default=0)
    shares_count = db.Column(db.Integer, default=0)
    bookmarks_count = db.Column(db.Integer, default=0)
    comments_count = db.Column(db.Integer, default=0)
    
    # Feedback
    helpful_votes = db.Column(db.Integer, default=0)
    not_helpful_votes = db.Column(db.Integer, default=0)
    
    # Search metrics
    search_appearances = db.Column(db.Integer, default=0)
    search_clicks = db.Column(db.Integer, default=0)
    
    # Performance
    avg_load_time = db.Column(db.Float)  # millisecondi
    bounce_rate = db.Column(db.Float, default=0)
    
    # Top referrers
    top_referrers = db.Column(JSONB, default=list)  # [{"source": "search", "count": 123}, ...]
    
    # Dispositivi
    device_stats = db.Column(JSONB, default=dict)  # {"desktop": 60, "mobile": 35, "tablet": 5}
    
    # Orari di punta
    peak_hours = db.Column(JSONB, default=dict)  # {"09": 45, "10": 67, ...}
    
    # Relazioni
    article = db.relationship('KBArticle', back_populates='analytics')
    department = db.relationship('Department')
    
    @property
    def satisfaction_score(self) -> float:
        """Calcola score di soddisfazione (0-100)"""
        total_votes = self.helpful_votes + self.not_helpful_votes
        if total_votes == 0:
            return 0
        return (self.helpful_votes / total_votes) * 100
    
    @property
    def engagement_score(self) -> float:
        """Calcola score di engagement (0-100)"""
        if self.views_count == 0:
            return 0
        
        engagement_actions = (
            self.downloads_count + 
            self.shares_count + 
            self.bookmarks_count + 
            self.comments_count
        )
        return min(100, (engagement_actions / self.views_count) * 100)
    
    def __repr__(self):
        return f'<KBAnalytics Article: {self.article_id} - Views: {self.views_count}>'


class KBActivityLog(TimestampMixin, db.Model):
    """
    Log dettagliato di tutte le azioni nella KB.
    Per audit trail e analytics.
    """
    __tablename__ = 'kb_activity_logs'
    __table_args__ = (
        Index('ix_kb_activity_logs_dept_date', 'department_id', 'created_at'),
        Index('ix_kb_activity_logs_user_action', 'user_id', 'action'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='SET NULL')
    )
    
    # Azione
    action = db.Column(
        _def(KBActionTypeEnum),
        nullable=False,
        index=True
    )
    
    # Dettagli
    details = db.Column(JSONB, default=dict)
    search_query = db.Column(db.String(255))  # Per azioni di ricerca
    
    # Context
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))
    referrer = db.Column(db.String(500))
    
    # Performance
    response_time_ms = db.Column(db.Integer)  # Tempo di risposta in ms
    
    # Session
    session_id = db.Column(db.String(100))
    
    # Relazioni
    department = db.relationship('Department')
    user = db.relationship('User')
    article = db.relationship('KBArticle')
    
    def __repr__(self):
        return f'<KBActivityLog {self.action} by User: {self.user_id}>'


class KBDepartmentAlert(TimestampMixin, db.Model):
    """
    Alert automatici per HEAD di dipartimento.
    Monitora problemi e opportunità.
    """
    __tablename__ = 'kb_department_alerts'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Alert info
    alert_type = db.Column(
        _def(KBAlertTypeEnum),
        nullable=False,
        index=True
    )
    
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    severity = db.Column(db.String(20), nullable=False)  # 'info', 'warning', 'critical'
    
    # Dati aggiuntivi
    alert_metadata = db.Column(JSONB, default=dict)
    action_url = db.Column(db.String(255))  # Link per risolvere
    
    # Stato
    is_read = db.Column(db.Boolean, default=False)
    is_resolved = db.Column(db.Boolean, default=False)
    resolved_at = db.Column(db.DateTime)
    resolved_by_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Auto-dismiss
    auto_dismiss_at = db.Column(db.DateTime)
    
    # Relazioni
    department = db.relationship('Department')
    resolved_by = db.relationship('User')
    
    @property
    def is_expired(self) -> bool:
        """Verifica se l'alert è scaduto"""
        if self.auto_dismiss_at:
            return datetime.utcnow() > self.auto_dismiss_at
        return False
    
    @property
    def severity_class(self) -> str:
        """Classe CSS per severity"""
        return {
            'info': 'alert-info',
            'warning': 'alert-warning', 
            'critical': 'alert-danger'
        }.get(self.severity, 'alert-secondary')
    
    def __repr__(self):
        return f'<KBDepartmentAlert {self.alert_type} - Dept: {self.department_id}>'


class KBBookmark(TimestampMixin, db.Model):
    """
    Preferiti/Segnalibri degli utenti per accesso rapido.
    """
    __tablename__ = 'kb_bookmarks'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'article_id', name='unique_user_article_bookmark'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    
    # Note personali
    notes = db.Column(db.Text)
    
    # Relazioni
    user = db.relationship('User', backref='kb_bookmarks')
    article = db.relationship('KBArticle', backref='bookmarks')
    
    def __repr__(self):
        return f'<KBBookmark User: {self.user_id} - Article: {self.article_id}>'


class KBArticleView(TimestampMixin, db.Model):
    """
    Tracciamento dettagliato visualizzazioni per analytics avanzati.
    """
    __tablename__ = 'kb_article_views'
    __table_args__ = (
        Index('ix_kb_article_views_article_date', 'article_id', 'viewed_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Timing
    viewed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    time_spent_seconds = db.Column(db.Integer)
    scroll_depth = db.Column(db.Integer)  # % di pagina vista
    
    # Context
    referrer_type = db.Column(db.String(50))  # 'search', 'direct', 'internal'
    search_query = db.Column(db.String(255))
    
    # Device
    device_type = db.Column(db.String(20))  # 'desktop', 'mobile', 'tablet'
    browser = db.Column(db.String(50))
    
    # Session
    session_id = db.Column(db.String(100))
    is_bounce = db.Column(db.Boolean, default=False)
    
    # Relazioni
    article = db.relationship('KBArticle')
    user = db.relationship('User')
    
    def __repr__(self):
        return f'<KBArticleView Article: {self.article_id} at {self.viewed_at}>'


class KBSearchLog(TimestampMixin, db.Model):
    """
    Log delle ricerche per migliorare risultati e identificare gap.
    """
    __tablename__ = 'kb_search_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='SET NULL')
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL')
    )
    
    # Ricerca
    query = db.Column(db.String(255), nullable=False, index=True)
    results_count = db.Column(db.Integer, default=0)
    clicked_result_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='SET NULL')
    )
    clicked_position = db.Column(db.Integer)  # Posizione del risultato cliccato
    
    # Performance
    search_time_ms = db.Column(db.Integer)
    
    # Relazioni
    department = db.relationship('Department')
    user = db.relationship('User')
    clicked_article = db.relationship('KBArticle')
    
    def __repr__(self):
        return f'<KBSearchLog "{self.query}" - Results: {self.results_count}>'


class KBComment(TimestampMixin, db.Model):
    """
    Commenti per gli articoli della Knowledge Base.
    """
    __tablename__ = 'kb_comments'
    
    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False
    )
    
    # Contenuto
    content = db.Column(db.Text, nullable=False)
    
    # Stato
    is_active = db.Column(db.Boolean, default=True)
    is_edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime)
    
    # Relazioni
    article = db.relationship('KBArticle', back_populates='comments')
    author = db.relationship('User')
    
    def __repr__(self):
        return f'<KBComment Article:{self.article_id} by User:{self.author_id}>'


class KBAcknowledgment(TimestampMixin, db.Model):
    """
    Conferme di lettura per articoli che richiedono acknowledgment.
    """
    __tablename__ = 'kb_acknowledgments'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(
        db.Integer,
        db.ForeignKey('kb_articles.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False
    )

    # Data conferma
    acknowledged_at = db.Column(db.DateTime, nullable=False, default=db.func.now())

    # Relazioni
    article = db.relationship('KBArticle', backref='acknowledgments')
    user = db.relationship('User')

    # Constraint: un utente può confermare un articolo una sola volta
    __table_args__ = (
        db.UniqueConstraint('article_id', 'user_id', name='unique_article_user_acknowledgment'),
    )

    def __repr__(self):
        return f'<KBAcknowledgment Article:{self.article_id} User:{self.user_id}>'


# ===================== FINANCE MODELS =====================

class Package(TimestampMixin, db.Model):
    """
    Modello per i pacchetti con calcolo automatico di costi e marginalità.
    """
    __tablename__ = 'finance_packages'
    __table_args__ = (
        db.UniqueConstraint('name', 'listino_type', name='uq_package_name_listino'),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Informazioni base
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)

    # Tipo listino (vecchio/nuovo)
    listino_type = db.Column(db.String(20), nullable=False, default='vecchio')
    
    # Prezzi e costi (in EUR)
    price = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Prezzo di vendita
    
    # Costi mensili per professionista
    nutritionist_cost_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Costo nutrizionista/mese
    coach_cost_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Costo coach/mese  
    psychologist_cost_monthly = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Costo psicologa/mese
    
    # Durata pacchetto in mesi (per calcolo costi totali)
    duration_months = db.Column(db.Integer, nullable=False, default=1)
    
    # Percentuale commissione sales (per calcolo netto post sales)
    sales_commission_percent = db.Column(db.Numeric(5, 2), nullable=False, default=10)  # Default 10%
    
    # Note aggiuntive
    notes = db.Column(db.Text)
    
    @property
    def total_costs(self):
        """Calcola il totale dei costi per la durata del pacchetto."""
        monthly_costs = (
            (self.nutritionist_cost_monthly or 0) +
            (self.coach_cost_monthly or 0) +
            (self.psychologist_cost_monthly or 0)
        )
        return monthly_costs * (self.duration_months or 1)
    
    @property
    def margin(self):
        """Calcola la marginalità (prezzo - costi totali)."""
        return (self.price or 0) - self.total_costs
    
    @property
    def margin_percent(self):
        """Calcola la marginalità percentuale."""
        if self.price and self.price > 0:
            return (self.margin / self.price) * 100
        return Decimal(0)
    
    @property
    def sales_commission_amount(self):
        """Calcola l'importo della commissione sales."""
        if self.price and self.sales_commission_percent:
            return (self.price * self.sales_commission_percent) / 100
        return Decimal(0)
    
    @property
    def margin_post_sales(self):
        """Calcola il margine dopo la commissione sales."""
        return self.margin - self.sales_commission_amount
    
    @property
    def margin_post_sales_percent(self):
        """Calcola la marginalità percentuale post sales."""
        if self.price and self.price > 0:
            return (self.margin_post_sales / self.price) * 100
        return Decimal(0)
    
    @property
    def net_post_sales(self):
        """Calcola il netto post sales (prezzo - commissione sales)."""
        return (self.price or 0) - self.sales_commission_amount
    
    def to_dict(self):
        """Serializza il modello per API/JSON."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'listino_type': self.listino_type,
            'price': float(self.price or 0),
            'duration_months': self.duration_months,
            'nutritionist_cost_monthly': float(self.nutritionist_cost_monthly or 0),
            'coach_cost_monthly': float(self.coach_cost_monthly or 0),
            'psychologist_cost_monthly': float(self.psychologist_cost_monthly or 0),
            'sales_commission_percent': float(self.sales_commission_percent or 0),
            'total_costs': float(self.total_costs),
            'margin': float(self.margin),
            'margin_percent': float(self.margin_percent),
            'sales_commission_amount': float(self.sales_commission_amount),
            'margin_post_sales': float(self.margin_post_sales),
            'margin_post_sales_percent': float(self.margin_post_sales_percent),
            'net_post_sales': float(self.net_post_sales),
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Package {self.name}: €{self.price} - Margine: €{self.margin}>'


# ===================== FINANCE CLIENT MODELS =====================

class ClienteSubscription(TimestampMixin, db.Model):
    """
    Abbonamenti/Sottoscrizioni dei clienti
    """
    __tablename__ = 'cliente_subscriptions'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    package_id = db.Column(db.Integer, db.ForeignKey('finance_packages.id'))
    
    # Date
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    sale_date = db.Column(db.Date)
    
    # Importi
    initial_payment = db.Column(db.Numeric(10, 2))  # Deposito iniziale
    total_amount = db.Column(db.Numeric(10, 2))     # Importo totale abbonamento
    monthly_amount = db.Column(db.Numeric(10, 2))   # Importo mensile calcolato
    
    # Stato
    status = db.Column(db.String(20), default='active')  # active, expired, renewed
    renewed_to_id = db.Column(db.Integer, db.ForeignKey('cliente_subscriptions.id'))
    
    # Relazioni
    cliente = db.relationship('Cliente', backref='subscriptions')
    package = db.relationship('Package', backref='subscriptions')
    renewed_to = db.relationship('ClienteSubscription', remote_side=[id])
    
    # Snapshot mensili
    monthly_snapshots = db.relationship('ClienteMonthlySnapshot', back_populates='subscription', cascade='all, delete-orphan')
    
    @property
    def duration_months(self):
        """Calcola durata in mesi"""
        if self.start_date and self.end_date:
            return ((self.end_date.year - self.start_date.year) * 12 + 
                    self.end_date.month - self.start_date.month + 1)
        return 0
    
    def __repr__(self):
        return f'<ClienteSubscription {self.cliente_id} - {self.package.name if self.package else "No Package"}>'


class ClienteMonthlySnapshot(TimestampMixin, db.Model):
    """
    Snapshot mensile per tracking finanziario
    """
    __tablename__ = 'cliente_monthly_snapshots'
    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'month', name='_cliente_month_uc'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('cliente_subscriptions.id'))
    
    # Periodo
    month = db.Column(db.Date, nullable=False)  # Primo del mese
    month_number = db.Column(db.Integer)        # Progressivo dal primo mese
    
    # Pacchetto attivo nel mese
    package_id = db.Column(db.Integer, db.ForeignKey('finance_packages.id'))
    
    # Commissioni
    comm_payment = db.Column(db.Numeric(10, 2))   # Commissione pagamento (manuale)
    comm_sales = db.Column(db.Numeric(10, 2))     # Commissione sales (10% primo mese)
    comm_setter = db.Column(db.Numeric(10, 2))    # Commissione setter (10€ primo mese)
    comm_coach = db.Column(db.Numeric(10, 2))     # Costo coach dal pacchetto
    comm_nutriz = db.Column(db.Numeric(10, 2))    # Costo nutrizionista dal pacchetto
    comm_psic = db.Column(db.Numeric(10, 2))      # Costo psicologa dal pacchetto
    
    # Calcolati
    monthly_revenue = db.Column(db.Numeric(10, 2))  # Ricavo mensile
    monthly_cost = db.Column(db.Numeric(10, 2))     # Costo totale mensile
    monthly_profit = db.Column(db.Numeric(10, 2))   # Profitto mensile
    
    # LTV progressivi
    ltv_cumulative = db.Column(db.Numeric(10, 2))   # LTV cumulativo
    ltgp_cumulative = db.Column(db.Numeric(10, 2))  # LTGP cumulativo
    
    # Relazioni
    cliente = db.relationship('Cliente', backref='monthly_snapshots')
    subscription = db.relationship('ClienteSubscription', back_populates='monthly_snapshots')
    package = db.relationship('Package')
    
    def calculate_monthly_cost(self):
        """Calcola costo totale mensile"""
        total = Decimal('0')
        if self.comm_payment: total += self.comm_payment
        if self.comm_sales: total += self.comm_sales
        if self.comm_setter: total += self.comm_setter
        if self.comm_coach: total += self.comm_coach
        if self.comm_nutriz: total += self.comm_nutriz
        if self.comm_psic: total += self.comm_psic
        return total
    
    def __repr__(self):
        return f'<MonthlySnapshot Cliente:{self.cliente_id} Month:{self.month}>'


class ClientePackageChange(TimestampMixin, db.Model):
    """
    Tracking cambi pacchetto
    """
    __tablename__ = 'cliente_package_changes'
    
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    subscription_id = db.Column(db.Integer, db.ForeignKey('cliente_subscriptions.id'))
    
    from_package_id = db.Column(db.Integer, db.ForeignKey('finance_packages.id'))
    to_package_id = db.Column(db.Integer, db.ForeignKey('finance_packages.id'))
    
    change_date = db.Column(db.Date, nullable=False)
    change_reason = db.Column(db.Text)
    
    # Relazioni
    cliente = db.relationship('Cliente', backref='package_changes')
    subscription = db.relationship('ClienteSubscription', backref='package_changes')
    from_package = db.relationship('Package', foreign_keys=[from_package_id])
    to_package = db.relationship('Package', foreign_keys=[to_package_id])
    
    def __repr__(self):
        return f'<PackageChange Cliente:{self.cliente_id} Date:{self.change_date}>'


# ─────────────────────────  PAGAMENTI INTERNI  ────────────────────────── #

class PagamentoInterno(TimestampMixin, db.Model):
    """
    Pagamenti interni per clienti (servizi acquistati, rinnovi, etc).
    Traccia tutte le transazioni economiche relative ai clienti.
    """
    __tablename__ = "pagamenti_interni"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # FK Cliente
    cliente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("clienti.cliente_id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Dati pagamento
    importo = db.Column(db.Numeric(10, 2), nullable=False)
    data_pagamento = db.Column(db.Date, nullable=False)
    metodo_pagamento = db.Column(_def(PagamentoEnum), nullable=True)

    # Dettagli servizio
    servizio_acquistato = db.Column(db.String(255), nullable=True)
    sotto_categoria = db.Column(db.String(20), nullable=True)  # Upgrade/Downgrade per Rinnovo e Promo Natale
    attribuibile_a = db.Column(_def(AttribuibileAEnum), nullable=True)  # A chi è attribuibile il rinnovo
    pacchetto_id = db.Column(db.Integer, db.ForeignKey("finance_packages.id"), nullable=True)
    durata = db.Column(db.String(50), nullable=True)

    # Info aggiuntive
    contabile = db.Column(db.String(255), nullable=True)
    note = db.Column(db.Text, nullable=True)

    # Status
    status = db.Column(
        _def(PagamentoInternoStatusEnum),
        nullable=False,
        default=PagamentoInternoStatusEnum.completato,
        index=True
    )

    # Chi ha creato
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relazioni
    cliente = db.relationship("Cliente", backref=db.backref("pagamenti_interni", lazy="dynamic"))
    pacchetto = db.relationship("Package", foreign_keys=[pacchetto_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    def __repr__(self):
        return f"<PagamentoInterno {self.id} cliente={self.cliente_id} €{self.importo}>"


class PagamentoInternoApprovazione(TimestampMixin, db.Model):
    """
    Gestione dell'approvazione dei pagamenti interni.
    Permette di specificare il tipo di pagamento e gestire l'approvazione con costi.
    """
    __tablename__ = "pagamenti_interni_approvazione"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # FK Pagamento Interno (1:1)
    pagamento_interno_id = db.Column(
        db.Integer,
        db.ForeignKey("pagamenti_interni.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True
    )

    # Tipo di Pagamento
    tipo_pagamento = db.Column(_def(TipoPagamentoInternoEnum), nullable=False)

    # Costi
    costo_delivery = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    costo_transazione = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Costi Professionisti
    costo_nutrizionista = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    costo_coach = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    costo_psicologo = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # Stato Approvazione
    stato_approvazione = db.Column(
        db.String(20),
        nullable=False,
        default="in_attesa",
        index=True
    )

    # Note
    note_approvazione = db.Column(db.Text, nullable=True)

    # Approvato/Rifiutato da
    approvato_da_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    data_approvazione = db.Column(db.DateTime, nullable=True)

    # Relazioni
    pagamento_interno = db.relationship(
        "PagamentoInterno",
        backref=db.backref("approvazione", uselist=False)
    )
    approvato_da = db.relationship("User", foreign_keys=[approvato_da_id])

    @property
    def importo_totale(self):
        """Calcola l'importo totale considerando i costi."""
        base = float(self.pagamento_interno.importo) if self.pagamento_interno else 0
        costi = float(self.costo_nutrizionista or 0) + float(self.costo_coach or 0) + \
                float(self.costo_psicologo or 0) + float(self.costo_transazione or 0)
        return base - costi

    def __repr__(self):
        return f"<PagamentoInternoApprovazione {self.id} stato={self.stato_approvazione}>"


# ─────────────────────────  PAGAMENTI TEAM  ────────────────────────── #

class TeamPayment(TimestampMixin, db.Model):
    """
    Pagamenti per i membri del team (fatture collaboratori).
    Traccia le fatture dei collaboratori con importo fisso e bonus.
    """
    __tablename__ = "team_payments"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # FK User (membro del team)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Dati fattura
    data_emissione = db.Column(db.Date, nullable=False)
    totale_fisso = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    totale_bonus = db.Column(db.Numeric(10, 2), nullable=False, default=0)

    # PDF fattura
    fattura_path = db.Column(db.String(500), nullable=True)
    fattura_filename = db.Column(db.String(255), nullable=True)

    # Numero fattura (opzionale)
    numero_fattura = db.Column(db.String(100), nullable=True)

    # Note
    note = db.Column(db.Text, nullable=True)

    # Status approvazione
    stato = db.Column(
        _def(TeamPaymentStatusEnum),
        nullable=False,
        default=TeamPaymentStatusEnum.da_valutare,
        index=True
    )

    # Approvazione
    approvato_da_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    data_approvazione = db.Column(db.DateTime, nullable=True)
    note_approvazione = db.Column(db.Text, nullable=True)

    # Chi ha creato
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relazioni
    user = db.relationship(
        "User",
        foreign_keys=[user_id],
        backref=db.backref("team_payments", lazy="dynamic")
    )
    approvato_da = db.relationship("User", foreign_keys=[approvato_da_id])
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    @property
    def totale(self):
        """Calcola il totale (fisso + bonus)."""
        return float(self.totale_fisso or 0) + float(self.totale_bonus or 0)

    def __repr__(self):
        return f"<TeamPayment {self.id} user={self.user_id} €{self.totale}>"


class UnmatchedFinanceClient(TimestampMixin, db.Model):
    """
    Clienti dall'Excel non ancora associati a clienti nel DB
    """
    __tablename__ = 'unmatched_finance_clients'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Dati dall'Excel
    excel_name = db.Column(db.String(255), nullable=False)
    excel_row_count = db.Column(db.Integer)  # Numero di righe nell'Excel
    
    # Dati finanziari aggregati
    total_ltv = db.Column(db.Numeric(10, 2))
    total_deposito = db.Column(db.Numeric(10, 2))
    first_sale_date = db.Column(db.Date)
    last_sale_date = db.Column(db.Date)
    
    # Dati anagrafici (se presenti)
    origine = db.Column(db.String(255))
    paese = db.Column(db.String(100))
    genere = db.Column(db.String(20))
    mail = db.Column(db.String(255))
    indirizzo = db.Column(db.Text)
    
    # Stato matching
    matched = db.Column(db.Boolean, default=False)
    matched_cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'))
    matched_date = db.Column(db.DateTime)
    matched_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # Note
    notes = db.Column(db.Text)
    
    # Relazioni
    matched_cliente = db.relationship('Cliente')
    matched_by = db.relationship('User')
    
    def __repr__(self):
        return f'<UnmatchedClient {self.excel_name} - Matched:{self.matched}>'


# ============================================================================
# SERVICE NOTES MODULE (Anamnesi + Diario per Nutrizione/Coaching/Psicologia)
# ============================================================================

class ServiceAnamnesi(TimestampMixin, db.Model):
    """
    Anamnesi (Valutazione Iniziale) per servizio.
    One-to-one: un cliente può avere una sola anamnesi per servizio.
    Sempre modificabile (no freeze logic).
    """
    __tablename__ = "service_anamnesi"
    __versioned__ = {}  # Abilita versioning per audit trail

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    service_type = db.Column(db.String(20), nullable=False)  # 'nutrizione', 'coaching', 'psicologia'

    # Professionista che l'ha creata/modificata per ultimo
    created_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    last_modified_by_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Contenuto
    content = db.Column(db.Text, nullable=False)

    # Relazioni
    cliente = relationship("Cliente", backref=db.backref(
        "anamnesi_entries", lazy="dynamic", cascade="all, delete-orphan"
    ))
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    last_modified_by = relationship("User", foreign_keys=[last_modified_by_user_id])

    # Unique constraint: una sola anamnesi per servizio per cliente
    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'service_type', name='uq_cliente_service_anamnesi'),
        db.Index('ix_anamnesi_cliente_service', 'cliente_id', 'service_type'),
    )

    def __repr__(self):
        return f"<ServiceAnamnesi {self.service_type} Cliente:{self.cliente_id}>"


class ServiceDiaryEntry(TimestampMixin, db.Model):
    """
    Voci del Diario per servizio.
    Sostituisce storia_nutrizione, storia_coach, storia_psicologica con un sistema strutturato.
    Multiple entries per cliente per servizio.
    Sempre modificabile.
    """
    __tablename__ = "service_diary_entries"
    __versioned__ = {}  # Abilita versioning

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False)
    service_type = db.Column(db.String(20), nullable=False)  # 'nutrizione', 'coaching', 'psicologia'

    # Professionista autore
    author_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Dettagli della nota
    entry_date = db.Column(db.Date, nullable=False, index=True)
    content = db.Column(db.Text, nullable=False)

    # Relazioni
    cliente = relationship("Cliente", backref=db.backref(
        "diary_entries", lazy="dynamic", cascade="all, delete-orphan",
        order_by="desc(ServiceDiaryEntry.entry_date)"
    ))
    author = relationship("User")

    __table_args__ = (
        db.Index('ix_diary_cliente_service_date', 'cliente_id', 'service_type', 'entry_date'),
    )

    def __repr__(self):
        return f"<ServiceDiaryEntry {self.service_type} {self.entry_date} Cliente:{self.cliente_id}>"


# ============================================================================
# HR NOTES MODULE
# ============================================================================

class HRNote(TimestampMixin, db.Model):
    """
    Note HR per i membri del team.
    
    Permette a HR e Finance di aggiungere note riservate su ogni membro.
    """
    __tablename__ = 'hr_notes'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=True,
        index=True
    )
    
    # Note content
    note_text = db.Column(db.Text, nullable=False)
    note_type = db.Column(
        db.String(50),
        default='generale'
    )  # colloquio, valutazione, disciplinare, generale
    
    # Visibility and priority
    visibility = db.Column(
        db.String(20),
        default='hr_only'
    )  # hr_only, hr_finance, all_admin
    is_pinned = db.Column(db.Boolean, default=False)
    
    # Relationships
    user = relationship(
        'User',
        foreign_keys=[user_id],
        backref=db.backref('hr_notes_list', lazy='dynamic', cascade='all, delete-orphan')
    )
    author = relationship(
        'User',
        foreign_keys=[author_id]
    )
    
    def __repr__(self) -> str:
        return f"<HRNote {self.id} for User {self.user_id}>"
    
    def to_dict(self) -> dict:
        """Serializza la nota in dizionario."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "author_id": self.author_id,
            "author_name": self.author.full_name if self.author else "Sistema",
            "note_text": self.note_text,
            "note_type": self.note_type,
            "visibility": self.visibility,
            "is_pinned": self.is_pinned,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


# ============================================================================
# OPENINGS MODULE - ATS (Applicant Tracking System)
# ============================================================================

# ---------------------------------------------------------------------------- #
#  ENUM per il modulo Openings
# ---------------------------------------------------------------------------- #

# ============================================================================
# RECRUITING MODULE - Complete ATS & Onboarding System
# ============================================================================

# ---------------------------------------------------------------------------- #
#  ENUM per il modulo Recruiting
# ---------------------------------------------------------------------------- #

class QuestionTypeEnum(str, Enum):
    """Tipi di domande per il form builder."""
    short_text = "short_text"
    long_text = "long_text"
    select = "select"
    multiselect = "multiselect"
    number = "number"
    date = "date"
    file = "file"
    email = "email"
    phone = "phone"
    url = "url"
    yesno = "yesno"

class ExpectedMatchTypeEnum(str, Enum):
    """Modalità di matching per risposte attese (scoring ATS)."""
    exact_all = "exact_all"           # TUTTE le opzioni devono matchare esattamente
    exact_any = "exact_any"           # ALMENO UNA opzione deve matchare
    contains_all = "contains_all"     # Deve contenere TUTTE le opzioni (può averne altre)
    contains_any = "contains_any"     # Deve contenere ALMENO UNA opzione
    partial = "partial"               # Score parziale proporzionale (default)
    range = "range"                   # Per number: valore nel range
    threshold = "threshold"           # Per number: sopra soglia minima

class JobOfferStatusEnum(str, Enum):
    """Stati dell'offerta di lavoro."""
    draft = "draft"
    published = "published"
    paused = "paused"
    closed = "closed"
    archived = "archived"

class KanbanStageTypeEnum(str, Enum):
    """Tipi di stage nel kanban."""
    applied = "applied"
    screening = "screening"
    phone_interview = "phone_interview"
    technical_test = "technical_test"
    hr_interview = "hr_interview"
    technical_interview = "technical_interview"
    final_interview = "final_interview"
    reference_check = "reference_check"
    offer = "offer"
    hired = "hired"
    rejected = "rejected"

class OnboardingTaskTypeEnum(str, Enum):
    """Tipi di task onboarding."""
    document = "document"
    training = "training"
    meeting = "meeting"
    system_access = "system_access"
    equipment = "equipment"
    introduction = "introduction"
    compliance = "compliance"
    other = "other"

class OnboardingTaskStatusEnum(str, Enum):
    """Stati del task onboarding."""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    blocked = "blocked"

class AdvertisingPlatformEnum(str, Enum):
    """Piattaforme advertising per recruiting."""
    linkedin = "linkedin"
    facebook = "facebook"
    instagram = "instagram"

class AdvertisingPeriodEnum(str, Enum):
    """Periodi mensili per tracciamento advertising (suddivisione decadi)."""
    period_1_10 = "1-10"
    period_11_20 = "11-20"
    period_21_30 = "21-30"

    # Override per far sì che SQLAlchemy usi il valore invece del nome
    def __str__(self):
        return self.value

# ---------------------------------------------------------------------------- #
#  JobOffer - Offerta di lavoro
# ---------------------------------------------------------------------------- #

class JobOffer(TimestampMixin, db.Model):
    """Offerta di lavoro con form builder integrato."""
    
    __tablename__ = "job_offers"
    
    id = db.Column(db.Integer, primary_key=True)
    
    # Informazioni base
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text)
    benefits = db.Column(db.Text)
    salary_range = db.Column(db.String(100))
    location = db.Column(db.String(255))
    employment_type = db.Column(db.String(50))  # full-time, part-time, contract, etc.
    
    # Dipartimento assegnato
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="SET NULL"),
        index=True
    )
    
    # ATS Configuration
    what_we_search = db.Column(db.Text)  # Cosa cerchiamo nel CV
    form_weight = db.Column(db.Integer, default=50)  # Peso % del form (0-100)
    cv_weight = db.Column(db.Integer, default=50)  # Peso % del CV (0-100)
    
    # Link pubblici univoci
    linkedin_link = db.Column(db.String(100), unique=True, index=True)
    facebook_link = db.Column(db.String(100), unique=True, index=True)
    instagram_link = db.Column(db.String(100), unique=True, index=True)
    
    # Kanban associato
    kanban_id = db.Column(
        db.Integer,
        db.ForeignKey("recruiting_kanbans.id", ondelete="SET NULL")
    )
    
    # Stato e tracking
    status = db.Column(
        _def(JobOfferStatusEnum),
        default=JobOfferStatusEnum.draft,
        nullable=False
    )
    published_at = db.Column(db.DateTime)
    closed_at = db.Column(db.DateTime)
    views_count = db.Column(db.Integer, default=0)
    applications_count = db.Column(db.Integer, default=0)
    
    # Visualizzazioni per fonte
    linkedin_views = db.Column(db.Integer, default=0)
    facebook_views = db.Column(db.Integer, default=0)
    instagram_views = db.Column(db.Integer, default=0)
    
    # Costo totale speso per advertising
    costo_totale_speso_instagram = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    costo_totale_speso_facebook = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)
    costo_totale_speso_linkedin = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)  # Costo totale speso per advertising

    # ROI Analysis
    avg_hire_value = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        default=0.00,
        comment="Valore medio stimato per ogni assunzione (per calcolo ROI per source)"
    )

    # Creatore
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relazioni
    department = db.relationship("Department", backref="job_offers")
    created_by = db.relationship("User", backref="created_job_offers")
    questions = db.relationship(
        "JobQuestion",
        backref="job_offer",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="JobQuestion.order"
    )
    applications = db.relationship(
        "JobApplication",
        backref="job_offer",
        lazy="dynamic",
        cascade="all, delete-orphan"
    )
    kanban = db.relationship("RecruitingKanban", backref="job_offers")
    
    # Metodi helper
    def generate_public_links(self):
        """Genera i 3 link pubblici univoci."""
        import uuid
        self.linkedin_link = f"ln-{uuid.uuid4().hex[:12]}"
        self.facebook_link = f"fb-{uuid.uuid4().hex[:12]}"
        self.instagram_link = f"ig-{uuid.uuid4().hex[:12]}"
    
    def get_public_url(self, source: str) -> str:
        """Ritorna l'URL pubblico completo per la fonte specificata."""
        from flask import url_for
        link_map = {
            'linkedin': self.linkedin_link,
            'facebook': self.facebook_link,
            'instagram': self.instagram_link
        }
        if link_code := link_map.get(source):
            return url_for('recruiting.public_apply', link_code=link_code, _external=True)
        return None
    
    @property
    def total_questions_weight(self) -> float:
        """Verifica che il peso totale delle domande sia 100%."""
        return sum(q.weight for q in self.questions)
    
    def __repr__(self) -> str:
        return f"<JobOffer {self.title!r}>"

# ---------------------------------------------------------------------------- #
#  JobQuestion - Domande del form
# ---------------------------------------------------------------------------- #

class JobQuestion(db.Model):
    """Domande personalizzate per ogni offerta di lavoro."""
    
    __tablename__ = "job_questions"
    
    id = db.Column(db.Integer, primary_key=True)
    job_offer_id = db.Column(
        db.Integer,
        db.ForeignKey("job_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Configurazione domanda
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(
        _def(QuestionTypeEnum),
        nullable=False,
        default=QuestionTypeEnum.short_text
    )
    
    # Opzioni (per select, radio, checkbox)
    options = db.Column(db.JSON, default=list)  # ["opzione1", "opzione2", ...]

    # Risposta attesa (per scoring ATS)
    expected_answer = db.Column(db.Text)  # Per text, textarea, select, yesno
    expected_options = db.Column(db.JSON, default=list)  # Per multiselect, checkbox
    expected_min = db.Column(db.Float)  # Per number, rating
    expected_max = db.Column(db.Float)  # Per number, rating
    expected_match_type = db.Column(
        _def(ExpectedMatchTypeEnum),
        nullable=True,
        default=ExpectedMatchTypeEnum.partial,
        comment="Modalità di matching per scoring (exact_all, contains_all, partial, etc.)"
    )
    
    # Configurazione
    is_required = db.Column(db.Boolean, default=True)
    order = db.Column(db.Integer, default=0)
    weight = db.Column(db.Float, default=0)  # Peso % (0-100)
    
    # Validazione
    min_length = db.Column(db.Integer)
    max_length = db.Column(db.Integer)
    regex_pattern = db.Column(db.String(500))
    
    # Help text
    help_text = db.Column(db.Text)
    placeholder = db.Column(db.String(255))
    
    def normalize_string(self, s: str) -> str:
        """Normalizza stringa per matching robusto (lowercase, no accenti, trim)."""
        if not s:
            return ""
        import unicodedata
        # Lowercase e trim
        s = s.lower().strip()
        # Rimuovi accenti
        s = ''.join(c for c in unicodedata.normalize('NFD', s)
                    if unicodedata.category(c) != 'Mn')
        # Rimuovi spazi multipli
        s = ' '.join(s.split())
        return s

    def calculate_score(self, answer_value) -> float:
        """
        Calcola il punteggio della risposta (0-100) con logica INFALLIBILE.

        Features:
        - Normalizzazione stringhe (lowercase, no accenti)
        - Gestione varianti per YESNO (Sì/Si/YES/1)
        - Modalità matching configurabile per MULTISELECT
        - Similarity fallback per typos
        - Penalità per risposte extra non richieste
        """
        # Se vuota e obbligatoria → 0
        if not answer_value and self.is_required:
            return 0.0

        # Se vuota e non obbligatoria → 100 (non penalizzare)
        # ECCEZIONE: lista vuota per multiselect è comunque 0
        if not answer_value:
            if self.question_type == QuestionTypeEnum.multiselect:
                return 0.0 if self.is_required else 0.0
            return 100.0 if not self.is_required else 0.0

        # ═══════════════════════════════════════════════════════════════════════
        # TEXT / TEXTAREA - Similarity matching
        # ═══════════════════════════════════════════════════════════════════════
        if self.question_type in [QuestionTypeEnum.short_text, QuestionTypeEnum.long_text]:
            if not self.expected_answer:
                return 100.0 if answer_value else 0.0

            from difflib import SequenceMatcher
            answer_norm = self.normalize_string(str(answer_value))
            expected_norm = self.normalize_string(self.expected_answer)

            similarity = SequenceMatcher(None, answer_norm, expected_norm).ratio()
            return similarity * 100

        # ═══════════════════════════════════════════════════════════════════════
        # SELECT - Matching esatto normalizzato
        # ═══════════════════════════════════════════════════════════════════════
        elif self.question_type == QuestionTypeEnum.select:
            if not self.expected_answer:
                return 100.0 if answer_value else 0.0

            answer_norm = self.normalize_string(str(answer_value))
            expected_norm = self.normalize_string(self.expected_answer)

            # Matching esatto
            if answer_norm == expected_norm:
                return 100.0

            # Fallback: similarity per typos minori
            from difflib import SequenceMatcher
            similarity = SequenceMatcher(None, answer_norm, expected_norm).ratio()
            if similarity > 0.9:  # 90%+ similarità
                return 80.0  # Penalità 20% per typo

            return 0.0

        # ═══════════════════════════════════════════════════════════════════════
        # MULTISELECT - Logiche multiple con expected_match_type
        # ═══════════════════════════════════════════════════════════════════════
        elif self.question_type == QuestionTypeEnum.multiselect:
            if not self.expected_options:
                return 100.0 if answer_value else 0.0

            # Converti answer in lista e normalizza
            if isinstance(answer_value, list):
                answer_list = answer_value
            elif isinstance(answer_value, str):
                # Parse da stringa separata da virgole
                answer_list = [a.strip() for a in answer_value.split(',') if a.strip()]
            else:
                answer_list = [answer_value]

            answer_set = {self.normalize_string(str(a)) for a in answer_list}
            expected_set = {self.normalize_string(str(e)) for e in self.expected_options}

            matches = answer_set & expected_set  # Intersezione
            extra = answer_set - expected_set    # Risposte extra non richieste
            missing = expected_set - answer_set  # Risposte mancanti

            match_type = self.expected_match_type or ExpectedMatchTypeEnum.partial

            if match_type == ExpectedMatchTypeEnum.exact_all:
                # Devono essere ESATTAMENTE le expected
                if answer_set == expected_set:
                    return 100.0
                else:
                    # Penalizza: -20 punti per ogni errore (mancante o extra)
                    # Ma se NESSUNA è corretta → 0 punti
                    if len(matches) == 0:
                        return 0.0
                    errors = len(missing) + len(extra)
                    return max(0, 100 - (errors * 20))

            elif match_type == ExpectedMatchTypeEnum.exact_any:
                # Almeno UNA delle expected deve essere presente
                return 100.0 if len(matches) > 0 else 0.0

            elif match_type == ExpectedMatchTypeEnum.contains_all:
                # Deve contenere TUTTE le expected (può averne altre)
                if expected_set.issubset(answer_set):
                    return 100.0
                else:
                    # Score parziale per quelle presenti
                    return (len(matches) / len(expected_set)) * 100 if expected_set else 0

            elif match_type == ExpectedMatchTypeEnum.contains_any:
                # Deve contenere ALMENO UNA expected
                if len(matches) > 0:
                    # Score proporzionale a quante ne ha
                    return (len(matches) / len(expected_set)) * 100
                return 0.0

            else:  # ExpectedMatchTypeEnum.partial (default)
                # Score proporzionale con penalità per extra
                if len(expected_set) == 0:
                    return 100.0

                match_score = (len(matches) / len(expected_set)) * 100

                # Penalizza risposte extra (max -20%)
                if len(extra) > 0 and len(answer_set) > 0:
                    penalty = min(20, (len(extra) / len(answer_set)) * 30)
                    match_score = max(0, match_score - penalty)

                return match_score

        # ═══════════════════════════════════════════════════════════════════════
        # YESNO - Gestione varianti robusta
        # ═══════════════════════════════════════════════════════════════════════
        elif self.question_type == QuestionTypeEnum.yesno:
            if not self.expected_answer:
                return 100.0

            answer_norm = self.normalize_string(str(answer_value))
            expected_norm = self.normalize_string(self.expected_answer)

            # Varianti YES
            yes_variants = {'si', 'sì', 'yes', 'y', '1', 'true', 'vero', 'ok'}
            # Varianti NO
            no_variants = {'no', 'n', '0', 'false', 'falso', 'nope'}

            # Determina booleano della risposta
            if answer_norm in yes_variants:
                answer_bool = 'yes'
            elif answer_norm in no_variants:
                answer_bool = 'no'
            else:
                # Fallback: confronto diretto
                return 100.0 if answer_norm == expected_norm else 0.0

            # Determina booleano atteso
            if expected_norm in yes_variants:
                expected_bool = 'yes'
            elif expected_norm in no_variants:
                expected_bool = 'no'
            else:
                # Fallback
                return 100.0 if answer_norm == expected_norm else 0.0

            return 100.0 if answer_bool == expected_bool else 0.0

        # ═══════════════════════════════════════════════════════════════════════
        # NUMBER - Range o threshold
        # ═══════════════════════════════════════════════════════════════════════
        elif self.question_type == QuestionTypeEnum.number:
            try:
                value = float(answer_value)
            except (ValueError, TypeError):
                return 0.0

            # CASO 1: Range (min e max definiti)
            if self.expected_min is not None and self.expected_max is not None:
                if self.expected_min <= value <= self.expected_max:
                    return 100.0

                # Score decrescente con distanza dal range
                range_width = self.expected_max - self.expected_min
                if range_width <= 0:
                    return 0.0

                if value < self.expected_min:
                    distance = self.expected_min - value
                else:
                    distance = value - self.expected_max

                penalty = (distance / range_width) * 100
                return max(0, 100 - penalty)

            # CASO 2: Solo minimo (threshold)
            elif self.expected_min is not None:
                if value >= self.expected_min:
                    return 100.0
                else:
                    # Score proporzionale sotto soglia (max 80%)
                    # Zero vale sempre 0
                    if value == 0:
                        return 0.0
                    if self.expected_min > 0:
                        return min(80, (value / self.expected_min) * 80)
                    else:
                        return 0.0

            # CASO 3: Solo massimo
            elif self.expected_max is not None:
                if value <= self.expected_max:
                    return 100.0
                else:
                    # Penalità per ogni unità sopra max
                    penalty = ((value - self.expected_max) / self.expected_max) * 100
                    return max(0, 100 - penalty)

            # CASO 4: Nessun vincolo
            # Se nessun vincolo definito, accetta qualsiasi numero (anche 0)
            return 100.0

        # ═══════════════════════════════════════════════════════════════════════
        # Altri tipi (email, phone, url, date, file) - Non hanno expected
        # ═══════════════════════════════════════════════════════════════════════
        return 100.0 if answer_value else 0.0
    
    def to_dict(self):
        """Converte l'oggetto JobQuestion in un dizionario per la serializzazione JSON."""
        return {
            'id': self.id,
            'question_text': self.question_text,
            'question_type': self.question_type.value if hasattr(self.question_type, 'value') else self.question_type,
            'options': self.options or [],
            'expected_answer': self.expected_answer,
            'expected_options': self.expected_options or [],
            'expected_min': self.expected_min,
            'expected_max': self.expected_max,
            'expected_match_type': self.expected_match_type.value if self.expected_match_type else 'partial',
            'is_required': self.is_required,
            'order': self.order,
            'weight': self.weight,
            'help_text': self.help_text,
            'placeholder': self.placeholder,
            'min_length': self.min_length,
            'max_length': self.max_length,
            'regex_pattern': self.regex_pattern
        }
    
    def __repr__(self) -> str:
        return f"<JobQuestion {self.question_text[:50]}>"

# ---------------------------------------------------------------------------- #
#  JobApplication - Candidatura
# ---------------------------------------------------------------------------- #

class JobApplication(TimestampMixin, db.Model):
    """Candidatura per un'offerta di lavoro."""
    
    __tablename__ = "job_applications"
    
    id = db.Column(db.Integer, primary_key=True)
    job_offer_id = db.Column(
        db.Integer,
        db.ForeignKey("job_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Dati candidato
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False, index=True)
    phone = db.Column(db.String(30))
    linkedin_profile = db.Column(db.String(255))
    portfolio_url = db.Column(db.String(255))
    
    # CV e documenti
    cv_file_path = db.Column(db.String(255))
    cv_text = db.Column(db.Text)  # Testo estratto via OCR
    cover_letter = db.Column(db.Text)
    additional_documents = db.Column(db.JSON, default=list)  # Lista di path
    
    # Fonte e tracking
    source = db.Column(
        _def(ApplicationSourceEnum),
        nullable=False,
        default=ApplicationSourceEnum.website
    )
    source_link = db.Column(db.String(100))  # linkedin_link, facebook_link, etc.
    referrer_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Stato
    status = db.Column(
        _def(ApplicationStatusEnum),
        nullable=False,
        default=ApplicationStatusEnum.new
    )
    
    # Scoring ATS
    form_score = db.Column(db.Float, default=0)  # 0-100
    cv_score = db.Column(db.Float, default=0)  # 0-100
    total_score = db.Column(db.Float, default=0)  # 0-100 weighted
    ats_analysis = db.Column(db.JSON)  # Dettagli analisi
    screened_at = db.Column(db.DateTime)

    # Funnel tracking
    form_started_at = db.Column(
        db.DateTime,
        nullable=True,
        index=True,
        comment="Timestamp di inizio compilazione form (per analisi funnel drop-off)"
    )
    
    # Kanban position
    kanban_stage_id = db.Column(
        db.Integer,
        db.ForeignKey("kanban_stages.id", ondelete="SET NULL")
    )
    kanban_order = db.Column(db.Integer, default=0)
    
    # Note e feedback
    internal_notes = db.Column(db.Text)
    rejection_reason = db.Column(db.Text)
    
    # Relazioni
    answers = db.relationship(
        "ApplicationAnswer",
        backref="application",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    kanban_stage = db.relationship("KanbanStage", backref="applications")
    referrer = db.relationship("User", foreign_keys=[referrer_id])
    
    # Metodi helper
    def calculate_scores(self):
        """Calcola i punteggi form e totale."""
        if not self.job_offer:
            return
        
        # Calcola score del form
        total_weight = 0
        weighted_score = 0
        
        for answer in self.answers:
            if answer.question:
                score = answer.score or 0
                weight = answer.question.weight or 0
                weighted_score += score * weight
                total_weight += weight
        
        if total_weight > 0:
            self.form_score = weighted_score / total_weight
        
        # Calcola score totale con pesi
        form_weight = self.job_offer.form_weight or 50
        cv_weight = self.job_offer.cv_weight or 50
        
        self.total_score = (
            (self.form_score * form_weight + self.cv_score * cv_weight) / 100
        )
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self) -> str:
        return f"<JobApplication {self.full_name} for {self.job_offer_id}>"

# ---------------------------------------------------------------------------- #
#  ApplicationAnswer - Risposte del candidato
# ---------------------------------------------------------------------------- #

class ApplicationAnswer(db.Model):
    """Risposte alle domande del form."""
    
    __tablename__ = "application_answers"
    
    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id = db.Column(
        db.Integer,
        db.ForeignKey("job_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Risposta
    answer_text = db.Column(db.Text)
    answer_json = db.Column(db.JSON)  # Per multiselect, checkbox
    answer_file_path = db.Column(db.String(255))  # Per file upload
    
    # Scoring
    score = db.Column(db.Float)  # 0-100
    
    # Relazioni
    question = db.relationship("JobQuestion")
    
    def calculate_score(self):
        """Calcola e salva il punteggio della risposta."""
        if not self.question:
            self.score = 0
            return
        
        # Determina il valore da analizzare
        if self.answer_json:
            answer_value = self.answer_json
        else:
            answer_value = self.answer_text
        
        self.score = self.question.calculate_score(answer_value)
    
    def __repr__(self) -> str:
        return f"<ApplicationAnswer {self.id}>"

# ---------------------------------------------------------------------------- #
#  ApplicationStageHistory - Storico movimenti tra stage
# ---------------------------------------------------------------------------- #

class ApplicationStageHistory(db.Model):
    """
    Tracciamento storico dei movimenti delle candidature tra stage del kanban.
    Fondamentale per calcolare metriche accurate su tempo per stage, conversion rate,
    e bottleneck detection.
    """

    __tablename__ = "application_stage_history"

    id = db.Column(db.Integer, primary_key=True)

    # Riferimenti
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    stage_id = db.Column(
        db.Integer,
        db.ForeignKey("kanban_stages.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    previous_stage_id = db.Column(
        db.Integer,
        db.ForeignKey("kanban_stages.id", ondelete="SET NULL"),
        nullable=True,
        comment="Stage precedente per tracking completo del percorso"
    )

    # Timing
    entered_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="Timestamp di ingresso nello stage"
    )
    exited_at = db.Column(
        db.DateTime,
        nullable=True,
        comment="Timestamp di uscita dallo stage (NULL se ancora nello stage)"
    )
    duration_seconds = db.Column(
        db.Integer,
        nullable=True,
        comment="Durata in secondi nello stage (calcolato automaticamente)"
    )

    # Metadata
    changed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Utente che ha effettuato il cambio (NULL per auto-assignment)"
    )
    notes = db.Column(
        db.Text,
        nullable=True,
        comment="Note opzionali sul cambio di stage"
    )

    # Relazioni
    application = db.relationship("JobApplication", backref="stage_history")
    stage = db.relationship("KanbanStage", foreign_keys=[stage_id], backref="history_entries")
    previous_stage = db.relationship("KanbanStage", foreign_keys=[previous_stage_id])
    changed_by = db.relationship("User", foreign_keys=[changed_by_id])

    # Indici compositi per performance
    __table_args__ = (
        Index('idx_app_stage_entered', 'application_id', 'stage_id', 'entered_at'),
        Index('idx_stage_entered_exited', 'stage_id', 'entered_at', 'exited_at'),
    )

    def calculate_duration(self):
        """Calcola e aggiorna duration_seconds se exited_at è impostato."""
        if self.exited_at and self.entered_at:
            delta = self.exited_at - self.entered_at
            self.duration_seconds = int(delta.total_seconds())
        return self.duration_seconds

    @property
    def duration_days(self) -> float:
        """Ritorna la durata in giorni (property di comodo)."""
        if self.duration_seconds:
            return self.duration_seconds / 86400
        return 0.0

    @property
    def is_active(self) -> bool:
        """Verifica se il candidato è ancora in questo stage."""
        return self.exited_at is None

    def __repr__(self) -> str:
        status = "active" if self.is_active else f"{self.duration_days:.1f}d"
        return f"<ApplicationStageHistory app={self.application_id} stage={self.stage_id} {status}>"

# ---------------------------------------------------------------------------- #
#  RecruitingKanban - Configurazione Kanban
# ---------------------------------------------------------------------------- #

class RecruitingKanban(TimestampMixin, db.Model):
    """Template di kanban per il recruiting."""
    
    __tablename__ = "recruiting_kanbans"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    is_default = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Configurazione
    color_scheme = db.Column(db.JSON)  # {"applied": "#blue", ...}
    auto_reject_days = db.Column(db.Integer)  # Auto-reject dopo X giorni
    
    # Creatore
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Relazioni
    stages = db.relationship(
        "KanbanStage",
        backref="kanban",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="KanbanStage.order"
    )
    created_by = db.relationship("User", backref="created_kanbans")
    
    @classmethod
    def get_default(cls):
        """Ritorna il kanban di default o ne crea uno."""
        default = cls.query.filter_by(is_default=True).first()
        if not default:
            default = cls(
                name="Default Recruiting Pipeline",
                is_default=True
            )
            # Aggiungi stage di default
            default_stages = [
                ("Applied", KanbanStageTypeEnum.applied, 0),
                ("Screening", KanbanStageTypeEnum.screening, 1),
                ("Phone Interview", KanbanStageTypeEnum.phone_interview, 2),
                ("Technical Interview", KanbanStageTypeEnum.technical_interview, 3),
                ("Final Interview", KanbanStageTypeEnum.final_interview, 4),
                ("Offer", KanbanStageTypeEnum.offer, 5),
                ("Hired", KanbanStageTypeEnum.hired, 6),
                ("Rejected", KanbanStageTypeEnum.rejected, 7),
            ]
            for name, stage_type, order in default_stages:
                stage = KanbanStage(
                    name=name,
                    stage_type=stage_type,
                    order=order,
                    is_final=(stage_type in [KanbanStageTypeEnum.hired, 
                                            KanbanStageTypeEnum.rejected])
                )
                default.stages.append(stage)
            
            db.session.add(default)
            db.session.commit()
        
        return default
    
    def __repr__(self) -> str:
        return f"<RecruitingKanban {self.name!r}>"

# ---------------------------------------------------------------------------- #
#  KanbanStage - Fasi del Kanban
# ---------------------------------------------------------------------------- #

class KanbanStage(db.Model):
    """Fase/colonna del kanban recruiting."""
    
    __tablename__ = "kanban_stages"
    
    id = db.Column(db.Integer, primary_key=True)
    kanban_id = db.Column(
        db.Integer,
        db.ForeignKey("recruiting_kanbans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Configurazione
    name = db.Column(db.String(100), nullable=False)
    stage_type = db.Column(
        _def(KanbanStageTypeEnum),
        nullable=False
    )
    description = db.Column(db.Text)
    color = db.Column(db.String(7))  # HEX color
    icon = db.Column(db.String(50))
    
    # Ordinamento e stato
    order = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    is_final = db.Column(db.Boolean, default=False)  # Hired/Rejected
    
    # Automazioni
    auto_email_template = db.Column(db.Text)  # Template email automatica
    required_fields = db.Column(db.JSON, default=list)  # Campi richiesti per entrare
    
    def __repr__(self) -> str:
        return f"<KanbanStage {self.name!r}>"

# ---------------------------------------------------------------------------- #
#  OnboardingTemplate - Template Onboarding per Dipartimento
# ---------------------------------------------------------------------------- #

class OnboardingTemplate(TimestampMixin, db.Model):
    """Template di onboarding configurabile per dipartimento."""
    
    __tablename__ = "onboarding_templates"
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Configurazione
    description = db.Column(db.Text)
    duration_days = db.Column(db.Integer, default=30)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relazioni
    department = db.relationship("Department", backref="onboarding_templates")
    tasks = db.relationship(
        "OnboardingTask",
        backref="template",
        lazy="selectin",
        cascade="all, delete-orphan",
        order_by="OnboardingTask.order"
    )
    
    def create_checklist_for(self, application_id: int) -> 'OnboardingChecklist':
        """Crea una checklist di onboarding per una candidatura."""
        checklist = OnboardingChecklist(
            application_id=application_id,
            template_id=self.id,
            due_date=datetime.utcnow() + timedelta(days=self.duration_days)
        )
        
        # Copia tutti i task del template
        for task in self.tasks:
            progress = OnboardingProgress(
                task_id=task.id,
                status=OnboardingTaskStatusEnum.pending,
                due_date=datetime.utcnow() + timedelta(days=task.due_after_days)
            )
            checklist.progress_items.append(progress)
        
        return checklist
    
    def __repr__(self) -> str:
        return f"<OnboardingTemplate {self.name!r}>"

# ---------------------------------------------------------------------------- #
#  OnboardingTask - Task di Onboarding
# ---------------------------------------------------------------------------- #

class OnboardingTask(db.Model):
    """Singolo task in un template di onboarding."""
    
    __tablename__ = "onboarding_tasks"
    
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("onboarding_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Dettagli task
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    task_type = db.Column(
        _def(OnboardingTaskTypeEnum),
        nullable=False,
        default=OnboardingTaskTypeEnum.other
    )
    
    # Configurazione
    order = db.Column(db.Integer, default=0)
    due_after_days = db.Column(db.Integer, default=0)  # Giorni dall'inizio
    is_required = db.Column(db.Boolean, default=True)
    
    # Assegnazione
    assigned_role = db.Column(db.String(100))  # HR, IT, Manager, etc.
    assigned_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Documenti/Link
    resources = db.Column(db.JSON, default=list)  # Link a risorse
    required_documents = db.Column(db.JSON, default=list)  # Documenti richiesti
    
    # Relazioni
    assigned_user = db.relationship("User", backref="assigned_onboarding_tasks")
    
    def __repr__(self) -> str:
        return f"<OnboardingTask {self.name!r}>"

# ---------------------------------------------------------------------------- #
#  OnboardingChecklist - Checklist per nuovo assunto
# ---------------------------------------------------------------------------- #

class OnboardingChecklist(TimestampMixin, db.Model):
    """Checklist di onboarding per un candidato assunto."""

    __tablename__ = "onboarding_checklists"

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(
        db.Integer,
        db.ForeignKey("job_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    template_id = db.Column(
        db.Integer,
        db.ForeignKey("onboarding_templates.id", ondelete="SET NULL")
    )
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="SET NULL")
    )

    # Stato
    start_date = db.Column(db.Date, nullable=False, default=date.today)
    expected_end_date = db.Column(db.Date)
    actual_end_date = db.Column(db.Date)

    # Assegnazioni
    assigned_hr_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_manager_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    assigned_buddy_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )

    # Status
    status = db.Column(db.String(50))

    # Note e feedback
    notes = db.Column(db.Text)
    feedback = db.Column(db.JSON)
    
    # Relazioni
    application = db.relationship("JobApplication", backref="onboarding_checklist")
    template = db.relationship("OnboardingTemplate")
    department = db.relationship("Department")
    assigned_hr = db.relationship("User", foreign_keys=[assigned_hr_id])
    assigned_manager = db.relationship("User", foreign_keys=[assigned_manager_id])
    assigned_buddy = db.relationship("User", foreign_keys=[assigned_buddy_id])
    progress_items = db.relationship(
        "OnboardingProgress",
        backref="checklist",
        lazy="selectin",
        cascade="all, delete-orphan"
    )
    
    @property
    def progress_percentage(self) -> float:
        """Calcola la percentuale di completamento."""
        if not self.progress_items:
            return 0.0
        
        completed = sum(
            1 for item in self.progress_items 
            if item.status == OnboardingTaskStatusEnum.completed
        )
        return (completed / len(self.progress_items)) * 100
    
    @property
    def is_completed(self) -> bool:
        """Verifica se tutti i task required sono completati."""
        for item in self.progress_items:
            if item.task and item.task.is_required:
                if item.status != OnboardingTaskStatusEnum.completed:
                    return False
        return True
    
    def __repr__(self) -> str:
        return f"<OnboardingChecklist {self.id}>"

# ---------------------------------------------------------------------------- #
#  OnboardingProgress - Progresso task onboarding
# ---------------------------------------------------------------------------- #

class OnboardingProgress(TimestampMixin, db.Model):
    """Tracciamento progresso per ogni task di onboarding."""
    
    __tablename__ = "onboarding_progress"
    
    id = db.Column(db.Integer, primary_key=True)
    checklist_id = db.Column(
        db.Integer,
        db.ForeignKey("onboarding_checklists.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    task_id = db.Column(
        db.Integer,
        db.ForeignKey("onboarding_tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    
    # Stato
    status = db.Column(
        _def(OnboardingTaskStatusEnum),
        nullable=False,
        default=OnboardingTaskStatusEnum.pending
    )
    
    # Date
    due_date = db.Column(db.Date)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    completed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    
    # Note e file
    notes = db.Column(db.Text)
    uploaded_files = db.Column(db.JSON, default=list)  # Path dei file caricati
    
    # Relazioni
    task = db.relationship("OnboardingTask")
    completed_by = db.relationship("User", foreign_keys=[completed_by_id])
    
    def mark_completed(self, user_id: int):
        """Marca il task come completato."""
        self.status = OnboardingTaskStatusEnum.completed
        self.completed_at = datetime.utcnow()
        self.completed_by_id = user_id
    
    def __repr__(self) -> str:
        return f"<OnboardingProgress {self.id}>"

# ---------------------------------------------------------------------------- #
#  JobOfferAdvertisingCost - Tracciamento costi advertising granulare
# ---------------------------------------------------------------------------- #

class JobOfferAdvertisingCost(TimestampMixin, db.Model):
    """
    Tracciamento granulare dei costi advertising per job offer.
    Suddiviso per piattaforma, anno, mese e periodo mensile (decadi).
    """

    __tablename__ = "job_offer_advertising_costs"

    id = db.Column(db.Integer, primary_key=True)

    # Riferimento all'offerta
    job_offer_id = db.Column(
        db.Integer,
        db.ForeignKey("job_offers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Piattaforma (usa String per evitare conversioni enum SQLAlchemy)
    platform = db.Column(
        db.String(20),  # Usa String semplice, PostgreSQL fa la validazione con enum advertisingplatformenum
        nullable=False,
        index=True
    )

    # Periodo temporale
    year = db.Column(db.Integer, nullable=False, index=True)
    month = db.Column(db.Integer, nullable=False, index=True)  # 1-12
    # NOTA: Usa String invece di Enum per evitare che SQLAlchemy converta name->value
    # PostgreSQL valida comunque con il suo enum advertisingperiodenum
    period = db.Column(
        db.String(10),  # Usa String semplice, PostgreSQL fa la validazione
        nullable=False,
        comment="Decade del mese: 1-10, 11-20, 21-30"
    )

    # Importo
    amount = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0.00,
        comment="Importo speso in EUR"
    )

    # Metadata
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL")
    )
    notes = db.Column(db.Text, comment="Note opzionali sul costo")

    # Relazioni
    job_offer = db.relationship("JobOffer", backref="advertising_costs")
    created_by = db.relationship("User", foreign_keys=[created_by_id])

    # Indici compositi per performance
    __table_args__ = (
        Index('idx_offer_platform_date', 'job_offer_id', 'platform', 'year', 'month'),
        Index('idx_platform_date', 'platform', 'year', 'month'),
    )

    def __repr__(self) -> str:
        # platform e period sono ora stringhe semplici, non enum
        return f"<JobOfferAdvertisingCost offer={self.job_offer_id} {self.platform} {self.year}/{self.month} {self.period} €{self.amount}>"


# ============================================================================
# GHL INTEGRATION MODELS
# ============================================================================

class GHLConfig(TimestampMixin, db.Model):
    """
    Configurazione globale per l'integrazione Go High Level.
    Singleton - una sola riga nel database.
    """
    __tablename__ = 'ghl_config'

    id = db.Column(db.Integer, primary_key=True)

    # API Configuration
    api_key = db.Column(db.Text, comment="API Key o Access Token GHL")
    location_id = db.Column(db.String(100), comment="Location ID GHL")

    # OAuth tokens (se usi OAuth invece di API Key)
    access_token = db.Column(db.Text)
    refresh_token = db.Column(db.Text)
    token_expires_at = db.Column(db.DateTime)

    # Status
    is_active = db.Column(db.Boolean, default=False)
    last_sync_at = db.Column(db.DateTime)
    last_error = db.Column(db.Text)

    @classmethod
    def get_config(cls):
        """Ottiene la configurazione singleton, creandola se non esiste."""
        config = cls.query.first()
        if not config:
            config = cls()
            db.session.add(config)
            db.session.commit()
        return config

    @classmethod
    def get_active_config(cls):
        """Ottiene la configurazione fresca dalla sessione corrente."""
        return db.session.query(cls).first() or cls.get_config()

    @classmethod
    def is_configured(cls):
        """Verifica se GHL è configurato e attivo."""
        config = cls.query.first()
        return config and config.is_active and config.api_key and config.location_id

    def __repr__(self):
        return f'<GHLConfig location={self.location_id} active={self.is_active}>'




class GHLOpportunityData(TimestampMixin, db.Model):
    """
    Dati opportunity ricevuti da webhook GHL (formato semplificato).
    Usato per la pagina Assegnazioni AI.
    """
    __tablename__ = 'ghl_opportunity_data'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    storia = db.Column(db.Text)
    pacchetto = db.Column(db.String(255))
    durata = db.Column(db.String(50))
    received_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    raw_payload = db.Column(db.JSON)
    processed = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<GHLOpportunityData {self.id} - {self.nome}>'

class GHLOpportunity(TimestampMixin, db.Model):
    """
    Tracking completo delle opportunità ricevute da GoHighLevel.
    Gestisce sia acconti che pagamenti completi con storicizzazione.
    """
    __tablename__ = 'ghl_opportunities'

    id = db.Column(db.Integer, primary_key=True)

    # Identificazione univoca da GHL
    ghl_opportunity_id = db.Column(db.String(100), unique=True, nullable=False, index=True)
    ghl_contact_id = db.Column(db.String(100), index=True)

    # Stati opportunità
    status = db.Column(db.String(50), nullable=False, index=True)  # 'acconto_open', 'chiuso_won'
    previous_status = db.Column(db.String(50))  # Per tracking cambi stato
    status_changed_at = db.Column(db.DateTime)

    # Dati anagrafici cliente
    nome_cognome = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255))
    cellulare = db.Column(db.String(50))

    # Dati finanziari
    acconto_pagato = db.Column(db.Numeric(10, 2), default=0)
    importo_totale = db.Column(db.Numeric(10, 2), default=0)
    saldo_residuo = db.Column(db.Numeric(10, 2), default=0)
    modalita_pagamento = db.Column(db.String(50))
    data_pagamento_acconto = db.Column(db.DateTime)
    data_pagamento_saldo = db.Column(db.DateTime)

    # Pacchetto e servizi
    pacchetto_comprato = db.Column(db.String(200))
    package_id = db.Column(db.Integer, db.ForeignKey('finance_packages.id'))
    data_inizio = db.Column(db.Date)
    durata_mesi = db.Column(db.Integer)

    # Assegnazioni e origine
    sales_consultant = db.Column(db.String(255))
    sales_person_id = db.Column(db.Integer, db.ForeignKey('sales_person.sales_person_id'))
    servizio_clienti_assegnato = db.Column(db.String(255))
    servizio_clienti_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    origine_contatto = db.Column(db.String(255))

    # Dati aggiuntivi
    note_cliente = db.Column(db.Text)
    contabile_allegata = db.Column(db.String(500))
    calendario_prenotazione = db.Column(db.String(100))

    # Collegamenti con sistema esistente
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'))

    # Storicizzazione
    package_history = db.Column(db.JSON, default=list)  # Traccia cambi pacchetto
    amount_history = db.Column(db.JSON, default=list)   # Traccia cambi importi
    subscription_id = db.Column(db.Integer, db.ForeignKey('cliente_subscriptions.id'))

    # Processing e audit
    processed = db.Column(db.Boolean, default=False, index=True)
    processed_at = db.Column(db.DateTime)
    processed_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    webhook_payload = db.Column(JSONB)

    # Relazioni
    cliente = db.relationship('Cliente', backref='ghl_opportunities')
    package = db.relationship('Package', backref='ghl_opportunities')
    sales_person = db.relationship('SalesPerson', backref='ghl_opportunities')
    servizio_clienti_user = db.relationship('User', foreign_keys=[servizio_clienti_id])
    processed_by_user = db.relationship('User', foreign_keys=[processed_by])
    subscription = db.relationship('ClienteSubscription', backref='ghl_opportunity')

    def __repr__(self):
        return f'<GHLOpportunity {self.ghl_opportunity_id}: {self.nome_cognome} - {self.status}>'


class ServiceClienteAssignment(TimestampMixin, db.Model):
    """
    Gestione del workflow di assegnazione clienti al servizio clienti.
    Traccia approvazioni finance e assegnazioni professionisti.
    """
    __tablename__ = 'service_cliente_assignments'
    __table_args__ = (
        db.UniqueConstraint('cliente_id', name='_cliente_assignment_uc'),
    )

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False, index=True)
    ghl_opportunity_id = db.Column(db.Integer, db.ForeignKey('ghl_opportunities.id'))

    # Workflow status
    status = db.Column(db.String(50), nullable=False, index=True, default='pending_finance')

    # Approvazione Finance
    finance_approved = db.Column(db.Boolean, default=False, index=True)
    finance_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    finance_approved_at = db.Column(db.DateTime)
    finance_notes = db.Column(db.Text)
    bank_verified = db.Column(db.Boolean, default=False)
    bank_verification_date = db.Column(db.Date)
    importo_verificato = db.Column(db.Numeric(10, 2))

    # Checkup iniziale
    checkup_iniziale_fatto = db.Column(db.Boolean, default=False, index=True)
    checkup_iniziale_data = db.Column(db.DateTime)
    checkup_iniziale_note = db.Column(db.Text)
    checkup_alert_sent = db.Column(db.Boolean, default=False)
    checkup_alert_count = db.Column(db.Integer, default=0)
    checkup_last_alert = db.Column(db.DateTime)

    # Servizio clienti owner
    servizio_clienti_owner = db.Column(db.Integer, db.ForeignKey('users.id'))
    servizio_clienti_assigned_at = db.Column(db.DateTime)
    servizio_clienti_notes = db.Column(db.Text)

    # Assegnazioni professionisti
    nutrizionista_assigned_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    nutrizionista_assigned_at = db.Column(db.DateTime)
    nutrizionista_assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    nutrizionista_first_call_date = db.Column(db.DateTime)

    coach_assigned_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    coach_assigned_at = db.Column(db.DateTime)
    coach_assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    coach_first_call_date = db.Column(db.DateTime)

    psicologa_assigned_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    psicologa_assigned_at = db.Column(db.DateTime)
    psicologa_assigned_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    psicologa_first_call_date = db.Column(db.DateTime)

    # AI Assignment metadata
    ai_suggestions = db.Column(JSONB)
    ai_suggested_at = db.Column(db.DateTime)
    ai_model_version = db.Column(db.String(50))
    ai_accepted = db.Column(db.Boolean, default=False)
    manual_override = db.Column(db.Boolean, default=False)
    override_reason = db.Column(db.Text)

    # History tracking
    assignment_history = db.Column(JSONB)
    status_history = db.Column(JSONB)

    # Priorità e urgenza
    priority_level = db.Column(db.Integer, default=0)
    urgent_flag = db.Column(db.Boolean, default=False)
    urgent_reason = db.Column(db.Text)

    # Relazioni
    cliente = db.relationship('Cliente', backref=db.backref('service_assignment', uselist=False))
    ghl_opportunity = db.relationship('GHLOpportunity', backref='service_assignment')

    # Relazioni users
    finance_approver = db.relationship('User', foreign_keys=[finance_approved_by])
    service_owner = db.relationship('User', foreign_keys=[servizio_clienti_owner])

    # Professionisti assegnati
    nutrizionista = db.relationship('User', foreign_keys=[nutrizionista_assigned_id])
    nutrizionista_assigner = db.relationship('User', foreign_keys=[nutrizionista_assigned_by])
    coach = db.relationship('User', foreign_keys=[coach_assigned_id])
    coach_assigner = db.relationship('User', foreign_keys=[coach_assigned_by])
    psicologa = db.relationship('User', foreign_keys=[psicologa_assigned_id])
    psicologa_assigner = db.relationship('User', foreign_keys=[psicologa_assigned_by])

    def update_status(self):
        """Aggiorna automaticamente lo status basato sulle assegnazioni"""
        if self.nutrizionista_assigned_id and self.coach_assigned_id and self.psicologa_assigned_id:
            if self.checkup_iniziale_fatto:
                self.status = 'active'
            else:
                self.status = 'fully_assigned'
        elif self.nutrizionista_assigned_id or self.coach_assigned_id or self.psicologa_assigned_id:
            self.status = 'partially_assigned'
        elif self.finance_approved:
            self.status = 'assigning'
        else:
            self.status = 'pending_finance'

    def __repr__(self):
        return f'<ServiceAssignment Cliente:{self.cliente_id} Status:{self.status}>'


class ServiceClienteNote(TimestampMixin, db.Model):
    """
    Note storicizzate del servizio clienti per tracciare tutte le interazioni.
    """
    __tablename__ = 'service_cliente_notes'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('service_cliente_assignments.id'), nullable=False)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)

    # Nota
    note_text = db.Column(db.Text, nullable=False)
    note_type = db.Column(db.String(50))

    # Autore
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Visibilità
    visible_to_client = db.Column(db.Boolean, default=False)
    visible_to_professionals = db.Column(db.Boolean, default=True)

    # Relazioni
    assignment = db.relationship('ServiceClienteAssignment', backref='notes')
    cliente = db.relationship('Cliente', backref='service_notes')
    author = db.relationship('User', backref='service_notes_written')

    def __repr__(self):
        return f'<ServiceNote Cliente:{self.cliente_id} Type:{self.note_type}>'


class ProfessionistCapacity(TimestampMixin, db.Model):
    """
    Gestione della capienza dei professionisti per l'assegnazione automatica.
    Utilizza conteggio semplice dei clienti attivi.
    """
    __tablename__ = 'professionist_capacity'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'role_type', name='_user_role_capacity_uc'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    # Tipo di ruolo
    role_type = db.Column(db.String(20), nullable=False)

    # Capienza
    max_clients = db.Column(db.Integer, nullable=False, default=50)
    current_clients = db.Column(db.Integer, default=0)

    # Disponibilità
    is_available = db.Column(db.Boolean, default=True, index=True)
    available_from = db.Column(db.Date)
    available_until = db.Column(db.Date)

    # Preferenze orarie
    preferred_shift = db.Column(db.String(20))
    working_days = db.Column(ARRAY(db.Integer))

    # Specializzazioni per AI matching
    specializations = db.Column(JSONB)
    expertise_keywords = db.Column(db.Text)

    # Performance metrics per AI
    client_satisfaction_avg = db.Column(db.Numeric(3, 2))
    retention_rate = db.Column(db.Numeric(5, 2))

    # Relazioni
    user = db.relationship('User', backref='professional_capacity')

    @property
    def availability_percentage(self):
        """Calcola percentuale di disponibilità"""
        if self.max_clients == 0:
            return 0
        return round((1 - self.current_clients / self.max_clients) * 100, 2)

    def has_capacity(self):
        """Verifica se ha ancora posti liberi"""
        return self.is_available and self.current_clients < self.max_clients

    def __repr__(self):
        return f'<Capacity {self.role_type} User:{self.user_id} {self.current_clients}/{self.max_clients}>'


# --------------------------------------------------------------------------- #
#  Meeting (Google Calendar Integration)
# --------------------------------------------------------------------------- #
class Meeting(TimestampMixin, db.Model):
    """
    Meeting/Eventi Google Calendar associati ai clienti.

    Permette di:
    - Sincronizzare eventi da Google Calendar
    - Associare meeting ai clienti
    - Tracciare esito delle call, note e link Loom
    - Gestire meeting direttamente dalla suite
    """
    __tablename__ = "meetings"
    __versioned__ = {}  # Abilita versioning per tracciare modifiche

    # ────────────────────────── CHIAVE PRIMARIA ───────────────────────────
    id = db.Column(db.Integer, primary_key=True)

    # ────────────────────────── GOOGLE CALENDAR ───────────────────────────
    google_event_id = db.Column(
        db.String(255),
        unique=True,
        index=True,
        nullable=True,  # Reso nullable per supportare eventi GHL senza Google
        comment="ID univoco dell'evento in Google Calendar"
    )

    # ────────────────────────── GHL (GO HIGH LEVEL) ─────────────────────────
    ghl_event_id = db.Column(
        db.String(255),
        unique=True,
        index=True,
        nullable=True,
        comment="ID univoco dell'evento in Go High Level"
    )

    # ────────────────────────── INFORMAZIONI EVENTO ───────────────────────
    title = db.Column(
        db.String(255),
        nullable=False,
        comment="Titolo dell'evento/meeting"
    )

    description = db.Column(
        db.Text,
        comment="Descrizione dell'evento"
    )

    start_time = db.Column(
        db.DateTime,
        nullable=False,
        index=True,
        comment="Data e ora di inizio meeting"
    )

    end_time = db.Column(
        db.DateTime,
        nullable=False,
        index=True,
        comment="Data e ora di fine meeting"
    )

    # ────────────────────────── ASSOCIAZIONE CLIENTE ──────────────────────
    cliente_id = db.Column(
        db.BigInteger,
        db.ForeignKey("clienti.cliente_id", ondelete="CASCADE"),
        nullable=True,  # Permette meeting senza cliente associato
        index=True,
        comment="Cliente associato al meeting (opzionale)"
    )

    # ────────────────────────── ASSOCIAZIONE USER ──────────────────────────
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User che gestisce/ha creato il meeting"
    )

    # ────────────────────────── GESTIONE MEETING ──────────────────────────
    meeting_outcome = db.Column(
        db.Text,
        comment="Esito della call/meeting"
    )

    meeting_notes = db.Column(
        db.Text,
        comment="Note del meeting"
    )

    loom_link = db.Column(
        db.String(500),
        comment="Link alla registrazione Loom del meeting"
    )

    meeting_link = db.Column(
        db.String(500),
        comment="Link al meeting online (Google Meet, Zoom, etc.)"
    )

    location = db.Column(
        db.String(500),
        comment="Luogo del meeting"
    )

    # ────────────────────────── STATO E METADATI ──────────────────────────
    status = db.Column(
        db.String(50),
        default="scheduled",
        comment="Stato del meeting: scheduled, completed, cancelled, no_show"
    )

    event_category = db.Column(
        db.String(50),
        nullable=True,
        index=True,
        comment="Categoria del meeting: call_iniziale, call_periodica, call_1_sales, call_2_sales, call_interna, call_customer_care, call_onboarding, call_followup"
    )

    # ────────────────────────── RELAZIONI ──────────────────────────────────
    cliente = db.relationship(
        "Cliente",
        backref=db.backref("meetings", lazy="dynamic", cascade="all, delete-orphan")
    )

    user = db.relationship(
        "User",
        backref=db.backref("meetings", lazy="dynamic")
    )

    # ────────────────────────── METODI ─────────────────────────────────────
    def __repr__(self) -> str:
        return f"<Meeting {self.id}: {self.title} ({self.start_time})>"

    @property
    def duration_minutes(self) -> int:
        """Calcola la durata del meeting in minuti."""
        if self.start_time and self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() / 60)
        return 0


# ─────────────────────────── CLIENT CHECKS MODELS ─────────────────────────── #

# ─────────────────────────── CLIENT CHECKS MODELS ─────────────────────────── #

# ENUM per Client Checks
class CheckFormTypeEnum(str, Enum):
    """Tipo di check form."""
    iniziale = "iniziale"
    settimanale = "settimanale"


class CheckFormStatusEnum(str, Enum):
    """Stato del form di controllo."""
    draft = "draft"
    active = "active"
    inactive = "inactive"
    archived = "archived"


class CheckFormFieldTypeEnum(str, Enum):
    """Tipo di campo del form."""
    text = "text"
    number = "number"
    email = "email"
    textarea = "textarea"
    select = "select"
    multiselect = "multiselect"
    radio = "radio"
    checkbox = "checkbox"
    scale = "scale"
    date = "date"
    file = "file"
    rating = "rating"
    yesno = "yesno"


class AssignmentStatusEnum(str, Enum):
    """Stato dell'assegnazione."""
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    overdue = "overdue"
    cancelled = "cancelled"


class CheckForm(TimestampMixin, db.Model):
    """
    Template di un form per check clienti.
    Può essere di tipo 'iniziale' o 'settimanale'.
    """
    __tablename__ = 'check_forms'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False, comment="Nome del form")
    description = db.Column(db.Text, comment="Descrizione del form")
    form_type = db.Column(
        db.Enum(CheckFormTypeEnum, name='checkformtypeenum', schema='public'),
        nullable=False,
        comment="Tipo di check: iniziale o settimanale"
    )
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="Form attivo/disattivo")
    
    # Relazioni
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=True)
    
    # Relationships
    created_by = relationship("User", backref="created_check_forms")
    department = relationship("Department", backref="check_forms")
    fields = relationship(
        "CheckFormField", 
        back_populates="form", 
        cascade="all, delete-orphan",
        order_by="CheckFormField.position"
    )
    assignments = relationship(
        "ClientCheckAssignment", 
        back_populates="form", 
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CheckForm {self.name!r} ({self.form_type})>"

    @property
    def total_assignments(self) -> int:
        """Numero totale di assegnazioni."""
        return len(self.assignments)

    @property
    def total_responses(self) -> int:
        """Numero totale di risposte ricevute."""
        return sum(assignment.response_count for assignment in self.assignments)


class CheckFormField(TimestampMixin, db.Model):
    """
    Campo di un form check.
    Supporta diversi tipi di input con opzioni personalizzabili.
    """
    __tablename__ = 'check_form_fields'

    id = db.Column(db.Integer, primary_key=True)
    form_id = db.Column(db.Integer, db.ForeignKey('check_forms.id'), nullable=False)
    label = db.Column(db.String(255), nullable=False, comment="Etichetta del campo")
    field_type = db.Column(
        db.Enum(CheckFormFieldTypeEnum, name='checkformfieldtypeenum', schema='public'),
        nullable=False,
        comment="Tipo di campo"
    )
    is_required = db.Column(db.Boolean, default=False, nullable=False, comment="Campo obbligatorio")
    position = db.Column(db.Integer, nullable=False, comment="Posizione nel form")
    
    # Opzioni per campi specifici (JSON)
    options = db.Column(JSONB, comment="Opzioni per select/radio/checkbox/scale")
    placeholder = db.Column(db.String(255), comment="Placeholder per campi di testo")
    help_text = db.Column(db.Text, comment="Testo di aiuto")
    
    # Relationships
    form = relationship("CheckForm", back_populates="fields")

    def __repr__(self) -> str:
        return f"<CheckFormField {self.label!r} ({self.field_type})>"

    @property
    def select_options(self) -> List[str]:
        """Lista opzioni per campi select/radio/checkbox."""
        if self.field_type in ['select', 'radio', 'checkbox'] and self.options:
            return self.options.get('choices', [])
        return []

    @property
    def scale_range(self) -> tuple[int, int]:
        """Range per campi scale (min, max)."""
        if self.field_type == 'scale' and self.options:
            return (
                self.options.get('min', 1),
                self.options.get('max', 10)
            )
        return (1, 10)


class ClientCheckAssignment(TimestampMixin, db.Model):
    """
    Assegnazione di un form check a un cliente specifico.
    Genera un token univoco per l'accesso pubblico.
    """
    __tablename__ = 'client_check_assignments'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    form_id = db.Column(db.Integer, db.ForeignKey('check_forms.id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, comment="Token univoco per accesso pubblico")
    
    # Statistiche
    response_count = db.Column(db.Integer, default=0, nullable=False, comment="Numero di compilazioni")
    last_response_at = db.Column(db.DateTime, comment="Data ultima compilazione")
    
    # Metadati
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="Assegnazione attiva")
    
    # Relationships
    cliente = relationship("Cliente", backref="check_assignments")
    form = relationship("CheckForm", back_populates="assignments")
    assigned_by = relationship("User", backref="assigned_check_forms")
    responses = relationship(
        "ClientCheckResponse", 
        back_populates="assignment", 
        cascade="all, delete-orphan",
        order_by="ClientCheckResponse.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<ClientCheckAssignment Cliente:{self.cliente_id} Form:{self.form_id}>"

    @classmethod
    def generate_token(cls) -> str:
        """Genera un token univoco per l'assignment."""
        import secrets
        return secrets.token_urlsafe(32)

    def get_public_url(self, base_url: str = "") -> str:
        """Genera l'URL pubblico per la compilazione."""
        return f"{base_url}/client-checks/public/{self.token}"

    @property
    def latest_response(self) -> ClientCheckResponse | None:
        """Ultima risposta ricevuta."""
        return self.responses[0] if self.responses else None

    def update_response_stats(self) -> None:
        """Aggiorna le statistiche di risposta."""
        self.response_count = len(self.responses)
        if self.responses:
            self.last_response_at = self.responses[0].created_at


class ClientCheckResponse(TimestampMixin, db.Model):
    """
    Risposta compilata da un cliente per un form check.
    Salva tutte le risposte in formato JSON.
    """
    __tablename__ = 'client_check_responses'

    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('client_check_assignments.id'), nullable=False)
    
    # Dati della compilazione
    responses = db.Column(JSONB, nullable=False, comment="Risposte in formato JSON")
    ip_address = db.Column(db.String(45), comment="IP del compilatore")
    user_agent = db.Column(db.Text, comment="User agent del browser")
    
    # Notifiche
    notifications_sent = db.Column(db.Boolean, default=False, nullable=False, comment="Notifiche inviate")
    notifications_sent_at = db.Column(db.DateTime, comment="Data invio notifiche")
    
    # Relationships
    assignment = relationship("ClientCheckAssignment", back_populates="responses")

    def __repr__(self) -> str:
        return f"<ClientCheckResponse Assignment:{self.assignment_id} {self.created_at}>"

    @property
    def cliente(self):
        """Cliente che ha compilato il form."""
        return self.assignment.cliente if self.assignment else None

    @property
    def form(self):
        """Form compilato."""
        return self.assignment.form if self.assignment else None

    def get_response_value(self, field_id: int):
        """Ottiene il valore di risposta per un campo specifico."""
        if self.responses and isinstance(self.responses, dict):
            return self.responses.get(str(field_id))
        return None

    def get_formatted_responses(self) -> dict:
        """Ottiene le risposte formattate con le etichette dei campi."""
        if not self.assignment or not self.assignment.form:
            return {}
        
        formatted = {}
        for field in self.assignment.form.fields:
            value = self.get_response_value(field.id)
            if value is not None:
                formatted[field.label] = value
        
        return formatted

    def mark_notifications_sent(self) -> None:
        """Marca le notifiche come inviate."""
        self.notifications_sent = True
        self.notifications_sent_at = datetime.utcnow()


class ClientCheckReadConfirmation(TimestampMixin, db.Model):
    """
    Conferma di lettura di un check da parte di un professionista.
    Permette di tracciare quali professionisti hanno letto quali check.
    Supporta sia WeeklyCheckResponse che DCACheckResponse tramite approccio polimorfico.
    """
    __tablename__ = 'client_check_read_confirmations'

    id = db.Column(db.Integer, primary_key=True)
    response_type = db.Column(db.String(50), nullable=False, comment="Tipo di check: 'weekly_check' o 'dca_check'")
    response_id = db.Column(db.Integer, nullable=False, comment="ID del check letto")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment="Professionista che ha letto")
    read_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, comment="Data e ora di lettura")

    # Relationships
    user = relationship("User", backref="check_read_confirmations")

    # Unique constraint: un professionista può confermare la lettura di un check una sola volta
    __table_args__ = (
        db.UniqueConstraint('response_type', 'response_id', 'user_id', name='uq_type_response_user_read'),
    )

    def __repr__(self) -> str:
        return f"<ClientCheckReadConfirmation {self.response_type}:{self.response_id} User:{self.user_id}>"

    @property
    def response(self):
        """Ottiene la risposta associata in base al tipo."""
        if self.response_type == 'weekly_check':
            return WeeklyCheckResponse.query.get(self.response_id)
        elif self.response_type == 'dca_check':
            return DCACheckResponse.query.get(self.response_id)
        return None


# ══════════════════════════════════════════════════════════════════════════ #
#                           WEEKLY CHECK 2.0                                    #
# ══════════════════════════════════════════════════════════════════════════ #

class WeeklyCheck(TimestampMixin, db.Model):
    """
    Assignment PERMANENTE per Check Settimanale "Check Normale" 2.0.

    QUESTO È IL LINK PERMANENTE - non contiene i dati delle compilazioni!
    I dati delle compilazioni sono in WeeklyCheckResponse.

    Il cliente usa sempre lo stesso link per compilare il check più volte.
    """
    __tablename__ = 'weekly_checks'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.cliente_id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True, comment="Token univoco PERMANENTE per link")

    # ─── Assignment Info ────────────────────────────────────────────────────
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="Assignment attivo (link valido)")
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment="Chi ha assegnato il check")
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, comment="Data assegnazione")
    deactivated_at = db.Column(db.DateTime, comment="Data disattivazione link")
    deactivated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment="Chi ha disattivato")

    # ─── Relationships ──────────────────────────────────────────────────────
    cliente = relationship("Cliente", back_populates="weekly_checks")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    deactivated_by = relationship("User", foreign_keys=[deactivated_by_id])
    responses = relationship("WeeklyCheckResponse", back_populates="assignment",
                           lazy='dynamic', order_by="desc(WeeklyCheckResponse.submit_date)")

    def __repr__(self) -> str:
        return f"<WeeklyCheck(id={self.id}, cliente={self.cliente_id}, active={self.is_active})>"

    @property
    def response_count(self) -> int:
        """Numero totale di compilazioni ricevute."""
        return self.responses.count()

    @property
    def last_response(self):
        """Ultima compilazione ricevuta."""
        return self.responses.first()

    @property
    def last_response_date(self):
        """Data ultima compilazione."""
        last = self.last_response
        return last.submit_date if last else None


class WeeklyCheckResponse(TimestampMixin, db.Model):
    """
    Singola COMPILAZIONE di un Check Settimanale.

    Ogni volta che il cliente compila il form, si crea un nuovo record qui.
    Il link rimane sempre lo stesso (WeeklyCheck.token).
    """
    __tablename__ = 'weekly_check_responses'

    id = db.Column(db.Integer, primary_key=True)
    weekly_check_id = db.Column(db.Integer, db.ForeignKey('weekly_checks.id'), nullable=False, index=True)

    # ─── Metadata Compilazione ──────────────────────────────────────────────
    submit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True, comment="Data compilazione")
    ip_address = db.Column(db.String(45), comment="IP compilatore")
    user_agent = db.Column(db.Text, comment="User agent browser")

    # ─── Foto Fisico (3 campi) ──────────────────────────────────────────────
    photo_front = db.Column(db.String(500), comment="URL foto fisico frontale")
    photo_side = db.Column(db.String(500), comment="URL foto fisico laterale")
    photo_back = db.Column(db.String(500), comment="URL foto fisico posteriore")

    # ─── Domande Aperte (13 campi) ──────────────────────────────────────────
    what_worked = db.Column(db.Text, comment="Cosa ha funzionato bene la settimana scorsa")
    what_didnt_work = db.Column(db.Text, comment="Cosa NON ha funzionato bene")
    what_learned = db.Column(db.Text, comment="Cosa hai imparato")
    what_focus_next = db.Column(db.Text, comment="Su cosa focalizzarci la prossima settimana")
    injuries_notes = db.Column(db.Text, comment="Infortuni o note importanti")
    nutrition_program_adherence = db.Column(db.Text, comment="Rispetto programma alimentare")
    training_program_adherence = db.Column(db.Text, comment="Rispetto programma sportivo")
    exercise_modifications = db.Column(db.Text, comment="Esercizi non fatti o aggiunti")
    daily_steps = db.Column(db.Text, comment="Passi medi giornalieri")
    completed_training_weeks = db.Column(db.Text, comment="Settimane allenamento rispettate al 100%")
    planned_training_days = db.Column(db.Text, comment="Giorni allenamento pianificati")
    live_session_topics = db.Column(db.Text, comment="Tematiche per LIVE settimanali")
    extra_comments = db.Column(db.Text, comment="Commenti extra")

    # ─── Valutazioni 0-10 (7 campi base) ────────────────────────────────────
    digestion_rating = db.Column(db.Integer, comment="Valutazione digestione (0-10)")
    energy_rating = db.Column(db.Integer, comment="Valutazione energia (0-10)")
    strength_rating = db.Column(db.Integer, comment="Valutazione forza (0-10)")
    hunger_rating = db.Column(db.Integer, comment="Valutazione fame (0-10)")
    sleep_rating = db.Column(db.Integer, comment="Valutazione sonno (0-10)")
    mood_rating = db.Column(db.Integer, comment="Valutazione umore (0-10)")
    motivation_rating = db.Column(db.Integer, comment="Valutazione motivazione (0-10)")

    # ─── Peso ───────────────────────────────────────────────────────────────
    weight = db.Column(db.Float, comment="Peso in Kg")

    # ─── Valutazioni Professionisti (con feedback) ──────────────────────────
    nutritionist_rating = db.Column(db.Integer, comment="Valutazione nutrizionista (1-10)")
    nutritionist_feedback = db.Column(db.Text, comment="Feedback nutrizionista")
    psychologist_rating = db.Column(db.Integer, comment="Valutazione psicologo (1-10)")
    psychologist_feedback = db.Column(db.Text, comment="Feedback psicologo")
    coach_rating = db.Column(db.Integer, comment="Valutazione coach (1-10)")
    coach_feedback = db.Column(db.Text, comment="Feedback coach")

    # ─── Valutazione Generale ───────────────────────────────────────────────
    progress_rating = db.Column(db.Integer, comment="Valutazione percorso complessivo (1-10)")
    coordinator_rating = db.Column(db.Integer, comment="Voto coordinatore (sostituisce progress_rating nel calcolo Quality se presente)")
    coordinator_notes = db.Column(db.Text, comment="Note obbligatorie del coordinatore")
    referral = db.Column(db.Text, comment="Persona da contattare (nome, telefono, email)")

    # ─── Relationships ──────────────────────────────────────────────────────
    assignment = relationship("WeeklyCheck", back_populates="responses")

    def __repr__(self) -> str:
        return f"<WeeklyCheckResponse(id={self.id}, check={self.weekly_check_id}, date={self.submit_date})>"

    @property
    def completion_percentage(self) -> int:
        """Calcola la percentuale di completamento."""
        total_fields = 29
        completed = 0

        # Conta campi compilati
        if self.photo_front: completed += 1
        if self.photo_side: completed += 1
        if self.photo_back: completed += 1
        if self.what_worked: completed += 1
        if self.what_didnt_work: completed += 1
        if self.what_learned: completed += 1
        if self.what_focus_next: completed += 1
        if self.injuries_notes: completed += 1
        if self.digestion_rating is not None: completed += 1
        if self.energy_rating is not None: completed += 1
        if self.strength_rating is not None: completed += 1
        if self.hunger_rating is not None: completed += 1
        if self.sleep_rating is not None: completed += 1
        if self.mood_rating is not None: completed += 1
        if self.motivation_rating is not None: completed += 1
        if self.weight is not None: completed += 1
        if self.nutrition_program_adherence: completed += 1
        if self.training_program_adherence: completed += 1
        if self.exercise_modifications: completed += 1
        if self.daily_steps: completed += 1
        if self.completed_training_weeks: completed += 1
        if self.planned_training_days: completed += 1
        if self.live_session_topics: completed += 1
        if self.nutritionist_rating is not None: completed += 1
        if self.psychologist_rating is not None: completed += 1
        if self.coach_rating is not None: completed += 1
        if self.progress_rating is not None: completed += 1
        if self.referral: completed += 1
        if self.extra_comments: completed += 1

        return int((completed / total_fields) * 100)


# ═══════════════════════════════════════════════════════════════════════════ #
#  MINOR CHECK - EDE-Q6 (Check Minori)                                        #
# ═══════════════════════════════════════════════════════════════════════════ #

class MinorCheck(TimestampMixin, db.Model):
    """
    Assignment PERMANENTE per Check Minori (EDE-Q6).

    QUESTO È IL LINK PERMANENTE - non contiene i dati delle compilazioni!
    I dati delle compilazioni sono in MinorCheckResponse.

    Il cliente usa sempre lo stesso link per compilare il check più volte.
    """
    __tablename__ = 'minor_checks'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.cliente_id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True, comment="Token univoco PERMANENTE per link")

    # ─── Assignment Info ────────────────────────────────────────────────────
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="Assignment attivo (link valido)")
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment="Chi ha assegnato il check")
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, comment="Data assegnazione")
    deactivated_at = db.Column(db.DateTime, comment="Data disattivazione link")
    deactivated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment="Chi ha disattivato")

    # ─── Relationships ──────────────────────────────────────────────────────
    cliente = relationship("Cliente", back_populates="minor_checks")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    deactivated_by = relationship("User", foreign_keys=[deactivated_by_id])
    responses = relationship("MinorCheckResponse", back_populates="assignment",
                           lazy='dynamic', order_by="desc(MinorCheckResponse.submit_date)")

    def __repr__(self) -> str:
        return f"<MinorCheck(id={self.id}, cliente={self.cliente_id}, active={self.is_active})>"

    @property
    def response_count(self) -> int:
        """Numero totale di compilazioni ricevute."""
        return self.responses.count()

    @property
    def last_response(self):
        """Ultima compilazione ricevuta."""
        return self.responses.first()

    @property
    def last_response_date(self):
        """Data ultima compilazione."""
        last = self.last_response
        return last.submit_date if last else None


class MinorCheckResponse(TimestampMixin, db.Model):
    """
    Singola COMPILAZIONE di un Check Minori (EDE-Q6).

    Ogni volta che il cliente compila il form, si crea un nuovo record qui.
    Il link rimane sempre lo stesso (MinorCheck.token).

    EDE-Q6 = Eating Disorder Examination Questionnaire (versione breve 6 domande + 22 comportamentali)
    """
    __tablename__ = 'minor_check_responses'

    id = db.Column(db.Integer, primary_key=True)
    minor_check_id = db.Column(db.Integer, db.ForeignKey('minor_checks.id'), nullable=False, index=True)

    # ─── Metadata Compilazione ──────────────────────────────────────────────
    submit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True, comment="Data compilazione")
    ip_address = db.Column(db.String(45), comment="IP compilatore")
    user_agent = db.Column(db.Text, comment="User agent browser")

    # ─── Peso e Altezza ─────────────────────────────────────────────────────
    peso_attuale = db.Column(db.Float, comment="Peso attuale in Kg")
    altezza = db.Column(db.Float, comment="Altezza in cm")

    # ─── EDE-Q6 Risposte (JSONB per flessibilità) ───────────────────────────
    # Le 28 domande del questionario EDE-Q6 sono salvate come JSON
    # Struttura: {"q1": 0-6, "q2": 0-6, ..., "q28": 0-6}
    # Domande 1-12: Scale 0-6 (frequenza)
    # Domande 13-18: Scale 0-6 (intensità preoccupazione)
    # Domande 19-28: Comportamenti (scale diverse o input numerici)
    responses_data = db.Column(db.JSON, nullable=False, default=dict, comment="Risposte EDE-Q6 in formato JSON")

    # ─── Punteggi Calcolati ─────────────────────────────────────────────────
    score_restraint = db.Column(db.Float, comment="Punteggio sottoscala Restrizione")
    score_eating_concern = db.Column(db.Float, comment="Punteggio sottoscala Preoccupazione Alimentare")
    score_shape_concern = db.Column(db.Float, comment="Punteggio sottoscala Preoccupazione Forma")
    score_weight_concern = db.Column(db.Float, comment="Punteggio sottoscala Preoccupazione Peso")
    score_global = db.Column(db.Float, comment="Punteggio Globale EDE-Q")

    # ─── Relationships ──────────────────────────────────────────────────────
    assignment = relationship("MinorCheck", back_populates="responses")

    def __repr__(self) -> str:
        return f"<MinorCheckResponse(id={self.id}, check={self.minor_check_id}, date={self.submit_date})>"

    def calculate_scores(self):
        """
        Calcola i punteggi delle sottoscale e il punteggio globale EDE-Q.

        Sottoscale EDE-Q6:
        - Restrizione (Restraint): domande 1, 2, 3, 4, 5
        - Preoccupazione Alimentare (Eating Concern): domande 7, 9, 19, 21
        - Preoccupazione Forma (Shape Concern): domande 6, 8, 10, 11, 23, 26, 27, 28
        - Preoccupazione Peso (Weight Concern): domande 8, 12, 22, 24, 25

        Nota: la domanda 8 contribuisce sia a Shape che a Weight concern.
        """
        if not self.responses_data:
            return

        data = self.responses_data

        # Helper per ottenere valore numerico
        def get_val(key):
            val = data.get(key)
            if val is not None and isinstance(val, (int, float)):
                return float(val)
            return None

        # Restrizione (5 items: q1-q5)
        restraint_items = [get_val(f'q{i}') for i in range(1, 6)]
        restraint_valid = [v for v in restraint_items if v is not None]
        if restraint_valid:
            self.score_restraint = sum(restraint_valid) / len(restraint_valid)

        # Preoccupazione Alimentare (4 items: q7, q9, q19, q21)
        eating_items = [get_val('q7'), get_val('q9'), get_val('q19'), get_val('q21')]
        eating_valid = [v for v in eating_items if v is not None]
        if eating_valid:
            self.score_eating_concern = sum(eating_valid) / len(eating_valid)

        # Preoccupazione Forma (8 items: q6, q8, q10, q11, q23, q26, q27, q28)
        shape_items = [get_val('q6'), get_val('q8'), get_val('q10'), get_val('q11'),
                       get_val('q23'), get_val('q26'), get_val('q27'), get_val('q28')]
        shape_valid = [v for v in shape_items if v is not None]
        if shape_valid:
            self.score_shape_concern = sum(shape_valid) / len(shape_valid)

        # Preoccupazione Peso (5 items: q8, q12, q22, q24, q25)
        weight_items = [get_val('q8'), get_val('q12'), get_val('q22'), get_val('q24'), get_val('q25')]
        weight_valid = [v for v in weight_items if v is not None]
        if weight_valid:
            self.score_weight_concern = sum(weight_valid) / len(weight_valid)

        # Punteggio Globale (media delle 4 sottoscale)
        subscales = [self.score_restraint, self.score_eating_concern,
                     self.score_shape_concern, self.score_weight_concern]
        subscales_valid = [s for s in subscales if s is not None]
        if subscales_valid:
            self.score_global = sum(subscales_valid) / len(subscales_valid)

    @property
    def completion_percentage(self) -> int:
        """Calcola la percentuale di completamento."""
        if not self.responses_data:
            return 0

        # 28 domande totali + peso + altezza = 30 campi
        total_fields = 30
        completed = 0

        if self.peso_attuale is not None:
            completed += 1
        if self.altezza is not None:
            completed += 1

        # Conta risposte compilate
        for i in range(1, 29):
            if self.responses_data.get(f'q{i}') is not None:
                completed += 1

        return int((completed / total_fields) * 100)


# Aggiungi relationship in Cliente
Cliente.weekly_checks = relationship("WeeklyCheck", back_populates="cliente", lazy='dynamic',
                                    order_by="desc(WeeklyCheck.assigned_at)")

Cliente.minor_checks = relationship("MinorCheck", back_populates="cliente", lazy='dynamic',
                                   order_by="desc(MinorCheck.assigned_at)")


# ═══════════════════════════════════════════════════════════════════════════ #
#  WEEKLY CHECK LINK ASSIGNMENT (Assignment invio link ai professionisti)     #
# ═══════════════════════════════════════════════════════════════════════════ #

class WeeklyCheckLinkAssignment(TimestampMixin, db.Model):
    """
    Traccia l'assegnazione dell'invio del link WeeklyCheck a un professionista specifico.

    Sistema di bilanciamento: per ogni cliente con più professionisti assegnati,
    viene scelto UN SOLO professionista per l'invio del link, bilanciando il carico.
    """
    __tablename__ = 'weekly_check_link_assignments'

    id = db.Column(db.Integer, primary_key=True)

    # Assignment info
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False,
                          comment="Cliente a cui inviare il link")
    weekly_check_id = db.Column(db.Integer, db.ForeignKey('weekly_checks.id'), nullable=False,
                               comment="Link WeeklyCheck da inviare")
    assigned_to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False,
                                   comment="Professionista che deve inviare il link")

    # Tracking invio
    sent_confirmed = db.Column(db.Boolean, default=False, nullable=False,
                              comment="Professionista ha confermato l'invio")
    sent_at = db.Column(db.DateTime, comment="Data/ora conferma invio")
    notes = db.Column(db.Text, comment="Note del professionista")

    # Relationships
    cliente = relationship("Cliente")
    weekly_check = relationship("WeeklyCheck")
    assigned_to = relationship("User", backref="weekly_check_link_assignments")

    # Unique constraint: un cliente può avere solo un assignment attivo
    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'weekly_check_id', name='uq_cliente_weekly_check_assignment'),
    )

    def __repr__(self):
        status = "✅ Inviato" if self.sent_confirmed else "⏳ Da inviare"
        return f"<WeeklyCheckLinkAssignment {self.cliente_id} → {self.assigned_to.full_name if self.assigned_to else 'N/A'} [{status}]>"


# ═══════════════════════════════════════════════════════════════════════════ #
#  DCA CHECK MODEL (Check per Disturbi del Comportamento Alimentare)          #
# ═══════════════════════════════════════════════════════════════════════════ #

class DCACheck(TimestampMixin, db.Model):
    """
    Assignment PERMANENTE per Check DCA (Disturbi del Comportamento Alimentare).

    QUESTO È IL LINK PERMANENTE - non contiene i dati delle compilazioni!
    I dati delle compilazioni sono in DCACheckResponse.

    Il cliente usa sempre lo stesso link per compilare il check più volte.
    """
    __tablename__ = 'dca_checks'

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('clienti.cliente_id'), nullable=False)
    token = db.Column(db.String(64), unique=True, nullable=False, index=True, comment="Token univoco PERMANENTE per link")

    # ─── Assignment Info ────────────────────────────────────────────────────
    is_active = db.Column(db.Boolean, default=True, nullable=False, comment="Assignment attivo (link valido)")
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment="Chi ha assegnato il check")
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, comment="Data assegnazione")
    deactivated_at = db.Column(db.DateTime, comment="Data disattivazione link")
    deactivated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), comment="Chi ha disattivato")

    # ─── Relationships ──────────────────────────────────────────────────────
    cliente = relationship("Cliente", back_populates="dca_checks")
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])
    deactivated_by = relationship("User", foreign_keys=[deactivated_by_id])
    responses = relationship("DCACheckResponse", back_populates="assignment",
                           lazy='dynamic', order_by="desc(DCACheckResponse.submit_date)")

    def __repr__(self) -> str:
        return f"<DCACheck(id={self.id}, cliente={self.cliente_id}, active={self.is_active})>"

    @property
    def response_count(self) -> int:
        """Numero totale di compilazioni ricevute."""
        return self.responses.count()

    @property
    def last_response(self):
        """Ultima compilazione ricevuta."""
        return self.responses.first()

    @property
    def last_response_date(self):
        """Data ultima compilazione."""
        last = self.last_response
        return last.submit_date if last else None


class DCACheckResponse(TimestampMixin, db.Model):
    """
    Singola COMPILAZIONE di un Check DCA.

    Ogni volta che il cliente compila il form DCA, si crea un nuovo record qui.
    Il link rimane sempre lo stesso (DCACheck.token).

    Include 32 domande focalizzate su aspetti psicologici ed emotivi.
    NON include foto fisiche né valutazioni professionisti.
    """
    __tablename__ = 'dca_check_responses'

    id = db.Column(db.Integer, primary_key=True)
    dca_check_id = db.Column(db.Integer, db.ForeignKey('dca_checks.id'), nullable=False, index=True)

    # ─── Metadata Compilazione ──────────────────────────────────────────────
    submit_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True, comment="Data compilazione")
    ip_address = db.Column(db.String(45), comment="IP compilatore")
    user_agent = db.Column(db.Text, comment="User agent browser")

    # ─── BENESSERE EMOTIVO E PSICOLOGICO (Scala 1-5) ──────────────────────
    mood_balance_rating = db.Column(db.Integer, comment="Stato d'animo: umore, energia, equilibrio (1-5)")
    food_plan_serenity = db.Column(db.Integer, comment="Serenità nel seguire piano alimentare (1-5)")
    food_weight_worry = db.Column(db.Integer, comment="Preoccupazione per cibo, peso, corpo (1-5)")
    emotional_eating = db.Column(db.Integer, comment="Mangiare in risposta ad emozioni (1-5)")
    body_comfort = db.Column(db.Integer, comment="Comfort nel proprio corpo (1-5)")
    body_respect = db.Column(db.Integer, comment="Rispetto per il corpo (1-5)")

    # ─── ALLENAMENTO E MOVIMENTO (Scala 1-5) ──────────────────────────────
    exercise_wellness = db.Column(db.Integer, comment="Gestione allenamento come benessere (1-5)")
    exercise_guilt = db.Column(db.Integer, comment="Senso di colpa per allenamenti saltati (1-5)")

    # ─── RIPOSO E RELAZIONI (Scala 1-5) ───────────────────────────────────
    sleep_satisfaction = db.Column(db.Integer, comment="Qualità del riposo (1-5)")
    relationship_time = db.Column(db.Integer, comment="Tempo dedicato a relazioni significative (1-5)")
    personal_time = db.Column(db.Integer, comment="Tempo per attività piacevoli (1-5)")

    # ─── INTERFERENZE E GESTIONE (Scala 1-5) ──────────────────────────────
    life_interference = db.Column(db.Integer, comment="Interferenza percorso con lavoro/vita sociale (1-5)")
    unexpected_management = db.Column(db.Integer, comment="Gestione imprevisti senza colpa (1-5)")
    self_compassion = db.Column(db.Integer, comment="Compassione verso se stessi (1-5)")
    inner_dialogue = db.Column(db.Integer, comment="Dialogo interiore gentile (1-5)")

    # ─── SOSTENIBILITÀ E MOTIVAZIONE (Scala 1-5) ──────────────────────────
    long_term_sustainability = db.Column(db.Integer, comment="Sostenibilità percorso lungo termine (1-5)")
    values_alignment = db.Column(db.Integer, comment="Allineamento con valori e obiettivi (1-5)")
    motivation_level = db.Column(db.Integer, comment="Motivazione nel proseguire (1-5)")

    # ─── ORGANIZZAZIONE PASTI (Scala 1-5) ─────────────────────────────────
    meal_organization = db.Column(db.Integer, comment="Organizzazione pasti (1-5)")
    meal_stress = db.Column(db.Integer, comment="Stress da gestione pasti (1-5)")
    shopping_awareness = db.Column(db.Integer, comment="Spesa consapevole (1-5)")
    shopping_impact = db.Column(db.Integer, comment="Impatto spesa su tempo/budget (1-5)")
    meal_clarity = db.Column(db.Integer, comment="Chiarezza su cosa cucinare (1-5)")

    # ─── PARAMETRI FISICI (Scala 1-10, come check regolare) ───────────────
    digestion_rating = db.Column(db.Integer, comment="Valutazione digestione (1-10)")
    energy_rating = db.Column(db.Integer, comment="Valutazione energia (1-10)")
    strength_rating = db.Column(db.Integer, comment="Valutazione forza (1-10)")
    hunger_rating = db.Column(db.Integer, comment="Valutazione fame (1-10)")
    sleep_rating = db.Column(db.Integer, comment="Valutazione sonno (1-10)")
    mood_rating = db.Column(db.Integer, comment="Valutazione umore (1-10)")
    motivation_rating = db.Column(db.Integer, comment="Valutazione motivazione (1-10)")

    # ─── REFERRAL E COMMENTI ───────────────────────────────────────────────
    referral = db.Column(db.Text, comment="Persona da contattare")
    extra_comments = db.Column(db.Text, comment="Commenti extra")

    # ─── Relationships ──────────────────────────────────────────────────────
    assignment = relationship("DCACheck", back_populates="responses")

    def __repr__(self) -> str:
        return f"<DCACheckResponse(id={self.id}, check={self.dca_check_id}, date={self.submit_date})>"

    @property
    def completion_percentage(self) -> int:
        """Calcola la percentuale di completamento del check DCA."""
        total_fields = 32  # 23 campi 1-5 + 7 campi 1-10 + referral + extra_comments
        completed = 0

        # Campi benessere emotivo (1-5)
        if self.mood_balance_rating is not None: completed += 1
        if self.food_plan_serenity is not None: completed += 1
        if self.food_weight_worry is not None: completed += 1
        if self.emotional_eating is not None: completed += 1
        if self.body_comfort is not None: completed += 1
        if self.body_respect is not None: completed += 1

        # Allenamento (1-5)
        if self.exercise_wellness is not None: completed += 1
        if self.exercise_guilt is not None: completed += 1

        # Riposo e relazioni (1-5)
        if self.sleep_satisfaction is not None: completed += 1
        if self.relationship_time is not None: completed += 1
        if self.personal_time is not None: completed += 1

        # Interferenze (1-5)
        if self.life_interference is not None: completed += 1
        if self.unexpected_management is not None: completed += 1
        if self.self_compassion is not None: completed += 1
        if self.inner_dialogue is not None: completed += 1

        # Sostenibilità (1-5)
        if self.long_term_sustainability is not None: completed += 1
        if self.values_alignment is not None: completed += 1
        if self.motivation_level is not None: completed += 1

        # Organizzazione pasti (1-5)
        if self.meal_organization is not None: completed += 1
        if self.meal_stress is not None: completed += 1
        if self.shopping_awareness is not None: completed += 1
        if self.shopping_impact is not None: completed += 1
        if self.meal_clarity is not None: completed += 1

        # Parametri fisici (1-10)
        if self.digestion_rating is not None: completed += 1
        if self.energy_rating is not None: completed += 1
        if self.strength_rating is not None: completed += 1
        if self.hunger_rating is not None: completed += 1
        if self.sleep_rating is not None: completed += 1
        if self.mood_rating is not None: completed += 1
        if self.motivation_rating is not None: completed += 1

        # Referral e commenti
        if self.referral: completed += 1
        if self.extra_comments: completed += 1

        return int((completed / total_fields) * 100)


# Aggiungi relationship in Cliente
Cliente.dca_checks = relationship("DCACheck", back_populates="cliente", lazy='dynamic',
                                 order_by="desc(DCACheck.assigned_at)")


# ─────────────────────────── INDICI CLIENT CHECKS ─────────────────────────── #

# Indice per ricerca veloce assignment per cliente e form
Index(
    'ix_client_check_assignments_cliente_form',
    ClientCheckAssignment.cliente_id,
    ClientCheckAssignment.form_id
)

# Indice per token univoco
Index(
    'ix_client_check_assignments_token',
    ClientCheckAssignment.token,
    unique=True
)

# Indice per ricerca assignment attive
Index(
    'ix_client_check_assignments_active',
    ClientCheckAssignment.is_active,
    ClientCheckAssignment.created_at.desc()
)

# Indice per ricerca form per tipo
Index(
    'ix_check_forms_type_active',
    CheckForm.form_type,
    CheckForm.is_active
)

# ───────────────── CLIENTE FREEZE HISTORY ───────────────── #
class ClienteFreezeHistory(TimestampMixin, db.Model):
    """
    Storico dei freeze applicati ai clienti.
    Traccia tutti i freeze/unfreeze con motivazioni e risoluzioni.
    """
    __tablename__ = "cliente_freeze_history"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False, index=True)

    # Dati del freeze
    freeze_date = db.Column(db.DateTime, nullable=False)
    freeze_reason = db.Column(db.Text)  # Motivazione (opzionale)
    frozen_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Dati dell'unfreeze
    unfreeze_date = db.Column(db.DateTime)
    unfreeze_resolution = db.Column(db.Text)  # Storia/risoluzione
    unfrozen_by_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Status
    is_active = db.Column(db.Boolean, default=True)  # True = attualmente in freeze

    # Relazioni
    cliente = db.relationship('Cliente', back_populates='freeze_history')
    frozen_by = db.relationship('User', foreign_keys=[frozen_by_id], backref='freeze_actions')
    unfrozen_by = db.relationship('User', foreign_keys=[unfrozen_by_id], backref='unfreeze_actions')

    def __repr__(self):
        return f"<FreezeHistory cliente={self.cliente_id} date={self.freeze_date}>"


class ClienteProfessionistaHistory(TimestampMixin, db.Model):
    """
    Storico delle assegnazioni dei professionisti ai clienti.
    Traccia tutte le assegnazioni/interruzioni con motivazioni e date.
    """
    __tablename__ = "cliente_professionista_history"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)

    # Tipo di professionista (stored as string, validated with enum)
    tipo_professionista = db.Column(db.String(50), nullable=False, index=True)

    # Dati assegnazione
    data_dal = db.Column(db.Date, nullable=False)  # Data inizio assegnazione
    motivazione_aggiunta = db.Column(db.Text, nullable=False)  # Motivazione dell'assegnazione
    assegnato_da_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # Dati interruzione (NULL se ancora attivo)
    data_al = db.Column(db.Date)  # Data fine assegnazione
    motivazione_interruzione = db.Column(db.Text)  # Motivazione interruzione
    interrotto_da_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Status
    is_active = db.Column(db.Boolean, default=True, index=True)  # True = assegnazione ancora attiva

    # Relazioni
    cliente = db.relationship('Cliente', backref='professionisti_history')
    professionista = db.relationship('User', foreign_keys=[user_id], backref='assegnazioni_clienti')
    assegnato_da = db.relationship('User', foreign_keys=[assegnato_da_id], backref='assegnazioni_fatte')
    interrotto_da = db.relationship('User', foreign_keys=[interrotto_da_id], backref='interruzioni_fatte')

    def __repr__(self):
        status = "attivo" if self.is_active else "terminato"
        return f"<ProfessionistaHistory cliente={self.cliente_id} tipo={self.tipo_professionista} status={status}>"


class CallBonus(TimestampMixin, db.Model):
    """
    Gestione delle richieste di call bonus per i clienti.
    Traccia tutte le proposte di call bonus con i professionisti assegnati,
    la risposta del cliente e la conferma dell'health manager.
    """
    __tablename__ = "call_bonus"

    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"), nullable=False, index=True)

    # Professionista con cui è stata proposta la call bonus
    professionista_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    tipo_professionista = db.Column(
        _def(TipoProfessionistaEnum),
        nullable=False,
        index=True
    )

    # Stato della richiesta
    status = db.Column(
        _def(CallBonusStatusEnum),
        nullable=False,
        default=CallBonusStatusEnum.proposta,
        index=True
    )

    # Date
    data_richiesta = db.Column(db.Date, nullable=False, default=date.today, index=True)
    data_risposta = db.Column(db.Date)  # Quando il cliente ha accettato/rifiutato
    data_conferma_hm = db.Column(db.Date)  # Quando l'HM ha confermato/segnalato non andata a buon fine

    # Dettagli risposta cliente
    motivazione_rifiuto = db.Column(db.Text)  # Se rifiutata

    # Dettagli conferma Health Manager
    confermata_hm = db.Column(db.Boolean)  # True = confermata, False = non andata a buon fine
    note_hm = db.Column(db.Text)  # Note dell'health manager
    gestita_da_hm_id = db.Column(db.Integer, db.ForeignKey("users.id"))  # HM che ha gestito

    # Chi ha creato la richiesta
    created_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    # ========== CAMPI ARR (Adjusted Renewal Rate) ==========
    # Tracciamento conversione a pagamento per calcolo bonus professionisti
    convertito = db.Column(db.Boolean, default=False, comment="Se ha portato a un upgrade/pagamento")
    data_conversione = db.Column(db.Date, nullable=True, comment="Data conversione in pagamento")
    pagamento_id = db.Column(db.Integer, db.ForeignKey("pagamenti_interni.id"), nullable=True, index=True)

    # Relazioni
    cliente = db.relationship('Cliente', backref='call_bonus_history')
    professionista = db.relationship('User', foreign_keys=[professionista_id], backref='call_bonus_professionista')
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='call_bonus_create')
    gestita_da_hm = db.relationship('User', foreign_keys=[gestita_da_hm_id], backref='call_bonus_gestite')
    pagamento = db.relationship('PagamentoInterno', foreign_keys=[pagamento_id], backref='call_bonus_origine')

    def __repr__(self):
        return f"<CallBonus cliente={self.cliente_id} professionista={self.professionista_id} status={self.status.value}>"


# Indice per ricerca risposte per data
Index(
    'ix_client_check_responses_created_at',
    ClientCheckResponse.created_at.desc()
)

# Indice per ricerca risposte per assignment
Index(
    'ix_client_check_responses_assignment',
    ClientCheckResponse.assignment_id,
    ClientCheckResponse.created_at.desc()
)

# ═══════════════════════════════════════════════════════════════════
# FORM SALES SYSTEM - LEAD MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

# ───────────────── ENUM PER FORM SALES ───────────────── #
class LeadStatusEnum(str, Enum):
    """Stati del processo lead → cliente"""
    NEW = "NEW"                           # Form compilato
    CONTACTED = "CONTACTED"               # Primo contatto effettuato
    QUALIFIED = "QUALIFIED"               # Storia aggiunta, qualificato
    PROPOSAL_SENT = "PROPOSAL_SENT"       # Proposta inviata
    NEGOTIATING = "NEGOTIATING"           # In negoziazione
    PARTIAL_PAYMENT = "PARTIAL_PAYMENT"   # Acconto ricevuto
    FULL_PAYMENT = "FULL_PAYMENT"         # Pagamento completo
    PENDING_FINANCE = "PENDING_FINANCE"   # Attesa conferma finance
    FINANCE_APPROVED = "FINANCE_APPROVED" # Approvato da finance
    PENDING_ASSIGNMENT = "PENDING_ASSIGNMENT" # Attesa assegnazione HM
    ASSIGNED = "ASSIGNED"                 # Professionisti assegnati
    CONVERTED = "CONVERTED"               # Convertito in cliente
    LOST = "LOST"                        # Perso
    ARCHIVED = "ARCHIVED"                # Archiviato

class PaymentTypeEnum(str, Enum):
    """Tipi di pagamento lead"""
    acconto = "acconto"
    saldo = "saldo"
    unico = "unico"
    rata = "rata"
    rimborso = "rimborso"

class PaymentMethodEnum(str, Enum):
    """Metodi di pagamento"""
    bonifico = "bonifico"
    klarna = "klarna"
    stripe = "stripe"
    carta = "carta"
    paypal = "paypal"
    contanti = "contanti"
    assegno = "assegno"
    altro = "altro"

class LeadPriorityEnum(str, Enum):
    """Priorità lead"""
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"

class LeadOriginEnum(str, Enum):
    """Origine lead / Canale di acquisizione"""
    AMMINISTRAZIONE = "Amministrazione"
    EMAIL_CELESTINO = "eMail (Dott.Celestino Mattucci)"
    FB_DM_CRISTIANOFALLAI = "FB DM (cristianofallai)"
    FB_DM_CELESTINO = "FB DM (Dott.Celestino Mattucci)"
    FB_DM_MISSBYFITNESS = "FB DM (MissByFitness)"
    FB_DM_SCIAUDONE = "FB DM (sciaudone.matteo)"
    IG_BIO_CORPOSOSTENIBILE = "IG Bio (corposostenibile)"
    IG_BIO_MISSBYFITNESS = "IG Bio (MissByFitness)"
    IG_BIO_SCIAUDONE = "IG Bio (sciaudone.matteo)"
    IG_DM_ASIACALIANI = "IG DM (asiacaliani)"
    IG_DM_CORPOSOSTENIBILE = "IG DM (corposostenibile)"
    IG_DM_CRISTIANOFALLAI = "IG DM (cristianofallai)"
    IG_DM_CELESTINO = "IG DM (Dott.Celestino Mattucci)"
    IG_DM_LORENZOLARI = "IG DM (lorenzolari_)"
    IG_DM_MISSBYFITNESS = "IG DM (MissByFitness)"
    IG_DM_SCIAUDONE = "IG DM (sciaudone.matteo)"
    REFERRAL_INTERNO = "Referral Interno"
    SONNO_FUNNEL_SCIAUDONE = "Sonno Funnel sciaudone.matteo"
    STRESS_FUNNEL_SCIAUDONE = "Stress Funnel sciaudone.matteo"
    TEST_FUNNEL_MISSBYFITNESS = "Test Funnel missbyfitness"
    TEST_FUNNEL_SCIAUDONE = "Test Funnel sciaudone.matteo"
    YT_SCIAUDONE = "YT sciaudone.matteo"
    YT_SCIAUDONE_PARENTESI = "YT (sciaudone.matteo)"

class FormFieldTypeEnum(str, Enum):
    """Tipi di campo form"""
    text = "text"
    email = "email"
    tel = "tel"
    number = "number"
    date = "date"
    time = "time"
    datetime = "datetime"
    select = "select"
    multiselect = "multiselect"
    radio = "radio"
    checkbox = "checkbox"
    textarea = "textarea"
    file = "file"
    hidden = "hidden"
    heading = "heading"
    paragraph = "paragraph"
    divider = "divider"

# ───────────────── FORM SALES MODELS ───────────────── #

class SalesFormConfig(TimestampMixin, db.Model):
    """Configurazione form unico di sistema per lead generation"""
    __tablename__ = "sales_form_configs"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)
    # Form unico di sistema - solo un record in questa tabella
    description = db.Column(db.Text, default="Form acquisizione clienti")
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Configurazioni form
    success_message = db.Column(db.Text, default='Grazie per aver compilato il form. Ti contatteremo presto!')
    redirect_url = db.Column(db.String(500))
    notification_emails = db.Column(ARRAY(db.String))  # Array email da notificare

    # Styling e branding
    primary_color = db.Column(db.String(7), default='#007bff')
    logo_url = db.Column(db.String(500))
    custom_css = db.Column(db.Text)

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Relazioni
    fields = db.relationship('SalesFormField', back_populates='config', cascade='all, delete-orphan', order_by='SalesFormField.position')
    # Links e leads non più collegati direttamente al config (form unico)
    created_by_user = db.relationship('User', foreign_keys=[created_by])

    def __repr__(self):
        return f"<SalesFormConfig {self.id}>"

    @property
    def field_count(self):
        return len(self.fields)

    @property
    def submission_count(self):
        return len(self.leads)


class SalesFormField(TimestampMixin, db.Model):
    """Campi configurabili per i form"""
    __tablename__ = "sales_form_fields"

    id = db.Column(db.Integer, primary_key=True)
    config_id = db.Column(db.Integer, db.ForeignKey("sales_form_configs.id", ondelete='CASCADE'), nullable=False)

    # Definizione campo
    field_name = db.Column(db.String(100), nullable=False)  # Nome tecnico
    field_type = db.Column(_def(FormFieldTypeEnum), nullable=False)
    field_label = db.Column(db.String(255), nullable=False)
    placeholder = db.Column(db.String(255))
    help_text = db.Column(db.Text)
    default_value = db.Column(db.Text)

    # Validazione
    is_required = db.Column(db.Boolean, default=False, nullable=False)
    validation_rules = db.Column(JSONB, default={})

    # Opzioni (per select, radio, checkbox)
    options = db.Column(JSONB)

    # Layout
    position = db.Column(db.Integer, nullable=False, default=0)
    width = db.Column(db.String(10), default='100')  # 25, 50, 75, 100
    section = db.Column(db.String(100))
    section_description = db.Column(db.Text)

    # Logica condizionale
    conditional_logic = db.Column(JSONB)

    # Relazioni
    config = db.relationship('SalesFormConfig', back_populates='fields')

    __table_args__ = (
        db.UniqueConstraint('config_id', 'field_name'),
        Index('idx_form_fields_config', 'config_id'),
        Index('idx_form_fields_position', 'position'),
    )

    def __repr__(self):
        return f"<SalesFormField {self.field_name}>"


class SalesFormLink(TimestampMixin, db.Model):
    """Link univoci per sales (generazione lead) o per lead (completamento form)"""
    __tablename__ = "sales_form_links"

    id = db.Column(db.Integer, primary_key=True)

    # MODIFICATO: user_id ora nullable e non unique (può esserci più di un link per sales)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # NUOVO: lead_id per link di completamento form
    lead_id = db.Column(db.Integer, db.ForeignKey("sales_leads.id", ondelete='CASCADE'), nullable=True)

    # NUOVO: check_number (1, 2, 3) - identifica quale check per link di completamento
    check_number = db.Column(db.Integer, nullable=True)

    # NUOVO: config_id - quale form config usare per questo link
    config_id = db.Column(db.Integer, db.ForeignKey("sales_form_configs.id", ondelete='SET NULL'), nullable=True)

    # Link management
    unique_code = db.Column(db.String(100), unique=True, nullable=False)
    custom_slug = db.Column(db.String(100))  # Personalizzazione URL
    short_url = db.Column(db.String(255))    # URL shortener service

    # Configurazioni link
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    expires_at = db.Column(db.DateTime)
    max_submissions = db.Column(db.Integer)

    # Tracking
    click_count = db.Column(db.Integer, default=0)
    submission_count = db.Column(db.Integer, default=0)
    last_clicked_at = db.Column(db.DateTime)

    # Custom fields per sales
    custom_message = db.Column(db.Text)
    custom_fields = db.Column(JSONB)  # Campi pre-compilati

    # Relazioni
    user = db.relationship('User', backref='sales_form_links')  # MODIFICATO: rimosso uselist=False
    lead = db.relationship('SalesLead', foreign_keys=[lead_id], backref='completion_links')  # NUOVO: lead con i suoi check link
    leads = db.relationship('SalesLead', foreign_keys='SalesLead.form_link_id', back_populates='form_link')  # Lead generate da questo link
    config = db.relationship('SalesFormConfig', foreign_keys=[config_id])  # Form config per questo link

    __table_args__ = (
        db.CheckConstraint('expires_at IS NULL OR expires_at > created_at'),
        # Constraint su check_number (deve essere 1, 2, o 3 se presente)
        db.CheckConstraint(
            'check_number IS NULL OR check_number IN (1, 2, 3)',
            name='check_number_valid'
        ),
        # NUOVO: Constraint XOR v2
        # - Link SALES: user_id NOT NULL, lead_id NULL, check_number NULL
        # - Link CHECK: user_id NULL, lead_id NOT NULL, check_number NOT NULL (1/2/3)
        db.CheckConstraint(
            '(user_id IS NOT NULL AND lead_id IS NULL AND check_number IS NULL) OR '
            '(user_id IS NULL AND lead_id IS NOT NULL AND check_number IS NOT NULL)',
            name='check_link_type_xor_v2'
        ),
        Index('idx_sales_form_links_user_id', 'user_id'),
        Index('idx_sales_form_links_lead_id', 'lead_id'),
        Index('idx_sales_form_links_check_number', 'check_number'),
    )

    def __repr__(self):
        return f"<SalesFormLink {self.unique_code} - {self.link_type}>"

    @property
    def link_type(self):
        """
        Tipo di link:
        - 'sales': genera nuove lead
        - 'check1': completamento check 1
        - 'check2': completamento check 2
        - 'check3': completamento check 3
        """
        if self.user_id:
            return 'sales'
        elif self.lead_id and self.check_number:
            return f'check{self.check_number}'
        return None

    @property
    def full_url(self):
        from flask import current_app
        base = current_app.config.get('SERVER_NAME', 'suite.corposostenibile.com')
        return f"https://{base}/welcome-form/{self.unique_code}"


class SalesLead(TimestampMixin, db.Model):
    """Lead management system - dal form alla conversione"""
    __tablename__ = "sales_leads"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # Tracking e origine (form_config_id rimosso - usiamo form unico)
    sales_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    form_link_id = db.Column(db.Integer, db.ForeignKey("sales_form_links.id"))
    unique_code = db.Column(db.String(100), unique=True)

    # Dati anagrafici base
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(50))
    birth_date = db.Column(db.Date)
    gender = db.Column(db.String(10), nullable=True)  # 'M' o 'F'
    professione = db.Column(db.Text, nullable=True)  # Professione del lead
    origin = db.Column(db.String(100), nullable=True)  # Origine/Canale acquisizione
    fiscal_code = db.Column(db.String(16))
    indirizzo = db.Column(db.Text, nullable=True)  # Indirizzo di residenza
    paese = db.Column(db.String(100), nullable=True)  # Paese di residenza

    # Dati form (flessibili)
    form_responses = db.Column(JSONB, nullable=False, default={})
    form_attachments = db.Column(JSONB, default=[])

    # NUOVO: Tracking completamento check multipli
    check1_completed_at = db.Column(db.DateTime, nullable=True)
    check2_completed_at = db.Column(db.DateTime, nullable=True)
    check3_completed_at = db.Column(db.DateTime, nullable=True)

    # NUOVO: Risposte separate per ogni check (non si sovrascrivono)
    check1_responses = db.Column(JSONB, nullable=True)
    check2_responses = db.Column(JSONB, nullable=True)
    check3_responses = db.Column(JSONB, nullable=True)

    # NUOVO: Scoring Check 3 (Psico-Alimentare)
    check3_score = db.Column(db.Integer, nullable=True)  # Punteggio totale (0-78)
    check3_type = db.Column(db.String(10), nullable=True)  # 'A', 'B', o 'C'

    # Storia e note vendita
    client_story = db.Column(db.Text)
    story_added_at = db.Column(db.DateTime)
    story_added_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    sales_notes = db.Column(db.Text)
    admin_notes = db.Column(db.Text)

    # Pacchetto e pricing
    package_id = db.Column(db.Integer, db.ForeignKey("finance_packages.id"))
    custom_package_name = db.Column(db.String(255))
    custom_package_details = db.Column(JSONB)
    total_amount = db.Column(NUMERIC(10, 2))
    discount_amount = db.Column(NUMERIC(10, 2), default=0)
    discount_reason = db.Column(db.Text)
    final_amount = db.Column(NUMERIC(10, 2))
    paid_amount = db.Column(NUMERIC(10, 2), default=0)

    # Workflow stati
    status = db.Column(_def(LeadStatusEnum), default=LeadStatusEnum.NEW, nullable=False)
    lost_reason = db.Column(db.Text)
    archived_reason = db.Column(db.Text)

    # Approvazione Finance
    finance_approved = db.Column(db.Boolean, default=False)
    finance_approved_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    finance_approved_at = db.Column(db.DateTime)
    finance_notes = db.Column(db.Text)
    payment_verified = db.Column(db.Boolean, default=False)

    # Assegnazione Health Manager (dal sales)
    health_manager_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    health_manager_assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    health_manager_assigned_at = db.Column(db.DateTime)
    onboarding_date = db.Column(db.Date)
    onboarding_time = db.Column(db.Time)  # Orario call di onboarding
    presentation_message_sent = db.Column(db.Boolean, default=False, nullable=False)
    presentation_message_sent_at = db.Column(db.DateTime)
    presentation_message_sent_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Assegnazioni pre-conversione (dal Health Manager)
    assigned_nutritionist_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    assigned_coach_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    assigned_psychologist_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    assigned_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    assigned_at = db.Column(db.DateTime)
    assignment_notes = db.Column(db.Text)

    # Conversione
    converted_to_client_id = db.Column(db.BigInteger, db.ForeignKey("clienti.cliente_id"))
    converted_at = db.Column(db.DateTime)
    converted_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    conversion_notes = db.Column(db.Text)

    # Tracking e analytics
    source_campaign = db.Column(db.String(255))
    source_medium = db.Column(db.String(100))
    source_url = db.Column(db.Text)
    referrer_url = db.Column(db.Text)
    landing_page = db.Column(db.Text)
    utm_source = db.Column(db.String(255))
    utm_medium = db.Column(db.String(255))
    utm_campaign = db.Column(db.String(255))
    utm_term = db.Column(db.String(255))
    utm_content = db.Column(db.String(255))

    # Dati tecnici
    ip_address = db.Column(db.String(45))
    ip_country = db.Column(db.String(2))
    ip_city = db.Column(db.String(100))
    user_agent = db.Column(db.Text)
    device_type = db.Column(db.String(50))
    browser = db.Column(db.String(50))
    os = db.Column(db.String(50))

    # Comunicazioni
    email_sent_count = db.Column(db.Integer, default=0)
    sms_sent_count = db.Column(db.Integer, default=0)
    whatsapp_sent_count = db.Column(db.Integer, default=0)
    last_contact_at = db.Column(db.DateTime)
    next_followup_at = db.Column(db.DateTime)

    # Priorità
    priority = db.Column(_def(LeadPriorityEnum), default=LeadPriorityEnum.NORMAL)
    followup_notes = db.Column(db.Text)

    # Tags
    tags = db.Column(ARRAY(db.String))

    # Archiviazione (FLAG per pulizia dashboard Sales, NON uno stato)
    archived_at = db.Column(db.DateTime, nullable=True)
    archived_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)

    # Relazioni
    sales_user = db.relationship('User', foreign_keys=[sales_user_id], backref='sales_leads')
    form_link = db.relationship('SalesFormLink', foreign_keys=[form_link_id], back_populates='leads')
    story_added_by_user = db.relationship('User', foreign_keys=[story_added_by])
    package = db.relationship('Package', backref='sales_leads')
    finance_approved_by_user = db.relationship('User', foreign_keys=[finance_approved_by])
    health_manager = db.relationship('User', foreign_keys=[health_manager_id])
    health_manager_assigned_by_user = db.relationship('User', foreign_keys=[health_manager_assigned_by])
    presentation_message_sent_by_user = db.relationship('User', foreign_keys=[presentation_message_sent_by])
    assigned_nutritionist = db.relationship('User', foreign_keys=[assigned_nutritionist_id])
    assigned_coach = db.relationship('User', foreign_keys=[assigned_coach_id])
    assigned_psychologist = db.relationship('User', foreign_keys=[assigned_psychologist_id])
    assigned_by_user = db.relationship('User', foreign_keys=[assigned_by])
    converted_to_client = db.relationship('Cliente', foreign_keys=[converted_to_client_id], backref=db.backref('original_lead', uselist=False))
    converted_by_user = db.relationship('User', foreign_keys=[converted_by])
    archived_by_user = db.relationship('User', foreign_keys=[archived_by])

    # Relazioni inverse
    payments = db.relationship('LeadPayment', back_populates='lead', cascade='all, delete-orphan')
    activity_logs = db.relationship('LeadActivityLog', back_populates='lead', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_sales_leads_status', 'status'),
        Index('idx_sales_leads_sales_user', 'sales_user_id'),
        Index('idx_sales_leads_email', 'email'),
        Index('idx_sales_leads_phone', 'phone'),
        Index('idx_sales_leads_created', 'created_at'),
        Index('idx_sales_leads_priority', 'priority'),
        Index('idx_leads_conversion', 'converted_to_client_id'),
        Index('idx_sales_leads_archived_at', 'archived_at'),
    )

    def __repr__(self):
        return f"<SalesLead {self.unique_code} - {self.first_name} {self.last_name}>"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def is_archived(self) -> bool:
        """Helper: True se lead archiviata"""
        return self.archived_at is not None

    @property
    def payment_status(self):
        """Determina lo stato del pagamento"""
        if not self.final_amount:
            return "NO_PRICE"
        if self.paid_amount == 0:
            return "UNPAID"
        if self.paid_amount < self.final_amount:
            return "PARTIAL"
        return "PAID"

    @property
    def remaining_amount(self):
        """Calcola importo rimanente"""
        if not self.final_amount:
            return 0
        return max(0, self.final_amount - self.paid_amount)

    def calculate_final_amount(self):
        """Calcola il prezzo finale con sconto"""
        if self.total_amount:
            self.final_amount = self.total_amount - (self.discount_amount or 0)

    def add_activity_log(self, activity_type, description, user_id=None, **kwargs):
        """Helper per aggiungere log attività"""
        log = LeadActivityLog(
            lead_id=self.id,
            activity_type=activity_type,
            description=description,
            user_id=user_id,
            activity_metadata=kwargs.get('metadata'),
            field_name=kwargs.get('field_name'),
            old_value=kwargs.get('old_value'),
            new_value=kwargs.get('new_value')
        )
        db.session.add(log)
        return log


class LeadPayment(TimestampMixin, db.Model):
    """Gestione pagamenti delle lead"""
    __tablename__ = "lead_payments"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("sales_leads.id", ondelete='CASCADE'), nullable=False)

    # Dettagli pagamento
    amount = db.Column(NUMERIC(10, 2), nullable=False)
    payment_type = db.Column(_def(PaymentTypeEnum), nullable=False)
    payment_method = db.Column(_def(PaymentMethodEnum))

    # Tracking transazione
    transaction_id = db.Column(db.String(255))
    payment_date = db.Column(db.Date, nullable=False)
    value_date = db.Column(db.Date)  # Data valuta bonifici

    # Dettagli aggiuntivi
    bank_name = db.Column(db.String(255))
    bank_account = db.Column(db.String(255))  # Ultimi 4 caratteri
    notes = db.Column(db.Text)

    # Documenti
    receipt_url = db.Column(db.Text)
    invoice_number = db.Column(db.String(50))

    # Stato
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    verified_at = db.Column(db.DateTime)

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Relazioni
    lead = db.relationship('SalesLead', back_populates='payments')
    created_by_user = db.relationship('User', foreign_keys=[created_by])
    verified_by_user = db.relationship('User', foreign_keys=[verified_by])

    __table_args__ = (
        Index('idx_lead_payments_lead', 'lead_id'),
        Index('idx_lead_payments_date', 'payment_date'),
        Index('idx_lead_payments_type', 'payment_type'),
        db.CheckConstraint('amount > 0', name='check_amount_positive'),
    )

    def __repr__(self):
        return f"<LeadPayment {self.lead_id} - {self.amount} - {self.payment_type}>"


class LeadActivityLog(TimestampMixin, db.Model):
    """Log di tutte le attività sulle lead"""
    __tablename__ = "lead_activity_logs"

    id = db.Column(db.Integer, primary_key=True)
    lead_id = db.Column(db.Integer, db.ForeignKey("sales_leads.id", ondelete='CASCADE'), nullable=False)

    # Tipo e descrizione attività
    activity_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # Tracking modifiche
    field_name = db.Column(db.String(100))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)

    # Metadata
    activity_metadata = db.Column(JSONB)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)

    # User tracking
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Relazioni
    lead = db.relationship('SalesLead', back_populates='activity_logs')
    user = db.relationship('User', backref='lead_activities')

    __table_args__ = (
        Index('idx_activity_lead', 'lead_id', 'created_at'),
        Index('idx_activity_type', 'activity_type'),
        Index('idx_activity_user', 'user_id'),
    )

    def __repr__(self):
        return f"<LeadActivityLog {self.lead_id} - {self.activity_type}>"


class ClientStoryTemplate(TimestampMixin, db.Model):
    """Template per storie cliente"""
    __tablename__ = "client_story_templates"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.String(100))  # dimagrimento, massa, salute

    # Template con variabili
    template_text = db.Column(db.Text, nullable=False)
    variables = db.Column(JSONB, default=[])

    # Configurazione
    is_active = db.Column(db.Boolean, default=True)
    usage_count = db.Column(db.Integer, default=0)

    # Metadata
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"))
    created_by_user = db.relationship('User', backref='story_templates')

    def __repr__(self):
        return f"<ClientStoryTemplate {self.name}>"


class LeadFollowupRule(TimestampMixin, db.Model):
    """Regole per follow-up automatici"""
    __tablename__ = "lead_followup_rules"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)

    # Condizioni
    trigger_status = db.Column(db.String(50))  # Status che triggera
    days_after = db.Column(db.Integer, nullable=False)

    # Azione
    action_type = db.Column(db.String(50))  # email, sms, whatsapp, task
    template_id = db.Column(db.Integer)  # Reference a template
    assigned_to = db.Column(db.Integer, db.ForeignKey("users.id"))

    # Configurazione
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=0)

    # Relazioni
    assigned_to_user = db.relationship('User', backref='followup_rules')

    def __repr__(self):
        return f"<LeadFollowupRule {self.name}>"


# ─────────────────────────── BLUEPRINT REGISTRY ─────────────────────────── #
class BlueprintStatusEnum(str, Enum):
    active = "active"
    beta = "beta"
    deprecated = "deprecated"
    planned = "planned"
    archived = "archived"

class AdoptionLevelEnum(str, Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"
    none = "none"

class IssueSeverityEnum(str, Enum):
    blocker = "blocker"
    critical = "critical"
    major = "major"
    minor = "minor"
    enhancement = "enhancement"

class IssueStatusEnum(str, Enum):
    open = "open"
    in_progress = "in_progress"
    resolved = "resolved"
    closed = "closed"
    wontfix = "wontfix"

class ImprovementStatusEnum(str, Enum):
    proposed = "proposed"
    approved = "approved"
    in_development = "in_development"
    completed = "completed"
    rejected = "rejected"


class WorkTypeEnum(str, Enum):
    """Tipo di lavoro per DevWorkLog."""
    coding = "coding"
    testing = "testing"
    review = "review"
    bug_fixing = "bug_fixing"
    meeting = "meeting"
    documentation = "documentation"
    refactoring = "refactoring"
    deployment = "deployment"


class CodeReviewStatusEnum(str, Enum):
    """Status code review."""
    pending = "pending"
    approved = "approved"
    changes_requested = "changes_requested"
    dismissed = "dismissed"


class SprintStatusEnum(str, Enum):
    """Status sprint."""
    planning = "planning"
    active = "active"
    completed = "completed"
    archived = "archived"


# Registra i nuovi ENUM
for _e in (BlueprintStatusEnum, AdoptionLevelEnum, IssueSeverityEnum,
           IssueStatusEnum, ImprovementStatusEnum, WorkTypeEnum,
           CodeReviewStatusEnum, SprintStatusEnum):
    _pg_enum(_e)


class GlobalActivityLog(TimestampMixin, db.Model):
    """Log globale attività di tutti i blueprint (tracking automatico)."""
    __tablename__ = "global_activity_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    blueprint = db.Column(db.String(50))  # Nome blueprint: 'customers', 'team', etc.
    action_type = db.Column(db.String(100))  # Nome endpoint/azione
    http_method = db.Column(db.String(10))
    http_status = db.Column(db.Integer)
    response_time_ms = db.Column(db.Integer)
    error_message = db.Column(db.Text)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(255))

    # Relazioni
    user = relationship("User", backref="activity_logs")

    __table_args__ = (
        Index('ix_global_activity_blueprint_date', 'blueprint', 'created_at'),
        Index('ix_global_activity_user_date', 'user_id', 'created_at'),
    )


class BlueprintRegistry(TimestampMixin, db.Model):
    """Registro centralizzato dei blueprint della suite."""
    __tablename__ = "blueprint_registry"

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(_def(BlueprintStatusEnum), nullable=False, default=BlueprintStatusEnum.active)
    adoption_level = db.Column(_def(AdoptionLevelEnum), default=AdoptionLevelEnum.none)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'))
    metrics = db.Column(JSONB, default={})
    kb_article_id = db.Column(db.Integer, db.ForeignKey('kb_articles.id'))
    readme_url = db.Column(db.String(500))
    current_version = db.Column(db.String(20))
    last_major_update = db.Column(db.DateTime)

    # Relazioni
    owner = relationship("User", backref="owned_blueprints")
    department = relationship("Department", backref="blueprints")
    kb_article = relationship("KBArticle", backref="blueprint_docs")
    issues = relationship("BlueprintIssue", back_populates="blueprint", cascade="all, delete-orphan")
    improvements = relationship("BlueprintImprovement", back_populates="blueprint", cascade="all, delete-orphan")
    interventions = relationship("BlueprintIntervention", back_populates="blueprint", cascade="all, delete-orphan")


class BlueprintIssue(TimestampMixin, db.Model):
    """Issues/problematiche dei blueprint."""
    __tablename__ = "blueprint_issues"

    id = db.Column(db.Integer, primary_key=True)
    blueprint_id = db.Column(db.Integer, db.ForeignKey('blueprint_registry.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    severity = db.Column(_def(IssueSeverityEnum), nullable=False, default=IssueSeverityEnum.minor)
    status = db.Column(_def(IssueStatusEnum), nullable=False, default=IssueStatusEnum.open)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reported_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    resolved_at = db.Column(db.DateTime)
    resolution_notes = db.Column(db.Text)
    github_issue_url = db.Column(db.String(500))
    # 🔗 Collegamento Dev Tracker
    intervention_id = db.Column(db.Integer, db.ForeignKey('blueprint_interventions.id', ondelete='SET NULL'), index=True)

    # 📧 Feedback Loop - Motivazioni Admin
    acknowledgment_message = db.Column(db.Text, nullable=True, comment='Messaggio admin quando prende in carico issue')
    resolution_motivation = db.Column(db.Text, nullable=True, comment='Motivazione dettagliata risoluzione issue')
    wontfix_motivation = db.Column(db.Text, nullable=True, comment='Motivazione se issue non verrà fixata')
    notified_at = db.Column(db.DateTime, nullable=True, comment='Timestamp ultima notifica email inviata')

    # Relazioni
    blueprint = relationship("BlueprintRegistry", back_populates="issues")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id], backref="assigned_blueprint_issues")
    reported_by = relationship("User", foreign_keys=[reported_by_id], backref="reported_blueprint_issues")
    intervention = relationship("BlueprintIntervention", backref="related_issue", foreign_keys=[intervention_id])


class BlueprintImprovement(TimestampMixin, db.Model):
    """Idee di miglioramento/feature request."""
    __tablename__ = "blueprint_improvements"

    id = db.Column(db.Integer, primary_key=True)
    blueprint_id = db.Column(db.Integer, db.ForeignKey('blueprint_registry.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(_def(ImprovementStatusEnum), nullable=False, default=ImprovementStatusEnum.proposed)
    priority = db.Column(_def(TaskPriorityEnum), default=TaskPriorityEnum.medium)
    expected_impact = db.Column(db.Text)
    effort_estimation = db.Column(db.String(50))
    proposed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    approved_at = db.Column(db.DateTime)
    target_completion_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    # 🔗 Collegamento Dev Tracker
    intervention_id = db.Column(db.Integer, db.ForeignKey('blueprint_interventions.id', ondelete='SET NULL'), index=True)

    # 📧 Feedback Loop - Motivazioni Admin
    approval_motivation = db.Column(db.Text, nullable=True, comment='Motivazione admin per approvazione idea')
    rejection_motivation = db.Column(db.Text, nullable=True, comment='Motivazione admin per rigetto idea')
    pending_motivation = db.Column(db.Text, nullable=True, comment='Motivazione admin per stato in sospeso')
    completion_notes = db.Column(db.Text, nullable=True, comment='Note su implementazione completata')
    notified_at = db.Column(db.DateTime, nullable=True, comment='Timestamp ultima notifica email inviata')

    # Relazioni
    blueprint = relationship("BlueprintRegistry", back_populates="improvements")
    proposed_by = relationship("User", foreign_keys=[proposed_by_id], backref="proposed_improvements")
    approved_by = relationship("User", foreign_keys=[approved_by_id], backref="approved_improvements")
    intervention = relationship("BlueprintIntervention", backref="related_improvement", foreign_keys=[intervention_id])


class BlueprintIntervention(TimestampMixin, db.Model):
    """Interventi/lavori in corso su blueprint."""
    __tablename__ = "blueprint_interventions"

    id = db.Column(db.Integer, primary_key=True)
    blueprint_id = db.Column(db.Integer, db.ForeignKey('blueprint_registry.id', ondelete='CASCADE'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    intervention_type = db.Column(db.String(50))
    status = db.Column(_def(TaskStatusEnum), nullable=False, default=TaskStatusEnum.todo)
    progress_percentage = db.Column(db.Integer, default=0)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    start_date = db.Column(db.Date)
    due_date = db.Column(db.Date)
    completed_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    blockers = db.Column(db.Text)
    project_id = db.Column(db.Integer, db.ForeignKey('development_projects.id'))

    # Relazioni
    blueprint = relationship("BlueprintRegistry", back_populates="interventions")
    assigned_to = relationship("User", backref="blueprint_interventions")
    project = relationship("DevelopmentProject", backref="blueprint_interventions")


class BlueprintMetricsSnapshot(TimestampMixin, db.Model):
    """Snapshot giornaliero metriche blueprint."""
    __tablename__ = "blueprint_metrics_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    blueprint_id = db.Column(db.Integer, db.ForeignKey('blueprint_registry.id', ondelete='CASCADE'), nullable=False)
    snapshot_date = db.Column(db.Date, nullable=False, default=date.today)
    total_users = db.Column(db.Integer)
    active_users_30d = db.Column(db.Integer)
    adoption_rate = db.Column(NUMERIC(5, 2))
    avg_daily_requests = db.Column(db.Integer)
    error_rate = db.Column(NUMERIC(5, 2))
    avg_response_time_ms = db.Column(db.Integer)
    custom_metrics = db.Column(JSONB, default={})

    # Relazioni
    blueprint = relationship("BlueprintRegistry", backref="metrics_snapshots")

    __table_args__ = (
        Index('ix_metrics_blueprint_date', 'blueprint_id', 'snapshot_date'),
    )


# ═══════════════════════════════════════════════════════════════════════════
#                          DEV TRACKER MODELS
# ═══════════════════════════════════════════════════════════════════════════

class DevWorkLog(TimestampMixin, db.Model):
    """
    Log giornaliero ore lavorate per intervention.
    Permette tracking preciso tempo speso per ogni sviluppatore.
    """
    __tablename__ = "dev_work_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    intervention_id = db.Column(
        db.Integer,
        db.ForeignKey('blueprint_interventions.id', ondelete='CASCADE'),
        index=True
    )
    date = db.Column(db.Date, nullable=False, default=date.today, index=True)
    hours_worked = db.Column(NUMERIC(4, 2), nullable=False)  # es. 2.5 ore
    description = db.Column(db.Text)
    work_type = db.Column(
        _def(WorkTypeEnum),
        nullable=False,
        default=WorkTypeEnum.coding
    )

    # Relazioni
    user = relationship("User", backref="work_logs")
    intervention = relationship("BlueprintIntervention", backref="work_logs")

    __table_args__ = (
        Index('ix_worklog_user_date', 'user_id', 'date'),
        Index('ix_worklog_intervention_date', 'intervention_id', 'date'),
    )

    def __repr__(self):
        return f"<DevWorkLog {self.user_id} - {self.date} - {self.hours_worked}h>"


class DevCommit(TimestampMixin, db.Model):
    """
    Tracking git commits linkati a interventions.
    Inserimento MANUALE da parte degli sviluppatori.
    """
    __tablename__ = "dev_commits"

    id = db.Column(db.Integer, primary_key=True)
    intervention_id = db.Column(
        db.Integer,
        db.ForeignKey('blueprint_interventions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    commit_hash = db.Column(db.String(40), unique=True, index=True)
    commit_message = db.Column(db.Text, nullable=False)
    branch = db.Column(db.String(100))
    files_changed = db.Column(db.Integer)
    additions = db.Column(db.Integer)
    deletions = db.Column(db.Integer)
    github_url = db.Column(db.String(500))
    committed_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    intervention = relationship("BlueprintIntervention", backref="commits")
    user = relationship("User", backref="dev_commits")

    __table_args__ = (
        Index('ix_commit_intervention_date', 'intervention_id', 'committed_at'),
    )

    def __repr__(self):
        return f"<DevCommit {self.commit_hash[:7]} - {self.commit_message[:30]}>"


class DevCodeReview(TimestampMixin, db.Model):
    """
    Code review tracking per intervention.
    Permette di tracciare review process e qualità del codice.
    """
    __tablename__ = "dev_code_reviews"

    id = db.Column(db.Integer, primary_key=True)
    intervention_id = db.Column(
        db.Integer,
        db.ForeignKey('blueprint_interventions.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    reviewer_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        index=True
    )
    author_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False,
        index=True
    )
    status = db.Column(
        _def(CodeReviewStatusEnum),
        nullable=False,
        default=CodeReviewStatusEnum.pending
    )
    pr_url = db.Column(db.String(500))
    comments_count = db.Column(db.Integer, default=0)
    review_notes = db.Column(db.Text)
    approved_at = db.Column(db.DateTime)

    # Relazioni
    intervention = relationship("BlueprintIntervention", backref="code_reviews")
    reviewer = relationship("User", foreign_keys=[reviewer_id], backref="dev_reviews_given")
    author = relationship("User", foreign_keys=[author_id], backref="dev_reviews_received")

    __table_args__ = (
        Index('ix_review_status_date', 'status', 'created_at'),
    )

    def __repr__(self):
        return f"<DevCodeReview #{self.id} - {self.status.value}>"


class DevSprint(TimestampMixin, db.Model):
    """
    Sprint planning per team di sviluppo.
    Permette di organizzare interventions in sprint con obiettivi e scadenze.
    """
    __tablename__ = "dev_sprints"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    department_id = db.Column(
        db.Integer,
        db.ForeignKey('departments.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    goal = db.Column(db.Text)
    status = db.Column(
        _def(SprintStatusEnum),
        nullable=False,
        default=SprintStatusEnum.planning,
        index=True
    )
    total_story_points = db.Column(db.Integer, default=0)
    completed_story_points = db.Column(db.Integer, default=0)

    # Relazioni
    department = relationship("Department", backref="sprints")
    interventions = relationship(
        "BlueprintIntervention",
        secondary="dev_sprint_interventions",
        backref="sprints"
    )

    __table_args__ = (
        Index('ix_sprint_dates', 'start_date', 'end_date'),
        Index('ix_sprint_dept_status', 'department_id', 'status'),
    )

    @property
    def progress_percentage(self):
        """Calcola percentuale completamento sprint."""
        if self.total_story_points == 0:
            return 0
        return int((self.completed_story_points / self.total_story_points) * 100)

    @property
    def is_active(self):
        """Verifica se sprint è attivo."""
        return self.status == SprintStatusEnum.active

    def __repr__(self):
        return f"<DevSprint {self.name} - {self.status.value}>"


class DevSprintIntervention(db.Model):
    """
    Many-to-many: interventions inclusi in uno sprint.
    Ogni intervention può avere story points associati.
    """
    __tablename__ = "dev_sprint_interventions"

    sprint_id = db.Column(
        db.Integer,
        db.ForeignKey('dev_sprints.id', ondelete='CASCADE'),
        primary_key=True
    )
    intervention_id = db.Column(
        db.Integer,
        db.ForeignKey('blueprint_interventions.id', ondelete='CASCADE'),
        primary_key=True
    )
    story_points = db.Column(db.Integer, default=0)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relazioni
    sprint = relationship("DevSprint", backref="sprint_interventions")
    intervention = relationship("BlueprintIntervention", backref="sprint_assignments")

    def __repr__(self):
        return f"<SprintIntervention S{self.sprint_id} - I{self.intervention_id} ({self.story_points}pt)>"


# ═══════════════════════════════════════════════════════════════════════════
# QUESTIONARI ANONIMI
# ═══════════════════════════════════════════════════════════════════════════

class AnonymousSurvey(TimestampMixin, db.Model):
    """Questionario anonimo (es. clima aziendale)"""
    __tablename__ = 'anonymous_surveys'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Relazioni
    creator = relationship('User', foreign_keys=[created_by])
    responses = relationship('AnonymousSurveyResponse', back_populates='survey', cascade='all, delete-orphan')

    def __repr__(self):
        return f"<AnonymousSurvey {self.id}: {self.title}>"

    @property
    def total_responses(self):
        """Numero totale di risposte ricevute"""
        return len(self.responses)


class AnonymousSurveyResponse(db.Model):
    """Risposta anonima a un questionario"""
    __tablename__ = 'anonymous_survey_responses'

    id = db.Column(db.Integer, primary_key=True)
    survey_id = db.Column(db.Integer, db.ForeignKey('anonymous_surveys.id', ondelete='CASCADE'), nullable=False)

    # user_id serve SOLO per garantire che ogni utente compili una volta sola
    # NON viene mai mostrato nelle visualizzazioni delle risposte (anonimato garantito)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Risposte salvate in formato JSON
    responses = db.Column(JSONB, nullable=False)

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relazioni
    survey = relationship('AnonymousSurvey', back_populates='responses')
    user = relationship('User', foreign_keys=[user_id])

    # Constraint: ogni user può rispondere una sola volta per questionario
    __table_args__ = (
        db.UniqueConstraint('survey_id', 'user_id', name='uq_survey_user'),
    )

    def __repr__(self):
        return f"<AnonymousSurveyResponse {self.id} - Survey {self.survey_id}>"


# ═══════════════════════════════════════════════════════════════════════════
# CONFERME LETTURA DOCUMENTI
# ═══════════════════════════════════════════════════════════════════════════

class DocumentTypeEnum(str, Enum):
    """Tipi di documento da confermare"""
    codice_condotta = "codice_condotta"
    regolamento_remoto = "regolamento_remoto"


class DocumentAcknowledgment(TimestampMixin, db.Model):
    """
    Traccia le conferme di lettura per documenti aziendali importanti.
    Ogni utente può confermare la lettura di ogni documento una sola volta.
    """
    __tablename__ = 'document_acknowledgments'

    id = db.Column(db.Integer, primary_key=True)

    # Utente che conferma
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Tipo di documento confermato (stored as String in DB)
    document_type = db.Column(
        db.String(50),
        nullable=False,
        index=True
    )

    # Timestamp conferma
    acknowledged_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # IP e User-Agent per audit trail (opzionale)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))

    # Relazioni
    user = relationship('User', backref=db.backref('document_acknowledgments', lazy='dynamic'))

    # Constraint: ogni user può confermare ogni documento una sola volta
    __table_args__ = (
        db.UniqueConstraint('user_id', 'document_type', name='uq_user_document'),
        Index('ix_acknowledgment_type_user', 'document_type', 'user_id'),
    )

    def __repr__(self):
        return f"<DocumentAcknowledgment user={self.user_id} doc={self.document_type}>"


# ══════════════════════════════════════════════════════════════════════════════
# QUALITY SCORE SYSTEM - KPI PROFESSIONISTI
# ══════════════════════════════════════════════════════════════════════════════

class QualityWeeklyScore(TimestampMixin, db.Model):
    """
    Score Quality settimanale aggregato per professionista.
    Calcolato manualmente da Admin tramite pulsante dashboard.
    """
    __tablename__ = 'quality_weekly_scores'
    __table_args__ = (
        db.UniqueConstraint('professionista_id', 'week_start_date', name='uq_prof_week'),
        db.Index('idx_prof_week', 'professionista_id', 'week_start_date'),
        db.Index('idx_week_start', 'week_start_date'),
        db.Index('idx_quality_final', 'quality_final'),
    )

    # ─── Primary Key ───
    id = db.Column(db.Integer, primary_key=True)

    # ─── Riferimenti ───
    professionista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professionista = relationship('User', foreign_keys=[professionista_id], backref='quality_weekly_scores')

    # ─── Periodo ───
    week_start_date = db.Column(db.Date, nullable=False, index=True)  # Lunedì
    week_end_date = db.Column(db.Date, nullable=False)                # Domenica
    week_number = db.Column(db.Integer)  # Settimana dell'anno (1-52)
    year = db.Column(db.Integer)         # Anno
    quarter = db.Column(db.String(10))   # "2025-Q4"

    # ─── Dati Eleggibilità ───
    n_clients_eligible = db.Column(db.Integer, nullable=False, default=0)
    n_checks_done = db.Column(db.Integer, nullable=False, default=0)
    miss_rate = db.Column(db.Float)  # % check mancati (0.0 - 1.0)

    # ─── Componenti Score ───
    quality_raw = db.Column(db.Float)           # Media pura voti senza correzioni
    avg_brec_week = db.Column(db.Float)         # Media bonus recensioni della settimana
    penalty_week = db.Column(db.Float)          # Malus check mancati (-0.00 to -0.05)
    quality_final = db.Column(db.Float, index=True)  # Score finale settimana

    # ─── Trend ───
    delta_vs_last_week = db.Column(db.Float)
    trend_indicator = db.Column(db.Enum('up', 'down', 'stable', name='trend_enum'))

    # ─── Aggregati Rolling ───
    quality_month = db.Column(db.Float)         # Media ultime 4 settimane
    quality_trim = db.Column(db.Float)          # Media ultime 12 settimane

    # ─── Bonus Band ───
    bonus_band = db.Column(db.String(10))  # Banda bonus ('100%', '60%', '30%', '0%')

    # ─── KPI Composito (trimestrale) ───
    rinnovo_adj_percentage = db.Column(db.Float)      # % rinnovo adj (clienti rinnovati / scaduti)
    rinnovo_adj_bonus_band = db.Column(db.String(10)) # '100%', '60%', '30%', '0%'
    quality_bonus_band = db.Column(db.String(10))     # '100%', '60%', '30%', '0%'
    final_bonus_percentage = db.Column(db.Float)      # Bonus finale dopo pesi (60% rinnovo + 40% quality)

    # ─── Super Malus (trimestrale) ───
    has_negative_review = db.Column(db.Boolean, default=False)  # Ha review negativa (stelle <= 2)
    has_refund = db.Column(db.Boolean, default=False)           # Ha rimborso nel trimestre
    is_primary_for_malus = db.Column(db.Boolean)                # È primario per almeno un cliente con malus
    super_malus_percentage = db.Column(db.Float, default=0.0)   # 0, 25, 50, 100
    super_malus_applied = db.Column(db.Boolean, default=False)  # Super Malus applicato
    super_malus_reason = db.Column(db.Text)                     # Motivo malus (JSON con dettagli clienti)
    final_bonus_after_malus = db.Column(db.Float)               # Bonus finale DOPO Super Malus

    # ─── Metadata Calcolo ───
    calculation_status = db.Column(db.Enum('pending', 'calculating', 'completed', 'error', name='calc_status_enum'), default='pending')
    calculation_error = db.Column(db.Text)
    calculated_at = db.Column(db.DateTime)
    calculated_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    calculated_by = relationship('User', foreign_keys=[calculated_by_user_id])

    # ─── Note ───
    notes = db.Column(db.Text)  # Note manuali Admin

    def __repr__(self):
        return f"<QualityWeeklyScore prof={self.professionista_id} week={self.week_start_date} score={self.quality_final}>"


class QualityClientScore(TimestampMixin, db.Model):
    """
    Score Quality dettagliato per singolo cliente in una settimana.
    Usato per breakdown calcolo settimanale e dettaglio.
    """
    __tablename__ = 'quality_client_scores'
    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'professionista_id', 'week_start_date', name='uq_client_prof_week'),
        db.Index('idx_client_week', 'cliente_id', 'week_start_date'),
        db.Index('idx_prof_week_client', 'professionista_id', 'week_start_date'),
    )

    # ─── Primary Key ───
    id = db.Column(db.Integer, primary_key=True)

    # ─── Riferimenti ───
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    cliente = relationship('Cliente', foreign_keys=[cliente_id], backref='quality_scores')

    professionista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professionista = relationship('User', foreign_keys=[professionista_id])

    week_start_date = db.Column(db.Date, nullable=False, index=True)
    week_end_date = db.Column(db.Date, nullable=False)  # Domenica

    # ─── Voti Base ───
    voto_professionista = db.Column(db.Float)  # 1-10 (nutritionist/coach/psychologist rating)
    voto_percorso = db.Column(db.Float)        # 1-10 (progress_rating)
    voto_coordinatore = db.Column(db.Float)    # coordinator_rating (se presente, override di voto_percorso)

    # ─── Bonus Recensione ───
    brec_value = db.Column(db.Float, default=0.0)  # +0.03 o +0.02/(n-1) o 0

    # ─── Score Calcolato ───
    quality_score = db.Column(db.Float)  # (VProf + (VCoord OR VPerc))/2 + BRec

    # ─── Metadata Check ───
    check_response_id = db.Column(db.Integer)  # ID della response (WeeklyCheck o TypeForm)
    check_response_type = db.Column(_def(CheckTypeEnum))
    check_effettuato = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<QualityClientScore client={self.cliente_id} prof={self.professionista_id} week={self.week_start_date} score={self.quality_score}>"


class TrustpilotReview(TimestampMixin, db.Model):
    """
    Tracciamento recensioni per distribuzione bonus BRec.
    NO integrazione API Trustpilot - gestione manuale da HM.
    """
    __tablename__ = 'trustpilot_reviews'
    __table_args__ = (
        db.Index('idx_cliente_review', 'cliente_id'),
        db.Index('idx_richiedente', 'richiesta_da_professionista_id'),
        db.Index('idx_quarter', 'applied_to_quarter'),
        db.Index('idx_pubblicata', 'pubblicata'),
    )

    # ─── Primary Key ───
    id = db.Column(db.Integer, primary_key=True)

    # ─── Riferimenti ───
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    cliente = relationship('Cliente', foreign_keys=[cliente_id], backref='trustpilot_reviews')

    # ─── Richiesta Recensione ───
    richiesta_da_professionista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    richiesta_da = relationship('User', foreign_keys=[richiesta_da_professionista_id])
    data_richiesta = db.Column(db.DateTime, nullable=False, index=True)

    # ─── Pubblicazione ───
    pubblicata = db.Column(db.Boolean, default=False, index=True)
    data_pubblicazione = db.Column(db.DateTime)
    stelle = db.Column(db.Integer)  # 1-5 (copiato da Cliente.recensione_stelle)
    testo_recensione = db.Column(db.Text)  # Copiato da Cliente.recensione_testo

    # ─── Distribuzione Bonus (JSON) ───
    bonus_distribution = db.Column(db.JSON)
    # Esempio:
    # {
    #   "richiedente_id": 123,
    #   "richiedente_bonus": 0.03,
    #   "team_ids": [124, 125, 126],
    #   "team_bonus_total": 0.02,
    #   "team_bonus_each": 0.0067,
    #   "team_count": 3
    # }

    # ─── Applicazione Trimestre ───
    applied_to_quarter = db.Column(db.String(10), index=True)  # "2025-Q4"
    applied_to_week_start = db.Column(db.Date, index=True)     # Settimana specifica

    # ─── Metadata ───
    confermata_da_hm_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    confermata_da_hm = relationship('User', foreign_keys=[confermata_da_hm_id])
    data_conferma_hm = db.Column(db.DateTime)

    # ─── Note ───
    note_interne = db.Column(db.Text)

    def __repr__(self):
        return f"<TrustpilotReview client={self.cliente_id} richiedente={self.richiesta_da_professionista_id} pubblicata={self.pubblicata}>"


class EleggibilitaSettimanale(TimestampMixin, db.Model):
    """
    Cache clienti eleggibili per check settimanale.
    Calcolata manualmente da Admin tramite pulsante.
    """
    __tablename__ = 'eleggibilita_settimanale'
    __table_args__ = (
        db.UniqueConstraint('cliente_id', 'professionista_id', 'week_start_date', name='uq_elig_client_prof_week'),
        db.Index('idx_elig_prof_week', 'professionista_id', 'week_start_date'),
        db.Index('idx_elig_week', 'week_start_date'),
    )

    # ─── Primary Key ───
    id = db.Column(db.Integer, primary_key=True)

    # ─── Riferimenti ───
    cliente_id = db.Column(db.BigInteger, db.ForeignKey('clienti.cliente_id'), nullable=False)
    cliente = relationship('Cliente', foreign_keys=[cliente_id])

    professionista_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    professionista = relationship('User', foreign_keys=[professionista_id])

    week_start_date = db.Column(db.Date, nullable=False, index=True)

    # ─── Eleggibilità ───
    eleggibile = db.Column(db.Boolean, nullable=False, default=False)
    motivo_non_eleggibile = db.Column(db.String(255))  # es: "stato_cliente=ghost", "non_attivo"

    # ─── Check Effettuato ───
    check_effettuato = db.Column(db.Boolean, default=False)
    check_response_id = db.Column(db.Integer)
    check_response_type = db.Column(db.Enum('weekly_check', 'typeform', 'dca_check', name='check_type_elig_enum'))
    data_check = db.Column(db.DateTime)

    # ─── Snapshot Stato Cliente ───
    stato_cliente_snapshot = db.Column(db.String(50))
    giorni_attivo_snapshot = db.Column(db.Integer)
    check_day_snapshot = db.Column(db.String(20))  # Giorno previsto check

    def __repr__(self):
        return f"<EleggibilitaSettimanale client={self.cliente_id} prof={self.professionista_id} week={self.week_start_date} elig={self.eleggibile}>"


# ═══════════════════════════════════════════════════════════════════════════════
#                            IT PROJECTS
# ═══════════════════════════════════════════════════════════════════════════════

# Tabella ponte M2M per team membri progetto
it_project_members = db.Table(
    "it_project_members",
    db.Column("project_id", db.Integer, db.ForeignKey("it_projects.id", ondelete="CASCADE"), primary_key=True),
    db.Column("user_id", db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    db.Column("assigned_at", db.DateTime, default=datetime.utcnow, nullable=False),
    db.Column("role", db.String(50), default="member")  # lead, member
)


class ITProject(TimestampMixin, db.Model):
    """
    Progetti IT del dipartimento.

    Gestisce i progetti in corso con:
    - Titolo, descrizione, specifiche tecniche
    - Strategia di adoption
    - Ore previste vs ore svolte
    - Team di lavoro (membri dipartimento IT)
    - Deadline e priorità (drag & drop)
    """
    __tablename__ = "it_projects"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # ─── Info Base ───
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    specifications = db.Column(db.Text)  # Specifiche tecniche dettagliate
    adoption_strategy = db.Column(db.Text)  # Strategia di adoption

    # ─── Ore di Lavoro ───
    estimated_hours = db.Column(db.Float, default=0)  # Ore previste
    worked_hours = db.Column(db.Float, default=0)  # Ore svolte

    # ─── Deadline ───
    deadline = db.Column(db.Date, nullable=True)  # Può essere NULL se da definire
    has_deadline = db.Column(db.Boolean, default=False, nullable=False)

    # ─── Ordinamento e Priorità ───
    # Per progetti con deadline: ordinamento per data
    # Per progetti senza deadline: ordinamento manuale drag & drop
    priority_order = db.Column(db.Integer, default=0, nullable=False, index=True)

    # ─── Stato ───
    status = db.Column(
        db.String(20),
        default='planning',
        nullable=False,
        index=True
    )  # planning, in_progress, review, completed, on_hold, cancelled

    # ─── Audit ───
    created_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─── Relazioni ───
    created_by = relationship("User", foreign_keys=[created_by_id])

    team_members = relationship(
        "User",
        secondary=it_project_members,
        backref=db.backref("it_projects_assigned", lazy="dynamic"),
        lazy="select"
    )

    # ─── Indici ───
    __table_args__ = (
        Index("idx_it_projects_status", "status"),
        Index("idx_it_projects_deadline", "has_deadline", "deadline"),
        Index("idx_it_projects_priority", "has_deadline", "priority_order"),
    )

    # ─── Properties ───
    @property
    def progress_percentage(self) -> float:
        """Percentuale di completamento basata sulle ore."""
        if not self.estimated_hours or self.estimated_hours <= 0:
            return 0
        return min(100, round((self.worked_hours / self.estimated_hours) * 100, 1))

    @property
    def remaining_hours(self) -> float:
        """Ore rimanenti."""
        return max(0, (self.estimated_hours or 0) - (self.worked_hours or 0))

    @property
    def is_overdue(self) -> bool:
        """True se la deadline è passata."""
        if not self.deadline or self.status in ('completed', 'cancelled'):
            return False
        return self.deadline < date.today()

    @property
    def days_until_deadline(self) -> int | None:
        """Giorni rimanenti alla deadline."""
        if not self.deadline:
            return None
        return (self.deadline - date.today()).days

    @property
    def status_label(self) -> str:
        """Label leggibile per lo stato."""
        labels = {
            'planning': 'Pianificazione',
            'in_progress': 'In Corso',
            'review': 'In Review',
            'completed': 'Completato',
            'on_hold': 'In Pausa',
            'cancelled': 'Annullato'
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        """Classe CSS per colore stato."""
        colors = {
            'planning': 'info',
            'in_progress': 'primary',
            'review': 'warning',
            'completed': 'success',
            'on_hold': 'secondary',
            'cancelled': 'danger'
        }
        return colors.get(self.status, 'secondary')

    def __repr__(self) -> str:
        return f"<ITProject {self.id} - {self.title!r}>"


# --------------------------------------------------------------------------- #
#  IT PROBLEMS - Sistema Segnalazione Problemi
# --------------------------------------------------------------------------- #
class ITProblem(TimestampMixin, db.Model):
    """
    Segnalazioni problemi IT.

    Gestisce le problematiche segnalate dagli utenti con:
    - Criticità (bloccante/non bloccante)
    - Strumento coinvolto (Suite, GHL, Respond.io, Altro)
    - Stato di risoluzione
    - Tempo di risoluzione tracciato
    """
    __tablename__ = "it_problems"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # ─── Info Base ───
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # ─── Classificazione ───
    criticality = db.Column(
        db.String(20),
        nullable=False,
        default='non_blocking',
        index=True
    )  # blocking, non_blocking

    tool = db.Column(
        db.String(30),
        nullable=False,
        default='suite',
        index=True
    )  # suite, ghl, respond_io, other

    # ─── Stato ───
    status = db.Column(
        db.String(20),
        nullable=False,
        default='open',
        index=True
    )  # open, in_progress, resolved, closed

    # ─── Utenti ───
    reported_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    assigned_to_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─── Risoluzione ───
    resolved_at = db.Column(db.DateTime, nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)

    # ─── Relazioni ───
    reported_by = relationship(
        "User",
        foreign_keys=[reported_by_id],
        backref=db.backref("it_problems_reported", lazy="dynamic")
    )
    assigned_to = relationship(
        "User",
        foreign_keys=[assigned_to_id],
        backref=db.backref("it_problems_assigned", lazy="dynamic")
    )

    # ─── Indici ───
    __table_args__ = (
        Index("idx_it_problems_status_criticality", "status", "criticality"),
        Index("idx_it_problems_tool", "tool"),
    )

    # ─── Properties ───
    @property
    def criticality_label(self) -> str:
        """Label leggibile per criticità."""
        labels = {
            'blocking': 'Bloccante',
            'non_blocking': 'Non Bloccante'
        }
        return labels.get(self.criticality, self.criticality)

    @property
    def criticality_color(self) -> str:
        """Colore per criticità."""
        colors = {
            'blocking': 'danger',
            'non_blocking': 'warning'
        }
        return colors.get(self.criticality, 'secondary')

    @property
    def tool_label(self) -> str:
        """Label leggibile per strumento."""
        labels = {
            'suite': 'Corposostenibile Suite',
            'ghl': 'Go High Level',
            'respond_io': 'Respond.io',
            'other': 'Altro'
        }
        return labels.get(self.tool, self.tool)

    @property
    def tool_icon(self) -> str:
        """Icona per strumento."""
        icons = {
            'suite': 'ri-dashboard-line',
            'ghl': 'ri-rocket-line',
            'respond_io': 'ri-message-3-line',
            'other': 'ri-question-line'
        }
        return icons.get(self.tool, 'ri-question-line')

    @property
    def status_label(self) -> str:
        """Label leggibile per stato."""
        labels = {
            'open': 'Aperto',
            'in_progress': 'In Lavorazione',
            'resolved': 'Risolto'
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        """Colore per stato."""
        colors = {
            'open': 'danger',
            'in_progress': 'warning',
            'resolved': 'success'
        }
        return colors.get(self.status, 'secondary')

    @property
    def resolution_time_hours(self) -> float | None:
        """Ore impiegate per risolvere (da creazione a risoluzione)."""
        if not self.resolved_at:
            return None
        delta = self.resolved_at - self.created_at
        return round(delta.total_seconds() / 3600, 1)

    @property
    def is_overdue(self) -> bool:
        """True se aperto da più di 48h (bloccante) o 7 giorni (non bloccante)."""
        if self.status == 'resolved':
            return False
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        if self.criticality == 'blocking':
            return (now - self.created_at) > timedelta(hours=48)
        return (now - self.created_at) > timedelta(days=7)

    @property
    def time_open_hours(self) -> float:
        """Ore da quando è stato aperto."""
        from datetime import datetime
        end_time = self.resolved_at if self.resolved_at else datetime.utcnow()
        delta = end_time - self.created_at
        return round(delta.total_seconds() / 3600, 1)

    def __repr__(self) -> str:
        return f"<ITProblem {self.id} - {self.title!r}>"


# --------------------------------------------------------------------------- #
#  IT IDEAS - Proposte Idee dal Team
# --------------------------------------------------------------------------- #
class ITIdea(TimestampMixin, db.Model):
    """
    Idee proposte dal team per miglioramenti IT.

    Tutti gli utenti possono proporre idee.
    Solo gli admin possono approvarle/rifiutarle e convertirle in progetti.
    """
    __tablename__ = "it_ideas"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # ─── Info Base ───
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    # ─── Stato ───
    status = db.Column(
        db.String(20),
        nullable=False,
        default='pending',
        index=True
    )  # pending, approved, rejected, converted

    # ─── Utenti ───
    proposed_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # ─── Conversione a Progetto ───
    converted_to_project_id = db.Column(
        db.Integer,
        db.ForeignKey("it_projects.id", ondelete="SET NULL"),
        nullable=True
    )
    converted_at = db.Column(db.DateTime, nullable=True)
    converted_by_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─── Note Admin ───
    admin_notes = db.Column(db.Text, nullable=True)

    # ─── Relazioni ───
    proposed_by = relationship(
        "User",
        foreign_keys=[proposed_by_id],
        backref=db.backref("it_ideas_proposed", lazy="dynamic")
    )
    converted_by = relationship(
        "User",
        foreign_keys=[converted_by_id]
    )
    converted_to_project = relationship(
        "ITProject",
        foreign_keys=[converted_to_project_id],
        backref=db.backref("source_idea", uselist=False)
    )

    # ─── Indici ───
    __table_args__ = (
        Index("idx_it_ideas_status", "status"),
    )

    # ─── Properties ───
    @property
    def status_label(self) -> str:
        """Label leggibile per stato."""
        labels = {
            'pending': 'In Attesa',
            'approved': 'Approvata',
            'rejected': 'Rifiutata',
            'converted': 'Convertita in Progetto'
        }
        return labels.get(self.status, self.status)

    @property
    def status_color(self) -> str:
        """Colore per stato."""
        colors = {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'converted': 'primary'
        }
        return colors.get(self.status, 'secondary')

    @property
    def is_convertible(self) -> bool:
        """True se l'idea può essere convertita in progetto."""
        return self.status in ['pending', 'approved'] and not self.converted_to_project_id

    def __repr__(self) -> str:
        return f"<ITIdea {self.id} - {self.title!r}>"


# --------------------------------------------------------------------------- #
#  IT MANUALS - Manuali e Guide per Piattaforme
# --------------------------------------------------------------------------- #

class ITPlatformEnum(str, Enum):
    """Piattaforme disponibili per i manuali"""
    suite = "suite"
    ghl = "ghl"
    respond_io = "respond_io"
    loom = "loom"


class ITManualCategory(TimestampMixin, db.Model):
    """
    Categorie per organizzare i manuali di ogni piattaforma.
    Es: "Gestione Clienti", "Configurazione", "Troubleshooting"
    """
    __tablename__ = "it_manual_categories"

    id = db.Column(db.Integer, primary_key=True)

    # ─── Info Base ───
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Classe icona (es. ri-folder-line)
    color = db.Column(db.String(7), default='#6c757d')  # Colore HEX

    # ─── Piattaforma ───
    platform = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )  # suite, ghl, respond_io, loom

    # ─── Ordinamento ───
    order_index = db.Column(db.Integer, default=0, nullable=False)

    # ─── Stato ───
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # ─── Relazioni ───
    articles = relationship(
        "ITManualArticle",
        back_populates="category",
        cascade="all, delete-orphan",
        order_by="ITManualArticle.order_index"
    )

    # ─── Indici ───
    __table_args__ = (
        Index("idx_it_manual_categories_platform", "platform", "order_index"),
    )

    @property
    def platform_label(self) -> str:
        """Label leggibile per piattaforma."""
        labels = {
            'suite': 'Corposostenibile Suite',
            'ghl': 'Go High Level',
            'respond_io': 'Respond.io',
            'loom': 'Loom'
        }
        return labels.get(self.platform, self.platform)

    @property
    def articles_count(self) -> int:
        """Numero di articoli attivi nella categoria."""
        return len([a for a in self.articles if a.is_published])

    def __repr__(self) -> str:
        return f"<ITManualCategory {self.id} - {self.name!r} ({self.platform})>"


class ITManualArticle(TimestampMixin, db.Model):
    """
    Articoli/Guide per ogni piattaforma.
    Supporta contenuto rich text e video Loom embedded.
    """
    __tablename__ = "it_manual_articles"
    __versioned__ = {}

    id = db.Column(db.Integer, primary_key=True)

    # ─── Info Base ───
    title = db.Column(db.String(255), nullable=False)
    slug = db.Column(db.String(300), nullable=False, index=True)
    summary = db.Column(db.Text)  # Breve descrizione
    content = db.Column(db.Text, nullable=False)  # HTML content

    # ─── Piattaforma e Categoria ───
    platform = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )
    category_id = db.Column(
        db.Integer,
        db.ForeignKey("it_manual_categories.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─── Video ───
    loom_url = db.Column(db.String(500))  # URL video Loom (opzionale)
    video_duration = db.Column(db.Integer)  # Durata in secondi

    # ─── Ordinamento ───
    order_index = db.Column(db.Integer, default=0, nullable=False)

    # ─── Stato ───
    is_published = db.Column(db.Boolean, default=False, nullable=False, index=True)
    is_featured = db.Column(db.Boolean, default=False, nullable=False)  # In evidenza
    published_at = db.Column(db.DateTime)

    # ─── Audit ───
    author_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    last_editor_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # ─── Statistiche ───
    views_count = db.Column(db.Integer, default=0, nullable=False)

    # ─── Relazioni ───
    category = relationship("ITManualCategory", back_populates="articles")
    author = relationship("User", foreign_keys=[author_id])
    last_editor = relationship("User", foreign_keys=[last_editor_id])

    # ─── Indici ───
    __table_args__ = (
        Index("idx_it_manual_articles_platform_published", "platform", "is_published"),
        Index("idx_it_manual_articles_category", "category_id", "order_index"),
    )

    @property
    def platform_label(self) -> str:
        """Label leggibile per piattaforma."""
        labels = {
            'suite': 'Corposostenibile Suite',
            'ghl': 'Go High Level',
            'respond_io': 'Respond.io',
            'loom': 'Loom'
        }
        return labels.get(self.platform, self.platform)

    @property
    def has_video(self) -> bool:
        """True se l'articolo ha un video Loom."""
        return bool(self.loom_url)

    @property
    def loom_embed_url(self) -> str | None:
        """Converte URL Loom in embed URL."""
        if not self.loom_url:
            return None
        # https://www.loom.com/share/xxx -> https://www.loom.com/embed/xxx
        if '/share/' in self.loom_url:
            return self.loom_url.replace('/share/', '/embed/')
        return self.loom_url

    @property
    def read_time_minutes(self) -> int:
        """Stima tempo di lettura."""
        if not self.content:
            return 0
        word_count = len(self.content.split())
        return max(1, word_count // 200)

    @property
    def video_duration_formatted(self) -> str | None:
        """Durata video formattata (MM:SS)."""
        if not self.video_duration:
            return None
        minutes = self.video_duration // 60
        seconds = self.video_duration % 60
        return f"{minutes}:{seconds:02d}"

    def __repr__(self) -> str:
        return f"<ITManualArticle {self.id} - {self.title!r}>"


# --------------------------------------------------------------------------- #
#  KPI SYSTEM - Snapshot e Tracking KPI
# --------------------------------------------------------------------------- #
class KPISnapshot(TimestampMixin, db.Model):
    """
    Snapshot periodici dei KPI aziendali.
    Salva i valori calcolati dei KPI per storicizzazione e reporting.

    KPI supportati:
    - tasso_rinnovi: percentuale clienti che rinnovano
    - tasso_referral: percentuale referral convertiti
    """
    __tablename__ = 'kpi_snapshots'
    __table_args__ = (
        db.Index('ix_kpi_snapshots_type_date', 'kpi_type', 'periodo_inizio', 'periodo_fine'),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Tipo di KPI
    kpi_type = db.Column(
        db.String(50),
        nullable=False,
        comment="Tipo KPI: tasso_rinnovi, tasso_referral"
    )

    # Periodo di riferimento
    periodo_inizio = db.Column(db.Date, nullable=False, comment="Data inizio periodo")
    periodo_fine = db.Column(db.Date, nullable=False, comment="Data fine periodo")

    # Valori calcolati
    numeratore = db.Column(db.Integer, nullable=False, default=0, comment="Valore numeratore formula")
    denominatore = db.Column(db.Integer, nullable=False, default=1, comment="Valore denominatore formula")
    valore_percentuale = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        comment="Valore percentuale calcolato"
    )

    # Target e performance
    target_percentuale = db.Column(
        db.Numeric(5, 2),
        nullable=True,
        comment="Target percentuale da raggiungere"
    )

    # Metadati calcolo
    dettagli_calcolo = db.Column(JSONB, comment="Dettagli del calcolo per debug/audit")
    calcolato_da_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=True,
        comment="User che ha triggherato il calcolo"
    )

    # Note
    note = db.Column(db.Text, comment="Note aggiuntive sullo snapshot")

    # Relazioni
    calcolato_da = db.relationship('User', backref='kpi_snapshots_calcolati')

    @property
    def raggiunto_target(self) -> bool | None:
        """Verifica se il target è stato raggiunto."""
        if self.target_percentuale is None:
            return None
        return self.valore_percentuale >= self.target_percentuale

    @property
    def scostamento_target(self) -> Decimal | None:
        """Calcola lo scostamento dal target."""
        if self.target_percentuale is None:
            return None
        return self.valore_percentuale - self.target_percentuale

    def __repr__(self) -> str:
        return f"<KPISnapshot {self.kpi_type} {self.periodo_inizio}->{self.periodo_fine}: {self.valore_percentuale}%>"


class ProfessionistaBonusSnapshot(TimestampMixin, db.Model):
    """
    Snapshot ARR (Adjusted Renewal Rate) per singolo professionista.
    Calcola e storicizza le performance individuali per il sistema bonus.

    Formula ARR:
    (Rinnovi + Upgrade_Convertiti*60% + Referral*60%) / (Clienti_Eleggibili + Upgrade_Totali + Referral)

    Il 60% rappresenta la quota che va al professionista proponente,
    il 40% va al professionista che riceve il cliente.
    """
    __tablename__ = 'professionista_bonus_snapshots'
    __table_args__ = (
        db.Index('ix_prof_bonus_user_periodo', 'user_id', 'periodo_inizio', 'periodo_fine'),
    )

    id = db.Column(db.Integer, primary_key=True)

    # Professionista
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id'),
        nullable=False,
        index=True,
        comment="Professionista di riferimento"
    )

    # Periodo di riferimento
    periodo_inizio = db.Column(db.Date, nullable=False, comment="Data inizio periodo")
    periodo_fine = db.Column(db.Date, nullable=False, comment="Data fine periodo")

    # ========== CONTATORI NUMERATORE ==========
    # Rinnovi diretti del professionista
    rinnovi_count = db.Column(db.Integer, default=0, comment="Numero rinnovi clienti propri")

    # Upgrade da Bonus Call (60% proponente)
    upgrade_convertiti_proponente = db.Column(
        db.Integer,
        default=0,
        comment="Upgrade convertiti come proponente (60%)"
    )
    # Upgrade ricevuti da altri (40% ricevente)
    upgrade_convertiti_ricevente = db.Column(
        db.Integer,
        default=0,
        comment="Upgrade ricevuti da altri (40%)"
    )

    # Referral (60% proponente)
    referral_convertiti_proponente = db.Column(
        db.Integer,
        default=0,
        comment="Referral convertiti come proponente (60%)"
    )
    # Referral ricevuti (40% ricevente)
    referral_convertiti_ricevente = db.Column(
        db.Integer,
        default=0,
        comment="Referral ricevuti da altri (40%)"
    )

    # ========== CONTATORI DENOMINATORE ==========
    # Clienti eleggibili (con has_goals_left=True o NULL)
    clienti_eleggibili = db.Column(
        db.Integer,
        default=0,
        comment="Clienti eleggibili nel denominatore"
    )

    # Totale upgrade proposti
    upgrade_totali = db.Column(
        db.Integer,
        default=0,
        comment="Totale upgrade proposti"
    )

    # Totale referral
    referral_totali = db.Column(
        db.Integer,
        default=0,
        comment="Totale referral nel periodo"
    )

    # ========== VALORI CALCOLATI ==========
    numeratore_pesato = db.Column(
        db.Numeric(10, 2),
        nullable=False,
        default=0,
        comment="Numeratore con pesi applicati"
    )
    denominatore_totale = db.Column(
        db.Integer,
        nullable=False,
        default=1,
        comment="Denominatore totale"
    )
    arr_percentuale = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        comment="ARR calcolato in percentuale"
    )

    # Target e soglie bonus
    target_arr = db.Column(
        db.Numeric(5, 2),
        nullable=True,
        comment="Target ARR per il bonus"
    )
    bonus_raggiunto = db.Column(
        db.Boolean,
        default=False,
        comment="Se il bonus è stato raggiunto"
    )
    importo_bonus = db.Column(
        db.Numeric(10, 2),
        nullable=True,
        comment="Importo bonus calcolato"
    )

    # Metadati
    dettagli_calcolo = db.Column(JSONB, comment="Dettagli completi del calcolo")
    note = db.Column(db.Text, comment="Note aggiuntive")

    # Relazioni
    professionista = db.relationship('User', backref='arr_snapshots')

    @property
    def raggiunto_target(self) -> bool | None:
        """Verifica se il target ARR è stato raggiunto."""
        if self.target_arr is None:
            return None
        return self.arr_percentuale >= self.target_arr

    @property
    def scostamento_target(self) -> Decimal | None:
        """Calcola lo scostamento dal target ARR."""
        if self.target_arr is None:
            return None
        return self.arr_percentuale - self.target_arr

    def calcola_arr(self) -> Decimal:
        """
        Calcola l'ARR con la formula:
        (Rinnovi + Upgrade_Conv*0.6 + Upgrade_Ric*0.4 + Referral_Conv*0.6 + Referral_Ric*0.4)
        / (Clienti_Eleggibili + Upgrade_Totali + Referral_Totali)
        """
        # Numeratore pesato
        numeratore = (
            self.rinnovi_count +
            (self.upgrade_convertiti_proponente * Decimal('0.6')) +
            (self.upgrade_convertiti_ricevente * Decimal('0.4')) +
            (self.referral_convertiti_proponente * Decimal('0.6')) +
            (self.referral_convertiti_ricevente * Decimal('0.4'))
        )

        # Denominatore
        denominatore = (
            self.clienti_eleggibili +
            self.upgrade_totali +
            self.referral_totali
        )

        if denominatore == 0:
            return Decimal('0')

        self.numeratore_pesato = numeratore
        self.denominatore_totale = denominatore
        self.arr_percentuale = (numeratore / denominatore) * 100

        return self.arr_percentuale

    def __repr__(self) -> str:
        return f"<ARRSnapshot User:{self.user_id} {self.periodo_inizio}->{self.periodo_fine}: {self.arr_percentuale}%>"


# ─────────────────────────── Impersonation Log ─────────────────────────── #
class ImpersonationLog(TimestampMixin, db.Model):
    """
    Log delle impersonazioni (accedi come) effettuate dagli admin.
    Traccia quando un admin accede come un altro utente per motivi di supporto/debug.
    """
    __tablename__ = 'impersonation_logs'

    id = db.Column(db.Integer, primary_key=True)

    # Chi ha effettuato l'impersonazione (admin)
    admin_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Chi è stato impersonato
    impersonated_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Timestamp inizio e fine impersonazione
    started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    ended_at = db.Column(db.DateTime)

    # IP e user agent per audit
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(500))

    # Motivo (opzionale)
    reason = db.Column(db.String(500))

    # Relazioni
    admin = db.relationship(
        'User',
        foreign_keys=[admin_id],
        backref=db.backref('impersonations_made', lazy='dynamic')
    )
    impersonated_user = db.relationship(
        'User',
        foreign_keys=[impersonated_user_id],
        backref=db.backref('impersonations_received', lazy='dynamic')
    )

    def __repr__(self):
        return f'<ImpersonationLog Admin:{self.admin_id} -> User:{self.impersonated_user_id}>'


# ───────────────────────── POST-IT / PROMEMORIA ──────────────────────────── #

class PostItColor(str, enum.Enum):
    """Colori disponibili per i post-it."""
    YELLOW = 'yellow'
    GREEN = 'green'
    BLUE = 'blue'
    PINK = 'pink'
    ORANGE = 'orange'
    PURPLE = 'purple'


class PostIt(TimestampMixin, db.Model):
    """
    Post-it / Promemoria personali dell'utente.
    Visibili nella sidebar destra della dashboard.
    """
    __tablename__ = 'post_its'

    id = db.Column(db.Integer, primary_key=True)

    # Utente proprietario del post-it
    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        index=True
    )

    # Contenuto del post-it
    content = db.Column(db.Text, nullable=False)

    # Colore del post-it (default: giallo)
    color = db.Column(
        db.String(20),
        default='yellow',
        nullable=False
    )

    # Data/ora promemoria (opzionale)
    reminder_at = db.Column(db.DateTime, nullable=True)

    # Ordine di visualizzazione (per drag & drop futuro)
    position = db.Column(db.Integer, default=0)

    # Soft delete
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Relazione con utente
    user = db.relationship(
        'User',
        backref=db.backref('post_its', lazy='dynamic', cascade='all, delete-orphan')
    )

    def __repr__(self):
        return f'<PostIt {self.id} user={self.user_id}>'

    def to_dict(self):
        """Serializza il post-it per le API."""
        return {
            'id': self.id,
            'content': self.content,
            'color': self.color,
            'reminderAt': self.reminder_at.isoformat() if self.reminder_at else None,
            'position': self.position,
            'createdAt': self.created_at.isoformat() if self.created_at else None,
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None,
        }


# ───────────────────────── Appointment Setting ──────────────────────────── #

class AppointmentSettingMessage(TimestampMixin, db.Model):
    """Stores monthly messaging stats from Respond.io CSV exports."""
    __tablename__ = "appointment_setting_messages"

    id = db.Column(db.Integer, primary_key=True)
    utente = db.Column(db.String(255), nullable=False)
    mese = db.Column(db.String(20), nullable=False)       # e.g. "Gennaio"
    anno = db.Column(db.Integer, nullable=False)           # e.g. 2025
    messaggi_inviati = db.Column(db.Integer, nullable=False, default=0)
    contatti_unici_chiusi = db.Column(db.Integer, nullable=False, default=0)
    conversazioni_assegnate = db.Column(db.Integer, nullable=False, default=0)
    conversazioni_chiuse = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('utente', 'mese', 'anno', name='uq_appt_utente_mese_anno'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'utente': self.utente,
            'mese': self.mese,
            'anno': self.anno,
            'messaggi_inviati': self.messaggi_inviati,
            'contatti_unici_chiusi': self.contatti_unici_chiusi,
            'conversazioni_assegnate': self.conversazioni_assegnate,
            'conversazioni_chiuse': self.conversazioni_chiuse,
        }


class AppointmentSettingContact(TimestampMixin, db.Model):
    """Stores daily contact counts per user from Respond.io bar chart CSV."""
    __tablename__ = "appointment_setting_contacts"

    id = db.Column(db.Integer, primary_key=True)
    utente = db.Column(db.String(255), nullable=False)
    giorno = db.Column(db.Integer, nullable=False)
    mese = db.Column(db.String(20), nullable=False)
    anno = db.Column(db.Integer, nullable=False)
    contatti = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('utente', 'giorno', 'mese', 'anno', name='uq_appt_contact_utente_giorno'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'utente': self.utente,
            'giorno': self.giorno,
            'mese': self.mese,
            'anno': self.anno,
            'contatti': self.contatti,
        }


class AppointmentSettingFunnel(TimestampMixin, db.Model):
    """Stores lifecycle journey breakdown data per stage."""
    __tablename__ = "appointment_setting_funnel"

    id = db.Column(db.Integer, primary_key=True)
    mese = db.Column(db.String(20), nullable=False)
    anno = db.Column(db.Integer, nullable=False)
    fase = db.Column(db.String(100), nullable=False)
    tasso_conversione = db.Column(db.Float, nullable=False, default=0)
    tempo_medio_fase = db.Column(db.Float, nullable=False, default=0)
    tasso_abbandono = db.Column(db.Float, nullable=False, default=0)
    cold = db.Column(db.Integer, nullable=False, default=0)
    non_in_target = db.Column(db.Integer, nullable=False, default=0)
    prenotato_non_in_target = db.Column(db.Integer, nullable=False, default=0)
    under = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('fase', 'mese', 'anno', name='uq_appt_funnel_fase_mese_anno'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'mese': self.mese,
            'anno': self.anno,
            'fase': self.fase,
            'tasso_conversione': self.tasso_conversione,
            'tempo_medio_fase': self.tempo_medio_fase,
            'tasso_abbandono': self.tasso_abbandono,
            'cold': self.cold,
            'non_in_target': self.non_in_target,
            'prenotato_non_in_target': self.prenotato_non_in_target,
            'under': self.under,
        }


configure_mappers()          # deve vedere anche Task
ClienteVersion = version_class(Cliente)