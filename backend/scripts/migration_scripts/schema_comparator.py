import re
import os
import sys
import subprocess
import tempfile
import shutil
import glob
from collections import OrderedDict, defaultdict
from datetime import datetime
from werkzeug.security import generate_password_hash

DEFAULT_IMPORTED_PASSWORD_HASH = generate_password_hash("Dev123?")

# =============================================================================
# ORGANIGRAMMA UFFICIALE 2026 (AUTORITATIVO PER MIGRAZIONE TEAM)
# =============================================================================
OFFICIAL_TEAMS = OrderedDict({
    '1': {
        'name': 'Nutrizione - Team 1',
        'team_type': 'nutrizione',
        'leader': 'Filippo Feliciani',
        'members': ['Alessandra Arcoleo', 'Caterina Esposito', 'Chiara Giombolini', 'Elisa Menichelli', 'Federica Cutolo', 'Giorgia Leone', 'Giorgia Santi', 'Jessica Di Colli', 'Maria Vittoria Sallicano', 'Marilena Franco', 'Marta Buccilli', 'Martina Mantovani', 'Michela Pagnani', 'Sara Goffi', 'Valeria Loliva'],
    },
    '2': {
        'name': 'Nutrizione - Team 2',
        'team_type': 'nutrizione',
        'leader': 'Isabella Rossi',
        'members': ['Alice Aresti', 'Alice Surbone', 'Florinda Masciello', 'Francesca Abatini', 'Gianluca Marino', 'Gianna Sannelli', 'Isabella Venticinque', 'Mara Adreola', 'Marisa Piras', 'Martina Roberti', 'Nicola Fassetta', 'Nicolò Lorenzo Marinelli', 'Rossana Picerno', 'Silvia Testoni', 'Virginia Vitelli'],
    },
    '3': {
        'name': 'Nutrizione - Team 3',
        'team_type': 'nutrizione',
        'leader': 'Alice Posenato',
        'members': ['Andrea Tuacris', 'Bianca Balzarini', 'Caterina Scarano', 'Chiara D\'Addesa', 'Elisa Mancini', 'Francesca Ceppetelli', 'Francesca Tornese', 'Giammarco Lamanda', 'Rossella Cariglia', 'Sabine Ardiccioni', 'Silvia Maria Scoletta', 'Valentina Botondi'],
    },
    '4': {
        'name': 'Nutrizione - Team 4',
        'team_type': 'nutrizione',
        'leader': 'Alice Posenato',
        'members': ['Carlotta Sed', 'Francesca Valentini', 'Gaia Sala', 'Marta Bendusi', 'Noemi Di Natale', 'Virginia Bonazzi'],
    },
    '5': {
        'name': 'Psicologia - Team 1',
        'team_type': 'psicologia',
        'leader': 'Delia De Santis',
        'members': ['Alice Lampone', 'Angela Velletri', 'Claudia Milione', 'Giorgia Del Bianco', 'Martina Calvi', 'Martina Loccisano'],
    },
    '6': {
        'name': 'Psicologia - Team 2',
        'team_type': 'psicologia',
        'leader': 'Francesca Zaccaro',
        'members': ['Angel Disney Armenise', 'Aurora Valente', 'Barbara Visalli', 'Denise Caravano', 'Germana Morganti', 'Manny Aiello'],
    },
    '7': {
        'name': 'Coach',
        'team_type': 'coach',
        'leader': 'Lorenzo Sambri',
        'members': ['Alessandra Di Lisciandro', 'Angbonon Ange Olivier Bile', 'Angelo Lacorte', 'Claudio Lopiano', 'Danilo Bonifati', 'Federico De Bene', 'Francesco Falcone', 'Giovanna Pirina', 'Giuseppe Summa', 'Ilaria Galesi', 'Marco Fratini', 'Matteo Test User', 'Nino Helera', 'Rebecca Masseroni', 'Ruggiero Balzano', 'Sara Paganotto', 'Valentina Carisio'],
    },
})

def get_professional_info(first_name, last_name):
    full_name = f"{first_name} {last_name}".strip().lower()
    for team in OFFICIAL_TEAMS.values():
        specialty = team['team_type']
        spec_map = {'nutrizione': 'nutrizionista', 'psicologia': 'psicologo', 'coach': 'coach'}
        if team['leader'].lower() == full_name:
            return spec_map[specialty], 'team_leader'
        if any(m.lower() == full_name for m in team['members']):
            return spec_map[specialty], 'professionista'
    return None, None

def generate_admin_user_sql():
    admin_email = "dev@corposostenibile.it"
    admin_password_hash = generate_password_hash("Dev123?")
    return f"""
    INSERT INTO public.users (
        email, password_hash, first_name, last_name,
        is_admin, is_active, role, is_external, is_trial,
        created_at, updated_at
    ) VALUES (
        '{admin_email}', '{admin_password_hash}', 'Dev', 'Admin',
        true, true, 'admin', false, false,
        NOW(), NOW()
    )
    ON CONFLICT (email) DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        first_name = EXCLUDED.first_name,
        last_name = EXCLUDED.last_name,
        is_admin = true,
        is_active = true,
        role = 'admin',
        is_external = false,
        is_trial = false,
        updated_at = NOW();
    """

def parse_sql_dump(file_path):
    schema = {}
    enum_defs = {}
    fk_deps = {}
    print(f"Parsing {file_path} (new attempt)...")
    
    def get_lines(path, use_pg_restore=False):
        if use_pg_restore:
            print("Trying with pg_restore...")
            process = subprocess.Popen(['pg_restore', '-f', '-', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.stdout:
                for line in process.stdout: yield line
            if process.stderr:
                print(f"pg_restore stderr: {process.stderr.read()}")
        else:
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                    for line in f: yield line
            except Exception as e:
                print(f"Direct file read error: {e}")
                return # empty generator
        
    in_table_definition = False
    current_table_name = None
    
    # Regex per trovare l'inizio di CREATE TABLE, più flessibile
    re_create_table = re.compile(r'CREATE TABLE\s+(?:\"?public\"?\.)?\"?(\w+)\"?\s*\(', re.IGNORECASE)
    # Regex per trovare la fine della definizione di tabella
    re_table_definition_end = re.compile(r'^\s*\);$', re.IGNORECASE)
    
    # Primo tentativo: lettura diretta
    lines_generator = get_lines(file_path, use_pg_restore=False)
    
    # Se non produce righe, prova pg_restore
    first_line = next(lines_generator, None)
    if first_line is None:
        print("Direct read yielded no lines, trying pg_restore for schema file.")
        lines_generator = get_lines(file_path, use_pg_restore=True)
        first_line = next(lines_generator, None) # Get first line again
        if first_line is None:
            print("pg_restore also yielded no lines for schema file.")
            return {}
    
    # Concatena la prima linea con il resto
    all_lines = [first_line] + list(lines_generator)

    for line in all_lines:
        line = line.strip()
        
        if in_table_definition:
            if re_table_definition_end.match(line): # Matches ');'
                in_table_definition = False
                current_table_name = None
                continue
            
            # Linea di colonna
            if not any(line.upper().startswith(kw) for kw in ['CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'CHECK', 'UNIQUE']):
                line_clean = line.rstrip(',')
                parts = line_clean.split(maxsplit=1)
                if len(parts) >= 2:
                    col_name = parts[0].strip('"').strip("'")
                    col_type = parts[1]
                    if current_table_name: # Assicurati di avere una tabella corrente
                        schema[current_table_name][col_name] = col_type
        else:
            match = re_create_table.search(line)
            if match:
                current_table_name = match.group(1)
                schema[current_table_name] = {}
                in_table_definition = True
    
    print(f"Tables found: {list(schema.keys())}")

    # Parse enum definitions from schema text to normalize invalid legacy enum values.
    try:
        schema_text = "".join(all_lines)
        enum_pattern = re.compile(
            r"CREATE TYPE\s+(?:\"?public\"?\.)?\"?(\w+)\"?\s+AS ENUM\s*\((.*?)\);",
            re.IGNORECASE | re.DOTALL,
        )
        enum_val_pattern = re.compile(r"'((?:''|[^'])*)'")
        for m in enum_pattern.finditer(schema_text):
            enum_name = m.group(1).strip().lower()
            raw_values = m.group(2)
            vals = []
            for vm in enum_val_pattern.finditer(raw_values):
                vals.append(vm.group(1).replace("''", "'"))
            if vals:
                enum_defs[enum_name] = set(vals)

        # Parse FK dependencies to order inserts: referenced tables first.
        fk_pattern = re.compile(
            r'ALTER TABLE ONLY\s+(?:\"?public\"?\.)?\"?(\w+)\"?.*?FOREIGN KEY\s*\(.*?\)\s*REFERENCES\s+(?:\"?public\"?\.)?\"?(\w+)\"?',
            re.IGNORECASE | re.DOTALL,
        )
        for m in fk_pattern.finditer(schema_text):
            child = m.group(1)
            parent = m.group(2)
            if child == parent:
                continue
            fk_deps.setdefault(child, set()).add(parent)
    except Exception as exc:
        print(f"Warning: enum parsing failed: {exc}")
    
    # Static Fallback if parsing fails
    if not schema:
        print("Using STATIC FALLBACK schema...")
        schema = {
            'users': {'id': 'int', 'email': 'v', 'password_hash': 'v', 'first_name': 'v', 'last_name': 'v', 'is_admin': 'b', 'is_active': 'b', 'role': 'v', 'specialty': 'v', 'is_external': 'b', 'created_at': 't', 'updated_at': 't'},
            'departments': {'id': 'int', 'name': 'v', 'head_id': 'int'},
            'teams': {'id': 'int', 'name': 'v', 'team_type': 'v', 'department_id': 'int', 'head_id': 'int', 'is_active': 'b'},
            'team_members': {'team_id': 'int', 'user_id': 'int', 'joined_at': 't'},
            'origins': {'id': 'int', 'name': 'v', 'active': 'b', 'influencer_id': 'int'},
            'clienti': {'cliente_id': 'int', 'nome_cognome': 'v', 'mail': 'v', 'nutrizionista_id': 'int', 'coach_id': 'int', 'psicologa_id': 'int', 'health_manager_id': 'int', 'storia_cliente': 'v', 'programma_attuale': 'v', 'stato_cliente': 'v'},
            'weekly_checks': {'id': 'int', 'cliente_id': 'int', 'check_date': 't'}
        }
    return schema, enum_defs, fk_deps

def unescape_copy(val):
    if val == r'\N' or val is None: return None
    return val.replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\t', '\t').replace(r'\\', '\\')

def to_sql_value(val, col_type=''):
    if val is None: return 'NULL'
    val = str(val).replace("'", "''")
    if col_type and 'json' in col_type.lower():
        # Ensure JSON strings do not contain raw control characters.
        val = val.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f"'{val}'"

TABLE_PRIORITY = [
    'users',
    'departments',
    'teams',
    'team_members',
    'origins',
    'clienti',
    'weekly_checks',
    'weekly_check_responses',
    'weekly_check_link_assignments',
    'dca_checks',
    'dca_check_responses',
    'minor_checks',
    'minor_check_responses',
]
MIGRATION_TABLES = None
EXCLUDED_TABLES = {
    t.strip()
    for t in os.environ.get('MIGRATION_EXCLUDED_TABLES', 'activity_log,global_activity_log').split(',')
    if t.strip()
}
# Optional compatibility mode: keep old behavior that filters professionals to OFFICIAL_TEAMS
# and rebuilds teams/team_members from official organigram.
STRICT_ORGANIGRAM = os.environ.get('STRICT_ORGANIGRAM', '0').strip().lower() in {'1', 'true', 'yes'}
TEAM_TYPE_BY_ID = {
    '1': 'nutrizione',
    '2': 'nutrizione',
    '3': 'nutrizione',
    '4': 'nutrizione',
    '5': 'psicologia',
    '6': 'psicologia',
    '7': 'coach',
}
ALLOWED_USER_ROLES = {'admin', 'team_leader', 'professionista', 'team_esterno', 'influencer'}
ALLOWED_USER_SPECIALTIES = {
    'amministrazione', 'cco', 'nutrizione', 'psicologia', 'coach', 'nutrizionista', 'psicologo'
}
ROLE_ALIASES = {
    'team leader': 'team_leader',
    'teamleader': 'team_leader',
    'professional': 'professionista',
    'professionist': 'professionista',
    'external_team': 'team_esterno',
    'external': 'team_esterno',
}
SPECIALTY_ALIASES = {
    'nutrizione': 'nutrizione',
    'nutrition': 'nutrizione',
    'nutritional': 'nutrizione',
    'nutrizionista': 'nutrizionista',
    'nutritionist': 'nutrizionista',
    'psicologia': 'psicologia',
    'psychology': 'psicologia',
    'psicologo': 'psicologo',
    'psychologist': 'psicologo',
    'coach': 'coach',
}
ENUM_ALIASES = {
    'checksaltatienum': {
        'tre_plus': '3_plus',
    },
    'ticketurgencyenum': {
        'alta': '1',
        'media': '2',
        'bassa': '3',
    },
    'tipopagamentointernoenum': {
        'primo_pagamento': 'deposito_iniziale',
        'primo': 'deposito_iniziale',
        'first_payment': 'deposito_iniziale',
    },
    'statoclienteenum': {
        'freeze': 'pausa',
        'insoluto': 'stop',
    },
}

def normalize_user_role(raw_role):
    role = str(raw_role or '').strip().lower().replace('-', '_')
    role = ROLE_ALIASES.get(role, role)
    return role if role in ALLOWED_USER_ROLES else None

def normalize_user_specialty(raw_specialty):
    specialty = str(raw_specialty or '').strip().lower()
    specialty = SPECIALTY_ALIASES.get(specialty, specialty)
    return specialty if specialty in ALLOWED_USER_SPECIALTIES else None

def normalize_bool(raw, default=False):
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, (int, float)):
        return raw != 0
    return str(raw).strip().lower() in {'1', 't', 'true', 'y', 'yes'}

def table_is_included(table_name, new_schema_def):
    if table_name in EXCLUDED_TABLES:
        return False
    if table_name not in new_schema_def:
        return False
    if MIGRATION_TABLES is not None and table_name not in MIGRATION_TABLES:
        return False
    return True


def refresh_new_schema_backup(schema_path: str) -> str:
    """
    Regenerate NEW_SUITE_BACKUP from target DB schema using pg_dump.
    Controlled by env:
      - MIGRATION_REFRESH_NEW_SCHEMA (default: 1)
      - MIGRATION_SCHEMA_REFRESH_STRICT (default: 1)
    """
    enabled = os.environ.get('MIGRATION_REFRESH_NEW_SCHEMA', '1').strip().lower() in {'1', 'true', 'yes'}
    strict = os.environ.get('MIGRATION_SCHEMA_REFRESH_STRICT', '1').strip().lower() in {'1', 'true', 'yes'}

    if not enabled:
        print(f"[schema-refresh] disabled (MIGRATION_REFRESH_NEW_SCHEMA=0), using existing: {schema_path}")
        return schema_path

    out_dir = os.path.dirname(schema_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    tmp_path = f"{schema_path}.tmp"

    pg_host = os.environ.get('PGHOST', '127.0.0.1')
    pg_port = os.environ.get('PGPORT', '5432')
    pg_user = os.environ.get('PGUSER', '')
    pg_db = os.environ.get('PGDATABASE', '')

    if not pg_user or not pg_db:
        msg = "[schema-refresh] PGUSER/PGDATABASE non impostati: impossibile rigenerare lo schema"
        if strict:
            raise RuntimeError(msg)
        print(f"{msg}; fallback file esistente")
        return schema_path

    cmd = [
        'pg_dump',
        '--schema-only',
        '--no-owner',
        '--no-privileges',
        '--quote-all-identifiers',
        '--no-comments',
        '-h', pg_host,
        '-p', pg_port,
        '-U', pg_user,
        '-d', pg_db,
        '-f', tmp_path,
    ]

    print(f"[schema-refresh] regenerating schema backup: {schema_path}")
    try:
        subprocess.run(cmd, check=True)
        os.replace(tmp_path, schema_path)
        print("[schema-refresh] done")
        return schema_path
    except Exception as exc:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass
        msg = f"[schema-refresh] failed: {exc}"
        if strict:
            raise RuntimeError(msg)
        print(f"{msg}; fallback file esistente")
        return schema_path

def load_fk_dependencies_from_db():
    """
    Read FK graph from target DB to avoid brittle parsing from schema SQL text.
    Requires PG* env vars and reachable DB (Cloud SQL proxy already up in Job).
    """
    sql = (
        "SELECT child.relname, parent.relname "
        "FROM pg_constraint c "
        "JOIN pg_class child ON c.conrelid = child.oid "
        "JOIN pg_namespace child_ns ON child.relnamespace = child_ns.oid "
        "JOIN pg_class parent ON c.confrelid = parent.oid "
        "JOIN pg_namespace parent_ns ON parent.relnamespace = parent_ns.oid "
        "WHERE c.contype = 'f' "
        "AND child_ns.nspname = 'public' "
        "AND parent_ns.nspname = 'public';"
    )
    deps = {}
    try:
        proc = subprocess.run(
            ['psql', '-At', '-F', '|', '-c', sql],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return deps
        for raw in proc.stdout.splitlines():
            if not raw or '|' not in raw:
                continue
            child, parent = raw.split('|', 1)
            child = child.strip()
            parent = parent.strip()
            if not child or not parent or child == parent:
                continue
            deps.setdefault(child, set()).add(parent)
    except Exception:
        return {}
    return deps

def apply_manual_fk_dependencies(deps):
    # Safety net for legacy dumps where inferred order can still be wrong in practice.
    manual = {
        'lead_activity_logs': {'sales_leads'},
        'lead_payments': {'sales_leads'},
        'sales_leads': {'sales_form_links'},
    }
    out = {k: set(v) for k, v in (deps or {}).items()}
    for child, parents in manual.items():
        out.setdefault(child, set()).update(parents)
    return out

def order_tables_by_fk(inserted_tables, fk_deps):
    tables = list(OrderedDict.fromkeys(inserted_tables))
    table_set = set(tables)
    parents = {t: set() for t in tables}
    children = {t: set() for t in tables}
    indegree = {t: 0 for t in tables}

    for child in tables:
        for parent in fk_deps.get(child, set()):
            if parent not in table_set:
                continue
            if parent == child:
                continue
            if parent in parents[child]:
                continue
            parents[child].add(parent)
            children[parent].add(child)
            indegree[child] += 1

    # Prefer critical roots only when they are valid roots (indegree=0).
    preferred_roots = ['users', 'departments', 'teams', 'team_members', 'clienti']
    ordered = []
    queue = []
    for root in preferred_roots:
        if root in indegree and indegree[root] == 0:
            queue.append(root)
    for t in sorted(tables):
        if indegree[t] == 0 and t not in queue:
            queue.append(t)

    while queue:
        node = queue.pop(0)
        if node in ordered:
            continue
        ordered.append(node)
        for ch in sorted(children[node]):
            indegree[ch] -= 1
            if indegree[ch] == 0:
                queue.append(ch)

    # Fallback for cycles/unparsed constraints.
    if len(ordered) != len(tables):
        for t in tables:
            if t not in ordered:
                ordered.append(t)
    return ordered

def enforce_table_precedence(ordered_tables, precedence_pairs):
    ordered = list(ordered_tables)
    # Iterate until stable so chained constraints are always respected.
    changed = True
    while changed:
        changed = False
        for parent, child in precedence_pairs:
            if parent not in ordered or child not in ordered:
                continue
            p_idx = ordered.index(parent)
            c_idx = ordered.index(child)
            if p_idx < c_idx:
                continue
            # Move parent just before child.
            ordered.pop(p_idx)
            c_idx = ordered.index(child)
            ordered.insert(c_idx, parent)
            changed = True
    return ordered


def sanitize_for_column(raw_value, col_type, enum_defs):
    if raw_value is None:
        return None
    col_type_norm = str(col_type or '').strip().lower()
    col_type_base = col_type_norm.strip('"')
    if '.' in col_type_base:
        col_type_base = col_type_base.split('.')[-1]
    col_type_base = col_type_base.strip('"')
    if col_type_base.endswith('[]'):
        col_type_base = col_type_base[:-2]
    val = str(raw_value)
    if val == '':
        if any(k in col_type_norm for k in ('int', 'numeric', 'decimal', 'double precision', 'real', 'date', 'time')):
            return None
    enum_type_key = None
    enum_values = enum_defs.get(col_type_norm) or enum_defs.get(col_type_base)
    if enum_values:
        enum_type_key = col_type_norm if col_type_norm in enum_defs else col_type_base
    else:
        # col_type may include extra tokens (e.g. "ticketurgencyenum NOT NULL").
        # Match by containment against known enum names.
        for enum_name, values in enum_defs.items():
            if enum_name and enum_name in col_type_norm:
                enum_type_key = enum_name
                enum_values = values
                break
    if enum_values:
        low = val.strip().lower().replace('-', '_').replace(' ', '_')
        alias_map = {}
        if enum_type_key:
            alias_map = ENUM_ALIASES.get(enum_type_key, {})
        if not alias_map:
            alias_map = ENUM_ALIASES.get(col_type_norm, {}) or ENUM_ALIASES.get(col_type_base, {})
        candidate = alias_map.get(low, val.strip())
        if candidate in enum_values:
            return candidate
        if low in enum_values:
            return low
        # Unknown enum labels are nulled so import can continue.
        return None
    if col_type_norm == 'boolean':
        low = val.strip().lower()
        if low in {'1', 't', 'true', 'y', 'yes'}:
            return True
        if low in {'0', 'f', 'false', 'n', 'no'}:
            return False
        return None
    # Keep oversized text values importable when target is varchar(n).
    varchar_match = re.search(r'(?:character varying|varchar)\s*\((\d+)\)', col_type_norm)
    if varchar_match:
        try:
            max_len = int(varchar_match.group(1))
            if max_len > 0 and len(val) > max_len:
                return val[:max_len]
        except Exception:
            pass
    return val

def apply_default_value(table, col, value, row):
    def has_val(v):
        if v is None:
            return False
        return str(v).strip() != ''

    if table == 'users' and col == 'trial_supervisor_id':
        # Old dumps can reference supervisors that are not imported in users.
        # Keep migration progressing by nulling this self-FK.
        return None
    if table == 'sales_leads' and col == 'form_link_id':
        # Break circular FK load dependency with sales_form_links during import.
        return None
    if table == 'sales_form_links':
        row_user_id = row.get('user_id')
        row_lead_id = row.get('lead_id')
        row_check_number = row.get('check_number')
        has_user = has_val(row_user_id)
        has_lead = has_val(row_lead_id)

        # Enforce check_link_type_xor_v2:
        # (user_id set, lead_id null, check_number null) OR
        # (user_id null, lead_id set, check_number set)
        if col == 'lead_id' and has_user:
            return None
        if col == 'check_number':
            if has_user:
                return None
            if has_lead and not has_val(value if value is not None else row_check_number):
                return 1
        if col == 'user_id' and has_lead:
            return None
    if table == 'sales_form_links' and col == 'unique_code' and (value is None or str(value).strip() == ''):
        link_id = str(row.get('id', '')).strip() or 'unknown'
        return f"legacy-link-{link_id}"
    if table == 'lead_payments' and col == 'amount':
        # Target DB enforces positive amounts (check_amount_positive).
        # Legacy dump can contain 0.00 rows: keep row importable with a small positive floor.
        if value is None:
            return '0.01'
        raw = str(value).strip().replace(',', '.')
        try:
            if float(raw) <= 0:
                return '0.01'
        except Exception:
            return '0.01'
    if table == 'teams' and col == 'team_type' and value is None:
        team_id = str(row.get('id', '')).strip()
        return TEAM_TYPE_BY_ID.get(team_id, 'nutrizione')
    if table == 'teams' and col == 'is_active' and value is None:
        return True
    if table == 'users' and col == 'is_trial' and value is None:
        return False
    if table == 'users' and col in {'created_at', 'updated_at'} and value is None:
        return datetime.now().isoformat()
    return value

def derived_user_value(col, row):
    raw_role = row.get('role')
    role = normalize_user_role(raw_role)
    is_admin = normalize_bool(row.get('is_admin'), default=False)
    is_external = normalize_bool(row.get('is_external'), default=False)
    raw_specialty = row.get('specialty')
    specialty = normalize_user_specialty(raw_specialty)
    # Fallback: infer specialty from official organigram when source value is missing.
    if not specialty:
        inferred_specialty, _ = get_professional_info(
            row.get('first_name') or '',
            row.get('last_name') or '',
        )
        specialty = inferred_specialty

    if col == 'role':
        if is_admin:
            return 'admin'
        if role:
            # A clinical role without specialty is invalid in the new model.
            if role in {'professionista', 'team_leader'} and not specialty:
                return None
            return role
        if is_external:
            return 'team_esterno'
        return 'professionista' if specialty else None
    if col == 'specialty':
        return specialty
    if col == 'email':
        email = (row.get('email') or '').strip()
        if email:
            return email
        uid = (row.get('id') or '').strip() or 'unknown'
        return f"imported_user_{uid}@invalid.local"
    if col == 'password_hash':
        return row.get('password_hash') or DEFAULT_IMPORTED_PASSWORD_HASH
    if col == 'first_name':
        return row.get('first_name') or 'Utente'
    if col == 'last_name':
        return row.get('last_name') or 'Sconosciuto'
    if col == 'is_admin':
        return is_admin
    if col == 'is_active':
        return normalize_bool(row.get('is_active'), default=True)
    if col == 'is_external':
        return is_external
    if col == 'is_trial':
        return normalize_bool(row.get('is_trial'), default=False)
    if col in {'created_at', 'updated_at'}:
        return row.get(col) or datetime.now().isoformat()
    return None

def discover_tables_in_dump(old_dump_path, new_schema_def):
    re_table_data = re.compile(r'TABLE DATA\s+public\s+("?)(\w+)\1', re.IGNORECASE)
    found = []
    seen = set()
    proc = subprocess.run(
        ['pg_restore', '-l', old_dump_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False
    )
    for raw in proc.stdout.splitlines():
        m = re_table_data.search(raw)
        if not m:
            continue
        table = m.group(2)
        if not table_is_included(table, new_schema_def):
            continue
        if table not in seen:
            seen.add(table)
            found.append(table)
    return found

def write_sequences_block(outfile, inserted_tables):
    if not inserted_tables:
        return
    inserted_tables_sql = ", ".join(f"'{t}'" for t in inserted_tables)
    outfile.write(
        "DO $$\n"
        "DECLARE r RECORD;\n"
        "DECLARE max_id BIGINT;\n"
        "BEGIN\n"
        "  FOR r IN\n"
        "    SELECT c.table_name, c.column_name,\n"
        "           pg_get_serial_sequence(format('%I.%I', c.table_schema, c.table_name), c.column_name) AS seq_name\n"
        "    FROM information_schema.columns c\n"
        "    WHERE c.table_schema = 'public'\n"
        f"      AND c.table_name IN ({inserted_tables_sql})\n"
        "      AND c.column_default LIKE 'nextval(%'\n"
        "  LOOP\n"
        "    IF r.seq_name IS NOT NULL THEN\n"
        "      EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I.%I', r.column_name, 'public', r.table_name) INTO max_id;\n"
        "      EXECUTE format('SELECT setval(%L, GREATEST(%s, 1), true)', r.seq_name, max_id);\n"
        "    END IF;\n"
        "  END LOOP;\n"
        "END$$;\n"
    )

def generate_migrated_dump_streaming(old_dump_path, output_path, new_schema_def, enum_defs, fk_deps):
    print("\nGENERATING MIGRATION DUMP (streaming)...")
    tables_in_dump = discover_tables_in_dump(old_dump_path, new_schema_def)
    insert_batch_size = int(os.environ.get('MIGRATION_INSERT_BATCH_SIZE', '1'))
    if insert_batch_size < 1:
        insert_batch_size = 1

    re_copy = re.compile(r'COPY\s+(?:public\.)?\"?(\w+)\"?\s+\((.*?)\)\s+FROM\s+stdin;', re.IGNORECASE)
    process = subprocess.Popen(
        ['pg_restore', '-f', '-', old_dump_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True
    )

    tmp_base_dir = os.environ.get('MIGRATION_TMP_DIR', '/tmp')
    os.makedirs(tmp_base_dir, exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix='migration_tables_', dir=tmp_base_dir)
    table_file_paths = {}
    inserted_tables = []
    inserted_tables_seen = set()
    table_row_counts = defaultdict(int)
    skipped_not_null_counts = defaultdict(int)
    split_dir = os.environ.get('MIGRATION_SPLIT_DIR', '').strip()
    order_file = os.environ.get('MIGRATION_ORDER_FILE', '').strip()
    skip_combined_dump = os.environ.get('MIGRATION_SKIP_COMBINED_DUMP', '0').strip().lower() in {'1', 'true', 'yes'}

    def get_table_file_path(table_name):
        path = table_file_paths.get(table_name)
        if not path:
            path = os.path.join(temp_dir, f'{table_name}.sql')
            table_file_paths[table_name] = path
        return path

    def append_table_sql(table_name, sql_line):
        path = get_table_file_path(table_name)
        with open(path, 'a', encoding='utf-8') as tf:
            tf.write(sql_line)

    try:
        in_copy = False
        current_table = None
        current_cols = []
        mapped_cols = []
        pending_values = []

        def flush_pending():
            nonlocal pending_values
            if not pending_values or not current_table or not mapped_cols:
                return
            final_cols_quoted = ", ".join(f'"{col}"' for col, _ in mapped_cols)
            append_table_sql(
                current_table,
                f"INSERT INTO public.{current_table} ({final_cols_quoted}) VALUES {', '.join(pending_values)} ON CONFLICT DO NOTHING;\n"
            )
            pending_values = []

        for raw_line in process.stdout:
            line = raw_line.rstrip('\n\r')
            m = re_copy.search(line)
            if m:
                flush_pending()
                tbl = m.group(1)
                cols = [c.strip().strip('"') for c in m.group(2).split(',')]
                if table_is_included(tbl, new_schema_def):
                    in_copy = True
                    current_table = tbl
                    current_cols = cols
                    mapped_cols = [(col, new_schema_def[tbl].get(col, '')) for col in current_cols if col in new_schema_def[tbl]]
                    if current_table == 'users':
                        extra_users_cols = [
                            'email', 'password_hash', 'first_name', 'last_name',
                            'is_admin', 'is_active', 'is_external', 'is_trial',
                            'role', 'specialty', 'created_at', 'updated_at'
                        ]
                        mapped_names = {name for name, _ in mapped_cols}
                        for extra_col in extra_users_cols:
                            if extra_col in new_schema_def[tbl] and extra_col not in mapped_names:
                                mapped_cols.append((extra_col, new_schema_def[tbl].get(extra_col, '')))
                    if current_table == 'teams':
                        # Legacy dumps may miss mandatory target columns.
                        extra_team_cols = ['team_type', 'is_active']
                        mapped_names = {name for name, _ in mapped_cols}
                        for extra_col in extra_team_cols:
                            if extra_col in new_schema_def[tbl] and extra_col not in mapped_names:
                                mapped_cols.append((extra_col, new_schema_def[tbl].get(extra_col, '')))
                    if current_table == 'sales_form_links':
                        # Legacy dumps may miss mandatory target columns.
                        mapped_names = {name for name, _ in mapped_cols}
                        if 'check_number' not in mapped_names:
                            mapped_cols.append(
                                ('check_number', new_schema_def[tbl].get('check_number', 'integer'))
                            )
                        if 'unique_code' not in mapped_names:
                            mapped_cols.append(
                                ('unique_code', new_schema_def[tbl].get('unique_code', 'character varying(255) NOT NULL'))
                            )
                    if current_table not in inserted_tables_seen:
                        inserted_tables_seen.add(current_table)
                        inserted_tables.append(current_table)
                else:
                    in_copy = True
                    current_table = None
                    current_cols = []
                    mapped_cols = []
                continue

            if not in_copy:
                continue

            if line == r'\.':
                flush_pending()
                in_copy = False
                current_table = None
                current_cols = []
                mapped_cols = []
                continue

            if not current_table or not mapped_cols:
                continue

            row_values = [unescape_copy(v) for v in line.split('\t')]
            if len(row_values) != len(current_cols):
                continue
            row = dict(zip(current_cols, row_values))
            sql_values = []
            not_null_violation_col = None
            for col, col_type in mapped_cols:
                if current_table == 'users' and col not in row:
                    val = derived_user_value(col, row)
                else:
                    val = row.get(col)
                val = sanitize_for_column(val, col_type, enum_defs)
                val = apply_default_value(current_table, col, val, row)
                if val is None and 'not null' in str(col_type or '').lower():
                    not_null_violation_col = col
                    break
                sql_values.append(to_sql_value(val, col_type))
            if not_null_violation_col:
                key = f"{current_table}.{not_null_violation_col}"
                skipped_not_null_counts[key] += 1
                if skipped_not_null_counts[key] <= 5:
                    row_id = row.get('id') or row.get('cliente_id') or '?'
                    print(
                        f"[migration][prepare][skip] table={current_table} "
                        f"column={not_null_violation_col} reason=not_null row_id={row_id}"
                    )
                continue
            pending_values.append(f"({', '.join(sql_values)})")
            table_row_counts[current_table] += 1
            if len(pending_values) >= insert_batch_size:
                flush_pending()

        flush_pending()
        process.wait()

        ordered_tables = order_tables_by_fk(inserted_tables, fk_deps)
        ordered_tables = enforce_table_precedence(
            ordered_tables,
            [
                ('sales_leads', 'sales_form_links'),
                ('sales_leads', 'lead_activity_logs'),
                ('sales_leads', 'lead_payments'),
                ('sales_form_links', 'lead_activity_logs'),
                ('sales_form_links', 'lead_payments'),
            ],
        )
        order_debug_tables = ['sales_form_links', 'sales_leads', 'lead_activity_logs', 'lead_payments']
        order_debug = []
        for name in order_debug_tables:
            if name in ordered_tables:
                order_debug.append(f"{name}={ordered_tables.index(name) + 1}")
        if order_debug:
            print(f"[migration][prepare][order-check] {' '.join(order_debug)}")
        if skip_combined_dump:
            # Keep OUTPUT_FILE contract for callers, without materializing a huge merged dump.
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write("-- combined dump disabled (MIGRATION_SKIP_COMBINED_DUMP=1)\n")
        else:
            with open(output_path, 'w', encoding='utf-8') as outfile:
                outfile.write("SET search_path TO public;\n")
                if tables_in_dump:
                    truncate_tables = ", ".join(f"public.{t}" for t in tables_in_dump)
                    outfile.write(f"TRUNCATE TABLE {truncate_tables} CASCADE;\n")
                for table in ordered_tables:
                    table_path = table_file_paths.get(table)
                    if not table_path or not os.path.exists(table_path):
                        continue
                    with open(table_path, 'r', encoding='utf-8') as tf:
                        for line in tf:
                            outfile.write(line)
                outfile.write(generate_admin_user_sql())
                write_sequences_block(outfile, ordered_tables)

        if split_dir:
            os.makedirs(split_dir, exist_ok=True)
            for old_sql in glob.glob(os.path.join(split_dir, '*.sql')):
                try:
                    os.remove(old_sql)
                except OSError:
                    pass
            order_path = order_file or os.path.join(split_dir, 'order.tsv')
            with open(order_path, 'w', encoding='utf-8') as of:
                of.write("idx\ttable\tsource_rows\tfile\n")
                for idx, table in enumerate(ordered_tables, start=1):
                    src = table_file_paths.get(table)
                    if not src or not os.path.exists(src):
                        continue
                    dst = os.path.join(split_dir, f"{idx:04d}_{table}.sql")
                    shutil.move(src, dst)
                    of.write(f"{idx}\t{table}\t{table_row_counts.get(table, 0)}\t{dst}\n")

        progress_file = os.environ.get('MIGRATION_PROGRESS_FILE', '')
        if progress_file:
            os.makedirs(os.path.dirname(progress_file), exist_ok=True)
            with open(progress_file, 'w', encoding='utf-8') as pf:
                pf.write("table\tsource_rows\n")
                for table in ordered_tables:
                    pf.write(f"{table}\t{table_row_counts.get(table, 0)}\n")

        total_rows = sum(table_row_counts.values())
        print(f"[migration][prepare] tables={len(ordered_tables)} source_rows={total_rows}")
        if split_dir:
            print(f"[migration][prepare] split_dir={split_dir} order_file={order_file or os.path.join(split_dir, 'order.tsv')}")
        for table in ordered_tables:
            print(f"[migration][prepare][table] name={table} source_rows={table_row_counts.get(table, 0)}")
        for key, count in sorted(skipped_not_null_counts.items()):
            if count > 0:
                print(f"[migration][prepare][skip-summary] key={key} skipped_rows={count}")
    finally:
        for path in table_file_paths.values():
            try:
                os.remove(path)
            except OSError:
                pass
        try:
            os.rmdir(temp_dir)
        except OSError:
            pass

def generate_migrated_dump(new_schema_path, old_dump_path, output_path, new_schema_def, enum_defs, fk_deps):
    print("\nGENERATING MIGRATION DUMP...")
    if not new_schema_def:
        print("CRITICAL ERROR: No tables found in schema.")
        sys.exit(1)

    if not STRICT_ORGANIGRAM:
        db_fk_deps = load_fk_dependencies_from_db()
        effective_fk_deps = db_fk_deps if db_fk_deps else fk_deps
        effective_fk_deps = apply_manual_fk_dependencies(effective_fk_deps)
        generate_migrated_dump_streaming(old_dump_path, output_path, new_schema_def, enum_defs, effective_fk_deps)
        return

    table_data = OrderedDict()
    process = subprocess.Popen(['pg_restore', '-f', '-', old_dump_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    current_table = None
    current_cols = []
    for line in process.stdout:
        line = line.rstrip('\n\r')
        match_copy = re.search(r'COPY (?:public\.)?\"?(\w+)\"? \((.*?)\) FROM stdin;', line, re.IGNORECASE)
        if match_copy:
            current_table = match_copy.group(1)
            if not table_is_included(current_table, new_schema_def):
                current_table = None
                continue
            current_cols = [c.strip().strip('"') for c in match_copy.group(2).split(',')]
            table_data[current_table] = []
            continue
        if line == r'\.':
            current_table = None
            continue
        if current_table:
            row_values = [unescape_copy(v) for v in line.split('\t')]
            if len(row_values) == len(current_cols):
                table_data[current_table].append(dict(zip(current_cols, row_values)))

    filtered_users = []
    name_to_id = {}
    clinical_specialties = {'nutrizione', 'nutrizionista', 'psicologia', 'psicologo', 'coach'}
    for u in table_data.get('users', []):
        first = (u.get('first_name') or '').strip()
        last = (u.get('last_name') or '').strip()
        email = (u.get('email') or '').strip()
        if not email:
            continue
        raw_specialty = str(u.get('specialty') or '').strip().lower()
        normalized_specialty = normalize_user_specialty(raw_specialty)
        normalized_role = normalize_user_role(u.get('role'))
        is_professional_role = normalized_role in {'professionista', 'team_leader'}
        is_professional_by_specialty = (raw_specialty in clinical_specialties) and normalized_role != 'admin'
        is_professional_user = is_professional_role or is_professional_by_specialty
        spec, role = (None, None)
        if STRICT_ORGANIGRAM:
            spec, role = get_professional_info(first, last)
            # Keep all non-professional users; for professionals keep only official organigram.
            if is_professional_user and not (spec or role):
                continue

        if spec:
            u['specialty'] = spec
        elif normalized_specialty:
            u['specialty'] = normalized_specialty
        else:
            u['specialty'] = None

        if role:
            u['role'] = role
            u['is_admin'] = False
        elif normalized_role:
            u['role'] = normalized_role

        u['is_admin'] = normalize_bool(u.get('is_admin'), default=False)
        u['is_active'] = normalize_bool(u.get('is_active'), default=True)
        u['is_external'] = normalize_bool(u.get('is_external'), default=False)
        u['is_trial'] = normalize_bool(u.get('is_trial'), default=False)

        if u['is_admin']:
            u['role'] = 'admin'
        if not u.get('role'):
            if u['is_admin']:
                u['role'] = 'admin'
            elif u['is_external']:
                u['role'] = 'team_esterno'
            elif u.get('specialty') in clinical_specialties:
                u['role'] = 'professionista'
            else:
                continue
        if u['role'] in {'professionista', 'team_leader'} and not u.get('specialty'):
            continue
        if u['role'] not in ALLOWED_USER_ROLES:
            continue
        if not u.get('first_name'):
            u['first_name'] = 'Utente'
        if not u.get('last_name'):
            u['last_name'] = 'Sconosciuto'
        if not u.get('password_hash'):
            u['password_hash'] = DEFAULT_IMPORTED_PASSWORD_HASH

        filtered_users.append(u)
        if u.get('id'):
            name_to_id[f"{first} {last}".strip().lower()] = u.get('id')
            
    table_data['users'] = filtered_users
    allowed_user_ids = {str(u.get('id')) for u in filtered_users if u.get('id') is not None}

    # Sanitize FK to users for migrated tables so inserts do not fail when users
    # outside official organigram have been removed.
    for d in table_data.get('departments', []):
        if d.get('head_id') is not None and str(d.get('head_id')) not in allowed_user_ids:
            d['head_id'] = None

    for t in table_data.get('teams', []):
        if t.get('head_id') is not None and str(t.get('head_id')) not in allowed_user_ids:
            t['head_id'] = None

    for o in table_data.get('origins', []):
        if o.get('influencer_id') is not None and str(o.get('influencer_id')) not in allowed_user_ids:
            o['influencer_id'] = None

    clienti_user_fk_cols = [
        'nutrizionista_id', 'coach_id', 'psicologa_id', 'health_manager_id',
        'consulente_alimentare_id', 'assigned_service_rep', 'created_by',
        'payment_verified_by', 'evaluated_by_user_id', 'frozen_by_id', 'unfrozen_by_id'
    ]
    for c in table_data.get('clienti', []):
        for col in clienti_user_fk_cols:
            if c.get(col) is not None and str(c.get(col)) not in allowed_user_ids:
                c[col] = None

    check_user_fk_cols_by_table = {
        'weekly_checks': ['assigned_by_id', 'deactivated_by_id'],
        'weekly_check_link_assignments': ['assigned_to_user_id'],
        'dca_checks': ['assigned_by_id', 'deactivated_by_id'],
        'minor_checks': ['assigned_by_id', 'deactivated_by_id'],
        'client_check_assignments': ['assigned_by_id'],
    }
    for table_name, fk_cols in check_user_fk_cols_by_table.items():
        for row in table_data.get(table_name, []):
            for col in fk_cols:
                if row.get(col) is not None and str(row.get(col)) not in allowed_user_ids:
                    row[col] = None

    if STRICT_ORGANIGRAM:
        # Build official teams as source of truth to avoid stale/swapped teams from legacy dumps.
        # Keep legacy department_id when possible.
        legacy_team_by_id = {
            str(t.get('id')).strip(): t
            for t in table_data.get('teams', [])
            if t.get('id') is not None
        }
        table_data['teams'] = []
        for team_id, team in OFFICIAL_TEAMS.items():
            legacy_team = legacy_team_by_id.get(team_id, {})
            leader_id = name_to_id.get(team['leader'].lower())
            table_data['teams'].append({
                'id': int(team_id),
                'name': team['name'],
                'team_type': team['team_type'],
                'head_id': leader_id,
                'department_id': legacy_team.get('department_id'),
                'is_active': True,
                'description': legacy_team.get('description') or team['name'],
                'created_at': legacy_team.get('created_at') or datetime.now().isoformat(),
                'updated_at': legacy_team.get('updated_at') or datetime.now().isoformat(),
            })

        # Rebuild team_members from official organigram and include leaders as team members.
        team_members = []
        seen_memberships = set()
        for team_id, team in OFFICIAL_TEAMS.items():
            person_names = [team['leader']] + list(team['members'])
            for person_name in person_names:
                found_id = name_to_id.get(person_name.lower())
                if not found_id:
                    continue
                membership_key = (int(team_id), str(found_id))
                if membership_key in seen_memberships:
                    continue
                seen_memberships.add(membership_key)
                team_members.append({
                    'team_id': int(team_id),
                    'user_id': found_id,
                    'joined_at': datetime.now().isoformat(),
                })
        table_data['team_members'] = team_members

    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write("SET search_path TO public;\n")
        tables_with_data = [t for t, rows in table_data.items() if rows]
        if tables_with_data:
            truncate_tables = ", ".join(f"public.{t}" for t in tables_with_data)
            outfile.write(f"TRUNCATE TABLE {truncate_tables} CASCADE;\n")

        insert_batch_size = int(os.environ.get('MIGRATION_INSERT_BATCH_SIZE', '1'))
        if insert_batch_size < 1:
            insert_batch_size = 1

        all_tables = [t for t in TABLE_PRIORITY if t in table_data] + [t for t in table_data if t not in TABLE_PRIORITY]
        seen = set()
        inserted_tables = []
        for table in all_tables:
            if table in seen or table not in table_data: continue
            seen.add(table)
            rows = table_data[table]
            if not rows: continue
            inserted_tables.append(table)
            
            source_cols = [c for c in rows[0].keys() if c in new_schema_def[table]]
            if table == 'sales_form_links' and 'check_number' not in source_cols:
                source_cols.append('check_number')
            if table == 'sales_form_links' and 'unique_code' not in source_cols:
                source_cols.append('unique_code')
            if not source_cols:
                continue
            
            for i in range(0, len(rows), insert_batch_size):
                batch = rows[i:i+insert_batch_size]
                batch_vals = []
                for row in batch:
                    row_vals = []
                    for col in source_cols:
                        col_type = new_schema_def[table].get(col, '')
                        val = sanitize_for_column(row.get(col), col_type, enum_defs)
                        val = apply_default_value(table, col, val, row)
                        row_vals.append(to_sql_value(val, col_type))
                    batch_vals.append(f"({', '.join(row_vals)})")
                
                final_cols_quoted = ', '.join(f'"{c}"' for c in source_cols)
                
                outfile.write(f"INSERT INTO public.{table} ({final_cols_quoted}) VALUES {', '.join(batch_vals)} ON CONFLICT DO NOTHING;\n")
        
        outfile.write(generate_admin_user_sql())
        if inserted_tables:
            inserted_tables_sql = ", ".join(f"'{t}'" for t in inserted_tables)
            outfile.write(
                "DO $$\n"
                "DECLARE r RECORD;\n"
                "DECLARE max_id BIGINT;\n"
                "BEGIN\n"
                "  FOR r IN\n"
                "    SELECT c.table_name, c.column_name,\n"
                "           pg_get_serial_sequence(format('%I.%I', c.table_schema, c.table_name), c.column_name) AS seq_name\n"
                "    FROM information_schema.columns c\n"
                "    WHERE c.table_schema = 'public'\n"
                f"      AND c.table_name IN ({inserted_tables_sql})\n"
                "      AND c.column_default LIKE 'nextval(%'\n"
                "  LOOP\n"
                "    IF r.seq_name IS NOT NULL THEN\n"
                "      EXECUTE format('SELECT COALESCE(MAX(%I), 0) FROM %I.%I', r.column_name, 'public', r.table_name) INTO max_id;\n"
                "      EXECUTE format('SELECT setval(%L, GREATEST(%s, 1), true)', r.seq_name, max_id);\n"
                "    END IF;\n"
                "  END LOOP;\n"
                "END$$;\n"
            )

if __name__ == "__main__":
    NEW_SUITE_BACKUP = os.environ.get('NEW_SUITE_BACKUP', 'new_schema.sql')
    OLD_SUITE_BACKUP = os.environ.get('OLD_SUITE_BACKUP', 'old_suite.dump')
    OUTPUT_FILE = os.environ.get('OUTPUT_FILE', 'migrated_db.sql')
    NEW_SUITE_BACKUP = refresh_new_schema_backup(NEW_SUITE_BACKUP)
    schema_def, enum_defs, fk_deps = parse_sql_dump(NEW_SUITE_BACKUP)
    generate_migrated_dump(NEW_SUITE_BACKUP, OLD_SUITE_BACKUP, OUTPUT_FILE, schema_def, enum_defs, fk_deps)
