#!/usr/bin/env python3
"""
Fix post-import: popola M2M e ClienteProfessionistaHistory via SQL diretto
(bypass SQLAlchemy-Continuum che intercetta le operazioni ORM).
"""

import sys
from datetime import date, datetime


def fix_team_assignments(dry_run: bool = False):
    from corposostenibile import create_app
    from corposostenibile.models import db

    app = create_app()
    with app.app_context():
        conn = db.engine.connect()

        # Carica i clienti importati con le loro FK
        result = conn.execute(db.text("""
            SELECT cliente_id, nome_cognome,
                   nutrizionista_id, coach_id, psicologa_id,
                   consulente_alimentare_id, health_manager_id,
                   data_inizio_abbonamento, onboarding_date, created_by
            FROM clienti
            WHERE cliente_id >= 28410 AND cliente_id <= 28568
        """))
        clienti = result.fetchall()
        print(f"\nClienti trovati: {len(clienti)}")
        print(f"Modalità: {'DRY-RUN' if dry_run else 'LIVE'}\n")

        # Carica tutti gli user_id validi
        valid_users = set(
            row[0] for row in conn.execute(db.text("SELECT id FROM users")).fetchall()
        )

        m2m_inserted = 0
        history_inserted = 0
        skipped = 0

        TIPO_MAP = [
            ("nutrizionista_id", 2, "nutrizionista", "cliente_nutrizionisti"),
            ("coach_id", 3, "coach", "cliente_coaches"),
            ("psicologa_id", 4, "psicologa", "cliente_psicologi"),
            ("consulente_alimentare_id", 5, "consulente", "cliente_consulenti"),
            ("health_manager_id", 6, "health_manager", None),
        ]

        m2m_values = []  # (table, cliente_id, user_id)
        history_values = []  # tuples for bulk insert

        for row in clienti:
            cliente_id = row[0]
            data_dal = row[7] or row[8] or date.today()
            created_by_id = row[9]

            for fk_field, col_idx, tipo, m2m_table in TIPO_MAP:
                user_id = row[col_idx]
                if not user_id:
                    continue

                if user_id not in valid_users:
                    print(f"  skip {row[1]}: {fk_field}={user_id} non esiste")
                    skipped += 1
                    continue

                # M2M
                if m2m_table:
                    m2m_values.append((m2m_table, cliente_id, user_id))
                    m2m_inserted += 1

                # History
                assegnato_da = created_by_id if (created_by_id and created_by_id in valid_users) else user_id
                history_values.append((
                    cliente_id, user_id, tipo, data_dal,
                    "Import CSV iniziale", assegnato_da
                ))
                history_inserted += 1

        if dry_run:
            print(f"\n{'='*60}")
            print(f"  DRY-RUN — Nessuna modifica")
            print(f"  M2M da inserire:     {m2m_inserted}")
            print(f"  History da inserire: {history_inserted}")
            if skipped:
                print(f"  Saltati: {skipped}")
            print(f"{'='*60}\n")
            conn.close()
            return

        # Esegui in transazione
        # Commit qualsiasi transazione auto-begin pendente
        if conn.in_transaction():
            conn.commit()
        trans = conn.begin()
        try:
            # Insert M2M con ON CONFLICT per sicurezza
            for table_name, cid, uid in m2m_values:
                conn.execute(db.text(f"""
                    INSERT INTO {table_name} (cliente_id, user_id)
                    VALUES (:cid, :uid)
                    ON CONFLICT DO NOTHING
                """), {"cid": cid, "uid": uid})

            # Insert History
            for h in history_values:
                conn.execute(db.text("""
                    INSERT INTO cliente_professionista_history
                        (cliente_id, user_id, tipo_professionista, data_dal,
                         motivazione_aggiunta, assegnato_da_id, is_active,
                         created_at, updated_at)
                    VALUES (:cid, :uid, :tipo, :data_dal,
                            :motiv, :assegnato, TRUE,
                            :now, :now)
                """), {
                    "cid": h[0], "uid": h[1], "tipo": h[2],
                    "data_dal": h[3], "motiv": h[4], "assegnato": h[5],
                    "now": datetime.utcnow(),
                })

            trans.commit()
            print(f"\n{'='*60}")
            print(f"  FIX COMPLETATO!")
            print(f"  M2M inseriti:     {m2m_inserted}")
            print(f"  History inseriti: {history_inserted}")
            if skipped:
                print(f"  Saltati: {skipped}")
            print(f"{'='*60}\n")
        except Exception as e:
            trans.rollback()
            print(f"\nERRORE: {e}")
            raise
        finally:
            conn.close()


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    fix_team_assignments(dry_run=dry_run)
