import re
import os
import sys
import subprocess
from collections import OrderedDict
from datetime import datetime
from werkzeug.security import generate_password_hash

DEFAULT_IMPORTED_PASSWORD_HASH = generate_password_hash("Dev123?")

# =============================================================================
# ORGANIGRAMMA UFFICIALE 2026
# =============================================================================
OFFICIAL_ORGANIGRAMMA = {
    'nutrizione': {
        'team_leaders': ['Filippo Feliciani', 'Isabella Rossi', 'Alice Posenato'],
        'teams': {
            '1': ['Alessandra Arcoleo', 'Caterina Esposito', 'Chiara Giombolini', 'Elisa Menichelli', 'Federica Cutolo', 'Giorgia Leone', 'Giorgia Santi', 'Jessica Di Colli', 'Maria Vittoria Sallicano', 'Marilena Franco', 'Marta Buccilli', 'Martina Mantovani', 'Michela Pagnani', 'Sara Goffi', 'Valeria Loliva'],
            '2': ['Alice Aresti', 'Alice Surbone', 'Florinda Masciello', 'Francesca Abatini', 'Gianluca Marino', 'Gianna Sannelli', 'Isabella Venticinque', 'Mara Adreola', 'Marisa Piras', 'Martina Roberti', 'Nicola Fassetta', 'Nicolò Lorenzo Marinelli', 'Rossana Picerno', 'Silvia Testoni', 'Virginia Vitelli'],
            '3': ['Andrea Tuacris', 'Bianca Balzarini', 'Caterina Scarano', 'Chiara D\'Addesa', 'Elisa Mancini', 'Francesca Ceppetelli', 'Francesca Tornese', 'Giammarco Lamanda', 'Rossella Cariglia', 'Sabine Ardiccioni', 'Silvia Maria Scoletta', 'Valentina Botondi'],
            '4': ['Carlotta Sed', 'Francesca Valentini', 'Gaia Sala', 'Marta Bendusi', 'Noemi Di Natale', 'Virginia Bonazzi']
        }
    },
    'psicologia': {
        'team_leaders': ['Delia De Santis', 'Francesca Zaccaro'],
        'teams': {
            '5': ['Alice Lampone', 'Angela Velletri', 'Claudia Milione', 'Giorgia Del Bianco', 'Martina Calvi', 'Martina Loccisano'],
            '6': ['Angel Disney Armenise', 'Aurora Valente', 'Barbara Visalli', 'Denise Caravano', 'Germana Morganti', 'Manny Aiello']
        }
    },
    'coach': {
        'team_leaders': ['Lorenzo Sambri'],
        'teams': {
            '7': ['Alessandra Di Lisciandro', 'Angbonon Ange Olivier Bile', 'Angelo Lacorte', 'Claudio Lopiano', 'Danilo Bonifati', 'Federico De Bene', 'Francesco Falcone', 'Giovanna Pirina', 'Giuseppe Summa', 'Ilaria Galesi', 'Marco Fratini', 'Matteo Test User', 'Nino Helera', 'Rebecca Masseroni', 'Ruggiero Balzano', 'Sara Paganotto', 'Valentina Carisio']
        }
    }
}

def get_professional_info(first_name, last_name):
    full_name = f"{first_name} {last_name}".strip().lower()
    for specialty, data in OFFICIAL_ORGANIGRAMMA.items():
        if any(tl.lower() == full_name for tl in data['team_leaders']):
            spec_map = {'nutrizione': 'nutrizionista', 'psicologia': 'psicologo', 'coach': 'coach'}
            return spec_map[specialty], 'team_leader'
        for team_id, members in data['teams'].items():
            if any(m.lower() == full_name for m in members):
                spec_map = {'nutrizione': 'nutrizionista', 'psicologia': 'psicologo', 'coach': 'coach'}
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
    return schema

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

TABLE_PRIORITY = ['users', 'departments', 'teams', 'team_members', 'origins', 'clienti']
MIGRATION_TABLES = set(TABLE_PRIORITY)
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

def generate_migrated_dump(new_schema_path, old_dump_path, output_path, new_schema_def):
    print("\nGENERATING MIGRATION DUMP...")
    if not new_schema_def:
        print("CRITICAL ERROR: No tables found in schema.")
        sys.exit(1)
        
    table_data = OrderedDict()
    process = subprocess.Popen(['pg_restore', '-f', '-', old_dump_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    current_table = None
    current_cols = []
    for line in process.stdout:
        line = line.rstrip('\n\r')
        match_copy = re.search(r'COPY (?:public\.)?\"?(\w+)\"? \((.*?)\) FROM stdin;', line, re.IGNORECASE)
        if match_copy:
            current_table = match_copy.group(1)
            # Keep memory bounded: process only tables needed for this migration.
            if current_table not in new_schema_def or current_table not in MIGRATION_TABLES:
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

    existing_team_ids = {
        str(t.get('id')).strip()
        for t in table_data.get('teams', [])
        if t.get('id') is not None
    }
    table_data['team_members'] = table_data.get('team_members', [])
    for spec, data in OFFICIAL_ORGANIGRAMMA.items():
        for t_id, members in data['teams'].items():
            for m in members:
                found_id = name_to_id.get(m.lower())
                if found_id and str(t_id) in existing_team_ids:
                    table_data['team_members'].append({'team_id': t_id, 'user_id': found_id, 'joined_at': datetime.now().isoformat()})

    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write("SET search_path TO public;\n")
        outfile.write("TRUNCATE TABLE public.users CASCADE;\n")
        outfile.write("TRUNCATE TABLE public.team_members CASCADE;\n")
        
        all_tables = [t for t in TABLE_PRIORITY if t in table_data] + [t for t in table_data if t not in TABLE_PRIORITY]
        seen = set()
        for table in all_tables:
            if table in seen or table not in table_data: continue
            seen.add(table)
            rows = table_data[table]
            if not rows: continue
            
            valid_new_cols = list(new_schema_def[table].keys())
            if table == 'clienti':
                pk = 'cliente_id'
            elif table == 'team_members':
                pk = 'team_id, user_id'
            else:
                pk = 'id'
            
            for i in range(0, len(rows), 500):
                batch = rows[i:i+500]
                batch_vals = []
                for row in batch:
                    row_vals = []
                    for col in valid_new_cols:
                        col_type = new_schema_def[table].get(col, '')
                        val = row.get(col)
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
                
                final_cols_quoted = ', '.join(f'"{c}"' for c in valid_new_cols)
                
                outfile.write(f"INSERT INTO public.{table} ({final_cols_quoted}) VALUES {', '.join(batch_vals)} ON CONFLICT ({pk}) DO NOTHING;\n")
        
        outfile.write(generate_admin_user_sql())
        for table in ['users', 'departments', 'teams', 'clienti']:
            id_col = 'cliente_id' if table == 'clienti' else 'id'
            outfile.write(f"SELECT setval(pg_get_serial_sequence('\"{table}\"', '{id_col}'), coalesce(max({id_col}), 1)) FROM \"{table}\" WHERE EXISTS (SELECT 1 FROM \"{table}\");\n")

if __name__ == "__main__":
    NEW_SUITE_BACKUP = os.environ.get('NEW_SUITE_BACKUP', 'new_schema.sql')
    OLD_SUITE_BACKUP = os.environ.get('OLD_SUITE_BACKUP', 'old_suite.dump')
    OUTPUT_FILE = os.environ.get('OUTPUT_FILE', 'migrated_db.sql')
    schema_def = parse_sql_dump(NEW_SUITE_BACKUP)
    generate_migrated_dump(NEW_SUITE_BACKUP, OLD_SUITE_BACKUP, OUTPUT_FILE, schema_def)
