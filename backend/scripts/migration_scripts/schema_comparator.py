import re
import os
import sys
import subprocess
from collections import OrderedDict
from datetime import datetime
from werkzeug.security import generate_password_hash

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
    for u in table_data.get('users', []):
        first, last, email = u.get('first_name', ''), u.get('last_name', ''), u.get('email', '')
        is_old_admin = u.get('is_admin') == 't'
        spec, role = get_professional_info(first, last)
        # Keep all users to preserve FK consistency for clienti/departments.
        if spec:
            u['specialty'] = spec
        if role:
            u['role'] = role
        elif not u.get('role'):
            u['role'] = 'admin' if is_old_admin else 'professionista'
        u['is_admin'] = is_old_admin or u.get('role') == 'admin'
        if u.get('is_external') is None:
            u['is_external'] = False
        filtered_users.append(u)
        if u.get('id'):
            name_to_id[f"{first} {last}".strip().lower()] = u.get('id')
            
    table_data['users'] = filtered_users

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
