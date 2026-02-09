import os
import sys
import argparse
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

# Add backend directory to path to load app
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User
from corposostenibile.blueprints.team.criteria_service import CriteriaService

def normalize_key(key):
    """Normalize Excel header to match schema key (trim spaces)."""
    return key.strip()

def parse_shared_strings(z):
    """Read shared strings from Excel xlsx."""
    strings = []
    if 'xl/sharedStrings.xml' in z.namelist():
        with z.open('xl/sharedStrings.xml') as f:
            tree = ET.parse(f)
            root = tree.getroot()
            ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
            for si in root.findall('ns:si', ns):
                t = si.find('ns:t', ns)
                if t is not None and t.text:
                    strings.append(t.text)
                else:
                    strings.append("") # Empty string placeholder
    return strings

def get_value(cell, shared_strings):
    """Extract value from cell node."""
    t = cell.get('t')
    v_node = cell.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
    if v_node is None:
        return None
    val = v_node.text
    if t == 's': # Shared string
        idx = int(val)
        if idx < len(shared_strings):
            return shared_strings[idx]
        return val
    return val

def process_sheet(z, sheet_filename, role_key):
    """Process a single sheet and return a dict {User: {Criterion: bool}}."""
    print(f"--- Processing {role_key} ({sheet_filename}) ---")
    data = {} # { "Nome Cognome": { "Criterio": True/False } }
    
    with z.open(f'xl/{sheet_filename}') as f:
        tree = ET.parse(f)
        root = tree.getroot()
        ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
        
        shared_strings = parse_shared_strings(z)
        
        sheet_data = root.find('ns:sheetData', ns)
        rows = sorted(sheet_data.findall('ns:row', ns), key=lambda r: int(r.get('r')))
        
        if not rows:
            print("Empty sheet")
            return {}

        # Parse Header (Row 1)
        header_row = rows[0]
        headers = [] # List of (col_idx, criteria_name)
        
        # Map column letter (e.g. 'A', 'B', 'AA') to index is complex, 
        # so we iterate cells. But cells might be sparse.
        # Simple assumption: Header row has all columns populated sequentially?
        # Let's trust the cell 'r' attribute like "A1", "B1".
        
        col_map = {} # 'A' -> 'Nome', 'B' -> 'UOMINI'
        
        for cell in header_row.findall('ns:c', ns):
            coord = cell.get('r') # e.g. A1
            col_letter = "".join([c for c in coord if c.isalpha()])
            val = get_value(cell, shared_strings)
            if val:
                col_map[col_letter] = normalize_key(val)
                # print(f"  Column {col_letter}: {val}")

        # Parse Data Rows (Row 2+)
        for row in rows[1:]:
            col_values = {} # 'A' -> 'Mario Ross', 'B' -> 'SI'
            for cell in row.findall('ns:c', ns):
                coord = cell.get('r')
                col_letter = "".join([c for c in coord if c.isalpha()])
                val = get_value(cell, shared_strings)
                col_values[col_letter] = val
            
            # Identify Professional Name (First column 'A')
            prof_name = col_values.get('A')
            if not prof_name:
                continue
                
            prof_name = prof_name.strip()
            # Special case cleanup (remove trailing spaces, etc)
            
            criteria_map = {}
            # Iterate all other columns
            for letter, header in col_map.items():
                if letter == 'A': continue # Skip Name
                
                cell_val = col_values.get(letter, "").strip().upper() if col_values.get(letter) else ""
                
                # Logic: "SI", "Sì", "Si" -> True. Anything else -> False?
                # Check empty strings
                is_active = cell_val in ['SI', 'SÌ', 'YES', 'X']
                criteria_map[header] = is_active
                
            data[prof_name] = criteria_map
            print(f"  Parsed: {prof_name} ({sum(criteria_map.values())} active criteria)")
            
    return data

def sync_db(all_data):
    """Sync parsed data with Database Users."""
    print("\n--- Syncing with Database ---")
    
    # Get all users (professionals)
    # We match by Name (First Last or Last First?)
    # DB has first_name, last_name.
    # Excel has "Nome Professionista" (e.g. "ALESSANDRA ARCOLEO")
    
    users = User.query.all()
    
    updated_count = 0
    not_found = []
    
    for prof_name, criteria in all_data.items():
        # Try to match user
        matched_user = None
        
        # Normalize search name
        search_name = prof_name.lower().replace("  ", " ")
        
        for u in users:
            u_full = f"{u.first_name} {u.last_name}".lower()
            u_rev = f"{u.last_name} {u.first_name}".lower() # Handle inverted
            
            if search_name == u_full or search_name == u_rev:
                matched_user = u
                break
        
        if matched_user:
            print(f"✅ Matched: '{prof_name}' -> ID {matched_user.id} ({matched_user.email})")
            
            # Merge or Overwrite? 
            # Strategy: Overwrite criteria that are parsed. 
            # Note: The parsed 'criteria' dict contains ALL parsed headers with True/False.
            
            # Use CriteriaService to validate (optional, but good practice)
            # valid_criteria = CriteriaService.validate_criteria(matched_user.role.value, criteria)
            # Just save the raw boolean map for now as schemas align with parsing
            
            matched_user.assignment_criteria = criteria
            updated_count += 1
        else:
            print(f"⚠️  Not Found in DB: '{prof_name}'")
            not_found.append(prof_name)

    db.session.commit()
    print(f"\nSynced {updated_count} users successfully.")
    if not_found:
        print(f"Users not found in DB ({len(not_found)}): {', '.join(not_found)}")

def main():
    app = create_app()
    
    file_path = str(BASE_DIR / 'corposostenibile/blueprints/sales_form/assegnazioni_xlsx/Criteri Ai.xlsx')
    
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return

    with app.app_context():
        print(f"Reading {file_path}...")
        try:
            with zipfile.ZipFile(file_path, 'r') as z:
                # Based on previous analysis (map_sheets.py)
                # Sheet 1 -> NUTRI (rId5 -> worksheet/sheet1.xml)
                # Sheet 2 -> PSICO (rId6 -> worksheet/sheet2.xml)
                # Sheet 3 -> COACH (rId7 -> worksheet/sheet3.xml)
                
                # We can't rely on rId being static, strictly speaking, but for this specific file it is.
                # A robust implementation would parse workbook.xml again. 
                # For this script, we'll assume the structure is stable or parse workbook.xml quickly.
                
                rels = {}
                # Parse workbook.xml to get map {name: target}
                sheet_map = {}
                with z.open('xl/_rels/workbook.xml.rels') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'ns': 'http://schemas.openxmlformats.org/package/2006/relationships'}
                    for rel in root.findall('ns:Relationship', ns):
                        rels[rel.get('Id')] = rel.get('Target')
                        
                with z.open('xl/workbook.xml') as f:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    ns = {'ns': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
                    for sheet in root.findall('ns:sheets/ns:sheet', ns):
                         r_id = sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                         name = sheet.get('name')
                         target = rels.get(r_id)
                         sheet_map[name] = target
                
                print(f"Sheet Mapping: {sheet_map}")
                
                all_data = {}
                
                # NUTRI
                if 'NUTRI' in sheet_map:
                    nutri_data = process_sheet(z, sheet_map['NUTRI'], 'NUTRI')
                    all_data.update(nutri_data)
                
                # PSICO
                if 'PSICO' in sheet_map:
                    psico_data = process_sheet(z, sheet_map['PSICO'], 'PSICO')
                    all_data.update(psico_data)
                    
                # COACH
                if 'COACH' in sheet_map:
                    coach_data = process_sheet(z, sheet_map['COACH'], 'COACH')
                    all_data.update(coach_data)
                
                sync_db(all_data)
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
