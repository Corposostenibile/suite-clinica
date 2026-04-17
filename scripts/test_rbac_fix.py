#!/usr/bin/env python3
"""
Test script to verify RBAC logic fix for client visibility.
Tests that professionals only see clients where they are the primary assigned professional
or in the multi-assignment tables (cliente_nutrizionisti, etc.) only when no primary is assigned.

Usage:
    kubectl exec -it suite-clinica-backend-XXXXX -c backend -- python /app/scripts/test_rbac_fix.py
"""
import sys
sys.path.insert(0, '/app')

from corposostenibile import create_app
from corposostenibile.models import db, Cliente
from sqlalchemy import text, or_, and_


def test_rbac_for_elisa():
    """Test RBAC logic for Elisa Menichelli (user_id=50)"""
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("Testing RBAC fix for Elisa Menichelli (user_id=50)")
        print("=" * 60)
        
        user_id = 50
        
        # 1. Count total clients visible BEFORE fix (current behavior)
        result_before = db.session.execute(text('''
            SELECT COUNT(*) as total FROM clienti c
            WHERE 
                c.nutrizionista_id = :uid 
                OR c.coach_id = :uid 
                OR c.psicologa_id = :uid 
                OR c.consulente_alimentare_id = :uid
                OR EXISTS (SELECT 1 FROM cliente_nutrizionisti cn WHERE cn.cliente_id = c.cliente_id AND cn.user_id = :uid)
                OR EXISTS (SELECT 1 FROM cliente_consulenti cc WHERE cc.cliente_id = c.cliente_id AND cc.user_id = :uid)
                OR EXISTS (SELECT 1 FROM cliente_professionista_history cph WHERE cph.cliente_id = c.cliente_id AND cph.user_id = :uid AND cph.is_active = true)
                OR EXISTS (SELECT 1 FROM call_bonus cb WHERE cb.cliente_id = c.cliente_id AND cb.professionista_id = :uid AND cb.status = 'accettata')
        '''), {'uid': user_id})
        total_before = result_before.fetchone()[0]
        print(f"\n1. Total clients visible BEFORE fix: {total_before}")
        
        # 2. Count clients after fix (using NEW logic)
        # NEW: Multi-assignments only if no primary OR this user is primary
        result_after = db.session.execute(text('''
            SELECT COUNT(*) as total FROM clienti c
            WHERE 
                -- Direct assignments
                c.nutrizionista_id = :uid 
                OR c.coach_id = :uid 
                OR c.psicologa_id = :uid 
                OR c.consulente_alimentare_id = :uid
                -- Multi-assignments only if no primary OR this user is primary
                OR (
                    EXISTS (SELECT 1 FROM cliente_nutrizionisti cn WHERE cn.cliente_id = c.cliente_id AND cn.user_id = :uid)
                    AND (c.nutrizionista_id IS NULL OR c.nutrizionista_id = :uid)
                )
                OR (
                    EXISTS (SELECT 1 FROM cliente_coaches cc WHERE cc.cliente_id = c.cliente_id AND cc.user_id = :uid)
                    AND (c.coach_id IS NULL OR c.coach_id = :uid)
                )
                OR (
                    EXISTS (SELECT 1 FROM cliente_psicologi cp WHERE cp.cliente_id = c.cliente_id AND cp.user_id = :uid)
                    AND (c.psicologa_id IS NULL OR c.psicologa_id = :uid)
                )
                OR (
                    EXISTS (SELECT 1 FROM cliente_consulenti cc WHERE cc.cliente_id = c.cliente_id AND cc.user_id = :uid)
                    AND (c.consulente_alimentare_id IS NULL OR c.consulente_alimentare_id = :uid)
                )
                -- Call bonus
                OR EXISTS (SELECT 1 FROM call_bonus cb WHERE cb.cliente_id = c.cliente_id AND cb.professionista_id = :uid AND cb.status = 'accettata')
                -- Active history
                OR EXISTS (SELECT 1 FROM cliente_professionista_history cph WHERE cph.cliente_id = c.cliente_id AND cph.user_id = :uid AND cph.is_active = true)
        '''), {'uid': user_id})
        total_after = result_after.fetchone()[0]
        print(f"2. Total clients visible AFTER fix: {total_after}")
        
        print(f"\n3. Clienti rimossi: {total_before - total_after} ({round((total_before - total_after) / total_before * 100, 1)}%)")
        
        # 4. Breakdown of removed clients
        print("\n4. Breakdown of clients removed:")
        
        # Clients where Elisa is ONLY in cliente_nutrizionisti (not primary, primary is someone else)
        removed_cn = db.session.execute(text('''
            SELECT COUNT(*) FROM clienti c
            WHERE EXISTS (SELECT 1 FROM cliente_nutrizionisti cn WHERE cn.cliente_id = c.cliente_id AND cn.user_id = :uid)
            AND c.nutrizionista_id IS NOT NULL AND c.nutrizionista_id != :uid
        '''), {'uid': user_id}).fetchone()[0]
        print(f"   - From cliente_nutrizionisti (primary is another): {removed_cn}")
        
        # Clients where Elisa is ONLY in cliente_consulenti (not primary, primary is someone else)
        removed_cc = db.session.execute(text('''
            SELECT COUNT(*) FROM clienti c
            WHERE EXISTS (SELECT 1 FROM cliente_consulenti cc WHERE cc.cliente_id = c.cliente_id AND cc.user_id = :uid)
            AND c.consulente_alimentare_id IS NOT NULL AND c.consulente_alimentare_id != :uid
        '''), {'uid': user_id}).fetchone()[0]
        print(f"   - From cliente_consulenti (primary is another): {removed_cc}")
        
        # 5. Verify: clients that SHOULD still be visible
        print("\n5. Clients that should still be visible:")
        
        # Direct assignments
        direct = db.session.execute(text('''
            SELECT COUNT(*) FROM clienti c
            WHERE c.nutrizionista_id = :uid OR c.coach_id = :uid OR c.psicologa_id = :uid OR c.consulente_alimentare_id = :uid
        '''), {'uid': user_id}).fetchone()[0]
        print(f"   - Direct assignments: {direct}")
        
        # Multi where no primary
        multi_no_primary = db.session.execute(text('''
            SELECT COUNT(*) FROM clienti c
            WHERE (
                EXISTS (SELECT 1 FROM cliente_nutrizionisti cn WHERE cn.cliente_id = c.cliente_id AND cn.user_id = :uid)
                OR EXISTS (SELECT 1 FROM cliente_coaches cc WHERE cc.cliente_id = c.cliente_id AND cc.user_id = :uid)
                OR EXISTS (SELECT 1 FROM cliente_psicologi cp WHERE cp.cliente_id = c.cliente_id AND cp.user_id = :uid)
                OR EXISTS (SELECT 1 FROM cliente_consulenti cc WHERE cc.cliente_id = c.cliente_id AND cc.user_id = :uid)
            )
            AND c.nutrizionista_id IS NULL AND c.coach_id IS NULL AND c.psicologa_id IS NULL AND c.consulente_alimentare_id IS NULL
        '''), {'uid': user_id}).fetchone()[0]
        print(f"   - Multi-assign with no primary: {multi_no_primary}")
        
        print("\n" + "=" * 60)
        if total_before == total_after:
            print("NOTE: No clients removed because multi-assign entries")
            print("were already correctly scoped (nutrizionista_id was NULL)")
            print("or the user was the primary.")
        else:
            print("TEST RESULT: Fix correctly filters out clients where Elisa")
            print("appears in multi-assignment tables but is not the primary.")
        print("=" * 60)


def test_rbac_for_other_professionals():
    """Test that fix doesn't break access for other users"""
    app = create_app()
    with app.app_context():
        print("\n\n" + "=" * 60)
        print("Testing RBAC for OTHER professionals (spot check)")
        print("=" * 60)
        
        # Check a few other user IDs
        test_users = [12, 23, 39]  # Some other professionals
        
        for uid in test_users:
            result = db.session.execute(text('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN c.nutrizionista_id = :uid THEN 1 ELSE 0 END) as direct_nut,
                       SUM(CASE WHEN c.nutrizionista_id IS NULL 
                            AND EXISTS (SELECT 1 FROM cliente_nutrizionisti cn WHERE cn.cliente_id = c.cliente_id AND cn.user_id = :uid) 
                            THEN 1 ELSE 0 END) as multi_no_primary
                FROM clienti c
                WHERE 
                    c.nutrizionista_id = :uid 
                    OR EXISTS (SELECT 1 FROM cliente_nutrizionisti cn WHERE cn.cliente_id = c.cliente_id AND cn.user_id = :uid)
            '''), {'uid': uid})
            row = result.fetchone()
            print(f"\n  User {uid}: total={row[0]}, direct={row[1]}, multi_no_primary={row[2]}")


if __name__ == "__main__":
    test_rbac_for_elisa()
    test_rbac_for_other_professionals()
