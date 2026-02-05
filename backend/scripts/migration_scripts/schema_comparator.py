import re
import os
import sys
import subprocess

def parse_sql_dump(file_path):
    """
    Parses a PostgreSQL dump file to extract table definitions and their columns.
    Returns a dictionary: { 'table_name': { 'column_name': 'column_type' } }
    Supports both plain text SQL files and binary .dump files (via pg_restore).
    """
    schema = {}
    current_table = None
    
    print(f"Parsing {file_path}...")
    
    # helper generator to read lines from file or subprocess
    def get_lines(path):
        if path.endswith('.dump'):
            print(f"Detected binary dump. Using pg_restore to read {path}...")
            # Run pg_restore and output to stdout (which we pipe)
            # We don't verify return code here, relying on output
            process = subprocess.Popen(['pg_restore', '-f', '-', path], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            # Yield lines from stdout
            if process.stdout:
                for line in process.stdout:
                    yield line
            
            # Check for errors after reading
            rc = process.poll()
            if rc and rc != 0:
                print(f"Warning: pg_restore exited with code {rc}")
                if process.stderr:
                    print(process.stderr.read())
        else:
            # Determine encoding - try utf-8 first, fallback to latin-1
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    for line in f:
                        yield line
            except UnicodeDecodeError:
                print("Warning: UTF-8 decode failed, retrying with latin-1...")
                with open(path, 'r', encoding='latin-1') as f:
                    for line in f:
                        yield line

    try:
        for line in get_lines(file_path):
            line = line.strip()
            
            # Detect CREATE TABLE
            # CREATE TABLE public.activity_logs (
            match_table = re.match(r'CREATE TABLE public\.(\w+) \(', line)
            if match_table:
                current_table = match_table.group(1)
                schema[current_table] = {}
                continue
            
            # Detect end of table definition
            if line.startswith(');') and current_table:
                current_table = None
                continue
            
            # Detect Columns inside a table
            if current_table:
                # heuristic regex for column definition
                if (line.upper().startswith('CONSTRAINT') or 
                    line.upper().startswith('PRIMARY KEY') or 
                    line.upper().startswith('FOREIGN KEY') or 
                    line.upper().startswith('CHECK') or
                    line.upper().startswith('UNIQUE') or 
                    line.startswith(')')):
                    continue

                line_clean = line.rstrip(',')
                parts = line_clean.split(maxsplit=1)
                if len(parts) >= 2:
                    col_name = parts[0]
                    col_name = col_name.strip('"')
                    col_type = parts[1]
                    schema[current_table][col_name] = col_type

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        import traceback
        traceback.print_exc()
        return {}

    return schema

def compare_schemas(old_schema, new_schema):
    """
    Compares two schemas and returns a diff report.
    """
    diff = {
        'tables_only_in_old': [],
        'tables_only_in_new': [],
        'common_tables_diff': {}
    }
    
    old_tables = set(old_schema.keys())
    new_tables = set(new_schema.keys())
    
    diff['tables_only_in_old'] = list(old_tables - new_tables)
    diff['tables_only_in_new'] = list(new_tables - old_tables)
    
    common_tables = old_tables.intersection(new_tables)
    
    for table in common_tables:
        table_diff = {
            'columns_only_in_old': [],
            'columns_only_in_new': [],
            'type_mismatches': []
        }
        
        old_cols = old_schema[table]
        new_cols = new_schema[table]
        
        old_col_names = set(old_cols.keys())
        new_col_names = set(new_cols.keys())
        
        table_diff['columns_only_in_old'] = list(old_col_names - new_col_names)
        table_diff['columns_only_in_new'] = list(new_col_names - old_col_names)
        
        common_cols = old_col_names.intersection(new_col_names)
        
        for col in common_cols:
            # Simple string comparison of types (normalization might be needed for perfect accuracy)
            if old_cols[col] != new_cols[col]:
                 table_diff['type_mismatches'].append({
                     'column': col,
                     'old_type': old_cols[col],
                     'new_type': new_cols[col]
                 })
        
        if (table_diff['columns_only_in_old'] or 
            table_diff['columns_only_in_new'] or 
            table_diff['type_mismatches']):
            diff['common_tables_diff'][table] = table_diff
            
    return diff

def print_report(diff):
    print("\n" + "="*50)
    print("SCHEMA COMPARISON REPORT")
    print("="*50 + "\n")
    
    print(f"Tables ONLY in OLD Suite: {len(diff['tables_only_in_old'])}")
    for t in sorted(diff['tables_only_in_old']):
        print(f" - {t}")
    print("")

    print(f"Tables ONLY in NEW Suite: {len(diff['tables_only_in_new'])}")
    for t in sorted(diff['tables_only_in_new']):
        print(f" - {t}")
    print("")

    print(f"Tables with DIFFERENCES: {len(diff['common_tables_diff'])}")
    for table, irregularities in diff['common_tables_diff'].items():
        print(f"\n[TABLE: {table}]")
        if irregularities['columns_only_in_old']:
            print("  Missing in NEW (Columns):")
            for c in irregularities['columns_only_in_old']:
                 print(f"   - {c}")
        
        if irregularities['columns_only_in_new']:
            print("  Added in NEW (Columns):")
            for c in irregularities['columns_only_in_new']:
                 print(f"   + {c}")
                 
        if irregularities['type_mismatches']:
            print("  Type Mismatches:")
            for m in irregularities['type_mismatches']:
                print(f"   ~ {m['column']}: '{m['old_type']}' -> '{m['new_type']}'")

import csv

def to_sql_value(val):
    r"""
    Converts a COPY format value to a SQL INSERT value.
    Handles \N as NULL and escapes single quotes.
    """
    if val == r'\N':
        return 'NULL'
    # Escape single quotes and wrapping in quotes
    escaped = val.replace("'", "''")
    return f"'{escaped}'"

def generate_migrated_dump(new_schema_path, old_dump_path, output_path, new_schema_def):
    """
    Generates a new SQL dump file by:
    1. Copying the structure (Schema) from the New Suite backup.
    2. Reading data from Old Suite backup (via pg_restore COPY).
    3. Transforming data to match New Suite schema.
    4. Writing INSERT statements to the output file.
    """
    print("\n" + "="*50)
    print("GENERATING MIGRATED DUMP")
    print("="*50)
    
    try:
        with open(output_path, 'w', encoding='utf-8') as outfile:
            outfile.write(f"-- MIGRATED DATABASE DUMP\n")
            outfile.write(f"-- Generated by schema_comparator.py\n\n")
            
            # 1. Copy Schema from New Suite (Filtering out COPY/INSERT)
            print(f"Reading Schema from {new_schema_path}...")
            outfile.write(f"-- SCHEMA DEFINITION (Copied from New Suite)\n")
            
            with open(new_schema_path, 'r', encoding='utf-8') as infile:
                in_copy_block = False
                for line in infile:
                    # Simple state machine to skip COPY blocks
                    if line.startswith('COPY ') and ' FROM stdin;' in line:
                        in_copy_block = True
                        continue
                    if in_copy_block:
                        if line.strip() == r'\.':
                            in_copy_block = False
                        continue
                    
                    # Also skip explicit INSERTs if any (New suite might have seed data)
                    if line.startswith('INSERT INTO '):
                        continue

                    outfile.write(line)
            
            outfile.write(f"\n\n-- DATA MIGRATION (Transformed from Old Suite)\n")
            
            # 2. Data Migration: Read Old Suite via pg_restore and transform
            print("Processing Data from Old Suite (Parsing COPY streams)...")
            
            # We assume old_dump_path is valid .dump file
            process = subprocess.Popen(['pg_restore', '-f', '-', old_dump_path], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            
            current_table = None
            current_cols = []
            
            # Use a buffer/iterator for reading lines
            if process.stdout:
                for line in process.stdout:
                    line = line.strip()
                    
                    # Detect COPY start
                    # COPY public.users (id, name, ...) FROM stdin;
                    match_copy = re.match(r'COPY public\.(\w+) \((.*?)\) FROM stdin;', line)
                    if match_copy:
                        current_table = match_copy.group(1)
                        # Parse columns from the COPY header (comma separated)
                        raw_cols = match_copy.group(2)
                        current_cols = [c.strip().strip('"') for c in raw_cols.split(',')]
                        
                        # Check if this table exists in New Schema
                        if current_table not in new_schema_def:
                            print(f"Skipping table {current_table} (Not in New Suite)")
                            current_table = None # Skip this block
                            continue
                        
                        print(f"Migrating table: {current_table}")
                        outfile.write(f"\n-- Data for {current_table}\n")
                        continue
                    
                    # Detect end of COPY
                    if line == r'\.':
                        current_table = None
                        current_cols = []
                        continue
                    
                    # Process Row
                    if current_table and current_cols:
                        # Parse COPY row (tab separated)
                        # We use simple split, assuming standard pg_dump text format
                        # WARNING: This might be fragile with complex text containing tabs, 
                        # but standard dumps escape tabs as \t.
                        row_values = line.split('\t')
                        
                        if len(row_values) != len(current_cols):
                            # Mismatch in columns vs values, skip row or log warning
                            continue
                            
                        # Build Dictionary for easy mapping
                        row_dict = dict(zip(current_cols, row_values))
                        
                        # Construct INSERT
                        # 1. Start with New Suite columns for this table
                        valid_new_cols = new_schema_def[current_table] # expected {col: type}
                        
                        target_cols = []
                        target_vals = []
                        
                        for col in valid_new_cols:
                            # If column exists in Old Row, use it
                            if col in row_dict:
                                target_cols.append(f'"{col}"')
                                target_vals.append(to_sql_value(row_dict[col]))
                            # Else, we rely on Default (omit from Insert) or set NULL?
                            # Standard pattern: if omitted, DB uses DEFAULT or NULL.
                            # So we just don't add it to target_cols.
                        
                        if target_cols:
                            cols_str = ", ".join(target_cols)
                            vals_str = ", ".join(target_vals)
                            outfile.write(f"INSERT INTO public.{current_table} ({cols_str}) VALUES ({vals_str});\n")

            # Check for errors
            rc = process.poll()
            if rc and rc != 0:
                print(f"Warning: pg_restore exited with code {rc}")
                if process.stderr:
                    print(process.stderr.read())

        print(f"Migrated dump created at: {output_path}")

    except Exception as e:
        print(f"Error generating dump: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Hardcoded paths based on user request/context, or can be arguments
    NEW_SUITE_BACKUP = '/home/manu/suite-clinica/backend/backups/new_suite_backups/db_backup_20260202_154552.sql'
    OLD_SUITE_BACKUP = '/home/manu/suite-clinica/backend/backups/old_suite_backups/db_backup_20260205_121004.dump'
    OUTPUT_FILE = '/home/manu/suite-clinica/backend/backups/migrated_db.sql'
    
    if not os.path.exists(NEW_SUITE_BACKUP):
        print(f"New suite backup not found: {NEW_SUITE_BACKUP}")
        sys.exit(1)
        
    if not os.path.exists(OLD_SUITE_BACKUP):
        print(f"Old suite backup not found: {OLD_SUITE_BACKUP}")
        sys.exit(1)

    print("Starting Schema Comparison...")
    
    old_schema = parse_sql_dump(OLD_SUITE_BACKUP)
    new_schema = parse_sql_dump(NEW_SUITE_BACKUP)
    
    differences = compare_schemas(old_schema, new_schema)
    
    print_report(differences)
    
    # Generate the migrated DB file
    generate_migrated_dump(NEW_SUITE_BACKUP, OLD_SUITE_BACKUP, OUTPUT_FILE, new_schema)
