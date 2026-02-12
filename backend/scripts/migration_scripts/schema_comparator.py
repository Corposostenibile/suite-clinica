import re
import os
import sys
import subprocess
import tempfile
from collections import OrderedDict
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

    # Boost common roots first when possible.
    preferred_roots = ['users', 'departments', 'teams', 'team_members', 'clienti']
    queue = [t for t in preferred_roots if t in indegree and indegree[t] == 0]
    for t in sorted(tables):
        if indegree[t] == 0 and t not in queue:
            queue.append(t)

    ordered = []
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


def sanitize_for_column(raw_value, col_type, enum_defs):
    if raw_value is None:
        return None
    col_type_norm = str(col_type or '').strip().lower()
    val = str(raw_value)
    if val == '':
        if any(k in col_type_norm for k in ('int', 'numeric', 'decimal', 'double precision', 'real', 'date', 'time')):
            return None
    enum_values = enum_defs.get(col_type_norm)
    if enum_values:
        low = val.strip().lower().replace('-', '_').replace(' ', '_')
        alias_map = ENUM_ALIASES.get(col_type_norm, {})
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
    return val

def apply_default_value(table, col, value, row):
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
            for col, col_type in mapped_cols:
                val = sanitize_for_column(row.get(col), col_type, enum_defs)
                val = apply_default_value(current_table, col, val, row)
                sql_values.append(to_sql_value(val, col_type))
            pending_values.append(f"({', '.join(sql_values)})")
            if len(pending_values) >= insert_batch_size:
                flush_pending()

        flush_pending()
        process.wait()

        ordered_tables = order_tables_by_fk(inserted_tables, fk_deps)
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
        generate_migrated_dump_streaming(old_dump_path, output_path, new_schema_def, enum_defs, fk_deps)
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
                u['role'] = 'influencer'
        if u['role'] not in ALLOWED_USER_ROLES:
            u['role'] = 'professionista'
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
                        if table == 'teams' and col == 'team_type' and val is None:
                            team_id = str(row.get('id', '')).strip()
                            val = TEAM_TYPE_BY_ID.get(team_id, 'nutrizione')
                        if table == 'teams' and col == 'is_active' and val is None:
                            val = True
                        if table == 'users' and col == 'is_trial' and val is None:
                            val = False
                        if table == 'users' and col in {'created_at', 'updated_at'} and val is None:
                            val = datetime.now().isoformat()
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
    schema_def, enum_defs, fk_deps = parse_sql_dump(NEW_SUITE_BACKUP)
    generate_migrated_dump(NEW_SUITE_BACKUP, OLD_SUITE_BACKUP, OUTPUT_FILE, schema_def, enum_defs, fk_deps)
