"""
customers.permissions
=====================

• Enum `CustomerPerm` – tutti i permessi per il dominio *Clienti*  
• Helper `has_permission()` + decoratore `permission_required`  
• Mappatura di default *ruolo → permessi*

NB  
--
✓ Il ruolo **finance** mantiene i permessi “read-only” sui clienti  
✓ I permessi per la contabilità (*accounting:view / export*) sono
  definiti **nel modulo `accounting.permissions`** così da tenere separati
  i due domini ACL.
"""
from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import Any, Callable, Iterable, Mapping, MutableMapping, Set, TypeVar, Union, cast

from flask import abort, current_app, g
from flask_login import current_user  # type: ignore

# Flask-Principal (opzionale – non obbliga la dipendenza)
try:
    from flask_principal import Identity, Need, Permission, RoleNeed, identity_loaded  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    Identity = Need = Permission = RoleNeed = identity_loaded = None  # type: ignore


__all__ = [
    "CustomerPerm",
    "has_permission",
    "permission_required",
    "register_acl",
]

# ────────────────────────────────────────────────────────────────────────
#  Enum permessi (CLIENTI)
# ────────────────────────────────────────────────────────────────────────
class CustomerPerm(str, Enum):
    # Lettura / export
    VIEW = "customers:view"
    VIEW_HISTORY = "customers:view-history"
    EXPORT = "customers:export"

    # CRUD anagrafica
    CREATE = "customers:create"
    EDIT = "customers:edit"
    DELETE = "customers:delete"
    IMPORT = "customers:import"

    # Operazioni estese
    ADD_CONTRACT = "customers:add-contract"
    ADD_PAYMENT = "customers:add-payment"
    ADD_RENEWAL = "customers:add-renewal"

    # Super-user di dominio
    MANAGE = "customers:manage"

    # python → str
    def __str__(self) -> str:  # pragma: no cover
        return self.value


_ALL_PERMS: Set[CustomerPerm] = set(CustomerPerm)  # per admin / test

# ────────────────────────────────────────────────────────────────────────
#  Mapping default (ruolo → permessi CLIENTI)
# ────────────────────────────────────────────────────────────────────────
# MODIFICATO: Tutti i ruoli hanno accesso completo al modulo Clienti
_DEFAULT_ROLE_PERMS: dict[str, Set[CustomerPerm]] = {
    "admin": _ALL_PERMS,
    "sales": _ALL_PERMS,
    "setter": _ALL_PERMS,
    "nutrizionista": _ALL_PERMS,
    "coach": _ALL_PERMS,
    "psicologa": _ALL_PERMS,
    "finance": _ALL_PERMS,
    # Qualsiasi altro ruolo avrà comunque accesso completo grazie alla modifica in has_permission()
}

# ────────────────────────────────────────────────────────────────────────
#  Helper: merge con eventuale override app-config
# ────────────────────────────────────────────────────────────────────────
def _role_permissions() -> Mapping[str, Set[CustomerPerm]]:
    """
    Merge dei permessi di default con eventuali override tramite
    ``app.config["CUSTOMERS_ROLE_PERMISSIONS"]`` (lista di stringhe).
    """
    custom: Mapping[str, Iterable[str]] | None = current_app.config.get(  # type: ignore[attr-defined]
        "CUSTOMERS_ROLE_PERMISSIONS"
    )
    if not custom:
        return _DEFAULT_ROLE_PERMS

    merged: MutableMapping[str, Set[CustomerPerm]] = {
        role: set(perms) for role, perms in _DEFAULT_ROLE_PERMS.items()
    }
    for role, perm_list in custom.items():
        merged.setdefault(role, set()).update(CustomerPerm(p) for p in perm_list)
    return merged


def _user_roles(user: Any) -> list[str]:
    """
    Estrae la/le stringhe di ruolo dall’oggetto utente.

    Supporta:
        • `.roles` iterable (con o senza attr .name)  
        • `.role`  singolo  
    """
    if not user or getattr(user, "is_anonymous", False):
        return []
    if hasattr(user, "roles"):
        roles = user.roles
        return [getattr(r, "name", str(r)) for r in roles] if not isinstance(roles, str) else [roles]
    if hasattr(user, "role"):
        return [str(user.role)]
    return []


# ────────────────────────────────────────────────────────────────────────
#  API pubblica
# ────────────────────────────────────────────────────────────────────────
def has_permission(
    user: Any,
    perm: Union[CustomerPerm, str],
    obj: object | None = None,
) -> bool:
    """
    True se *user* possiede *perm*.

    MODIFICATO: Tutti gli utenti autenticati hanno accesso completo al modulo Clienti.
    """
    # Se l'utente non è autenticato, nega l'accesso
    if user is None or getattr(user, "is_anonymous", False):
        return False

    # ACCESSO COMPLETO: Tutti gli utenti autenticati hanno tutti i permessi sul modulo Clienti
    if getattr(user, "is_authenticated", False):
        return True

    # Codice originale mantenuto ma non verrà mai raggiunto
    perm = CustomerPerm(perm) if not isinstance(perm, CustomerPerm) else perm

    # super-user globale
    if getattr(user, "is_admin", False):
        return True

    role_perms = _role_permissions()
    for role in _user_roles(user):
        r_perms = role_perms.get(role, set())
        if perm in r_perms or CustomerPerm.MANAGE in r_perms:
            if role == "sales" and obj is not None:
                from corposostenibile.models import Cliente  # avoid circular
                return isinstance(obj, Cliente) and obj.personal_consultant_id == getattr(
                    user, "sales_person_id", None
                )
            return True
    return False


F = TypeVar("F", bound=Callable[..., Any])


def permission_required(perm: Union[CustomerPerm, str]):  # noqa: D401
    """Decoratore Flask view: 403 se l’utente non possiede il permesso."""
    perm = CustomerPerm(perm) if not isinstance(perm, CustomerPerm) else perm

    def decorator(func: F) -> F:  # type: ignore[misc]
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any):  # type: ignore[override]
            obj = kwargs.get("cliente") or g.get("cliente")
            if not has_permission(current_user, perm, obj):
                abort(403)
            return func(*args, **kwargs)

        return cast(F, wrapper)

    return decorator


# ────────────────────────────────────────────────────────────────────────
#  Bridge verso un’ACL esterna (facoltativo)
# ────────────────────────────────────────────────────────────────────────
def register_acl(acl_ext) -> None:  # pragma: no cover
    """Inserisce tutti i permessi definiti in un’ACL esterna."""
    for role, perms in _role_permissions().items():
        for p in perms:
            acl_ext.allow(role, p.value)


# ────────────────────────────────────────────────────────────────────────
#  Flask-Principal integration (opzionale)
# ────────────────────────────────────────────────────────────────────────
if Identity and identity_loaded:  # pragma: no cover

    @identity_loaded.connect
    def _on_identity_loaded(sender, identity: Identity):  # type: ignore[override]
        user = current_user
        if getattr(user, "is_anonymous", True):
            return
        for role in _user_roles(user):
            identity.provides.add(RoleNeed(role))  # type: ignore[arg-type]
            for p in _role_permissions().get(role, set()):
                identity.provides.add(Need("perm", p.value))  # type: ignore[arg-type]
