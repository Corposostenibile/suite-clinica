import os
import sys
import argparse
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET

# Add backend directory to path to load app
BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import User
from corposostenibile.blueprints.team.criteria_service import CriteriaService

def normalize_key(key):
    """Normalize Excel header to match schema key (trim spaces)."""
    return key.strip()


def normalize_person_name(name):
    """Normalize person names for matching across Excel/DB variants."""
    text = (name or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("’", "'")
    text = re.sub(r"[^a-z0-9' ]+", " ", text)
    text = text.replace("'", "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def name_tokens(name):
    return [t for t in normalize_person_name(name).split(" ") if t]


def _find_best_user_match(prof_name, target_specialty, users):
    """Match Excel name to DB user, avoiding ambiguous single-word coach rows."""
    search_norm = normalize_person_name(prof_name)
    search_tokens = [t for t in search_norm.split(" ") if t]
    if not search_tokens:
        return None, "empty"

    candidates = [
        u for u in users
        if getattr(u, "role", None) == "professionista" or str(getattr(u, "role", "")) == "UserRoleEnum.professionista"
    ]
    if target_specialty:
        candidates = [
            u for u in candidates
            if (
                getattr(u, "specialty", None) == target_specialty
                or str(getattr(u, "specialty", "")).endswith(f".{target_specialty}")
            )
        ]

    prepared = []
    for u in candidates:
        full = f"{u.first_name or ''} {u.last_name or ''}".strip()
        rev = f"{u.last_name or ''} {u.first_name or ''}".strip()
        prepared.append((u, full, normalize_person_name(full), normalize_person_name(rev), name_tokens(full)))

    # 1) Exact normalized full/reversed match
    for u, _full, full_norm, rev_norm, _tokens in prepared:
        if search_norm == full_norm or search_norm == rev_norm:
            return u, "exact"

    # Single-word entries (common in COACH sheet) are intentionally skipped.
    if len(search_tokens) < 2:
        return None, "single_token_skipped"

    # 2) Multiword token subset match (e.g. "Nicolo Lorenzo Marinelli" vs "Nicolo Marinelli")
    subset_matches = []
    search_set = set(search_tokens)
    for u, _full, _full_norm, _rev_norm, u_tokens in prepared:
        u_set = set(u_tokens)
        if len(u_set) >= 2 and (search_set.issubset(u_set) or u_set.issubset(search_set)):
            subset_matches.append(u)
    if len(subset_matches) == 1:
        return subset_matches[0], "token_subset"

    # 3) Fuzzy multiword match on full string + surname (handles small typos like Andreola/Adreola)
    fuzzy_matches = []
    for u, _full, full_norm, _rev_norm, u_tokens in prepared:
        if len(u_tokens) < 2:
            continue
        full_ratio = SequenceMatcher(None, search_norm, full_norm).ratio()
        surname_ratio = SequenceMatcher(None, search_tokens[-1], u_tokens[-1]).ratio()
        first_ratio = SequenceMatcher(None, search_tokens[0], u_tokens[0]).ratio()
        if first_ratio >= 0.9 and surname_ratio >= 0.84 and full_ratio >= 0.84:
            fuzzy_matches.append((full_ratio + surname_ratio, u))
    if len(fuzzy_matches) == 1:
        return fuzzy_matches[0][1], "fuzzy"
    if len(fuzzy_matches) > 1:
        fuzzy_matches.sort(key=lambda x: x[0], reverse=True)
        top_score = fuzzy_matches[0][0]
        second_score = fuzzy_matches[1][0]
        if top_score - second_score > 0.08:
            return fuzzy_matches[0][1], "fuzzy_ranked"

    return None, "no_match"

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
    """Process a single sheet and return a dict {User: {'criteria': {}, 'specialty': str}}."""
    print(f"--- Processing {role_key} ({sheet_filename}) ---")
    data = {} # { "Nome Cognome": { "criteria": {}, "specialty": "..." } }
    
    # Map role_key to DB specialty (MUST MATCH UserSpecialtyEnum values)
    specialty_map = {
        'NUTRI': 'nutrizionista',
        'PSICO': 'psicologo',
        'COACH': 'coach'
    }
    target_specialty = specialty_map.get(role_key)
    
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
        col_map = {} # 'A' -> 'Nome', 'B' -> 'UOMINI'
        
        for cell in header_row.findall('ns:c', ns):
            coord = cell.get('r') # e.g. A1
            col_letter = "".join([c for c in coord if c.isalpha()])
            val = get_value(cell, shared_strings)
            if val:
                col_map[col_letter] = normalize_key(val)

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
            
            criteria_map = {}
            # Iterate all other columns
            for letter, header in col_map.items():
                if letter == 'A': continue # Skip Name
                
                cell_val = col_values.get(letter, "").strip().upper() if col_values.get(letter) else ""
                is_active = cell_val in ['SI', 'SÌ', 'YES', 'X']
                criteria_map[header] = is_active
                
            data[prof_name] = {
                'criteria': criteria_map,
                'specialty': target_specialty
            }
            print(f"  Parsed: {prof_name} ({sum(criteria_map.values())} active criteria) as {target_specialty}")
            
    return data

def sync_db(all_data, create_missing=False):
    """Sync parsed data with Database Users. Optionally create missing ones."""
    print("\n--- Syncing with Database ---")
    from werkzeug.security import generate_password_hash
    
    users = User.query.all()
    
    updated_count = 0
    created_count = 0
    
    for prof_name, info in all_data.items():
        criteria = info['criteria']
        target_specialty = info['specialty']
        
        # Try to match user
        matched_user, match_mode = _find_best_user_match(prof_name, target_specialty, users)
        
        if matched_user:
            print(
                f"✅ Updating ID {matched_user.id} ({matched_user.email}) | "
                f"Specialty: {target_specialty} | match={match_mode}"
            )
            matched_user.assignment_criteria = criteria
            matched_user.specialty = target_specialty
            updated_count += 1
        else:
            if not create_missing:
                print(
                    f"⏭️  Skipping missing user '{prof_name}' "
                    f"(reason={match_mode}, create_missing disabled)"
                )
                continue

            print(f"➕ Creating '{prof_name}' | Specialty: {target_specialty}")
            # Create a slug for email
            email_prefix = prof_name.lower().replace(" ", ".").replace("'", "")
            new_user = User(
                email=f"{email_prefix}@corposostenibile.it",
                first_name=prof_name.split(" ")[0],
                last_name=" ".join(prof_name.split(" ")[1:]) if " " in prof_name else "Professional",
                password_hash=generate_password_hash("Professional123!"),
                role="professionista",
                specialty=target_specialty,
                is_active=True,
                is_admin=False,
                assignment_criteria=criteria
            )
            db.session.add(new_user)
            created_count += 1

    db.session.commit()
    print(f"\nCompleted. Updated: {updated_count} | Created: {created_count}")

def main():
    parser = argparse.ArgumentParser(description="Sync AI criteria from Excel into prod DB users")
    parser.add_argument(
        "--create-missing",
        action="store_true",
        help="Create missing users found in the Excel (disabled by default for safety in prod)",
    )
    args = parser.parse_args()

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
                
                sync_db(all_data, create_missing=args.create_missing)
                
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
