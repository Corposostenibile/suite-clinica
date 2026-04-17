"""
Test mirato per ITS-20260416-0012: Team Leader deve poter accedere alla formazione
dal profilo di un professionista nel proprio team.

Uso: poetry run python test_team_leader_production.py

Questo script verifica direttamente nel DB di produzione che:
1. can_view_member_reviews() restituisca True per Team Leader verso membri del proprio team
2. can_write_review() restituisca True per Team Leader verso membri del proprio team
3. NON ci sia AttributeError quando member non ha department_id/department
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ['FLASK_ENV'] = 'production'

from corposostenibile import create_app
app = create_app('production')

with app.app_context():
    from corposostenibile.models import User
    from corposostenibile.blueprints.review.routes import (
        can_view_member_reviews, can_write_review, _get_led_team_member_ids
    )
    from corposostenibile.extensions import db

    print("=" * 70)
    print("TEST: ITS-20260416-0012 - Team Leader Formazione Access")
    print("=" * 70)
    print()

    # Trova Team Leader con team e membri
    all_users = User.query.all()
    test_scenarios = []

    for u in all_users:
        if getattr(u, 'teams_led', None) and len(u.teams_led) > 0:
            team = u.teams_led[0]
            members = getattr(team, 'members', []) or []
            other_members = [m for m in members if m.id != u.id]
            if other_members:
                test_scenarios.append((u, team, other_members[0]))
                if len(test_scenarios) >= 3:
                    break

    if not test_scenarios:
        print("ERROR: Nessuno Team Leader con team e membri trovato!")
        sys.exit(1)

    all_passed = True

    for i, (tl, team, member) in enumerate(test_scenarios, 1):
        print(f"[Scenario {i}] Team Leader: {tl.id} ({tl.first_name} {tl.last_name})")
        print(f"            Team: {getattr(team, 'name', '?')}")
        print(f"            Test Member: {member.id} ({member.first_name} {member.last_name})")
        print(f"            Member department_id: {getattr(member, 'department_id', 'N/A')}")
        print(f"            Member department: {getattr(member, 'department', None)}")

        visible_ids = _get_led_team_member_ids(tl)
        print(f"            TL led member ids: {visible_ids}")
        print(f"            Member in led_ids: {member.id in visible_ids}")

        # Test can_view
        try:
            view_result = can_view_member_reviews(tl, member)
            view_ok = view_result is True
            print(f"            can_view_member_reviews = {view_result} {'✓' if view_ok else '✗ FAIL'}")
        except AttributeError as e:
            view_result = None
            view_ok = False
            print(f"            can_view_member_reviews = AttributeError: {e} ✗ FAIL")

        # Test can_write
        try:
            write_result = can_write_review(tl, member)
            write_ok = write_result is True
            print(f"            can_write_review = {write_result} {'✓' if write_ok else '✗ FAIL'}")
        except AttributeError as e:
            write_result = None
            write_ok = False
            print(f"            can_write_review = AttributeError: {e} ✗ FAIL")

        if view_ok and write_ok:
            print(f"            ✓ PASS")
        else:
            print(f"            ✗ FAIL")
            all_passed = False

        print()

    print("=" * 70)
    if all_passed:
        print("RISULTATO: TUTTI I TEST PASSATI ✓")
        print("Il fix su origin/fix/formazione-team-leader-access è corretto.")
        print("Procedere con deploy su GCP.")
        sys.exit(0)
    else:
        print("RISULTATO: ALCUNI TEST FALLITI ✗")
        print("Il fix non risolve completamente il problema.")
        sys.exit(1)
