"""
Estrae il testo dai PDF in guidelines/ e scrive guidelines/guidelines_extracted.txt.
Eseguire dalla repo: cd backend && poetry run python -m corposostenibile.blueprints.marketing_automation.extract_guidelines_text
"""
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Errore: pdfplumber non installato. Esegui: poetry install")
    raise

BLUEPRINT_DIR = Path(__file__).resolve().parent
GUIDELINES_DIR = BLUEPRINT_DIR / "guidelines"
OUTPUT_FILE = GUIDELINES_DIR / "guidelines_extracted.txt"

def main():
    if not GUIDELINES_DIR.is_dir():
        print(f"Cartella non trovata: {GUIDELINES_DIR}")
        return 1
    pdf_files = sorted(GUIDELINES_DIR.glob("*.pdf"))
    if not pdf_files:
        print(f"Nessun PDF in {GUIDELINES_DIR}. Copia qui i due PDF e riesegui.")
        return 1
    parts = []
    for path in pdf_files:
        print(f"Estrazione: {path.name}")
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    parts.append(t)
        parts.append("\n\n---\n\n")
    if not parts:
        print("Nessun testo estratto. Verifica che i PDF siano in guidelines/.")
        return 1
    text = "\n".join(parts).strip()
    OUTPUT_FILE.write_text(text, encoding="utf-8")
    print(f"Scritto: {OUTPUT_FILE} ({len(text)} caratteri)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
