"""
customers.forms
===============

WTForms (Flask-WTF) per il dominio *customers* – **VERSIONE COMPLETA**.

• `ClienteForm`            – anagrafica cliente (campi ridotti)
• `CustomerFilterForm`     – filtri lista / ricerca
"""

from __future__ import annotations

from typing import Any, List

from flask_babel import lazy_gettext as _l
from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateField,
    DecimalField,
    HiddenField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

# ENUM (modello ridotto)
from corposostenibile.models import (
    CallBonusStatusEnum,
    CheckSaltatiEnum,
    CoachEnum,
    FiguraRifEnum,
    GiornoEnum,
    LuogoAllenEnum,
    NutrizionistaEnum,
    PagamentoEnum,
    PsicologaEnum,
    StatoClienteEnum,
    TeamEnum,
    TipologiaClienteEnum,
    TipoProfessionistaEnum,
    TrasformazioneEnum,
)

__all__ = [
    "ClienteForm",
    "ClienteCreateForm",
    "CustomerFilterForm",
    "FeedbackAssignForm",
    "CallBonusCreateForm",
    "CallBonusResponseForm",
    "CallBonusHMConfirmForm",
]

# --------------------------------------------------------------------------- #
# Helper: enum → choices                                                      #
# --------------------------------------------------------------------------- #


def _enum_choices(enum_cls) -> List[tuple[str, str]]:
    """Trasforma un Enum in lista di tuple (value, label “Title”)."""
    return [(e.value, e.value.replace("_", " ").title()) for e in enum_cls]


# --------------------------------------------------------------------------- #
#  FORM CREAZIONE CLIENTE SEMPLIFICATO                                        #
# --------------------------------------------------------------------------- #


class ClienteCreateForm(FlaskForm):
    """Form semplificato per la creazione iniziale del cliente - solo nome."""
    
    nome_cognome = StringField(
        _l("Nome e Cognome del Cliente"), 
        validators=[DataRequired(message="Il nome e cognome è obbligatorio"), Length(min=2, max=255)]
    )
    
    submit = SubmitField(_l("Crea Cliente"))


# --------------------------------------------------------------------------- #
#  FORM PRINCIPALE CLIENTE                                                    #
# --------------------------------------------------------------------------- #


class ClienteForm(FlaskForm):
    """Form con **solo** i campi presenti nel modello Cliente ridotto."""

    # chiave nascosta (edit)
    cliente_id = HiddenField()

    # ───────────────────── ANAGRAFICA BASE ─────────────────────────── #
    nome_cognome = StringField(
        _l("Nome e cognome"), validators=[DataRequired(), Length(max=255)]
    )
    data_di_nascita = DateField(_l("Data di nascita"), validators=[Optional()])
    professione = TextAreaField(_l("Professione"), validators=[Optional()])

    # ─────────────────── PROGRAMMA ────────────────────────────────── #
    storico_programma = TextAreaField(_l("Storico programma"), validators=[Optional()])
    programma_attuale = TextAreaField(_l("Programma attuale"), validators=[Optional()])
    macrocategoria = TextAreaField(_l("Macrocategoria"), validators=[Optional()])

    # ─────────────────── ABBONAMENTO ──────────────────────────────── #
    data_inizio_abbonamento = DateField(
        _l("Data inizio abbonamento"), validators=[Optional()]
    )
    durata_programma_giorni = IntegerField(
        _l("Durata programma (giorni)"), validators=[Optional(), NumberRange(min=0)]
    )
    rate_cliente_sales = DecimalField(
        _l("Rate cliente sales"), places=2, validators=[Optional(), NumberRange(min=0)]
    )

    # ────────────────── OBIETTIVI & PROBLEMATICHE ─────────────────── #
    obiettivo_semplicato = TextAreaField(_l("Obiettivo"), validators=[Optional()])
    consulente_alimentare = TextAreaField(
        _l("Consulente alimentare"), validators=[Optional()]
    )
    problema = TextAreaField(_l("Problema"), validators=[Optional()])
    paure = TextAreaField(_l("Paure"), validators=[Optional()])
    conseguenze = TextAreaField(_l("Conseguenze"), validators=[Optional()])

    # ────────────────── DATE CALL INIZIALI ────────────────────────── #
    data_call_iniziale_nutrizionista = DateField(
        _l("Data call nutrizionista"), validators=[Optional()]
    )
    data_call_iniziale_psicologia = DateField(
        _l("Data call psicologia"), validators=[Optional()]
    )
    data_call_iniziale_coach = DateField(
        _l("Data call coach"), validators=[Optional()]
    )

    # ──────────────────── BONUS E ALERT ───────────────────────────── #
    bonus = BooleanField(_l("Bonus"))
    alert = BooleanField(_l("Alert"))
    alert_storia = TextAreaField(_l("Alert – storia"), validators=[Optional()])

    # ──────────────────── RINNOVI ─────────────────────────────────── #
    data_rinnovo = DateField(_l("Data rinnovo"), validators=[Optional()])
    # giorni_rimanenti rimosso - ora calcolato dinamicamente
    in_scadenza = BooleanField(_l("In scadenza"))

    # ──────────────── TEAM E CLASSIFICAZIONE ──────────────────────── #
    di_team = SelectField(
        _l("Team"), choices=[("", "—")] + _enum_choices(TeamEnum), validators=[Optional()]
    )
    modalita_pagamento = SelectField(
        _l("Modalità pagamento"),
        choices=[("", "—")] + _enum_choices(PagamentoEnum),
        validators=[Optional()],
    )
    note_rinnovo = TextAreaField(_l("Note rinnovo"), validators=[Optional()])
    tipologia_cliente = SelectField(
        _l("Tipologia cliente"),
        choices=[("", "—")] + _enum_choices(TipologiaClienteEnum),
        validators=[Optional()],
    )

    # ──────────────────── STAFF ───────────────────────────────────── #
    nutrizionista = SelectField(
        _l("Nutrizionista"),
        choices=[("", "—")] + _enum_choices(NutrizionistaEnum),
        validators=[Optional()],
    )
    coach = SelectField(
        _l("Coach"),
        choices=[("", "—")] + _enum_choices(CoachEnum),
        validators=[Optional()],
    )
    psicologa = SelectField(
        _l("Psicologa"),
        choices=[("", "—")] + _enum_choices(PsicologaEnum),
        validators=[Optional()],
    )

    # ─────────────── CALL INIZIALI (BOOLEAN) ──────────────────────── #
    call_iniziale_nutrizionista = BooleanField(_l("Call nutrizionista effettuata"))
    call_iniziale_coach = BooleanField(_l("Call coach effettuata"))
    call_iniziale_psicologa = BooleanField(_l("Call psicologa effettuata"))

    # ──────────────── TEST E TIPI ─────────────────────────────────── #
    data_test_alim = DateField(_l("Data test alimentare"), validators=[Optional()])
    tipo_iniziale = TextAreaField(_l("Tipo iniziale"), validators=[Optional()])
    tipo_attuale = TextAreaField(_l("Tipo attuale"), validators=[Optional()])
    piano_alimentare = TextAreaField(_l("Piano alimentare"), validators=[Optional()])

    # ─────────────── CHECK E STATI ────────────────────────────────── #
    check_day = SelectField(
        _l("Giorno check"),
        choices=[("", "—")] + _enum_choices(GiornoEnum),
        validators=[Optional()],
    )
    stato_cliente = SelectField(
        _l("Stato cliente"), choices=_enum_choices(StatoClienteEnum), validators=[DataRequired()]
    )
    check_saltati = SelectField(
        _l("Check saltati"),
        choices=[("", "—")] + _enum_choices(CheckSaltatiEnum),
        validators=[Optional()],
    )
    stato_cliente_chat = SelectField(
        _l("Stato chat"),
        choices=[("", "—")] + _enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    stato_cliente_sedute_psico = SelectField(
        _l("Stato sedute psicologia"),
        choices=[("", "—")] + _enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )

    # ──────────── STORIE SPECIALISTI ──────────────────────────────── #
    storia_coach = TextAreaField(_l("Storia coach"), validators=[Optional()])
    storia_nutrizione = TextAreaField(_l("Storia nutrizione"), validators=[Optional()])
    note_extra_nutrizione = TextAreaField(
        _l("Note extra nutrizione"), validators=[Optional()]
    )
    storia_psicologica = TextAreaField(_l("Storia psicologia"), validators=[Optional()])

    # ──────────────── REACH OUT ───────────────────────────────────── #
    reach_out = BooleanField(_l("Reach out"))

    # ──────────────── ALLENAMENTO ─────────────────────────────────── #
    allenamento_dal = DateField(_l("Allenamento dal"), validators=[Optional()])
    nuovo_allenamento_il = DateField(_l("Nuovo allenamento il"), validators=[Optional()])
    luogo_di_allenamento = SelectField(
        _l("Luogo allenamento"),
        choices=[("", "—")] + _enum_choices(LuogoAllenEnum),
        validators=[Optional()],
    )

    # ──────────────── DIETA ───────────────────────────────────────── #
    dieta_dal = DateField(_l("Dieta dal"), validators=[Optional()])
    nuova_dieta_dal = DateField(_l("Nuova dieta dal"), validators=[Optional()])

    # ──────────── FIGURA DI RIFERIMENTO ───────────────────────────── #
    figura_di_riferimento = SelectField(
        _l("Figura di riferimento"),
        choices=[("", "—")] + _enum_choices(FiguraRifEnum),
        validators=[Optional()],
    )

    # ──────────────── SOCIAL E MEDIA ──────────────────────────────── #
    no_social = BooleanField(_l("No social"))
    video_feedback = BooleanField(_l("Video feedback"))
    proposta_live_training = BooleanField(_l("Proposta live training"))
    live_training_proposte = BooleanField(_l("Live training proposte"))
    video_feedback_richiesto = BooleanField(_l("Video feedback richiesto"))
    video_feedback_svolto = BooleanField(_l("Video feedback svolto"))
    video_feedback_condiviso = BooleanField(_l("Video feedback condiviso"))

    # ──────────────── TRASFORMAZIONE ──────────────────────────────── #
    trasformazione_fisica = BooleanField(_l("Trasformazione fisica"))
    trasformazione_fisica_condivisa = BooleanField(
        _l("Trasformazione fisica condivisa")
    )
    trasformazione = SelectField(
        _l("Trasformazione"),
        choices=[("", "—")] + _enum_choices(TrasformazioneEnum),
        validators=[Optional()],
    )

    # ──────────────── EXIT CALL ───────────────────────────────────── #
    exit_call_richiesta = BooleanField(_l("Exit call richiesta"))
    exit_call_svolta = BooleanField(_l("Exit call svolta"))
    exit_call_condivisa = BooleanField(_l("Exit call condivisa"))

    # ──────────────── PATOLOGIE ───────────────────────────────────── #
    patologia_ibs = BooleanField(_l("IBS"))
    patologia_reflusso = BooleanField(_l("Reflusso"))
    patologia_gastrite = BooleanField(_l("Gastrite"))
    patologia_dca = BooleanField(_l("DCA"))
    patologia_insulino_resistenza = BooleanField(_l("Insulino-resistenza"))
    patologia_diabete = BooleanField(_l("Diabete"))
    patologia_dislipidemie = BooleanField(_l("Dislipidemie"))
    patologia_steatosi_epatica = BooleanField(_l("Steatosi epatica"))
    patologia_ipertensione = BooleanField(_l("Ipertensione"))
    patologia_pcos = BooleanField(_l("PCOS"))
    patologia_endometriosi = BooleanField(_l("Endometriosi"))
    patologia_obesita_sindrome = BooleanField(_l("Obesità-sindrome metabolica"))
    patologia_osteoporosi = BooleanField(_l("Osteoporosi"))
    patologia_diverticolite = BooleanField(_l("Diverticolite"))
    patologia_crohn = BooleanField(_l("Morbo di Crohn"))
    patologia_stitichezza = BooleanField(_l("Stitichezza"))
    patologia_tiroidee = BooleanField(_l("Malattie tiroidee"))

    # ──────────────── SUBMIT ──────────────────────────────────────── #
    submit = SubmitField(_l("Salva"))


# --------------------------------------------------------------------------- #
#  FORM FILTRI LISTA CLIENTI                                                  #
# --------------------------------------------------------------------------- #


class CustomerFilterForm(FlaskForm):
    """Filtri ricerca lista clienti."""

    # Ricerca full-text
    q = StringField(_l("Ricerca"), validators=[Optional(), Length(max=255)])

    # Filtro tipologia cliente
    tipologia_cliente = SelectField(
        _l("Tipologia"),
        choices=[("", "Tutte le tipologie")] + _enum_choices(TipologiaClienteEnum),
        validators=[Optional()],
    )
    
    # Filtri professionisti - saranno popolati dinamicamente con gli User
    nutrizionista_id = SelectField(
        _l("Nutrizionista"),
        choices=[("", "Tutti i nutrizionisti")],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None
    )
    
    coach_id = SelectField(
        _l("Coach"),
        choices=[("", "Tutti i coach")],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None
    )
    
    psicologa_id = SelectField(
        _l("Psicologa"),
        choices=[("", "Tutti gli psicologi")],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None
    )
    
    consulente_alimentare_id = SelectField(
        _l("Consulente Alimentare"),
        choices=[("", "Tutti i consulenti")],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None
    )

    health_manager_id = SelectField(
        _l("Health Manager"),
        choices=[("", "Tutti gli health manager")],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None
    )

    # ─────────────── FILTRI SECONDARI/AVANZATI ───────────────────── #
    
    # Stato Cliente
    stato_cliente = SelectField(
        _l("Stato Cliente"),
        choices=[("", "Tutti gli stati")] + _enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    
    
    # Trasformazione Fisica
    trasformazione_fisica = SelectField(
        _l("Trasformazione Fisica"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    
    # Trasformazione Condivisa
    trasformazione_fisica_condivisa = SelectField(
        _l("Trasformazione Condivisa"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    
    # Giorno Check
    check_day = SelectField(
        _l("Giorno Check"),
        choices=[("", "Tutti i giorni")] + _enum_choices(GiornoEnum),
        validators=[Optional()],
    )
    
    # Reach Out (giorno della settimana come stringa)
    reach_out = SelectField(
        _l("Reach Out"),
        choices=[
            ("", "Tutti i giorni"),
            ("lunedi", "Lunedì"),
            ("martedi", "Martedì"),
            ("mercoledi", "Mercoledì"),
            ("giovedi", "Giovedì"),
            ("venerdi", "Venerdì"),
            ("sabato", "Sabato"),
            ("domenica", "Domenica"),
        ],
        validators=[Optional()],
    )

    # Filtri date allenamento
    allenamento_dal_from = DateField(
        _l("Allenamento Dal - Da"),
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    allenamento_dal_to = DateField(
        _l("Allenamento Dal - A"),
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    nuovo_allenamento_il_from = DateField(
        _l("Nuovo Allenamento Il - Da"),
        validators=[Optional()],
        format='%Y-%m-%d'
    )
    nuovo_allenamento_il_to = DateField(
        _l("Nuovo Allenamento Il - A"),
        validators=[Optional()],
        format='%Y-%m-%d'
    )

    # Filtro scadenze
    expiring_days = SelectField(
        _l("Scadenze"),
        choices=[
            ("", "Tutte le scadenze"),
            ("10", "Entro 10 giorni"),
            ("30", "Entro 1 mese"),
            ("60", "Entro 2 mesi"),
            ("90", "Entro 3 mesi"),
        ],
        validators=[Optional()],
        coerce=lambda x: int(x) if x and x != "" else None
    )

    # ─────────────── FILTRI CAMPI VUOTI/NON COMPILATI ────────────────── #
    missing_check_day = BooleanField(_l("Solo clienti con Giorno Check NON compilato"))
    missing_check_saltati = BooleanField(_l("Solo clienti con Check Saltati NON compilato"))
    missing_reach_out = BooleanField(_l("Solo clienti con Reach Out NON compilato"))

    # Filtri stati servizio non compilati
    missing_stato_nutrizione = BooleanField(_l("Solo clienti con Stato Servizio Nutrizione NON compilato"))
    missing_stato_chat_nutrizione = BooleanField(_l("Solo clienti con Stato Chat Nutrizione NON compilato"))
    missing_stato_coach = BooleanField(_l("Solo clienti con Stato Servizio Coaching NON compilato"))
    missing_stato_chat_coaching = BooleanField(_l("Solo clienti con Stato Chat Coaching NON compilato"))
    missing_stato_psicologia = BooleanField(_l("Solo clienti con Stato Servizio Psicologia NON compilato"))
    missing_stato_chat_psicologia = BooleanField(_l("Solo clienti con Stato Chat Psicologia NON compilato"))

    # Filtri piani attivi mancanti
    missing_piano_dieta = BooleanField(_l("Solo clienti SENZA Piano Dieta Attivo"))
    missing_piano_allenamento = BooleanField(_l("Solo clienti SENZA Piano Allenamento Attivo"))

    # ─────────────────── TAB 1: ANAGRAFICA E OBIETTIVI ─────────────────── #
    # Anagrafica
    eta_min = IntegerField(_l("Età minima"), validators=[Optional(), NumberRange(min=0, max=150)])
    eta_max = IntegerField(_l("Età massima"), validators=[Optional(), NumberRange(min=0, max=150)])
    genere = SelectMultipleField(
        _l("Genere"),
        choices=[("uomo", "Uomo"), ("donna", "Donna"), ("altro", "Altro")],
        validators=[Optional()],
    )
    origine = StringField(_l("Origine"), validators=[Optional(), Length(max=255)])
    professione = StringField(_l("Professione"), validators=[Optional(), Length(max=255)])
    paese = StringField(_l("Paese"), validators=[Optional(), Length(max=100)])
    
    # Missing anagrafica
    missing_email = BooleanField(_l("Solo clienti senza email"))
    missing_telefono = BooleanField(_l("Solo clienti senza telefono"))
    missing_storia_cliente = BooleanField(_l("Solo clienti senza storia cliente"))
    missing_problema = BooleanField(_l("Solo clienti senza problema"))
    missing_paure = BooleanField(_l("Solo clienti senza paure"))
    missing_conseguenze = BooleanField(_l("Solo clienti senza conseguenze"))

    # ─────────────────── TAB 2: PROGRAMMA E STATO ─────────────────── #
    check_saltati = SelectMultipleField(
        _l("Check Saltati"),
        choices=_enum_choices(CheckSaltatiEnum),
        validators=[Optional()],
    )
    programma_attuale_dettaglio = StringField(_l("Programma Attuale Dettaglio"), validators=[Optional(), Length(max=100)])
    data_inizio_abbonamento_from = DateField(_l("Data Inizio Abbonamento - Da"), validators=[Optional()], format='%Y-%m-%d')
    data_inizio_abbonamento_to = DateField(_l("Data Inizio Abbonamento - A"), validators=[Optional()], format='%Y-%m-%d')
    durata_programma_min = IntegerField(_l("Durata Programma Min (giorni)"), validators=[Optional(), NumberRange(min=0)])
    durata_programma_max = IntegerField(_l("Durata Programma Max (giorni)"), validators=[Optional(), NumberRange(min=0)])
    data_rinnovo_from = DateField(_l("Data Rinnovo - Da"), validators=[Optional()], format='%Y-%m-%d')
    data_rinnovo_to = DateField(_l("Data Rinnovo - A"), validators=[Optional()], format='%Y-%m-%d')
    in_scadenza = SelectField(
        _l("In Scadenza"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    goals_evaluation_date_from = DateField(_l("Data Valutazione Obiettivi - Da"), validators=[Optional()], format='%Y-%m-%d')
    goals_evaluation_date_to = DateField(_l("Data Valutazione Obiettivi - A"), validators=[Optional()], format='%Y-%m-%d')

    # ─────────────────── TAB 3: TEAM ─────────────────── #
    missing_nutrizionista = BooleanField(_l("Solo clienti senza nutrizionista"))
    missing_coach = BooleanField(_l("Solo clienti senza coach"))
    missing_psicologa = BooleanField(_l("Solo clienti senza psicologa"))
    missing_health_manager = BooleanField(_l("Solo clienti senza health manager"))
    missing_consulente_alimentare = BooleanField(_l("Solo clienti senza consulente alimentare"))

    # ─────────────────── TAB 7: HEALTH MANAGER ─────────────────── #
    # Consenso Social
    consenso_social_richiesto = SelectField(
        _l("Consenso Social Richiesto"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    consenso_social_accettato = SelectField(
        _l("Consenso Social Accettato"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    consenso_social_con_documento = BooleanField(_l("Consenso Social con Documento"))
    missing_consenso_social_richiesto = BooleanField(_l("Solo clienti senza consenso social richiesto"))
    
    # Recensioni
    recensione_richiesta = SelectField(
        _l("Recensione Richiesta"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    recensione_accettata = SelectField(
        _l("Recensione Accettata"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    recensione_risposta = SelectField(
        _l("Recensione con Risposta"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    recensione_stelle_min = IntegerField(_l("Rating Recensione Min"), validators=[Optional(), NumberRange(min=1, max=5)])
    recensione_stelle_max = IntegerField(_l("Rating Recensione Max"), validators=[Optional(), NumberRange(min=1, max=5)])
    recensioni_lifetime_count_min = IntegerField(_l("Numero Recensioni Lifetime Min"), validators=[Optional(), NumberRange(min=0)])
    recensioni_lifetime_count_max = IntegerField(_l("Numero Recensioni Lifetime Max"), validators=[Optional(), NumberRange(min=0)])
    ultima_recensione_trustpilot_data_from = DateField(_l("Data Ultima Recensione Trustpilot - Da"), validators=[Optional()], format='%Y-%m-%d')
    ultima_recensione_trustpilot_data_to = DateField(_l("Data Ultima Recensione Trustpilot - A"), validators=[Optional()], format='%Y-%m-%d')
    missing_recensione_richiesta = BooleanField(_l("Solo clienti senza recensione richiesta"))
    
    # Videofeedback
    video_feedback_richiesto = SelectField(
        _l("Videofeedback Richiesto"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    video_feedback_svolto = SelectField(
        _l("Videofeedback Svolto"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    video_feedback_condiviso = SelectField(
        _l("Videofeedback Condiviso"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    video_feedback_con_file = BooleanField(_l("Videofeedback con File"))
    missing_video_feedback_richiesto = BooleanField(_l("Solo clienti senza videofeedback richiesto"))
    
    # Sedute Psicologia
    sedute_psicologia_comprate_min = IntegerField(_l("Sedute Psicologia Comprate Min"), validators=[Optional(), NumberRange(min=0)])
    sedute_psicologia_comprate_max = IntegerField(_l("Sedute Psicologia Comprate Max"), validators=[Optional(), NumberRange(min=0)])
    sedute_psicologia_svolte_min = IntegerField(_l("Sedute Psicologia Svolte Min"), validators=[Optional(), NumberRange(min=0)])
    sedute_psicologia_svolte_max = IntegerField(_l("Sedute Psicologia Svolte Max"), validators=[Optional(), NumberRange(min=0)])
    sedute_psicologia_rimanenti = BooleanField(_l("Sedute Psicologia Rimanenti"))
    missing_sedute_psicologia = BooleanField(_l("Solo clienti senza sedute registrate"))
    
    # Freeze
    is_frozen = SelectField(
        _l("Cliente in Freeze"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    freeze_date_from = DateField(_l("Data Freeze - Da"), validators=[Optional()], format='%Y-%m-%d')
    freeze_date_to = DateField(_l("Data Freeze - A"), validators=[Optional()], format='%Y-%m-%d')
    
    # Onboarding
    onboarding_date_from = DateField(_l("Data Onboarding - Da"), validators=[Optional()], format='%Y-%m-%d')
    onboarding_date_to = DateField(_l("Data Onboarding - A"), validators=[Optional()], format='%Y-%m-%d')
    missing_onboarding_date = BooleanField(_l("Solo clienti senza data onboarding"))
    
    # Exit Call
    exit_call_richiesta = SelectField(
        _l("Exit Call Richiesta"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    exit_call_svolta = SelectField(
        _l("Exit Call Svolta"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    exit_call_condivisa = SelectField(
        _l("Exit Call Condivisa"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    
    # Social & Trasformazione
    no_social = SelectField(
        _l("No Social"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    social_oscurato = SelectField(
        _l("Social Oscurato"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    trasformazione = SelectMultipleField(
        _l("Trasformazione"),
        choices=_enum_choices(TrasformazioneEnum),
        validators=[Optional()],
    )
    proposta_live_training = SelectField(
        _l("Live Training Proposta"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    live_training_bonus_prenotata = SelectField(
        _l("Live Training Bonus Prenotata"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )

    # ─────────────────── TAB 8: NUTRIZIONE ─────────────────── #
    stato_nutrizione = SelectMultipleField(
        _l("Stato Nutrizione"),
        choices=_enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    stato_chat_nutrizione = SelectMultipleField(
        _l("Stato Chat Nutrizione"),
        choices=_enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    call_iniziale_nutrizionista = SelectField(
        _l("Call Iniziale Nutrizionista"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    data_call_iniziale_nutrizionista_from = DateField(_l("Data Call Iniziale Nutrizionista - Da"), validators=[Optional()], format='%Y-%m-%d')
    data_call_iniziale_nutrizionista_to = DateField(_l("Data Call Iniziale Nutrizionista - A"), validators=[Optional()], format='%Y-%m-%d')
    reach_out_nutrizione = SelectMultipleField(
        _l("Reach Out Nutrizione"),
        choices=_enum_choices(GiornoEnum),
        validators=[Optional()],
    )
    dieta_dal_from = DateField(_l("Dieta Dal - Da"), validators=[Optional()], format='%Y-%m-%d')
    dieta_dal_to = DateField(_l("Dieta Dal - A"), validators=[Optional()], format='%Y-%m-%d')
    nuova_dieta_dal_from = DateField(_l("Nuova Dieta Dal - Da"), validators=[Optional()], format='%Y-%m-%d')
    nuova_dieta_dal_to = DateField(_l("Nuova Dieta Dal - A"), validators=[Optional()], format='%Y-%m-%d')
    missing_call_iniziale_nutrizionista = BooleanField(_l("Solo clienti senza call iniziale nutrizionista"))
    missing_reach_out_nutrizione = BooleanField(_l("Solo clienti senza reach out nutrizione"))
    
    # Patologie Nutrizionali
    patologia_ibs = SelectField(
        _l("Patologia IBS"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_reflusso = SelectField(
        _l("Patologia Reflusso"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_gastrite = SelectField(
        _l("Patologia Gastrite"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_dca = SelectField(
        _l("Patologia DCA"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_insulino_resistenza = SelectField(
        _l("Patologia Insulino-Resistenza"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_diabete = SelectField(
        _l("Patologia Diabete"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_dislipidemie = SelectField(
        _l("Patologia Dislipidemie"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_steatosi_epatica = SelectField(
        _l("Patologia Steatosi Epatica"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_ipertensione = SelectField(
        _l("Patologia Ipertensione"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_pcos = SelectField(
        _l("Patologia PCOS"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_endometriosi = SelectField(
        _l("Patologia Endometriosi"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_obesita_sindrome = SelectField(
        _l("Patologia Obesità Sindrome"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_osteoporosi = SelectField(
        _l("Patologia Osteoporosi"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_diverticolite = SelectField(
        _l("Patologia Diverticolite"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_crohn = SelectField(
        _l("Patologia Crohn"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_stitichezza = SelectField(
        _l("Patologia Stitichezza"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_tiroidee = SelectField(
        _l("Patologia Tiroidee"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    con_almeno_una_patologia_nutrizionale = BooleanField(_l("Con almeno una patologia nutrizionale"))
    senza_patologie_nutrizionali = BooleanField(_l("Senza patologie nutrizionali"))

    # ─────────────────── TAB 9: COACHING ─────────────────── #
    stato_coach = SelectMultipleField(
        _l("Stato Coach"),
        choices=_enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    stato_chat_coaching = SelectMultipleField(
        _l("Stato Chat Coaching"),
        choices=_enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    call_iniziale_coach = SelectField(
        _l("Call Iniziale Coach"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    data_call_iniziale_coach_from = DateField(_l("Data Call Iniziale Coach - Da"), validators=[Optional()], format='%Y-%m-%d')
    data_call_iniziale_coach_to = DateField(_l("Data Call Iniziale Coach - A"), validators=[Optional()], format='%Y-%m-%d')
    reach_out_coaching = SelectMultipleField(
        _l("Reach Out Coaching"),
        choices=_enum_choices(GiornoEnum),
        validators=[Optional()],
    )
    luogo_di_allenamento = SelectMultipleField(
        _l("Luogo di Allenamento"),
        choices=_enum_choices(LuogoAllenEnum),
        validators=[Optional()],
    )
    missing_call_iniziale_coach = BooleanField(_l("Solo clienti senza call iniziale coach"))
    missing_reach_out_coaching = BooleanField(_l("Solo clienti senza reach out coaching"))
    missing_luogo_allenamento = BooleanField(_l("Solo clienti senza luogo allenamento"))

    # ─────────────────── TAB 10: PSICOLOGIA ─────────────────── #
    stato_psicologia = SelectMultipleField(
        _l("Stato Psicologia"),
        choices=_enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    stato_chat_psicologia = SelectMultipleField(
        _l("Stato Chat Psicologia"),
        choices=_enum_choices(StatoClienteEnum),
        validators=[Optional()],
    )
    call_iniziale_psicologa = SelectField(
        _l("Call Iniziale Psicologa"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    data_call_iniziale_psicologia_from = DateField(_l("Data Call Iniziale Psicologia - Da"), validators=[Optional()], format='%Y-%m-%d')
    data_call_iniziale_psicologia_to = DateField(_l("Data Call Iniziale Psicologia - A"), validators=[Optional()], format='%Y-%m-%d')
    reach_out_psicologia = SelectMultipleField(
        _l("Reach Out Psicologia"),
        choices=_enum_choices(GiornoEnum),
        validators=[Optional()],
    )
    missing_call_iniziale_psicologa = BooleanField(_l("Solo clienti senza call iniziale psicologa"))
    missing_reach_out_psicologia = BooleanField(_l("Solo clienti senza reach out psicologia"))
    
    # Patologie Psicologiche
    patologia_psico_dca = SelectField(
        _l("Patologia Psico DCA"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_psico_obesita_psicoemotiva = SelectField(
        _l("Patologia Psico Obesità Psicoemotiva"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_psico_ansia_umore_cibo = SelectField(
        _l("Patologia Psico Ansia/Umore/Cibo"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_psico_comportamenti_disfunzionali = SelectField(
        _l("Patologia Psico Comportamenti Disfunzionali"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_psico_immagine_corporea = SelectField(
        _l("Patologia Psico Immagine Corporea"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_psico_psicosomatiche = SelectField(
        _l("Patologia Psico Psicosomatiche"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    patologia_psico_relazionali_altro = SelectField(
        _l("Patologia Psico Relazionali/Altro"),
        choices=[("", "Tutti"), ("1", "Sì"), ("0", "No")],
        validators=[Optional()],
        coerce=lambda x: None if x == "" else bool(int(x))
    )
    con_almeno_una_patologia_psicologica = BooleanField(_l("Con almeno una patologia psicologica"))
    senza_patologie_psicologiche = BooleanField(_l("Senza patologie psicologiche"))

    submit = SubmitField(_l("Filtra"))


# --------------------------------------------------------------------------- #
#  FORM ASSEGNAZIONE MANUALE FEEDBACK                                         #
# --------------------------------------------------------------------------- #


class FeedbackAssignForm(FlaskForm):
    """Form per assegnare manualmente un feedback a un cliente."""
    cliente_id = IntegerField(_l("Cliente ID"), validators=[DataRequired()])
    submit = SubmitField(_l("Assegna"))


# --------------------------------------------------------------------------- #
#  FORM CALL BONUS                                                            #
# --------------------------------------------------------------------------- #


class CallBonusCreateForm(FlaskForm):
    """Form per creare una nuova richiesta di call bonus."""

    professionista_id = SelectField(
        _l("Professionista"),
        coerce=int,
        validators=[DataRequired(message="Seleziona un professionista")]
    )

    tipo_professionista = SelectField(
        _l("Tipo Professionista"),
        choices=_enum_choices(TipoProfessionistaEnum),
        validators=[DataRequired(message="Seleziona il tipo di professionista")]
    )

    data_richiesta = DateField(
        _l("Data Richiesta"),
        validators=[DataRequired(message="La data è obbligatoria")],
        format='%Y-%m-%d'
    )

    submit = SubmitField(_l("Crea Richiesta Call Bonus"))


class CallBonusResponseForm(FlaskForm):
    """Form per registrare la risposta del cliente alla call bonus."""

    status = SelectField(
        _l("Risposta Cliente"),
        choices=[
            ('accettata', 'Accettata'),
            ('rifiutata', 'Rifiutata')
        ],
        validators=[DataRequired(message="Seleziona la risposta")]
    )

    motivazione_rifiuto = TextAreaField(
        _l("Motivazione Rifiuto"),
        validators=[Optional()],
        render_kw={"rows": 3, "placeholder": "Inserisci la motivazione se il cliente ha rifiutato"}
    )

    data_risposta = DateField(
        _l("Data Risposta"),
        validators=[DataRequired(message="La data è obbligatoria")],
        format='%Y-%m-%d'
    )

    submit = SubmitField(_l("Salva Risposta"))


class CallBonusHMConfirmForm(FlaskForm):
    """Form per la conferma dell'health manager della call bonus."""

    confermata_hm = SelectField(
        _l("Esito"),
        choices=[
            ('True', 'Confermata - Adottata'),
            ('False', 'Non Andata a Buon Fine')
        ],
        validators=[DataRequired(message="Seleziona l'esito")],
        coerce=lambda x: x == 'True'
    )

    note_hm = TextAreaField(
        _l("Note Health Manager"),
        validators=[Optional()],
        render_kw={"rows": 4, "placeholder": "Inserisci eventuali note sull'esito della call bonus"}
    )

    data_conferma_hm = DateField(
        _l("Data Conferma"),
        validators=[DataRequired(message="La data è obbligatoria")],
        format='%Y-%m-%d'
    )

    submit = SubmitField(_l("Salva Conferma"))


