#!/usr/bin/env python3
"""Valida la logica capienza sui dati reali del DB locale/VPS."""

from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy import and_, or_, select

from corposostenibile import create_app
from corposostenibile.blueprints.team.api import (
    _calculate_capacity_metrics,
    _get_assigned_clients_by_type,
    _get_assigned_clients_count_map_active_by_role,
    _get_capacity_role_type,
    _get_capacity_weights_by_role,
    _get_hm_split_counts,
)
from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente,
    ProfessionistCapacity,
    StatoClienteEnum,
    TeamTypeEnum,
    User,
    UserRoleEnum,
    UserSpecialtyEnum,
    cliente_coaches,
    cliente_consulenti,
    cliente_nutrizionisti,
    cliente_psicologi,
)


SUPPORTED_TYPES = {"a", "b", "c", "secondario"}


def _clinical_professionals() -> list[User]:
    clinical_specialties = [
        UserSpecialtyEnum.nutrizione,
        UserSpecialtyEnum.nutrizionista,
        UserSpecialtyEnum.coach,
        UserSpecialtyEnum.psicologia,
        UserSpecialtyEnum.psicologo,
        UserSpecialtyEnum.medico,
    ]
    return (
        User.query.filter(
            User.is_active == True,
            or_(
                and_(
                    User.role == UserRoleEnum.professionista,
                    User.specialty.in_(clinical_specialties),
                ),
                and_(
                    User.role == UserRoleEnum.team_leader,
                    User.specialty.in_(clinical_specialties),
                ),
                User.role == UserRoleEnum.health_manager,
            ),
        )
        .order_by(User.first_name, User.last_name)
        .all()
    )


def _empty_result():
    return {
        "assigned": defaultdict(set),
        "typed": defaultdict(lambda: defaultdict(set)),
        "missing_typed": defaultdict(set),
    }


def _collect_direct_capacity_data(user_ids: list[int]) -> dict[str, dict]:
    result = _empty_result()

    def add_rows(rows, role_type: str) -> None:
        for user_id, cliente_id, tipo in rows:
            key = (int(user_id), role_type)
            cliente_id = int(cliente_id)
            result["assigned"][key].add(cliente_id)
            tipo_val = tipo.value if hasattr(tipo, "value") else tipo
            if tipo_val in SUPPORTED_TYPES:
                result["typed"][key][str(tipo_val)].add(cliente_id)
            else:
                result["missing_typed"][key].add(cliente_id)

    nutrizione_rows = db.session.execute(
        select(
            Cliente.nutrizionista_id,
            Cliente.cliente_id,
            Cliente.tipologia_supporto_nutrizione,
        ).where(
            Cliente.nutrizionista_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(nutrizione_rows, "nutrizionista")

    nutrizione_cons_rows = db.session.execute(
        select(
            Cliente.consulente_alimentare_id,
            Cliente.cliente_id,
            Cliente.tipologia_supporto_nutrizione,
        ).where(
            Cliente.consulente_alimentare_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(nutrizione_cons_rows, "nutrizionista")

    nutrizione_m2m_rows = db.session.execute(
        select(
            cliente_nutrizionisti.c.user_id,
            cliente_nutrizionisti.c.cliente_id,
            Cliente.tipologia_supporto_nutrizione,
        )
        .select_from(
            cliente_nutrizionisti.join(
                Cliente, cliente_nutrizionisti.c.cliente_id == Cliente.cliente_id
            )
        )
        .where(
            cliente_nutrizionisti.c.user_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(nutrizione_m2m_rows, "nutrizionista")

    nutrizione_cons_m2m_rows = db.session.execute(
        select(
            cliente_consulenti.c.user_id,
            cliente_consulenti.c.cliente_id,
            Cliente.tipologia_supporto_nutrizione,
        )
        .select_from(
            cliente_consulenti.join(
                Cliente, cliente_consulenti.c.cliente_id == Cliente.cliente_id
            )
        )
        .where(
            cliente_consulenti.c.user_id.in_(user_ids),
            Cliente.stato_nutrizione == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(nutrizione_cons_m2m_rows, "nutrizionista")

    coach_rows = db.session.execute(
        select(
            Cliente.coach_id,
            Cliente.cliente_id,
            Cliente.tipologia_supporto_coach,
        ).where(
            Cliente.coach_id.in_(user_ids),
            Cliente.stato_coach == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(coach_rows, "coach")

    coach_m2m_rows = db.session.execute(
        select(
            cliente_coaches.c.user_id,
            cliente_coaches.c.cliente_id,
            Cliente.tipologia_supporto_coach,
        )
        .select_from(
            cliente_coaches.join(Cliente, cliente_coaches.c.cliente_id == Cliente.cliente_id)
        )
        .where(
            cliente_coaches.c.user_id.in_(user_ids),
            Cliente.stato_coach == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(coach_m2m_rows, "coach")

    psico_rows = db.session.execute(
        select(
            Cliente.psicologa_id,
            Cliente.cliente_id,
            Cliente.tipologia_cliente,
        ).where(
            Cliente.psicologa_id.in_(user_ids),
            Cliente.stato_psicologia == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(psico_rows, "psicologa")

    psico_m2m_rows = db.session.execute(
        select(
            cliente_psicologi.c.user_id,
            cliente_psicologi.c.cliente_id,
            Cliente.tipologia_cliente,
        )
        .select_from(
            cliente_psicologi.join(
                Cliente, cliente_psicologi.c.cliente_id == Cliente.cliente_id
            )
        )
        .where(
            cliente_psicologi.c.user_id.in_(user_ids),
            Cliente.stato_psicologia == StatoClienteEnum.attivo,
        )
    ).all()
    add_rows(psico_m2m_rows, "psicologa")

    hm_rows = db.session.execute(
        select(
            Cliente.health_manager_id,
            Cliente.cliente_id,
            Cliente.tipologia_cliente,
        ).where(
            Cliente.health_manager_id.in_(user_ids),
            or_(
                Cliente.stato_cliente == StatoClienteEnum.attivo,
                Cliente.service_status == "pending_assignment",
            ),
        )
    ).all()
    add_rows(hm_rows, "health_manager")

    return result


def main() -> int:
    app = create_app()

    with app.app_context():
        professionals = _clinical_professionals()
        user_ids = [u.id for u in professionals]
        role_by_user = {u.id: _get_capacity_role_type(u) for u in professionals}
        name_by_user = {u.id: u.full_name for u in professionals}

        helper_assigned = _get_assigned_clients_count_map_active_by_role(user_ids)
        helper_types = _get_assigned_clients_by_type(user_ids)
        helper_weights = _get_capacity_weights_by_role()
        helper_hm_split = _get_hm_split_counts(
            [u.id for u in professionals if role_by_user.get(u.id) == "health_manager"]
        )
        direct = _collect_direct_capacity_data(user_ids)

        capacities = ProfessionistCapacity.query.filter(
            ProfessionistCapacity.user_id.in_(user_ids)
        ).all()
        capacity_by_pair = {(c.user_id, c.role_type): c.max_clients for c in capacities}

        mismatch_rows: list[dict[str, object]] = []
        incomplete_rows: list[dict[str, object]] = []
        role_summary: dict[str, dict[str, int]] = defaultdict(
            lambda: {
                "professionals": 0,
                "assigned_clients": 0,
                "typed_clients": 0,
                "missing_typed_clients": 0,
                "helper_mismatches": 0,
            }
        )

        for user in professionals:
            role_type = role_by_user.get(user.id)
            if not role_type:
                continue

            key = (user.id, role_type)
            helper_assigned_count = helper_assigned.get(key, 0)
            direct_assigned_count = len(direct["assigned"].get(key, set()))
            helper_type_counts = helper_types.get(key, {})
            direct_type_counts = {
                tipo: len(ids)
                for tipo, ids in direct["typed"].get(key, {}).items()
            }
            missing_typed_count = len(direct["missing_typed"].get(key, set()))
            max_clients = int(capacity_by_pair.get(key, 30) or 0)
            helper_metrics = _calculate_capacity_metrics(
                role_type=role_type,
                assigned_clients=helper_assigned_count,
                contractual_capacity=max_clients,
                type_counts=helper_type_counts,
                weights_by_role=helper_weights,
            )
            direct_metrics = _calculate_capacity_metrics(
                role_type=role_type,
                assigned_clients=direct_assigned_count,
                contractual_capacity=max_clients,
                type_counts=direct_type_counts,
                weights_by_role=helper_weights,
            )

            role_summary[role_type]["professionals"] += 1
            role_summary[role_type]["assigned_clients"] += direct_assigned_count
            role_summary[role_type]["typed_clients"] += sum(direct_type_counts.values())
            role_summary[role_type]["missing_typed_clients"] += missing_typed_count

            mismatch = False
            reasons: list[str] = []
            if helper_assigned_count != direct_assigned_count:
                mismatch = True
                reasons.append(
                    f"assigned_count helper={helper_assigned_count} direct={direct_assigned_count}"
                )
            if role_type != "psicologa":
                for tipo in sorted(SUPPORTED_TYPES):
                    if int(helper_type_counts.get(tipo, 0) or 0) != int(direct_type_counts.get(tipo, 0) or 0):
                        mismatch = True
                        reasons.append(
                            f"type_{tipo} helper={helper_type_counts.get(tipo, 0)} direct={direct_type_counts.get(tipo, 0)}"
                        )
            if helper_metrics["capienza_ponderata"] != direct_metrics["capienza_ponderata"]:
                mismatch = True
                reasons.append(
                    f"ponderata helper={helper_metrics['capienza_ponderata']} direct={direct_metrics['capienza_ponderata']}"
                )
            if helper_metrics["percentuale_capienza"] != direct_metrics["percentuale_capienza"]:
                mismatch = True
                reasons.append(
                    f"percentuale helper={helper_metrics['percentuale_capienza']} direct={direct_metrics['percentuale_capienza']}"
                )

            if mismatch:
                role_summary[role_type]["helper_mismatches"] += 1
                mismatch_rows.append(
                    {
                        "user_id": user.id,
                        "full_name": name_by_user[user.id],
                        "role_type": role_type,
                        "reasons": reasons,
                    }
                )

            if role_type in {"nutrizionista", "coach"} and missing_typed_count > 0:
                incomplete_rows.append(
                    {
                        "user_id": user.id,
                        "full_name": name_by_user[user.id],
                        "role_type": role_type,
                        "assigned_clients": direct_assigned_count,
                        "typed_clients": sum(direct_type_counts.values()),
                        "missing_typed_clients": missing_typed_count,
                    }
                )

        report = {
            "professionals_total": len(professionals),
            "role_summary": role_summary,
            "notes": {
                "psicologia": "Per psicologia il backend usa ponderata=count clienti e ignora i bucket A/B/C/Secondario.",
            },
            "helper_vs_direct_mismatches": mismatch_rows[:50],
            "helper_vs_direct_mismatch_count": len(mismatch_rows),
            "nutrizione_coach_incomplete_rows": incomplete_rows[:50],
            "nutrizione_coach_incomplete_count": len(incomplete_rows),
            "hm_split_count": len(helper_hm_split),
        }
        print(json.dumps(report, ensure_ascii=True, indent=2, default=dict))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
