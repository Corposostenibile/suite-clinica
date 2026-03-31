# customers/filters.py
"""
customers.filters
=================
Unico punto di verità per la logica di filtraggio dei clienti.
Le stesse regole vengono usate da HTML view, API, export e CLI.

Quick start
-----------
>>> from customers.filters import parse_filter_args, apply_customer_filters
>>> params = parse_filter_args(request.args)            # → CustomerFilterParams
>>> qry = apply_customer_filters(db.session.query(Cliente), params)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Iterable, List, Optional, Sequence, Tuple, Union

from flask import Request
from sqlalchemy import Numeric, cast, func, or_, and_
from sqlalchemy.orm import Query
from sqlalchemy.orm.dynamic import AppenderQuery  # patch __len__

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    ClienteMarketingFlag,
    ClienteMarketingContent,
    MarketingFlagTypeEnum,
    MarketingContentTypeEnum,
    TipologiaClienteEnum,
    StatoClienteEnum,
    GiornoEnum,
    CheckSaltatiEnum,
    TrasformazioneEnum,
    LuogoAllenEnum,
    PagamentoEnum,
)

__all__ = [
    "CustomerFilterParams",
    "parse_filter_args",
    "apply_customer_filters",
]

# ────────────────────────────────────────────────────────────────────────────
# Patch globale: len(AppenderQuery) → count()
# ────────────────────────────────────────────────────────────────────────────
def _aq_len(self):  # type: ignore[no-self-use]
    """Permette len(some_dynamic_rel) senza errori."""
    return self.count()


if not hasattr(AppenderQuery, "__len__"):
    AppenderQuery.__len__ = _aq_len  # type: ignore[assignment]


# ────────────────────────────────────────────────────────────────────────────
# Helper multi-value
# ────────────────────────────────────────────────────────────────────────────
def _parse_multi_value(raw: str | Iterable[str] | None, cast_func) -> List:
    """Converte stringhe CSV o liste in lista di Enum; ignora valori non validi."""
    if not raw:
        return []
    items: Sequence[str] = raw.split(",") if isinstance(raw, str) else list(raw)
    result: List = []
    for itm in items:
        itm = itm.strip()
        if itm:
            try:
                if cast_func == StatoClienteEnum:
                    stato_mapping = {
                        "cliente": "attivo",
                        "ex_cliente": "stop",
                        "acconto": "stop",
                        "ghosting": "ghost",
                        "insoluto": "stop",
                        "freeze": "pausa",
                    }
                    itm = stato_mapping.get(itm.lower(), itm)

                # Prova prima come valore enum diretto
                if hasattr(cast_func, '__members__'):  # È un Enum
                    # Prova a trovare l'enum per nome o valore
                    enum_member = None
                    for name, member in cast_func.__members__.items():
                        if name.lower() == itm.lower() or str(member.value).lower() == itm.lower():
                            enum_member = member
                            break
                    if enum_member:
                        result.append(enum_member)
                    else:
                        # Fallback: prova come valore
                        result.append(cast_func(itm))
                else:
                    result.append(cast_func(itm))
            except (ValueError, AttributeError):
                continue
    return result


# ────────────────────────────────────────────────────────────────────────────
# Dataclass parametri
# ────────────────────────────────────────────────────────────────────────────
@dataclass(slots=True)
class CustomerFilterParams:
    """Struttura immutabile con tutti i filtri accettati dalle query."""

    q: Optional[str] = None
    tipologia: List[TipologiaClienteEnum] = field(default_factory=list)
    tipologia_supporto_nutrizione: Optional[str] = None
    tipologia_supporto_coach: Optional[str] = None

    # Filtri professionisti (FK)
    nutrizionista_id: Optional[int] = None
    nutrizionista_ids: List[int] = field(default_factory=list)  # Per filtrare per più nutrizionisti (team leader)
    coach_id: Optional[int] = None
    psicologa_id: Optional[int] = None
    consulente_alimentare_id: Optional[int] = None
    health_manager_id: Optional[int] = None

    # Filtri per clienti con professionista assegnato
    has_nutrizionista: bool = False
    has_coach: bool = False
    has_psicologo: bool = False

    created_from: Optional[date] = None
    created_to: Optional[date] = None
    rate_min: Optional[float] = None
    rate_max: Optional[float] = None

    # Filtri secondari/avanzati
    stato_cliente: Optional[StatoClienteEnum] = None
    programma_attuale: Optional[str] = None
    trasformazione_fisica: Optional[bool] = None
    trasformazione_fisica_condivisa: Optional[bool] = None
    check_day: Optional[GiornoEnum] = None
    reach_out: Optional[str] = None

    # Filtri date allenamento
    allenamento_dal_from: Optional[date] = None
    allenamento_dal_to: Optional[date] = None
    nuovo_allenamento_il_from: Optional[date] = None
    nuovo_allenamento_il_to: Optional[date] = None
    
    # Filtro scadenze (numero di giorni entro cui scade)
    expiring_days: Optional[int] = None

    # Filtri per campi vuoti/non compilati
    missing_check_day: bool = False
    missing_check_saltati: bool = False
    missing_reach_out: bool = False

    # Filtri per stati servizio non compilati
    missing_stato_nutrizione: bool = False
    missing_stato_chat_nutrizione: bool = False
    missing_stato_coach: bool = False
    missing_stato_chat_coaching: bool = False
    missing_stato_psicologia: bool = False
    missing_stato_chat_psicologia: bool = False

    # Filtri per piani attivi mancanti
    missing_piano_dieta: bool = False
    missing_piano_allenamento: bool = False

    # ─────────────────── TAB 1: ANAGRAFICA E OBIETTIVI ─────────────────── #
    # Anagrafica
    eta_min: Optional[int] = None
    eta_max: Optional[int] = None
    genere: List[str] = field(default_factory=list)  # Lista di stringhe (uomo, donna, ecc.)
    origine: Optional[str] = None
    professione: Optional[str] = None
    paese: Optional[str] = None
    origine_ids: List[int] = field(default_factory=list)  # Added for Influencer filtering
    
    # Missing anagrafica
    missing_email: bool = False
    missing_telefono: bool = False
    missing_storia_cliente: bool = False
    missing_problema: bool = False
    missing_paure: bool = False
    missing_conseguenze: bool = False

    # ─────────────────── TAB 2: PROGRAMMA E STATO ─────────────────── #
    check_saltati: List[CheckSaltatiEnum] = field(default_factory=list)
    programma_attuale_dettaglio: Optional[str] = None
    data_inizio_abbonamento_from: Optional[date] = None
    data_inizio_abbonamento_to: Optional[date] = None
    durata_programma_min: Optional[int] = None
    durata_programma_max: Optional[int] = None
    data_rinnovo_from: Optional[date] = None
    data_rinnovo_to: Optional[date] = None
    in_scadenza: Optional[bool] = None  # 3-state boolean
    goals_evaluation_date_from: Optional[date] = None
    goals_evaluation_date_to: Optional[date] = None

    # ─────────────────── TAB 3: TEAM ─────────────────── #
    missing_nutrizionista: bool = False
    missing_coach: bool = False
    missing_psicologa: bool = False
    missing_health_manager: bool = False
    missing_consulente_alimentare: bool = False

    # ─────────────────── TAB 7: HEALTH MANAGER ─────────────────── #
    # Marketing
    marketing_usabile: Optional[bool] = None  # 3-state
    marketing_stories: Optional[bool] = None  # 3-state
    marketing_carosello: Optional[bool] = None  # 3-state
    marketing_videofeedback: Optional[bool] = None  # 3-state

    # Consenso Social
    consenso_social_richiesto: Optional[bool] = None  # 3-state
    consenso_social_accettato: Optional[bool] = None  # 3-state
    consenso_social_con_documento: bool = False
    missing_consenso_social_richiesto: bool = False
    
    # Recensioni
    recensione_richiesta: Optional[bool] = None  # 3-state
    recensione_accettata: Optional[bool] = None  # 3-state
    recensione_risposta: Optional[bool] = None  # 3-state
    recensione_stelle_min: Optional[int] = None
    recensione_stelle_max: Optional[int] = None
    recensioni_lifetime_count_min: Optional[int] = None
    recensioni_lifetime_count_max: Optional[int] = None
    ultima_recensione_trustpilot_data_from: Optional[date] = None
    ultima_recensione_trustpilot_data_to: Optional[date] = None
    missing_recensione_richiesta: bool = False
    
    # Videofeedback
    video_feedback_richiesto: Optional[bool] = None  # 3-state
    video_feedback_svolto: Optional[bool] = None  # 3-state
    video_feedback_condiviso: Optional[bool] = None  # 3-state
    video_feedback_con_file: bool = False
    missing_video_feedback_richiesto: bool = False
    
    # Sedute Psicologia
    sedute_psicologia_comprate_min: Optional[int] = None
    sedute_psicologia_comprate_max: Optional[int] = None
    sedute_psicologia_svolte_min: Optional[int] = None
    sedute_psicologia_svolte_max: Optional[int] = None
    sedute_psicologia_rimanenti: bool = False
    missing_sedute_psicologia: bool = False
    
    # Freeze
    is_frozen: Optional[bool] = None
    freeze_date_from: Optional[date] = None
    freeze_date_to: Optional[date] = None
    
    # Onboarding
    onboarding_date_from: Optional[date] = None
    onboarding_date_to: Optional[date] = None
    missing_onboarding_date: bool = False
    
    # Exit Call
    exit_call_richiesta: Optional[bool] = None  # 3-state
    exit_call_svolta: Optional[bool] = None  # 3-state
    exit_call_condivisa: Optional[bool] = None  # 3-state
    
    # Social & Trasformazione
    no_social: Optional[bool] = None  # 3-state
    social_oscurato: Optional[bool] = None  # 3-state
    trasformazione: List[TrasformazioneEnum] = field(default_factory=list)
    proposta_live_training: Optional[bool] = None  # 3-state
    live_training_bonus_prenotata: Optional[bool] = None  # 3-state

    # ─────────────────── TAB 8: NUTRIZIONE ─────────────────── #
    stato_nutrizione: List[StatoClienteEnum] = field(default_factory=list)
    stato_chat_nutrizione: List[StatoClienteEnum] = field(default_factory=list)
    call_iniziale_nutrizionista: Optional[bool] = None  # 3-state
    data_call_iniziale_nutrizionista_from: Optional[date] = None
    data_call_iniziale_nutrizionista_to: Optional[date] = None
    reach_out_nutrizione: List[GiornoEnum] = field(default_factory=list)
    dieta_dal_from: Optional[date] = None
    dieta_dal_to: Optional[date] = None
    nuova_dieta_dal_from: Optional[date] = None
    nuova_dieta_dal_to: Optional[date] = None
    missing_call_iniziale_nutrizionista: bool = False
    missing_reach_out_nutrizione: bool = False
    
    # Patologie Nutrizionali
    patologia_ibs: Optional[bool] = None
    patologia_reflusso: Optional[bool] = None
    patologia_gastrite: Optional[bool] = None
    patologia_dca: Optional[bool] = None
    patologia_insulino_resistenza: Optional[bool] = None
    patologia_diabete: Optional[bool] = None
    patologia_dislipidemie: Optional[bool] = None
    patologia_steatosi_epatica: Optional[bool] = None
    patologia_ipertensione: Optional[bool] = None
    patologia_pcos: Optional[bool] = None
    patologia_endometriosi: Optional[bool] = None
    patologia_obesita_sindrome: Optional[bool] = None
    patologia_osteoporosi: Optional[bool] = None
    patologia_diverticolite: Optional[bool] = None
    patologia_crohn: Optional[bool] = None
    patologia_stitichezza: Optional[bool] = None
    patologia_tiroidee: Optional[bool] = None
    con_almeno_una_patologia_nutrizionale: bool = False
    senza_patologie_nutrizionali: bool = False  # nessuna_patologia = True (utente ha scelto esplicitamente)
    patologie_non_indicate_nutri: bool = False  # tutti i campi patologia vuoti/False e nessuna_patologia = False

    # ─────────────────── TAB 9: COACHING ─────────────────── #
    stato_coach: List[StatoClienteEnum] = field(default_factory=list)
    stato_chat_coaching: List[StatoClienteEnum] = field(default_factory=list)
    call_iniziale_coach: Optional[bool] = None  # 3-state
    data_call_iniziale_coach_from: Optional[date] = None
    data_call_iniziale_coach_to: Optional[date] = None
    reach_out_coaching: List[GiornoEnum] = field(default_factory=list)
    luogo_di_allenamento: List[LuogoAllenEnum] = field(default_factory=list)
    missing_call_iniziale_coach: bool = False
    missing_reach_out_coaching: bool = False
    missing_luogo_allenamento: bool = False

    # ─────────────────── TAB 10: PSICOLOGIA ─────────────────── #
    stato_psicologia: List[StatoClienteEnum] = field(default_factory=list)
    stato_chat_psicologia: List[StatoClienteEnum] = field(default_factory=list)
    call_iniziale_psicologa: Optional[bool] = None  # 3-state
    data_call_iniziale_psicologia_from: Optional[date] = None
    data_call_iniziale_psicologia_to: Optional[date] = None
    reach_out_psicologia: List[GiornoEnum] = field(default_factory=list)
    missing_call_iniziale_psicologa: bool = False
    missing_reach_out_psicologia: bool = False
    
    # Patologie Psicologiche
    patologia_psico_dca: Optional[bool] = None
    patologia_psico_obesita_psicoemotiva: Optional[bool] = None
    patologia_psico_ansia_umore_cibo: Optional[bool] = None
    patologia_psico_comportamenti_disfunzionali: Optional[bool] = None
    patologia_psico_immagine_corporea: Optional[bool] = None
    patologia_psico_psicosomatiche: Optional[bool] = None
    patologia_psico_relazionali_altro: Optional[bool] = None
    con_almeno_una_patologia_psicologica: bool = False
    senza_patologie_psicologiche: bool = False  # nessuna_patologia_psico = True (utente ha scelto esplicitamente)
    patologie_non_indicate_psico: bool = False  # tutti i campi patologia psico vuoti/False e nessuna_patologia_psico = False

    # ─────────────────── TIPOLOGIA MANCANTE ─────────────────── #
    missing_tipologia: bool = False  # tipologia_cliente IS NULL

    # ─────────────────── TAB 12: PAGAMENTI ─────────────────── #
    modalita_pagamento: List[PagamentoEnum] = field(default_factory=list)
    deposito_iniziale_min: Optional[float] = None
    deposito_iniziale_max: Optional[float] = None

    sort: str = "created_at:desc"
    page: int = 1
    per_page: int = 25

    # ------------------------------------------------------------------ #
    # Factory                                                            #
    # ------------------------------------------------------------------ #
    @classmethod
    def from_request(cls, req: Union[Request, dict]) -> "CustomerFilterParams":
        """
        Costruisce l'istanza da ``flask.Request`` o da un mapping (per i test).
        Gestisce sia i nomi brevi (CLI / API) che quelli generati dal form.
        """
        args = req.args if isinstance(req, Request) else req

        def _val(primary: str, *fallback: str):
            for k in (primary, *fallback):
                if k in args:
                    return args.get(k)
            return None
        
        def _getlist(key: str):
            """Helper per ottenere liste da request args o dict."""
            if isinstance(req, Request):
                return req.args.getlist(key)
            elif hasattr(args, 'getlist'):
                # Supporta ImmutableMultiDict e simili
                return args.getlist(key)
            elif isinstance(args, dict):
                val = args.get(key)
                if isinstance(val, list):
                    return val
                elif val:
                    return [val]
            return []

        # Parse dei filtri avanzati
        stato_str = args.get("stato_cliente")
        stato = None
        if stato_str:
            # Mappatura per vecchi valori
            stato_mapping = {
                'cliente': 'attivo',
                'ex_cliente': 'stop',
                'acconto': 'stop',
                'ghosting': 'ghost',
                'insoluto': 'stop',
                'freeze': 'pausa',
            }
            stato_str = stato_mapping.get(stato_str, stato_str)
            try:
                stato = StatoClienteEnum(stato_str)
            except ValueError:
                pass
                
        check_day_str = args.get("check_day")
        check_day = None
        if check_day_str:
            try:
                check_day = GiornoEnum(check_day_str)
            except ValueError:
                pass
        
        # Parse bool fields
        trasf_fisica = None
        if args.get("trasformazione_fisica") == "1":
            trasf_fisica = True
        elif args.get("trasformazione_fisica") == "0":
            trasf_fisica = False
            
        trasf_condivisa = None
        if args.get("trasformazione_fisica_condivisa") == "1":
            trasf_condivisa = True
        elif args.get("trasformazione_fisica_condivisa") == "0":
            trasf_condivisa = False

        # Parse nutrizionista_ids (lista di ID per team leader)
        nutrizionista_ids_raw = _getlist("nutrizionista_ids")
        nutrizionista_ids = []
        for nid in nutrizionista_ids_raw:
            try:
                nutrizionista_ids.append(int(nid))
            except (ValueError, TypeError):
                continue

        return cls(
            q=args.get("q"),
            tipologia=_parse_multi_value(
                _val("tipologia_cliente", "tipologia"), TipologiaClienteEnum
            ),
            tipologia_supporto_nutrizione=args.get("tipologia_supporto_nutrizione") or None,
            tipologia_supporto_coach=args.get("tipologia_supporto_coach") or None,
            nutrizionista_id=_parse_int(args.get("nutrizionista_id"), None, 0) if args.get("nutrizionista_id") else None,
            nutrizionista_ids=nutrizionista_ids,
            coach_id=_parse_int(args.get("coach_id"), None, 0) if args.get("coach_id") else None,
            psicologa_id=_parse_int(args.get("psicologa_id"), None, 0) if args.get("psicologa_id") else None,
            consulente_alimentare_id=_parse_int(args.get("consulente_alimentare_id"), None, 0) if args.get("consulente_alimentare_id") else None,
            health_manager_id=_parse_int(args.get("health_manager_id"), None, 0) if args.get("health_manager_id") else None,
            # Filtri per clienti con professionista assegnato
            has_nutrizionista=args.get("has_nutrizionista") == "1",
            has_coach=args.get("has_coach") == "1",
            has_psicologo=args.get("has_psicologo") == "1",
            created_from=_parse_date(_val("from_date", "created_from")),
            created_to=_parse_date(_val("to_date", "created_to")),
            rate_min=_parse_float(_val("min_rate", "rate_min")),
            rate_max=_parse_float(_val("max_rate", "rate_max")),
            allenamento_dal_from=_parse_date(args.get("allenamento_dal_from")),
            allenamento_dal_to=_parse_date(args.get("allenamento_dal_to")),
            nuovo_allenamento_il_from=_parse_date(args.get("nuovo_allenamento_il_from")),
            nuovo_allenamento_il_to=_parse_date(args.get("nuovo_allenamento_il_to")),
            stato_cliente=stato,
            programma_attuale=args.get("programma_attuale") if args.get("programma_attuale") else None,
            trasformazione_fisica=trasf_fisica,
            trasformazione_fisica_condivisa=trasf_condivisa,
            check_day=check_day,
            reach_out=args.get("reach_out") if args.get("reach_out") else None,
            expiring_days=_parse_int(args.get("expiring_days"), None, 0) if args.get("expiring_days") else None,
            missing_check_day=args.get("missing_check_day") == "1",
            missing_check_saltati=args.get("missing_check_saltati") == "1",
            missing_reach_out=args.get("missing_reach_out") == "1",
            missing_stato_nutrizione=args.get("missing_stato_nutrizione") == "1",
            missing_stato_chat_nutrizione=args.get("missing_stato_chat_nutrizione") == "1",
            missing_stato_coach=args.get("missing_stato_coach") == "1",
            missing_stato_chat_coaching=args.get("missing_stato_chat_coaching") == "1",
            missing_stato_psicologia=args.get("missing_stato_psicologia") == "1",
            missing_stato_chat_psicologia=args.get("missing_stato_chat_psicologia") == "1",
            missing_piano_dieta=args.get("missing_piano_dieta") == "1",
            missing_piano_allenamento=args.get("missing_piano_allenamento") == "1",
            # ─────────────────── TAB 1: ANAGRAFICA ─────────────────── #
            eta_min=_parse_int(args.get("eta_min"), None, 0),
            eta_max=_parse_int(args.get("eta_max"), None, 0),
            genere=_getlist("genere"),
            origine=args.get("origine") if args.get("origine") else None,
            professione=args.get("professione") if args.get("professione") else None,
            paese=args.get("paese") if args.get("paese") else None,
            missing_email=args.get("missing_email") == "1",
            missing_telefono=args.get("missing_telefono") == "1",
            missing_storia_cliente=args.get("missing_storia_cliente") == "1",
            missing_problema=args.get("missing_problema") == "1",
            missing_paure=args.get("missing_paure") == "1",
            missing_conseguenze=args.get("missing_conseguenze") == "1",
            # ─────────────────── TAB 2: PROGRAMMA ─────────────────── #
            check_saltati=_parse_multi_value(_getlist("check_saltati"), CheckSaltatiEnum),
            programma_attuale_dettaglio=args.get("programma_attuale_dettaglio") if args.get("programma_attuale_dettaglio") else None,
            data_inizio_abbonamento_from=_parse_date(args.get("data_inizio_abbonamento_from")),
            data_inizio_abbonamento_to=_parse_date(args.get("data_inizio_abbonamento_to")),
            durata_programma_min=_parse_int(args.get("durata_programma_min"), None, 0),
            durata_programma_max=_parse_int(args.get("durata_programma_max"), None, 0),
            data_rinnovo_from=_parse_date(args.get("data_rinnovo_from")),
            data_rinnovo_to=_parse_date(args.get("data_rinnovo_to")),
            in_scadenza=_parse_3state_bool(args.get("in_scadenza")),
            goals_evaluation_date_from=_parse_date(args.get("goals_evaluation_date_from")),
            goals_evaluation_date_to=_parse_date(args.get("goals_evaluation_date_to")),
            # ─────────────────── TAB 3: TEAM ─────────────────── #
            missing_nutrizionista=args.get("missing_nutrizionista") == "1",
            missing_coach=args.get("missing_coach") == "1",
            missing_psicologa=args.get("missing_psicologa") == "1",
            missing_health_manager=args.get("missing_health_manager") == "1",
            missing_consulente_alimentare=args.get("missing_consulente_alimentare") == "1",
            # ─────────────────── TAB 7: HEALTH MANAGER ─────────────────── #
            marketing_usabile=_parse_3state_bool(args.get("marketing_usabile")),
            marketing_stories=_parse_3state_bool(args.get("marketing_stories")),
            marketing_carosello=_parse_3state_bool(args.get("marketing_carosello")),
            marketing_videofeedback=_parse_3state_bool(args.get("marketing_videofeedback")),
            consenso_social_richiesto=_parse_3state_bool(args.get("consenso_social_richiesto")),
            consenso_social_accettato=_parse_3state_bool(args.get("consenso_social_accettato")),
            consenso_social_con_documento=args.get("consenso_social_con_documento") == "1",
            missing_consenso_social_richiesto=args.get("missing_consenso_social_richiesto") == "1",
            recensione_richiesta=_parse_3state_bool(args.get("recensione_richiesta")),
            recensione_accettata=_parse_3state_bool(args.get("recensione_accettata")),
            recensione_risposta=_parse_3state_bool(args.get("recensione_risposta")),
            recensione_stelle_min=_parse_int(args.get("recensione_stelle_min"), None, 1, 5),
            recensione_stelle_max=_parse_int(args.get("recensione_stelle_max"), None, 1, 5),
            recensioni_lifetime_count_min=_parse_int(args.get("recensioni_lifetime_count_min"), None, 0),
            recensioni_lifetime_count_max=_parse_int(args.get("recensioni_lifetime_count_max"), None, 0),
            ultima_recensione_trustpilot_data_from=_parse_date(args.get("ultima_recensione_trustpilot_data_from")),
            ultima_recensione_trustpilot_data_to=_parse_date(args.get("ultima_recensione_trustpilot_data_to")),
            missing_recensione_richiesta=args.get("missing_recensione_richiesta") == "1",
            video_feedback_richiesto=_parse_3state_bool(args.get("video_feedback_richiesto")),
            video_feedback_svolto=_parse_3state_bool(args.get("video_feedback_svolto")),
            video_feedback_condiviso=_parse_3state_bool(args.get("video_feedback_condiviso")),
            video_feedback_con_file=args.get("video_feedback_con_file") == "1",
            missing_video_feedback_richiesto=args.get("missing_video_feedback_richiesto") == "1",
            sedute_psicologia_comprate_min=_parse_int(args.get("sedute_psicologia_comprate_min"), None, 0),
            sedute_psicologia_comprate_max=_parse_int(args.get("sedute_psicologia_comprate_max"), None, 0),
            sedute_psicologia_svolte_min=_parse_int(args.get("sedute_psicologia_svolte_min"), None, 0),
            sedute_psicologia_svolte_max=_parse_int(args.get("sedute_psicologia_svolte_max"), None, 0),
            sedute_psicologia_rimanenti=args.get("sedute_psicologia_rimanenti") == "1",
            missing_sedute_psicologia=args.get("missing_sedute_psicologia") == "1",
            is_frozen=_parse_3state_bool(args.get("is_frozen")),
            freeze_date_from=_parse_date(args.get("freeze_date_from")),
            freeze_date_to=_parse_date(args.get("freeze_date_to")),
            onboarding_date_from=_parse_date(args.get("onboarding_date_from")),
            onboarding_date_to=_parse_date(args.get("onboarding_date_to")),
            missing_onboarding_date=args.get("missing_onboarding_date") == "1",
            exit_call_richiesta=_parse_3state_bool(args.get("exit_call_richiesta")),
            exit_call_svolta=_parse_3state_bool(args.get("exit_call_svolta")),
            exit_call_condivisa=_parse_3state_bool(args.get("exit_call_condivisa")),
            no_social=_parse_3state_bool(args.get("no_social")),
            social_oscurato=_parse_3state_bool(args.get("social_oscurato")),
            trasformazione=_parse_multi_value(_getlist("trasformazione"), TrasformazioneEnum) if _getlist("trasformazione") else [],
            proposta_live_training=_parse_3state_bool(args.get("proposta_live_training")),
            live_training_bonus_prenotata=_parse_3state_bool(args.get("live_training_bonus_prenotata")),
            # ─────────────────── TAB 8: NUTRIZIONE ─────────────────── #
            stato_nutrizione=_parse_multi_value(_getlist("stato_nutrizione"), StatoClienteEnum) if _getlist("stato_nutrizione") else [],
            stato_chat_nutrizione=_parse_multi_value(_getlist("stato_chat_nutrizione"), StatoClienteEnum) if _getlist("stato_chat_nutrizione") else [],
            call_iniziale_nutrizionista=_parse_3state_bool(args.get("call_iniziale_nutrizionista")),
            data_call_iniziale_nutrizionista_from=_parse_date(args.get("data_call_iniziale_nutrizionista_from")),
            data_call_iniziale_nutrizionista_to=_parse_date(args.get("data_call_iniziale_nutrizionista_to")),
            reach_out_nutrizione=_parse_multi_value(_getlist("reach_out_nutrizione"), GiornoEnum) if _getlist("reach_out_nutrizione") else [],
            dieta_dal_from=_parse_date(args.get("dieta_dal_from")),
            dieta_dal_to=_parse_date(args.get("dieta_dal_to")),
            nuova_dieta_dal_from=_parse_date(args.get("nuova_dieta_dal_from")),
            nuova_dieta_dal_to=_parse_date(args.get("nuova_dieta_dal_to")),
            missing_call_iniziale_nutrizionista=args.get("missing_call_iniziale_nutrizionista") == "1",
            missing_reach_out_nutrizione=args.get("missing_reach_out_nutrizione") == "1",
            patologia_ibs=_parse_3state_bool(args.get("patologia_ibs")),
            patologia_reflusso=_parse_3state_bool(args.get("patologia_reflusso")),
            patologia_gastrite=_parse_3state_bool(args.get("patologia_gastrite")),
            patologia_dca=_parse_3state_bool(args.get("patologia_dca")),
            patologia_insulino_resistenza=_parse_3state_bool(args.get("patologia_insulino_resistenza")),
            patologia_diabete=_parse_3state_bool(args.get("patologia_diabete")),
            patologia_dislipidemie=_parse_3state_bool(args.get("patologia_dislipidemie")),
            patologia_steatosi_epatica=_parse_3state_bool(args.get("patologia_steatosi_epatica")),
            patologia_ipertensione=_parse_3state_bool(args.get("patologia_ipertensione")),
            patologia_pcos=_parse_3state_bool(args.get("patologia_pcos")),
            patologia_endometriosi=_parse_3state_bool(args.get("patologia_endometriosi")),
            patologia_obesita_sindrome=_parse_3state_bool(args.get("patologia_obesita_sindrome")),
            patologia_osteoporosi=_parse_3state_bool(args.get("patologia_osteoporosi")),
            patologia_diverticolite=_parse_3state_bool(args.get("patologia_diverticolite")),
            patologia_crohn=_parse_3state_bool(args.get("patologia_crohn")),
            patologia_stitichezza=_parse_3state_bool(args.get("patologia_stitichezza")),
            patologia_tiroidee=_parse_3state_bool(args.get("patologia_tiroidee")),
            con_almeno_una_patologia_nutrizionale=args.get("con_almeno_una_patologia_nutrizionale") == "1",
            senza_patologie_nutrizionali=args.get("senza_patologie_nutrizionali") == "1",
            patologie_non_indicate_nutri=args.get("patologie_non_indicate_nutri") == "1",
            # ─────────────────── TAB 9: COACHING ─────────────────── #
            stato_coach=_parse_multi_value(_getlist("stato_coach"), StatoClienteEnum) if _getlist("stato_coach") else [],
            stato_chat_coaching=_parse_multi_value(_getlist("stato_chat_coaching"), StatoClienteEnum) if _getlist("stato_chat_coaching") else [],
            call_iniziale_coach=_parse_3state_bool(args.get("call_iniziale_coach")),
            data_call_iniziale_coach_from=_parse_date(args.get("data_call_iniziale_coach_from")),
            data_call_iniziale_coach_to=_parse_date(args.get("data_call_iniziale_coach_to")),
            reach_out_coaching=_parse_multi_value(_getlist("reach_out_coaching"), GiornoEnum) if _getlist("reach_out_coaching") else [],
            luogo_di_allenamento=_parse_multi_value(_getlist("luogo_di_allenamento"), LuogoAllenEnum) if _getlist("luogo_di_allenamento") else [],
            missing_call_iniziale_coach=args.get("missing_call_iniziale_coach") == "1",
            missing_reach_out_coaching=args.get("missing_reach_out_coaching") == "1",
            missing_luogo_allenamento=args.get("missing_luogo_allenamento") == "1",
            # ─────────────────── TAB 10: PSICOLOGIA ─────────────────── #
            stato_psicologia=_parse_multi_value(args.get("stato_psicologia"), StatoClienteEnum) if args.get("stato_psicologia") else [],
            stato_chat_psicologia=_parse_multi_value(args.get("stato_chat_psicologia"), StatoClienteEnum) if args.get("stato_chat_psicologia") else [],
            call_iniziale_psicologa=_parse_3state_bool(args.get("call_iniziale_psicologa")),
            data_call_iniziale_psicologia_from=_parse_date(args.get("data_call_iniziale_psicologia_from")),
            data_call_iniziale_psicologia_to=_parse_date(args.get("data_call_iniziale_psicologia_to")),
            reach_out_psicologia=_parse_multi_value(args.get("reach_out_psicologia"), GiornoEnum) if args.get("reach_out_psicologia") else [],
            missing_call_iniziale_psicologa=args.get("missing_call_iniziale_psicologa") == "1",
            missing_reach_out_psicologia=args.get("missing_reach_out_psicologia") == "1",
            patologia_psico_dca=_parse_3state_bool(args.get("patologia_psico_dca")),
            patologia_psico_obesita_psicoemotiva=_parse_3state_bool(args.get("patologia_psico_obesita_psicoemotiva")),
            patologia_psico_ansia_umore_cibo=_parse_3state_bool(args.get("patologia_psico_ansia_umore_cibo")),
            patologia_psico_comportamenti_disfunzionali=_parse_3state_bool(args.get("patologia_psico_comportamenti_disfunzionali")),
            patologia_psico_immagine_corporea=_parse_3state_bool(args.get("patologia_psico_immagine_corporea")),
            patologia_psico_psicosomatiche=_parse_3state_bool(args.get("patologia_psico_psicosomatiche")),
            patologia_psico_relazionali_altro=_parse_3state_bool(args.get("patologia_psico_relazionali_altro")),
            con_almeno_una_patologia_psicologica=args.get("con_almeno_una_patologia_psicologica") == "1",
            senza_patologie_psicologiche=args.get("senza_patologie_psicologiche") == "1",
            patologie_non_indicate_psico=args.get("patologie_non_indicate_psico") == "1",
            # ─────────────────── TIPOLOGIA MANCANTE ─────────────────── #
            missing_tipologia=args.get("missing_tipologia") == "1",
            # ─────────────────── TAB 12: PAGAMENTI ─────────────────── #
            modalita_pagamento=_parse_multi_value(_getlist("modalita_pagamento"), PagamentoEnum) if _getlist("modalita_pagamento") else [],
            deposito_iniziale_min=_parse_float(args.get("deposito_iniziale_min")),
            deposito_iniziale_max=_parse_float(args.get("deposito_iniziale_max")),
            sort=args.get("sort", "created_at:desc"),
            page=_parse_int(args.get("page"), 1, 1),
            per_page=_parse_int(args.get("per_page"), 25, 5, 200),
        )


# ────────────────────────────────────────────────────────────────────────────
# Parse primitivi
# ────────────────────────────────────────────────────────────────────────────
def _parse_date(val: str | None) -> Optional[date]:
    try:
        return date.fromisoformat(val) if val else None
    except ValueError:
        return None


def _parse_float(val: str | None) -> Optional[float]:
    try:
        return float(val) if val else None
    except ValueError:
        return None


def _parse_int(val: str | None, default: int | None, min_v: int, max_v: int | None = None) -> int | None:
    if default is None and (val is None or val == ""):
        return None
    try:
        num = int(val) if val else default
    except (TypeError, ValueError):
        num = default
    if num is not None:
        num = max(num, min_v)
        if max_v is not None:
            num = min(num, max_v)
    return num


def _parse_3state_bool(val: str | None) -> Optional[bool]:
    """Parse 3-state boolean: "1" -> True, "0" -> False, None/"" -> None"""
    if not val or val == "":
        return None
    if val == "1" or val.lower() == "true":
        return True
    if val == "0" or val.lower() == "false":
        return False
    return None


# ────────────────────────────────────────────────────────────────────────────
# Compat legacy
# ────────────────────────────────────────────────────────────────────────────
def parse_filter_args(args) -> "CustomerFilterParams":  # noqa: D401
    """Alias legacy usato dalle view HTML / routes API."""
    return CustomerFilterParams.from_request(args)


# ────────────────────────────────────────────────────────────────────────────
# Applicazione filtri
# ────────────────────────────────────────────────────────────────────────────
def apply_customer_filters(qry: Query, p: CustomerFilterParams) -> Query:
    """Applica tutti i filtri di *p* alla query clienti."""
    # -------- full-text --------
    if p.q:
        term = p.q.strip()
        if term:
            # Usiamo ILIKE per tutti i database per semplicità e consistenza
            # Questo permette ricerche parziali come "francesc" -> "francesca"
            like = f"%{term}%"
            qry = qry.filter(
                or_(
                    Cliente.nome_cognome.ilike(like),
                    Cliente.mail.ilike(like),
                    Cliente.numero_telefono.ilike(like),
                )
            )

    # -------- tipologia filter ------
    if p.tipologia:
        qry = qry.filter(Cliente.tipologia_cliente.in_(p.tipologia))

    if p.missing_tipologia:
        qry = qry.filter(Cliente.tipologia_cliente.is_(None))

    if p.tipologia_supporto_nutrizione:
        qry = qry.filter(Cliente.tipologia_supporto_nutrizione == p.tipologia_supporto_nutrizione)

    if p.tipologia_supporto_coach:
        qry = qry.filter(Cliente.tipologia_supporto_coach == p.tipologia_supporto_coach)

    # -------- origine filter (Influencer) ------
    if p.origine_ids:
        qry = qry.filter(Cliente.origine_id.in_(p.origine_ids))
    
    # -------- professional filters ------
    # Usa le tabelle many-to-many per i filtri professionisti
    from sqlalchemy import text
    
    if p.nutrizionista_id is not None:
        # Usa subquery per filtrare i clienti che hanno questo nutrizionista
        subquery = text("""
            SELECT cn.cliente_id
            FROM cliente_nutrizionisti cn
            WHERE cn.user_id = :user_id
        """).bindparams(user_id=p.nutrizionista_id)
        qry = qry.filter(Cliente.cliente_id.in_(subquery))
    elif p.nutrizionista_ids:
        # Filtro per più nutrizionisti (team leader)
        placeholders = ','.join([str(int(uid)) for uid in p.nutrizionista_ids])
        subquery = text(f"""
            SELECT cn.cliente_id
            FROM cliente_nutrizionisti cn
            WHERE cn.user_id IN ({placeholders})
        """)
        qry = qry.filter(Cliente.cliente_id.in_(subquery))

    if p.coach_id is not None:
        # Usa subquery per filtrare i clienti che hanno questo coach
        subquery = text("""
            SELECT cc.cliente_id 
            FROM cliente_coaches cc 
            WHERE cc.user_id = :user_id
        """).bindparams(user_id=p.coach_id)
        qry = qry.filter(Cliente.cliente_id.in_(subquery))
    
    if p.psicologa_id is not None:
        # Usa subquery per filtrare i clienti che hanno questa psicologa
        subquery = text("""
            SELECT cp.cliente_id 
            FROM cliente_psicologi cp 
            WHERE cp.user_id = :user_id
        """).bindparams(user_id=p.psicologa_id)
        qry = qry.filter(Cliente.cliente_id.in_(subquery))
    
    if p.consulente_alimentare_id is not None:
        # Usa subquery per filtrare i clienti che hanno questo consulente alimentare
        subquery = text("""
            SELECT cca.cliente_id
            FROM cliente_consulenti_alimentari cca
            WHERE cca.user_id = :user_id
        """).bindparams(user_id=p.consulente_alimentare_id)
        qry = qry.filter(Cliente.cliente_id.in_(subquery))

    if p.health_manager_id is not None:
        # Filtro diretto su FK health_manager_id
        qry = qry.filter(Cliente.health_manager_id == p.health_manager_id)

    # -------- filtri clienti con professionista assegnato ------
    if p.has_nutrizionista:
        # Clienti che hanno almeno un nutrizionista assegnato
        subquery = text("SELECT cn.cliente_id FROM cliente_nutrizionisti cn")
        qry = qry.filter(Cliente.cliente_id.in_(subquery))

    if p.has_coach:
        # Clienti che hanno almeno un coach assegnato
        subquery = text("SELECT cc.cliente_id FROM cliente_coaches cc")
        qry = qry.filter(Cliente.cliente_id.in_(subquery))

    if p.has_psicologo:
        # Clienti che hanno almeno uno psicologo assegnato
        subquery = text("SELECT cp.cliente_id FROM cliente_psicologi cp")
        qry = qry.filter(Cliente.cliente_id.in_(subquery))

    # -------- advanced filters ------
    if p.stato_cliente is not None:
        qry = qry.filter(Cliente.stato_cliente == p.stato_cliente)
    
    if p.programma_attuale:
        term = p.programma_attuale.strip()
        like = f"%{term}%"
        qry = qry.filter(
            or_(
                func.lower(Cliente.programma_attuale).like(func.lower(like)),
                func.lower(Cliente.programma_attuale_dettaglio).like(func.lower(like))
            )
        )
    
    if p.trasformazione_fisica is not None:
        qry = qry.filter(Cliente.trasformazione_fisica == p.trasformazione_fisica)
    
    if p.trasformazione_fisica_condivisa is not None:
        qry = qry.filter(Cliente.trasformazione_fisica_condivisa == p.trasformazione_fisica_condivisa)
    
    if p.check_day is not None:
        qry = qry.filter(Cliente.check_day == p.check_day)
    
    if p.reach_out:
        # reach_out è un GiornoEnum, non serve lower()
        try:
            from corposostenibile.models import GiornoEnum
            # Prova a convertire il valore in GiornoEnum
            giorno_value = GiornoEnum(p.reach_out.lower())
            qry = qry.filter(Cliente.reach_out == giorno_value)
        except (ValueError, AttributeError):
            # Se non è un valore valido di GiornoEnum, ignora il filtro
            pass

    # -------- range -------------
    if p.created_from:
        qry = qry.filter(Cliente.created_at >= p.created_from)
    if p.created_to:
        qry = qry.filter(Cliente.created_at <= p.created_to)
    if p.rate_min is not None:
        qry = qry.filter(cast(Cliente.rate_cliente_sales, Numeric) >= p.rate_min)
    if p.rate_max is not None:
        qry = qry.filter(cast(Cliente.rate_cliente_sales, Numeric) <= p.rate_max)

    # -------- filtri date allenamento -----------
    if p.allenamento_dal_from:
        qry = qry.filter(Cliente.allenamento_dal >= p.allenamento_dal_from)
    if p.allenamento_dal_to:
        qry = qry.filter(Cliente.allenamento_dal <= p.allenamento_dal_to)
    if p.nuovo_allenamento_il_from:
        qry = qry.filter(Cliente.nuovo_allenamento_il >= p.nuovo_allenamento_il_from)
    if p.nuovo_allenamento_il_to:
        qry = qry.filter(Cliente.nuovo_allenamento_il <= p.nuovo_allenamento_il_to)
    
    # -------- filtro scadenze -----------
    if p.expiring_days is not None:
        threshold = date.today() + timedelta(days=p.expiring_days)
        qry = qry.filter(
            Cliente.data_rinnovo.isnot(None),
            Cliente.data_rinnovo <= threshold
        )

    # -------- filtri campi vuoti/non compilati -----------
    if p.missing_check_day:
        qry = qry.filter(Cliente.check_day.is_(None))

    if p.missing_check_saltati:
        qry = qry.filter(Cliente.check_saltati.is_(None))

    if p.missing_reach_out:
        qry = qry.filter(Cliente.reach_out.is_(None))

    # -------- filtri stati servizio non compilati -----------
    if p.missing_stato_nutrizione:
        qry = qry.filter(Cliente.stato_nutrizione.is_(None))

    if p.missing_stato_chat_nutrizione:
        qry = qry.filter(Cliente.stato_cliente_chat_nutrizione.is_(None))

    if p.missing_stato_coach:
        qry = qry.filter(Cliente.stato_coach.is_(None))

    if p.missing_stato_chat_coaching:
        qry = qry.filter(Cliente.stato_cliente_chat_coaching.is_(None))

    if p.missing_stato_psicologia:
        qry = qry.filter(Cliente.stato_psicologia.is_(None))

    if p.missing_stato_chat_psicologia:
        qry = qry.filter(Cliente.stato_cliente_chat_psicologia.is_(None))

    # -------- filtri piani attivi mancanti -----------
    if p.missing_piano_dieta:
        # Clienti che NON hanno un MealPlan attivo
        from corposostenibile.models import MealPlan
        subquery_dieta = db.session.query(MealPlan.cliente_id).filter(
            MealPlan.is_active == True
        ).distinct().subquery()
        qry = qry.filter(~Cliente.cliente_id.in_(subquery_dieta))

    if p.missing_piano_allenamento:
        # Clienti che NON hanno un TrainingPlan attivo
        from corposostenibile.models import TrainingPlan
        subquery_training = db.session.query(TrainingPlan.cliente_id).filter(
            TrainingPlan.is_active == True
        ).distinct().subquery()
        qry = qry.filter(~Cliente.cliente_id.in_(subquery_training))

    # ─────────────────── TAB 1: ANAGRAFICA E OBIETTIVI ─────────────────── #
    # Filtro età (calcolo dinamico da data_di_nascita)
    if p.eta_min is not None or p.eta_max is not None:
        from datetime import date as date_type
        today = date_type.today()
        if p.eta_min is not None:
            # Data di nascita massima (più recente) per avere almeno eta_min anni
            max_birth_date = date_type(today.year - p.eta_min, today.month, today.day)
            qry = qry.filter(Cliente.data_di_nascita <= max_birth_date)
        if p.eta_max is not None:
            # Data di nascita minima (più vecchia) per avere al massimo eta_max anni
            min_birth_date = date_type(today.year - p.eta_max - 1, today.month, today.day)
            qry = qry.filter(Cliente.data_di_nascita >= min_birth_date)
    
    # Filtro genere (multi-selezione)
    if p.genere:
        qry = qry.filter(Cliente.genere.in_(p.genere))
    
    # Filtri testo (origine, professione, paese)
    if p.origine:
        term = p.origine.strip()
        like = f"%{term}%"
        qry = qry.filter(func.lower(Cliente.origine).like(func.lower(like)))
    
    if p.professione:
        term = p.professione.strip()
        like = f"%{term}%"
        qry = qry.filter(func.lower(Cliente.professione).like(func.lower(like)))
    
    if p.paese:
        term = p.paese.strip()
        like = f"%{term}%"
        qry = qry.filter(func.lower(Cliente.paese).like(func.lower(like)))
    
    # Missing anagrafica
    if p.missing_email:
        qry = qry.filter(or_(Cliente.mail.is_(None), Cliente.mail == ""))
    
    if p.missing_telefono:
        qry = qry.filter(or_(Cliente.numero_telefono.is_(None), Cliente.numero_telefono == ""))
    
    if p.missing_storia_cliente:
        qry = qry.filter(or_(Cliente.storia_cliente.is_(None), Cliente.storia_cliente == ""))
    
    if p.missing_problema:
        qry = qry.filter(or_(Cliente.problema.is_(None), Cliente.problema == ""))
    
    if p.missing_paure:
        qry = qry.filter(or_(Cliente.paure.is_(None), Cliente.paure == ""))
    
    if p.missing_conseguenze:
        qry = qry.filter(or_(Cliente.conseguenze.is_(None), Cliente.conseguenze == ""))

    # ─────────────────── TAB 2: PROGRAMMA E STATO ─────────────────── #
    if p.check_saltati:
        # Extract enum values since PostgreSQL expects the actual enum value ("1", "2", etc.)
        # not the Python enum member name ("uno", "due", etc.)
        # We also need to cast to String to prevent SQLAlchemy's enum type processor
        # from converting back to enum names
        from sqlalchemy import String, cast
        check_saltati_values = [e.value if hasattr(e, 'value') else e for e in p.check_saltati]
        qry = qry.filter(cast(Cliente.check_saltati, String).in_(check_saltati_values))
    
    if p.programma_attuale_dettaglio:
        term = p.programma_attuale_dettaglio.strip()
        like = f"%{term}%"
        qry = qry.filter(func.lower(Cliente.programma_attuale_dettaglio).like(func.lower(like)))
    
    if p.data_inizio_abbonamento_from:
        qry = qry.filter(Cliente.data_inizio_abbonamento >= p.data_inizio_abbonamento_from)
    if p.data_inizio_abbonamento_to:
        qry = qry.filter(Cliente.data_inizio_abbonamento <= p.data_inizio_abbonamento_to)
    
    if p.durata_programma_min is not None:
        qry = qry.filter(Cliente.durata_programma_giorni >= p.durata_programma_min)
    if p.durata_programma_max is not None:
        qry = qry.filter(Cliente.durata_programma_giorni <= p.durata_programma_max)
    
    if p.data_rinnovo_from:
        qry = qry.filter(Cliente.data_rinnovo >= p.data_rinnovo_from)
    if p.data_rinnovo_to:
        qry = qry.filter(Cliente.data_rinnovo <= p.data_rinnovo_to)
    
    if p.in_scadenza is not None:
        # in_scadenza è un campo String(20) che può essere "True", "False" o "Interno"
        if p.in_scadenza:
            qry = qry.filter(Cliente.in_scadenza.in_(["True", "Interno"]))
        else:
            qry = qry.filter(or_(Cliente.in_scadenza.is_(None), Cliente.in_scadenza == "False"))
    
    if p.goals_evaluation_date_from:
        qry = qry.filter(Cliente.goals_evaluation_date >= p.goals_evaluation_date_from)
    if p.goals_evaluation_date_to:
        qry = qry.filter(Cliente.goals_evaluation_date <= p.goals_evaluation_date_to)

    # ─────────────────── TAB 3: TEAM ─────────────────── #
    if p.missing_nutrizionista:
        # Nessun nutrizionista assegnato (né FK né many-to-many)
        from sqlalchemy import exists
        from corposostenibile.models import cliente_nutrizionisti
        qry = qry.filter(
            Cliente.nutrizionista_id.is_(None),
            ~exists().where(cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id)
        )
    
    if p.missing_coach:
        from sqlalchemy import exists
        from corposostenibile.models import cliente_coaches
        qry = qry.filter(
            Cliente.coach_id.is_(None),
            ~exists().where(cliente_coaches.c.cliente_id == Cliente.cliente_id)
        )
    
    if p.missing_psicologa:
        from sqlalchemy import exists
        from corposostenibile.models import cliente_psicologi
        qry = qry.filter(
            Cliente.psicologa_id.is_(None),
            ~exists().where(cliente_psicologi.c.cliente_id == Cliente.cliente_id)
        )
    
    if p.missing_health_manager:
        qry = qry.filter(Cliente.health_manager_id.is_(None))
    
    if p.missing_consulente_alimentare:
        from sqlalchemy import exists
        from corposostenibile.models import cliente_consulenti
        qry = qry.filter(
            Cliente.consulente_alimentare_id.is_(None),
            ~exists().where(cliente_consulenti.c.cliente_id == Cliente.cliente_id)
        )

    # ─────────────────── TAB 7: HEALTH MANAGER ─────────────────── #
    if p.marketing_usabile is not None:
        if p.marketing_usabile:
            qry = qry.filter(
                Cliente.cliente_id.in_(
                    db.session.query(ClienteMarketingFlag.cliente_id).filter(
                        ClienteMarketingFlag.flag_type == MarketingFlagTypeEnum.usabile_marketing,
                        ClienteMarketingFlag.checked.is_(True),
                    )
                )
            )
        else:
            qry = qry.filter(
                ~Cliente.cliente_id.in_(
                    db.session.query(ClienteMarketingFlag.cliente_id).filter(
                        ClienteMarketingFlag.flag_type == MarketingFlagTypeEnum.usabile_marketing,
                        ClienteMarketingFlag.checked.is_(True),
                    )
                )
            )

    def _apply_marketing_content_filter(base_query: Query, content_type: MarketingContentTypeEnum, expected: bool) -> Query:
        content_subq = db.session.query(ClienteMarketingContent.cliente_id).filter(
            ClienteMarketingContent.content_type == content_type,
            ClienteMarketingContent.checked.is_(True),
        )
        return (
            base_query.filter(Cliente.cliente_id.in_(content_subq))
            if expected
            else base_query.filter(~Cliente.cliente_id.in_(content_subq))
        )

    if p.marketing_stories is not None:
        qry = _apply_marketing_content_filter(qry, MarketingContentTypeEnum.stories, p.marketing_stories)
    if p.marketing_carosello is not None:
        qry = _apply_marketing_content_filter(qry, MarketingContentTypeEnum.carosello, p.marketing_carosello)
    if p.marketing_videofeedback is not None:
        qry = _apply_marketing_content_filter(qry, MarketingContentTypeEnum.videofeedback, p.marketing_videofeedback)

    # Consenso Social
    if p.consenso_social_richiesto is not None:
        qry = qry.filter(Cliente.consenso_social_richiesto == p.consenso_social_richiesto)
    if p.consenso_social_accettato is not None:
        qry = qry.filter(Cliente.consenso_social_accettato == p.consenso_social_accettato)
    if p.consenso_social_con_documento:
        qry = qry.filter(
            Cliente.consenso_social_documento.isnot(None),
            Cliente.consenso_social_documento != ""
        )
    if p.missing_consenso_social_richiesto:
        qry = qry.filter(Cliente.consenso_social_richiesto.is_(None))
    
    # Recensioni
    if p.recensione_richiesta is not None:
        qry = qry.filter(Cliente.recensione_richiesta == p.recensione_richiesta)
    if p.recensione_accettata is not None:
        qry = qry.filter(Cliente.recensione_accettata == p.recensione_accettata)
    if p.recensione_risposta is not None:
        qry = qry.filter(Cliente.recensione_risposta == p.recensione_risposta)
    if p.recensione_stelle_min is not None:
        qry = qry.filter(Cliente.recensione_stelle >= p.recensione_stelle_min)
    if p.recensione_stelle_max is not None:
        qry = qry.filter(Cliente.recensione_stelle <= p.recensione_stelle_max)
    if p.recensioni_lifetime_count_min is not None:
        qry = qry.filter(Cliente.recensioni_lifetime_count >= p.recensioni_lifetime_count_min)
    if p.recensioni_lifetime_count_max is not None:
        qry = qry.filter(Cliente.recensioni_lifetime_count <= p.recensioni_lifetime_count_max)
    if p.ultima_recensione_trustpilot_data_from:
        qry = qry.filter(Cliente.ultima_recensione_trustpilot_data >= p.ultima_recensione_trustpilot_data_from)
    if p.ultima_recensione_trustpilot_data_to:
        qry = qry.filter(Cliente.ultima_recensione_trustpilot_data <= p.ultima_recensione_trustpilot_data_to)
    if p.missing_recensione_richiesta:
        qry = qry.filter(Cliente.recensione_richiesta.is_(None))
    
    # Videofeedback
    if p.video_feedback_richiesto is not None:
        qry = qry.filter(Cliente.video_feedback_richiesto == p.video_feedback_richiesto)
    if p.video_feedback_svolto is not None:
        qry = qry.filter(Cliente.video_feedback_svolto == p.video_feedback_svolto)
    if p.video_feedback_condiviso is not None:
        qry = qry.filter(Cliente.video_feedback_condiviso == p.video_feedback_condiviso)
    if p.video_feedback_con_file:
        qry = qry.filter(
            Cliente.videofeedback_file.isnot(None),
            Cliente.videofeedback_file != ""
        )
    if p.missing_video_feedback_richiesto:
        qry = qry.filter(Cliente.video_feedback_richiesto.is_(None))
    
    # Sedute Psicologia
    if p.sedute_psicologia_comprate_min is not None:
        qry = qry.filter(Cliente.sedute_psicologia_comprate >= p.sedute_psicologia_comprate_min)
    if p.sedute_psicologia_comprate_max is not None:
        qry = qry.filter(Cliente.sedute_psicologia_comprate <= p.sedute_psicologia_comprate_max)
    if p.sedute_psicologia_svolte_min is not None:
        qry = qry.filter(Cliente.sedute_psicologia_svolte >= p.sedute_psicologia_svolte_min)
    if p.sedute_psicologia_svolte_max is not None:
        qry = qry.filter(Cliente.sedute_psicologia_svolte <= p.sedute_psicologia_svolte_max)
    if p.sedute_psicologia_rimanenti:
        # Comprate - svolte > 0
        qry = qry.filter(
            Cliente.sedute_psicologia_comprate.isnot(None),
            (func.coalesce(Cliente.sedute_psicologia_comprate, 0) - func.coalesce(Cliente.sedute_psicologia_svolte, 0)) > 0
        )
    if p.missing_sedute_psicologia:
        qry = qry.filter(
            or_(
                Cliente.sedute_psicologia_comprate.is_(None),
                Cliente.sedute_psicologia_comprate == 0
            )
        )
    
    # Freeze
    if p.is_frozen is not None:
        qry = qry.filter(Cliente.is_frozen == p.is_frozen)
    if p.freeze_date_from:
        qry = qry.filter(Cliente.freeze_date >= p.freeze_date_from)
    if p.freeze_date_to:
        qry = qry.filter(Cliente.freeze_date <= p.freeze_date_to)
    
    # Onboarding
    if p.onboarding_date_from:
        qry = qry.filter(Cliente.onboarding_date >= p.onboarding_date_from)
    if p.onboarding_date_to:
        qry = qry.filter(Cliente.onboarding_date <= p.onboarding_date_to)
    if p.missing_onboarding_date:
        qry = qry.filter(Cliente.onboarding_date.is_(None))
    
    # Exit Call
    if p.exit_call_richiesta is not None:
        qry = qry.filter(Cliente.exit_call_richiesta == p.exit_call_richiesta)
    if p.exit_call_svolta is not None:
        qry = qry.filter(Cliente.exit_call_svolta == p.exit_call_svolta)
    if p.exit_call_condivisa is not None:
        qry = qry.filter(Cliente.exit_call_condivisa == p.exit_call_condivisa)
    
    # Social & Trasformazione
    if p.no_social is not None:
        qry = qry.filter(Cliente.no_social == p.no_social)
    if p.social_oscurato is not None:
        qry = qry.filter(Cliente.social_oscurato == p.social_oscurato)
    if p.trasformazione:
        qry = qry.filter(Cliente.trasformazione.in_(p.trasformazione))
    if p.proposta_live_training is not None:
        qry = qry.filter(Cliente.proposta_live_training == p.proposta_live_training)
    if p.live_training_bonus_prenotata is not None:
        qry = qry.filter(Cliente.live_training_bonus_prenotata == p.live_training_bonus_prenotata)

    # ─────────────────── TAB 8: NUTRIZIONE ─────────────────── #
    if p.stato_nutrizione:
        qry = qry.filter(Cliente.stato_nutrizione.in_(p.stato_nutrizione))
    if p.stato_chat_nutrizione:
        qry = qry.filter(Cliente.stato_cliente_chat_nutrizione.in_(p.stato_chat_nutrizione))
    if p.call_iniziale_nutrizionista is not None:
        qry = qry.filter(Cliente.call_iniziale_nutrizionista == p.call_iniziale_nutrizionista)
    if p.data_call_iniziale_nutrizionista_from:
        qry = qry.filter(Cliente.data_call_iniziale_nutrizionista >= p.data_call_iniziale_nutrizionista_from)
    if p.data_call_iniziale_nutrizionista_to:
        qry = qry.filter(Cliente.data_call_iniziale_nutrizionista <= p.data_call_iniziale_nutrizionista_to)
    if p.reach_out_nutrizione:
        qry = qry.filter(Cliente.reach_out_nutrizione.in_(p.reach_out_nutrizione))
    if p.dieta_dal_from:
        qry = qry.filter(Cliente.dieta_dal >= p.dieta_dal_from)
    if p.dieta_dal_to:
        qry = qry.filter(Cliente.dieta_dal <= p.dieta_dal_to)
    if p.nuova_dieta_dal_from:
        qry = qry.filter(Cliente.nuova_dieta_dal >= p.nuova_dieta_dal_from)
    if p.nuova_dieta_dal_to:
        qry = qry.filter(Cliente.nuova_dieta_dal <= p.nuova_dieta_dal_to)
    if p.missing_call_iniziale_nutrizionista:
        qry = qry.filter(
            or_(
                Cliente.call_iniziale_nutrizionista.is_(None),
                Cliente.call_iniziale_nutrizionista == False
            )
        )
    if p.missing_reach_out_nutrizione:
        qry = qry.filter(Cliente.reach_out_nutrizione.is_(None))
    
    # Patologie Nutrizionali
    patologie_nutrizionali = [
        ('patologia_ibs', Cliente.patologia_ibs),
        ('patologia_reflusso', Cliente.patologia_reflusso),
        ('patologia_gastrite', Cliente.patologia_gastrite),
        ('patologia_dca', Cliente.patologia_dca),
        ('patologia_insulino_resistenza', Cliente.patologia_insulino_resistenza),
        ('patologia_diabete', Cliente.patologia_diabete),
        ('patologia_dislipidemie', Cliente.patologia_dislipidemie),
        ('patologia_steatosi_epatica', Cliente.patologia_steatosi_epatica),
        ('patologia_ipertensione', Cliente.patologia_ipertensione),
        ('patologia_pcos', Cliente.patologia_pcos),
        ('patologia_endometriosi', Cliente.patologia_endometriosi),
        ('patologia_obesita_sindrome', Cliente.patologia_obesita_sindrome),
        ('patologia_osteoporosi', Cliente.patologia_osteoporosi),
        ('patologia_diverticolite', Cliente.patologia_diverticolite),
        ('patologia_crohn', Cliente.patologia_crohn),
        ('patologia_stitichezza', Cliente.patologia_stitichezza),
        ('patologia_tiroidee', Cliente.patologia_tiroidee),
    ]
    
    for pat_name, pat_field in patologie_nutrizionali:
        pat_value = getattr(p, pat_name, None)
        if pat_value is not None:
            qry = qry.filter(pat_field == pat_value)
    
    if p.con_almeno_una_patologia_nutrizionale:
        conditions = [pat_field == True for _, pat_field in patologie_nutrizionali]
        qry = qry.filter(or_(*conditions))
    
    if p.senza_patologie_nutrizionali:
        # "Nessuna Patologia" = l'utente ha selezionato esplicitamente "nessuna patologia"
        qry = qry.filter(Cliente.nessuna_patologia == True)
    
    if p.patologie_non_indicate_nutri:
        # "Non Indicato" = nessun campo compilato (nessuna patologia specifica E nessuna_patologia = False)
        conditions_false = [pat_field.isnot(True) for _, pat_field in patologie_nutrizionali]
        qry = qry.filter(
            and_(
                Cliente.nessuna_patologia.isnot(True),
                *conditions_false
            )
        )

    # ─────────────────── TAB 9: COACHING ─────────────────── #
    if p.stato_coach:
        qry = qry.filter(Cliente.stato_coach.in_(p.stato_coach))
    if p.stato_chat_coaching:
        qry = qry.filter(Cliente.stato_cliente_chat_coaching.in_(p.stato_chat_coaching))
    if p.call_iniziale_coach is not None:
        qry = qry.filter(Cliente.call_iniziale_coach == p.call_iniziale_coach)
    if p.data_call_iniziale_coach_from:
        qry = qry.filter(Cliente.data_call_iniziale_coach >= p.data_call_iniziale_coach_from)
    if p.data_call_iniziale_coach_to:
        qry = qry.filter(Cliente.data_call_iniziale_coach <= p.data_call_iniziale_coach_to)
    if p.reach_out_coaching:
        qry = qry.filter(Cliente.reach_out_coaching.in_(p.reach_out_coaching))
    if p.luogo_di_allenamento:
        qry = qry.filter(Cliente.luogo_di_allenamento.in_(p.luogo_di_allenamento))
    if p.missing_call_iniziale_coach:
        qry = qry.filter(
            or_(
                Cliente.call_iniziale_coach.is_(None),
                Cliente.call_iniziale_coach == False
            )
        )
    if p.missing_reach_out_coaching:
        qry = qry.filter(Cliente.reach_out_coaching.is_(None))
    if p.missing_luogo_allenamento:
        qry = qry.filter(Cliente.luogo_di_allenamento.is_(None))

    # ─────────────────── TAB 10: PSICOLOGIA ─────────────────── #
    if p.stato_psicologia:
        qry = qry.filter(Cliente.stato_psicologia.in_(p.stato_psicologia))
    if p.stato_chat_psicologia:
        qry = qry.filter(Cliente.stato_cliente_chat_psicologia.in_(p.stato_chat_psicologia))
    if p.call_iniziale_psicologa is not None:
        qry = qry.filter(Cliente.call_iniziale_psicologa == p.call_iniziale_psicologa)
    if p.data_call_iniziale_psicologia_from:
        qry = qry.filter(Cliente.data_call_iniziale_psicologia >= p.data_call_iniziale_psicologia_from)
    if p.data_call_iniziale_psicologia_to:
        qry = qry.filter(Cliente.data_call_iniziale_psicologia <= p.data_call_iniziale_psicologia_to)
    if p.reach_out_psicologia:
        qry = qry.filter(Cliente.reach_out_psicologia.in_(p.reach_out_psicologia))
    if p.missing_call_iniziale_psicologa:
        qry = qry.filter(
            or_(
                Cliente.call_iniziale_psicologa.is_(None),
                Cliente.call_iniziale_psicologa == False
            )
        )
    if p.missing_reach_out_psicologia:
        qry = qry.filter(Cliente.reach_out_psicologia.is_(None))
    
    # Patologie Psicologiche
    patologie_psicologiche = [
        ('patologia_psico_dca', Cliente.patologia_psico_dca),
        ('patologia_psico_obesita_psicoemotiva', Cliente.patologia_psico_obesita_psicoemotiva),
        ('patologia_psico_ansia_umore_cibo', Cliente.patologia_psico_ansia_umore_cibo),
        ('patologia_psico_comportamenti_disfunzionali', Cliente.patologia_psico_comportamenti_disfunzionali),
        ('patologia_psico_immagine_corporea', Cliente.patologia_psico_immagine_corporea),
        ('patologia_psico_psicosomatiche', Cliente.patologia_psico_psicosomatiche),
        ('patologia_psico_relazionali_altro', Cliente.patologia_psico_relazionali_altro),
    ]
    
    for pat_name, pat_field in patologie_psicologiche:
        pat_value = getattr(p, pat_name, None)
        if pat_value is not None:
            qry = qry.filter(pat_field == pat_value)
    
    if p.con_almeno_una_patologia_psicologica:
        conditions = [pat_field == True for _, pat_field in patologie_psicologiche]
        qry = qry.filter(or_(*conditions))
    
    if p.senza_patologie_psicologiche:
        # "Nessuna Patologia Psicologica" = l'utente ha selezionato esplicitamente "nessuna patologia psico"
        qry = qry.filter(Cliente.nessuna_patologia_psico == True)
    
    if p.patologie_non_indicate_psico:
        # "Non Indicato" = nessun campo compilato (nessuna patologia specifica E nessuna_patologia_psico = False)
        conditions_false = [pat_field.isnot(True) for _, pat_field in patologie_psicologiche]
        qry = qry.filter(
            and_(
                Cliente.nessuna_patologia_psico.isnot(True),
                *conditions_false
            )
        )

    # ─────────────────── TAB 12: PAGAMENTI ─────────────────── #
    if p.modalita_pagamento:
        qry = qry.filter(Cliente.modalita_pagamento.in_(p.modalita_pagamento))
    if p.deposito_iniziale_min is not None:
        qry = qry.filter(Cliente.deposito_iniziale >= p.deposito_iniziale_min)
    if p.deposito_iniziale_max is not None:
        qry = qry.filter(Cliente.deposito_iniziale <= p.deposito_iniziale_max)

    # -------- sorting -----------
    field, direction = _parse_sort(p.sort)
    column = _sort_column_map().get(field, Cliente.created_at)
    qry = qry.order_by(column.desc() if direction == "desc" else column.asc())

    return qry


# ────────────────────────────────────────────────────────────────────────────
# Helpers ordinamento
# ────────────────────────────────────────────────────────────────────────────
def _parse_sort(raw: str) -> Tuple[str, str]:
    try:
        col, direction = raw.split(":", 1)
        if direction.lower() not in {"asc", "desc"}:
            raise ValueError
    except ValueError:
        return "created_at", "desc"
    return col, direction.lower()


def _sort_column_map():
    return {
        "created_at":        Cliente.created_at,
        "nome":              Cliente.nome_cognome,
        "rate":              Cliente.rate_cliente_sales,
        "data_rinnovo":      Cliente.data_rinnovo,  # Sostituisce giorni_rimanenti
    }

