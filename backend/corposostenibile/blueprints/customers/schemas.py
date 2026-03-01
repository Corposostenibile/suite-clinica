"""
customers.schemas
=================

Serializzazione ↔︎ validazione (Marshmallow) per il pacchetto *customers*.

• Converte gli ENUM Postgres nei loro valori stringa tramite :class:`EnumField`.
• Converte tutte le colonne NUMERIC/Decimal in *float* sul dump (MoneyField).
• Restituisce chiavi camelCase per i meta-field (createdAt, updatedAt).
• Copertura 100 % delle colonne/relazioni di `models.Cliente`.
"""

from __future__ import annotations

import decimal
from typing import Any, Dict, Mapping, Type, Union

from marshmallow import EXCLUDE, ValidationError, fields, post_dump, pre_load, validates
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, SQLAlchemySchema, auto_field

from corposostenibile.extensions import ma
from corposostenibile.models import (  # pylint: disable=too-many-imports
    Allegato,
    CartellaClinica,
    Cliente,
    ClienteVersion,
    NutrizionistaEnum,
    CoachEnum,
    PsicologaEnum,
    PaymentTransaction,
    SalesPerson,
    SubscriptionContract,
    SubscriptionRenewal,
    # ENUM per singola colonna
    CatEnum,
    CheckSaltatiEnum,
    FiguraRifEnum,
    GenereEnum,
    GiornoEnum,
    LuogoAllenEnum,
    PagamentoEnum,
    StatoClienteEnum,
    TeamEnum,
    TipologiaClienteEnum,
    TransactionTypeEnum,
    TrasformazioneEnum,
)

__all__ = [
    "EnumField",
    "MoneyField",
    "SalesPersonBriefSchema",
    "UserBriefSchema",
    "AllegatoSchema",
    "CartellaClinicaSchema",
    "PaymentTransactionSchema",
    "SubscriptionRenewalSchema",
    "SubscriptionContractSchema",
    "ClienteSchema",
    "ClienteVersionSchema",
]

# --------------------------------------------------------------------------- #
#  Field helpers                                                              #
# --------------------------------------------------------------------------- #


class EnumField(fields.Field):
    """(De)serializza un :class:`enum.Enum` usando il suo valore stringa."""

    def __init__(self, enum: Type, **kwargs):
        super().__init__(**kwargs)
        self.enum = enum

    @staticmethod
    def _normalize_stato_cliente_value(value: Any) -> Any:
        """Normalizza valori legacy/non ufficiali per gli stati cliente."""
        mapping = {
            "cliente": "attivo",
            "ex_cliente": "stop",
            "acconto": "stop",
            "ghosting": "ghost",
            "insoluto": "stop",
            "freeze": "pausa",
        }
        return mapping.get(value, value)

    @staticmethod
    def _normalize_genere_value(value: Any) -> Any:
        """Normalizza valori legacy per il genere."""
        if value is None:
            return value
        v = str(value).strip().lower()
        mapping = {
            "m": "uomo",
            "male": "uomo",
            "uomo": "uomo",
            "f": "donna",
            "female": "donna",
            "donna": "donna",
        }
        return mapping.get(v, value)

    # ----- dump ------------------------------------------------------------ #
    def _serialize(self, value, attr, obj, **kwargs):  # noqa: ANN001
        if value is None:
            return None
        # Handle both enum objects and string values
        raw = value.value if hasattr(value, "value") else str(value)
        if self.enum.__name__ == "StatoClienteEnum":
            raw = self._normalize_stato_cliente_value(raw)
        elif self.enum.__name__ == "GenereEnum":
            raw = self._normalize_genere_value(raw)
        return raw

    # ----- load ------------------------------------------------------------ #
    def _deserialize(self, value, attr, data, **kwargs):  # noqa: ANN001
        if value is None:
            return None
        
        original_value = value
        
        # Mappatura per vecchi valori StatoClienteEnum
        if self.enum.__name__ == 'StatoClienteEnum':
            value = self._normalize_stato_cliente_value(value)
        elif self.enum.__name__ == "GenereEnum":
            value = self._normalize_genere_value(value)
            
            # Log per debug
            import logging
            logger = logging.getLogger(__name__)
            if original_value != value:
                logger.info(f"Mappato valore {self.enum.__name__}: '{original_value}' -> '{value}'")
        
        try:
            return self.enum(value)
        except ValueError as exc:  # pragma: no cover
            # Log dettagliato dell'errore
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Errore deserializzazione {self.enum.__name__}: valore '{value}' (originale: '{original_value}') non valido. Valori possibili: {[e.value for e in self.enum]}")
            
            # Genera un messaggio di errore più specifico
            valid_values = [e.value for e in self.enum]
            raise ValidationError(
                f"'{original_value}' non è un valore valido per {self.enum.__name__}. "
                f"Valori accettati: {valid_values}"
            ) from exc


class MoneyField(fields.Field):
    """NUMERIC/Decimal ←→ float (dump)  |  float/str ←→ Decimal (load)."""

    def _serialize(self, value, attr, obj, **kwargs):  # noqa: ANN001
        return float(value) if value is not None else None

    def _deserialize(self, value, attr, data, **kwargs):  # noqa: ANN001
        if value in (None, ""):
            return None
        try:
            return decimal.Decimal(str(value))
        except decimal.InvalidOperation as exc:  # pragma: no cover
            raise ValidationError("Numero non valido") from exc


# --------------------------------------------------------------------------- #
#  Schemi *brief* / nested                                                    #
# --------------------------------------------------------------------------- #


class SalesPersonBriefSchema(SQLAlchemySchema):
    """Estratto minimale di SalesPerson (solo per annidamento "read-only")."""

    class Meta:
        model = SalesPerson
        load_instance = False
        ordered = True

    sales_person_id = auto_field(dump_only=True)
    full_name = auto_field(dump_only=True)


class UserBriefSchema(ma.Schema):
    """Estratto minimale di User per professionisti (dump-only)."""

    id = fields.Integer(dump_only=True)
    email = fields.String(dump_only=True)
    full_name = fields.String(dump_only=True)
    avatar_path = fields.String(dump_only=True)
    avatar_url = fields.String(dump_only=True)


class AllegatoSchema(SQLAlchemySchema):
    """Allegato (read-only)."""

    class Meta:
        model = Allegato
        load_instance = False
        ordered = True

    id = auto_field()
    file_path = auto_field()
    file_type = auto_field()
    note = auto_field()
    upload_date = auto_field()


class CartellaClinicaSchema(SQLAlchemySchema):
    """Cartella clinica + allegati (read-only)."""

    class Meta:
        model = CartellaClinica
        load_instance = False
        ordered = True

    id = auto_field()
    nome = auto_field()
    note = auto_field()
    allegati = fields.Nested(AllegatoSchema, many=True, dump_only=True)


# --------------------------------------------------------------------------- #
#  Schemi pagamenti / abbonamenti                                             #
# --------------------------------------------------------------------------- #


class PaymentTransactionSchema(SQLAlchemyAutoSchema):
    """Pagamento – serializzazione completa (read-only)."""

    class Meta:
        model = PaymentTransaction
        include_fk = True
        load_instance = False
        ordered = True

    payment_date = auto_field()
    amount = MoneyField()
    payment_method = EnumField(PagamentoEnum)
    transaction_type = EnumField(TransactionTypeEnum)
    refund_amount = MoneyField()
    commission_split = auto_field()
    note = auto_field()


class SubscriptionRenewalSchema(SQLAlchemyAutoSchema):
    """Rinnovo abbonamento (read-only)."""

    class Meta:
        model = SubscriptionRenewal
        include_fk = True
        load_instance = False
        ordered = True

    renewal_payment_date = auto_field()
    renewal_amount = MoneyField()
    renewal_duration_days = auto_field()
    renewal_responsible = auto_field()
    payment_method = EnumField(PagamentoEnum)
    note = auto_field()


class SubscriptionContractSchema(SQLAlchemyAutoSchema):
    """Contratto – include pagamenti + rinnovi (nested)."""

    class Meta:
        model = SubscriptionContract
        include_fk = True
        load_instance = False
        ordered = True

    sale_date = auto_field()
    start_date = auto_field()
    end_date = auto_field()
    duration_days = auto_field()
    initial_deposit = MoneyField()
    service_type = auto_field()
    team_vendita = auto_field()
    plusvalenze = MoneyField()
    sedute_psicologia = auto_field()
    rate_cliente_sales = MoneyField()

    payments = fields.Nested(PaymentTransactionSchema, many=True, dump_only=True)
    renewals = fields.Nested(SubscriptionRenewalSchema, many=True, dump_only=True)


# --------------------------------------------------------------------------- #
#  Schema principale Cliente                                                  #
# --------------------------------------------------------------------------- #


class ClienteSchema(SQLAlchemyAutoSchema):
    """
    Serializza **tutte** le colonne di :class:`models.Cliente`
    più le relazioni primarie (read-only).

    Dump-only *nested*:
        • personal_consultant (estratto SalesPerson)
        • subscriptions       (contratti + pagamenti + rinnovi)
        • cartelle            (cartelle cliniche + allegati)
        • meetings            (Google Meet associati)
    """

    # ───────────────────────── META ────────────────────────── #
    class Meta:
        model = Cliente
        include_fk = True
        load_instance = False
        ordered = True
        unknown = EXCLUDE
        exclude = (
            "search_vector",          # FTS interno - non serve nel frontend
        )

    # ────────────────────── ENUM fields ────────────────────── #
    stato_cliente              = EnumField(StatoClienteEnum)
    stato_cliente_chat         = EnumField(StatoClienteEnum)
    stato_cliente_sedute_psico = EnumField(StatoClienteEnum)  # Compatibilità vecchio nome
    
    # Nuovi stati servizi
    stato_psicologia           = EnumField(StatoClienteEnum)
    stato_nutrizione           = EnumField(StatoClienteEnum)
    stato_coach                = EnumField(StatoClienteEnum)
    
    # Date cambio stato (read-only)
    stato_cliente_data         = fields.DateTime(dump_only=True)
    stato_psicologia_data      = fields.DateTime(dump_only=True)
    stato_nutrizione_data      = fields.DateTime(dump_only=True)
    stato_coach_data           = fields.DateTime(dump_only=True)

    tipologia_cliente     = EnumField(TipologiaClienteEnum)
    categoria             = EnumField(CatEnum)
    genere                = EnumField(GenereEnum)
    di_team               = EnumField(TeamEnum)
    check_day             = EnumField(GiornoEnum)
    check_saltati         = EnumField(CheckSaltatiEnum)
    luogo_di_allenamento  = EnumField(LuogoAllenEnum)
    figura_di_riferimento = EnumField(FiguraRifEnum)
    trasformazione        = EnumField(TrasformazioneEnum)
    modalita_pagamento    = EnumField(PagamentoEnum)

    # ───────────── Staff fields (ora stringhe singole) ───────────── #
    nutrizionista = fields.String()
    coach         = fields.String()
    psicologa     = fields.String()

    # ───────────── MONEY / NUMERIC fields ───────────── #
    ltv               = MoneyField()
    ltv_90_gg         = MoneyField()
    ltgp              = MoneyField()
    ltgp_90_gg        = MoneyField()
    plusvalenze       = MoneyField()
    deposito_iniziale = MoneyField()
    importo_rinnovo   = MoneyField()

    comm_pagamento   = MoneyField()
    comm_sales       = MoneyField()
    comm_setter      = MoneyField()
    comm_coach       = MoneyField()
    comm_nutriz      = MoneyField()
    comm_psic        = MoneyField()
    comm_influencer  = MoneyField()
    variabile_bonus_cn = MoneyField()
    costi_extra        = MoneyField()

    # ──────────────── RELAZIONI annidate (dump-only) ──────────────── #
    personal_consultant = fields.Nested(SalesPersonBriefSchema, dump_only=True)
    health_manager_user = fields.Nested(UserBriefSchema, dump_only=True)
    subscriptions       = fields.Nested(SubscriptionContractSchema, many=True, dump_only=True)
    cartelle            = fields.Nested(CartellaClinicaSchema,   many=True, dump_only=True)

    # ──────────────── PROFESSIONISTI MULTIPLI (dump-only) ──────────────── #
    nutrizionisti_multipli = fields.Nested(UserBriefSchema, many=True, dump_only=True)
    coaches_multipli       = fields.Nested(UserBriefSchema, many=True, dump_only=True)
    psicologi_multipli     = fields.Nested(UserBriefSchema, many=True, dump_only=True)
    consulenti_multipli    = fields.Nested(UserBriefSchema, many=True, dump_only=True)

    # ───────────────────── VALIDAZIONE singoli campi ───────────────────── #
    @validates("mail")
    def _validate_email(self, value: str):  # noqa: D401
        if value and "@" not in value:
            raise ValidationError("Email non valida")

    # ───────────────────── POST-DUMP: meta camelCase ───────────────────── #
    @post_dump(pass_original=True)
    def _camelcase_meta(self, data: Dict[str, Any], original, **kwargs):  # noqa: ANN001
        data["createdAt"] = data.pop("created_at", None)
        data["updatedAt"] = data.pop("updated_at", None)
        return data

    # ───────────────────── PRE-LOAD: strip readonly ────────────────────── #
    @pre_load
    def _strip_readonly(self, data: Mapping[str, Any], **kwargs):  # noqa: ANN001
        readonly = {
            "cliente_id",
            "created_at",
            "updated_at",
            "createdAt",
            "updatedAt",
        }
        return {k: v for k, v in data.items() if k not in readonly}


# --------------------------------------------------------------------------- #
#  Schema versione Cliente (history)                                          #
# --------------------------------------------------------------------------- #


class ClienteVersionSchema(SQLAlchemyAutoSchema):
    """
    Serializza le revisioni di Cliente (SQLAlchemy-Continuum).

    Extra-field «changes» = dict { campo: [before, after] }
    """

    class Meta:
        model = ClienteVersion
        load_instance = False
        ordered = True
        include_relationships = False
        exclude = ("search_vector",)

    # ---- METADATI TRANSAZIONE -------------------------------------------- #
    transaction_id = auto_field()
    issued_at = fields.DateTime(attribute="transaction.issued_at", dump_only=True)
    actor_id = fields.Integer(attribute="transaction.actor_id", dump_only=True)
    operation_type = fields.String(dump_only=True)

    # ---- DIFF ------------------------------------------------------------- #
    changes = fields.Method("get_changes", dump_only=True)

    def get_changes(self, obj: ClienteVersion) -> Dict[str, Union[list[Any], Any]]:
        """Converte il changeset in liste JSON-friendly per output JSON."""
        raw = getattr(obj, "changeset", None) or getattr(obj, "diff", {})
        return {field: list(pair) for field, pair in raw.items()} if raw else {}
