import re
import os
import sys
import subprocess
from collections import OrderedDict
from datetime import datetime

def parse_sql_dump(file_path):
    """Parses a PostgreSQL dump file to extract table definitions and their columns."""
    schema = {}
    current_table = None
    print(f"Parsing {file_path}...")
    
    def get_lines(path):
        if path.endswith('.dump'):
            process = subprocess.Popen(['pg_restore', '-f', '-', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if process.stdout:
                for line in process.stdout: yield line
        else:
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f: yield line
            except UnicodeDecodeError:
                with open(path, 'r', encoding='latin-1') as f:
                    for line in f: yield line

    try:
        for line in get_lines(file_path):
            line = line.strip()
            match_table = re.match(r'CREATE TABLE public\.(\w+) \(', line)
            if match_table:
                current_table = match_table.group(1)
                schema[current_table] = {}
                continue
            if line.startswith(');') and current_table:
                current_table = None
                continue
            if current_table:
                if any(line.upper().startswith(x) for x in ['CONSTRAINT', 'PRIMARY KEY', 'FOREIGN KEY', 'CHECK', 'UNIQUE', ')']):
                    continue
                line_clean = line.rstrip(',')
                parts = line_clean.split(maxsplit=1)
                if len(parts) >= 2:
                    col_name = parts[0].strip('"')
                    col_type = parts[1]
                    schema[current_table][col_name] = col_type
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return {}
    return schema

def unescape_copy(val):
    if val == r'\N' or val is None: return None
    return val.replace(r'\n', '\n').replace(r'\r', '\r').replace(r'\t', '\t').replace(r'\\', '\\')

def to_sql_value(val, col_type=''):
    if val is None: return 'NULL'
    val = str(val).replace("'", "''")
    if col_type and 'json' in col_type.lower():
        val = val.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    return f"'{val}'"

# Rigorous order to respect Foreign Keys
TABLE_PRIORITY = [
    'users', 'departments', 'teams', 'team_members', 'origins', 'finance_packages', 
    'ghl_opportunities', 'clienti', 'clienti_version', 'cartelle_cliniche', 
    'service_cliente_assignments', 'anonymous_surveys', 'anonymous_survey_responses',
    'check_forms', 'check_form_fields',
    'recruiting_kanbans', 'kanban_stages', 'job_offers', 'job_questions', 
    'job_applications', 'application_answers', 'application_stage_history',
    'it_projects', 'it_projects_version', 'it_project_members', 'it_project_members_version',
    'weekly_checks', 'weekly_check_responses', 
    'dca_checks', 'dca_check_responses', 'respond_io_users', 
    'respond_io_calendar_events', 'respond_io_calendar_breaks', 
    'respond_io_work_timestamps', 'respond_io_daily_metrics', 'allegati'
]

def generate_migrated_dump(new_schema_path, old_dump_path, output_path, new_schema_def):
    print("\n" + "="*50 + "\nGENERATING AUTOMATED MIGRATION DUMP\n" + "="*50)
    
    table_data = OrderedDict()
    
    # 1. Extraction from old dump
    process = subprocess.Popen(['pg_restore', '-f', '-', old_dump_path], stdout=subprocess.PIPE, text=True)
    current_table = None
    current_cols = []
    
    print("Extracting data from Old Suite...")
    for line in process.stdout:
        line = line.rstrip('\n\r')
        match_copy = re.match(r'COPY public\.(\w+) \((.*?)\) FROM stdin;', line)
        if match_copy:
            current_table = match_copy.group(1)
            raw_cols = match_copy.group(2)
            current_cols = [c.strip().strip('"') for c in raw_cols.split(',')]
            if current_table not in new_schema_def or current_table in ['activity_log', 'global_activity_log']:
                current_table = None
                continue
            table_data[current_table] = []
            continue
        
        if line == r'\.':
            current_table = None
            continue
            
        if current_table:
            row_values = [unescape_copy(v) for v in line.split('\t')]
            if len(row_values) == len(current_cols):
                table_data[current_table].append(dict(zip(current_cols, row_values)))

    # Artificial team members generation if missing
    if 'team_members' not in table_data and 'users' in table_data:
        print("Generating team associations from provided ORGANIGRAMMA...")
        table_data['team_members'] = []
        
        # Helper to find user ID by name
        def find_user(first, last):
            for u in table_data['users']:
                if u.get('first_name', '').strip().lower() == first.lower() and \
                   u.get('last_name', '').strip().lower() == last.lower():
                    return u.get('id')
            return None

        # Hardcoded mapping based on user input
        organigramma = {
            '1': [ # Nutrizione Team 1
                ('Filippo', 'Feliciani'), ('Alessandra', 'Arcoleo'), ('Caterina', 'Esposito'), 
                ('Chiara', 'Giombolini'), ('Elisa', 'Menichelli'), ('Federica', 'Cutolo'), 
                ('Giorgia', 'Leone'), ('Giorgia', 'Santi'), ('Jessica', 'Di Colli'), 
                ('Maria Vittoria', 'Sallicano'), ('Marilena', 'Franco'), ('Marta', 'Buccilli'), 
                ('Martina', 'Mantovani'), ('Michela', 'Pagnani'), ('Sara', 'Goffi'), ('Valeria', 'Loliva')
            ],
            '2': [ # Nutrizione Team 2
                ('Isabella', 'Rossi'), ('Alice', 'Aresti'), ('Alice', 'Surbone'), 
                ('Florinda', 'Masciello'), ('Francesca', 'Abatini'), ('Gianluca', 'Marino'), 
                ('Gianna', 'Sannelli'), ('Isabella', 'Venticinque'), ('Mara', 'Adreola'), 
                ('Marisa', 'Piras'), ('Martina', 'Roberti'), ('Nicola', 'Fassetta'), 
                ('Nicolò Lorenzo', 'Marinelli'), ('Rossana', 'Picerno'), ('Silvia', 'Testoni'), 
                ('Virginia', 'Vitelli')
            ],
            '3': [ # Nutrizione Team 3
                ('Alice', 'Posenato'), ('Andrea', 'Tuacris'), ('Bianca', 'Balzarini'), 
                ('Caterina', 'Scarano'), ('Chiara', 'D\'Addesa'), ('Elisa', 'Mancini'), 
                ('Francesca', 'Ceppetelli'), ('Francesca', 'Tornese'), ('Giammarco', 'Lamanda'), 
                ('Rossella', 'Cariglia'), ('Sabine', 'Ardiccioni'), ('Silvia Maria', 'Scoletta'), 
                ('Valentina', 'Botondi')
            ],
            '4': [ # Nutrizione Team 4
                ('Alice', 'Posenato'), ('Carlotta', 'Sed'), ('Francesca', 'Valentini'), 
                ('Gaia', 'Sala'), ('Marta', 'Bendusi'), ('Noemi', 'Di Natale'), ('Virginia', 'Bonazzi')
            ],
            '5': [ # Psicologia Team 1
                ('Delia', 'De Santis'), ('Alice', 'Lampone'), ('Angela', 'Velletri'), 
                ('Claudia', 'Milione'), ('Giorgia', 'Del Bianco'), ('Martina', 'Calvi'), 
                ('Martina', 'Loccisano')
            ],
            '6': [ # Psicologia Team 2
                ('Francesca', 'Zaccaro'), ('Angel Disney', 'Armenise'), ('Aurora', 'Valente'), 
                ('Barbara', 'Visalli'), ('Denise', 'Caravano'), ('Germana', 'Morganti'), ('Manny', 'Aiello')
            ]
        }

        found_count = 0
        for t_id, members in organigramma.items():
            for first, last in members:
                u_id = find_user(first, last)
                if u_id:
                    table_data['team_members'].append({
                        'team_id': t_id,
                        'user_id': u_id,
                        'joined_at': datetime.now().isoformat()
                    })
                    found_count += 1
                else:
                    print(f"Warning: Could not find user {first} {last} in database.")
        
        print(f"Successfully mapped {found_count} members to teams based on organigramma.")

    # 2. Ordered writing
    with open(output_path, 'w', encoding='utf-8') as outfile:
        outfile.write("-- AUTOMATED MIGRATION DUMP\n")
        outfile.write("SET search_path TO public;\n")
        # Direct SQL cleanup to ensure no leftovers from previous failed attempts
        outfile.write("TRUNCATE TABLE public.team_members CASCADE;\n\n") 
        
        sorted_tables = [t for t in TABLE_PRIORITY if t in table_data]
        sorted_tables += [t for t in table_data if t not in TABLE_PRIORITY]
        
        for table in sorted_tables:
            rows = table_data[table]
            if not rows: continue
            
            print(f"Transforming table: {table} ({len(rows)} rows)")
            outfile.write(f"\n-- Data for {table}\n")
            
            valid_new_cols = list(new_schema_def[table].keys())
            
            # Determine PK name for this table in NEW schema
            # Strategy: Use ON CONFLICT if a clear PK is found
            pk_name = None
            if table == 'clienti':
                pk_name = 'cliente_id'
            elif 'id' in valid_new_cols and not table.endswith('_version') and table != 'transaction':
                pk_name = 'id'
            
            # Special case for composite PKs we are sure about
            composite_pk = None
            if table == 'clienti_version':
                composite_pk = 'cliente_id, transaction_id'
            elif table == 'it_project_members':
                composite_pk = 'project_id, user_id'
            elif table == 'it_project_members_version':
                composite_pk = 'project_id, user_id, transaction_id'
            elif '_version' in table:
                # Common versioning patterns
                if 'id' in valid_new_cols and 'transaction_id' in valid_new_cols:
                    composite_pk = 'id, transaction_id'
                elif 'cliente_id' in valid_new_cols and 'transaction_id' in valid_new_cols:
                    composite_pk = 'cliente_id, transaction_id'
                elif 'communication_id' in valid_new_cols and 'department_id' in valid_new_cols and 'transaction_id' in valid_new_cols:
                    composite_pk = 'communication_id, department_id, transaction_id'

            # Check if PK column(s) exist in NEW schema
            pk_cols_str = composite_pk if composite_pk else pk_name
            pk_cols = [c.strip() for c in (pk_cols_str.split(',') if pk_cols_str else [])]
            all_pk_present = all(c in valid_new_cols for c in pk_cols) if pk_cols else False

            for i in range(0, len(rows), 500):
                batch = rows[i:i+500]
                batch_vals = []
                
                for row in batch:
                    row_vals = []
                    for col in valid_new_cols:
                        col_type = new_schema_def[table].get(col, '')
                        val = row.get(col)
                        
                        # User role and specialty mapping
                        if table == 'users':
                            if col == 'role':
                                old_is_admin = row.get('is_admin') == 't'
                                old_role = row.get('role')
                                job_title = (row.get('job_title') or '').lower()
                                if old_is_admin: val = 'admin'
                                elif any(x in job_title for x in ['leader', 'head', 'responsabile']): val = 'team_leader'
                                else: val = 'professionista'
                            elif col == 'specialty':
                                dept_id = row.get('department_id')
                                if dept_id in ['2', '24']: val = 'nutrizionista'
                                elif dept_id == '3': val = 'coach'
                                elif dept_id == '4': val = 'psicologo'
                                elif dept_id == '23': val = 'cco'
                                elif dept_id in ['1', '17', '19', '22']: val = 'amministrazione'
                        
                        # Fallback for missing but derivable columns
                        if val is None and table == 'users':
                            if col == 'specialty':
                                dept_id = row.get('department_id')
                                if dept_id in ['2', '24']: val = 'nutrizionista'
                                elif dept_id == '3': val = 'coach'
                                elif dept_id == '4': val = 'psicologo'
                            elif col == 'role':
                                val = 'admin' if row.get('is_admin') == 't' else 'professionista'
                            elif col == 'is_external': val = False
                            elif col == 'is_active': val = True
                            elif col == 'is_admin': val = (row.get('role') == 'admin' or row.get('is_admin') == 't')
                        
                        elif table == 'teams':
                            if col == 'team_type':
                                dept_id = str(row.get('department_id'))
                                if dept_id in ['2', '24']: val = 'nutrizione'
                                elif dept_id == '3': val = 'coach'
                                elif dept_id == '4': val = 'psicologia'
                                else: val = 'nutrizione' # Default safe value
                            elif col == 'is_active':
                                val = True
                        
                        # General boolean defaults for NOT NULL columns
                        if val is None and 'boolean' in col_type.lower():
                            val = False

                        row_vals.append(to_sql_value(val, col_type))
                    
                    batch_vals.append(f"({', '.join(row_vals)})")
                
                if batch_vals:
                    final_cols = [f'"{c}"' for c in valid_new_cols]
                    if table == 'teams' and all_pk_present:
                        update_cols = [f'"{c}" = EXCLUDED."{c}"' for c in valid_new_cols if c != 'id']
                        outfile.write(f"INSERT INTO public.{table} ({', '.join(final_cols)}) VALUES {', '.join(batch_vals)} ON CONFLICT (id) DO UPDATE SET {', '.join(update_cols)};\n")
                    elif composite_pk and all_pk_present:
                        outfile.write(f"INSERT INTO public.{table} ({', '.join(final_cols)}) VALUES {', '.join(batch_vals)} ON CONFLICT ({composite_pk}) DO NOTHING;\n")
                    elif pk_name and all_pk_present:
                        outfile.write(f"INSERT INTO public.{table} ({', '.join(final_cols)}) VALUES {', '.join(batch_vals)} ON CONFLICT ({pk_name}) DO NOTHING;\n")
                    else:
                        outfile.write(f"INSERT INTO public.{table} ({', '.join(final_cols)}) VALUES {', '.join(batch_vals)};\n")

        outfile.write("\n-- Post-migration: Sync ID sequences\n")
        for table in table_data:
            id_col = 'id'
            if table == 'clienti': id_col = 'cliente_id'
            elif table == 'clienti_version': continue # Usually no serial on version tables
            
            if id_col in new_schema_def[table]:
                outfile.write(f"SELECT setval(pg_get_serial_sequence('\"{table}\"', '{id_col}'), coalesce(max({id_col}), 1)) FROM \"{table}\" WHERE EXISTS (SELECT 1 FROM \"{table}\");\n")

    print(f"\nSuccess. Migrated dump ready: {output_path}")

if __name__ == "__main__":
    # Allow overriding paths via environment variables so the script can run inside containers/CI.
    NEW_SUITE_BACKUP = os.environ.get(
        'NEW_SUITE_BACKUP',
        '/home/manu/suite-clinica/backend/backups/new_suite_backups/db_backup_20260202_154552.sql'
    )
    OLD_SUITE_BACKUP = os.environ.get(
        'OLD_SUITE_BACKUP',
        '/home/manu/suite-clinica/backend/backups/old_suite_backups/db_backup_20260205_121004.dump'
    )
    OUTPUT_FILE = os.environ.get(
        'OUTPUT_FILE',
        '/home/manu/suite-clinica/backend/backups/migrated_db.sql'
    )

    new_schema = parse_sql_dump(NEW_SUITE_BACKUP)
    if not new_schema:
        print("New schema parsing failed; aborting migration dump generation.")
        sys.exit(1)
    generate_migrated_dump(NEW_SUITE_BACKUP, OLD_SUITE_BACKUP, OUTPUT_FILE, new_schema)
