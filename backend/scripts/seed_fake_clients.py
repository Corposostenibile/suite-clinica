#!/usr/bin/env python3
"""
Script di seed per creare 50.000 clienti fittizi.
Step 1: Dati base (anagrafica)
"""

import sys
import os
import random
from datetime import datetime, date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

TOTAL_CLIENTS = 50000
BATCH_SIZE = 1000  # Inserimento a batch per performance

# Nomi italiani comuni
NOMI_MASCHILI = [
    "Marco", "Luca", "Andrea", "Francesco", "Alessandro", "Matteo", "Lorenzo",
    "Davide", "Simone", "Federico", "Gabriele", "Riccardo", "Tommaso", "Stefano",
    "Giuseppe", "Antonio", "Giovanni", "Michele", "Paolo", "Roberto", "Filippo",
    "Nicola", "Daniele", "Emanuele", "Fabio", "Giacomo", "Leonardo", "Pietro",
    "Vincenzo", "Alberto", "Claudio", "Diego", "Enrico", "Giorgio", "Ivan",
    "Jacopo", "Massimo", "Omar", "Sergio", "Vittorio", "Bruno", "Carlo",
    "Dario", "Edoardo", "Franco", "Giulio", "Hugo", "Igor", "Kevin", "Luigi",
    "Mattia", "Nicolò", "Oscar", "Patrick", "Raffaele", "Salvatore", "Tiziano",
    "Umberto", "Valerio", "Walter", "Xavier", "Yuri", "Zeno", "Adriano",
    "Agostino", "Alfredo", "Amedeo", "Armando", "Arturo", "Aurelio", "Benito",
    "Bernardo", "Camillo", "Cesare", "Corrado", "Cristiano", "Damiano", "Domenico"
]

NOMI_FEMMINILI = [
    "Giulia", "Francesca", "Sara", "Chiara", "Valentina", "Alessia", "Martina",
    "Federica", "Elisa", "Silvia", "Laura", "Anna", "Maria", "Elena", "Giorgia",
    "Alice", "Beatrice", "Camilla", "Claudia", "Daniela", "Emma", "Gaia",
    "Ilaria", "Jessica", "Lisa", "Marta", "Nicole", "Paola", "Rebecca",
    "Sofia", "Teresa", "Valeria", "Aurora", "Bianca", "Carlotta", "Diana",
    "Eva", "Fiamma", "Gloria", "Helena", "Irene", "Jasmine", "Katia",
    "Lucia", "Monica", "Nadia", "Olivia", "Patrizia", "Rachele", "Serena",
    "Viola", "Azzurra", "Barbara", "Caterina", "Debora", "Eleonora", "Fabiana",
    "Giada", "Giovanna", "Grazia", "Isabella", "Lara", "Letizia", "Lorena",
    "Manuela", "Margherita", "Michela", "Miriam", "Noemi", "Pamela", "Roberta",
    "Sabrina", "Samantha", "Sandra", "Simona", "Stefania", "Susanna", "Tania"
]

COGNOMI = [
    "Rossi", "Russo", "Ferrari", "Esposito", "Bianchi", "Romano", "Colombo",
    "Ricci", "Marino", "Greco", "Bruno", "Gallo", "Conti", "De Luca", "Mancini",
    "Costa", "Giordano", "Rizzo", "Lombardi", "Moretti", "Barbieri", "Fontana",
    "Santoro", "Mariani", "Rinaldi", "Caruso", "Ferrara", "Galli", "Martini",
    "Leone", "Longo", "Gentile", "Martinelli", "Vitale", "Lombardo", "Serra",
    "Coppola", "De Santis", "D'Angelo", "Marchetti", "Parisi", "Villa", "Conte",
    "Ferraro", "Ferri", "Fabbri", "Bianco", "Marini", "Grasso", "Valentini",
    "Messina", "Sala", "De Angelis", "Gatti", "Pellegrini", "Palumbo", "Sanna",
    "Farina", "Rizzi", "Monti", "Cattaneo", "Morelli", "Amato", "Silvestri",
    "Mazza", "Testa", "Grassi", "Pellegrino", "Carbone", "Giuliani", "Benedetti",
    "Barone", "Orlando", "Damico", "Palmieri", "Bernardi", "Martino", "Fiore",
    "De Rosa", "Ferretti", "Bellini", "Basile", "Riva", "Donati", "Piras",
    "Vitali", "Battaglia", "Sartori", "Neri", "Costantini", "Milani", "Parodi",
    "Montanari", "Guerra", "Pagano", "Ruggiero", "Sorrentino", "D'Amico", "Tosi"
]

# Professioni realistiche
PROFESSIONI = [
    "Impiegato/a", "Libero professionista", "Insegnante", "Infermiere/a",
    "Medico", "Avvocato", "Commercialista", "Ingegnere", "Architetto",
    "Farmacista", "Commerciante", "Artigiano/a", "Operaio/a", "Manager",
    "Consulente", "Imprenditore/trice", "Studente/ssa", "Pensionato/a",
    "Casalinga/o", "Disoccupato/a", "Agente di commercio", "Bancario/a",
    "Assicuratore/trice", "Programmatore/trice", "Designer", "Giornalista",
    "Fotografo/a", "Chef", "Estetista", "Parrucchiere/a", "Personal trainer",
    "Fisioterapista", "Psicologo/a", "Veterinario/a", "Dentista",
    "Receptionist", "Segretario/a", "Autista", "Corriere", "Magazziniere",
    "Commesso/a", "Cameriere/a", "Barista", "Cuoco/a", "Muratore",
    "Elettricista", "Idraulico", "Meccanico", "Tecnico informatico",
    "Social media manager", "Marketing manager", "HR manager", "Project manager",
    "Data analyst", "Web developer", "Graphic designer", "Content creator"
]

# Città e province italiane
CITTA_PROVINCE = [
    ("Milano", "MI"), ("Roma", "RM"), ("Napoli", "NA"), ("Torino", "TO"),
    ("Palermo", "PA"), ("Genova", "GE"), ("Bologna", "BO"), ("Firenze", "FI"),
    ("Bari", "BA"), ("Catania", "CT"), ("Venezia", "VE"), ("Verona", "VR"),
    ("Messina", "ME"), ("Padova", "PD"), ("Trieste", "TS"), ("Taranto", "TA"),
    ("Brescia", "BS"), ("Parma", "PR"), ("Prato", "PO"), ("Modena", "MO"),
    ("Reggio Calabria", "RC"), ("Reggio Emilia", "RE"), ("Perugia", "PG"),
    ("Livorno", "LI"), ("Ravenna", "RA"), ("Cagliari", "CA"), ("Foggia", "FG"),
    ("Rimini", "RN"), ("Salerno", "SA"), ("Ferrara", "FE"), ("Sassari", "SS"),
    ("Latina", "LT"), ("Giugliano in Campania", "NA"), ("Monza", "MB"),
    ("Siracusa", "SR"), ("Pescara", "PE"), ("Bergamo", "BG"), ("Forlì", "FC"),
    ("Trento", "TN"), ("Vicenza", "VI"), ("Terni", "TR"), ("Bolzano", "BZ"),
    ("Novara", "NO"), ("Piacenza", "PC"), ("Ancona", "AN"), ("Andria", "BT"),
    ("Arezzo", "AR"), ("Udine", "UD"), ("Cesena", "FC"), ("Lecce", "LE")
]

# Vie italiane comuni
VIE = [
    "Via Roma", "Via Garibaldi", "Via Mazzini", "Via Cavour", "Via Dante",
    "Via Verdi", "Via Marconi", "Via Kennedy", "Via Gramsci", "Via Matteotti",
    "Via XX Settembre", "Via IV Novembre", "Via della Repubblica", "Via Europa",
    "Via dei Mille", "Via Nazionale", "Via del Corso", "Via Vittorio Emanuele",
    "Via San Francesco", "Via della Libertà", "Corso Italia", "Corso Vittorio",
    "Viale della Stazione", "Piazza del Popolo", "Via Leopardi", "Via Pascoli",
    "Via Carducci", "Via Petrarca", "Via Foscolo", "Via Montale", "Via Ungaretti",
    "Via dei Tigli", "Via delle Rose", "Via dei Pini", "Via degli Ulivi",
    "Via del Sole", "Via della Luna", "Via delle Stelle", "Via Nuova",
    "Via Vecchia", "Via Principale", "Via Centrale", "Via Circonvallazione"
]

# Domini email
EMAIL_DOMAINS = [
    "gmail.com", "hotmail.it", "yahoo.it", "libero.it", "virgilio.it",
    "outlook.it", "tiscali.it", "alice.it", "tim.it", "fastwebnet.it",
    "icloud.com", "live.it", "msn.com", "email.it", "pec.it"
]

# Prefissi telefonici italiani
PREFISSI_MOBILE = ["320", "328", "329", "330", "331", "333", "334", "335",
                   "336", "337", "338", "339", "340", "342", "343", "345",
                   "346", "347", "348", "349", "350", "351", "360", "366",
                   "368", "370", "371", "373", "375", "377", "380", "388", "389"]


def generate_birth_date() -> date:
    """Genera data di nascita realistica (18-75 anni)"""
    today = date.today()
    min_age = 18
    max_age = 75

    days_range = (max_age - min_age) * 365
    random_days = random.randint(0, days_range)
    birth_date = today - timedelta(days=min_age * 365 + random_days)

    return birth_date


def generate_phone() -> str:
    """Genera numero di telefono italiano"""
    prefisso = random.choice(PREFISSI_MOBILE)
    numero = ''.join([str(random.randint(0, 9)) for _ in range(7)])
    return f"+39 {prefisso} {numero[:3]} {numero[3:]}"


def generate_address() -> str:
    """Genera indirizzo italiano"""
    via = random.choice(VIE)
    numero = random.randint(1, 200)
    citta, provincia = random.choice(CITTA_PROVINCE)
    cap = f"{random.randint(10, 99)}{random.randint(100, 999)}"

    return f"{via} {numero}, {cap} {citta} ({provincia})"


def generate_email(first_name: str, last_name: str, idx: int) -> str:
    """Genera email unica"""
    first = first_name.lower().replace("'", "").replace(" ", "").replace("à", "a").replace("è", "e").replace("ì", "i").replace("ò", "o").replace("ù", "u")
    last = last_name.lower().replace("'", "").replace(" ", "").replace("à", "a").replace("è", "e").replace("ì", "i").replace("ò", "o").replace("ù", "u")
    domain = random.choice(EMAIL_DOMAINS)

    formats = [
        f"{first}.{last}{idx}@{domain}",
        f"{first}{last}{idx}@{domain}",
        f"{first[0]}{last}{idx}@{domain}",
        f"{last}.{first}{idx}@{domain}",
    ]
    return random.choice(formats)


def generate_client(idx: int) -> dict:
    """Genera un cliente con dati realistici"""
    # 60% donne (target tipico per nutrizione/benessere)
    is_female = random.random() < 0.6

    first_name = random.choice(NOMI_FEMMINILI if is_female else NOMI_MASCHILI)
    last_name = random.choice(COGNOMI)

    return {
        'nome_cognome': f"{first_name} {last_name}",
        'mail': generate_email(first_name, last_name, idx),
        'data_di_nascita': generate_birth_date(),
        'genere': 'donna' if is_female else 'uomo',
        'numero_telefono': generate_phone(),
        'indirizzo': generate_address(),
        'professione': random.choice(PROFESSIONI),
        'paese': 'Italia',
    }


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED FAKE CLIENTS - Step 1: Anagrafica")
        print("=" * 60)

        # Conta clienti esistenti
        existing_count = Cliente.query.count()
        print(f"\n📊 Clienti esistenti: {existing_count}")

        if existing_count > 0:
            confirm = input(f"\n⚠️  Vuoi eliminare i {existing_count} clienti esistenti? (s/n): ")
            if confirm.lower() == 's':
                print("🗑️  Eliminazione clienti esistenti...")
                # Delete all clients (standard deletion without FK disabling)
                Cliente.query.delete()
                db.session.commit()
                print("✅ Clienti eliminati")
            else:
                print("❌ Operazione annullata")
                return

        # ============================================================
        # GENERAZIONE CLIENTI
        # ============================================================
        print(f"\n📦 Generazione {TOTAL_CLIENTS:,} clienti...")

        start_time = datetime.now()
        created = 0

        for batch_start in range(0, TOTAL_CLIENTS, BATCH_SIZE):
            batch_end = min(batch_start + BATCH_SIZE, TOTAL_CLIENTS)
            batch_clients = []

            for idx in range(batch_start, batch_end):
                client_data = generate_client(idx)

                cliente = Cliente(
                    nome_cognome=client_data['nome_cognome'],
                    mail=client_data['mail'],
                    data_di_nascita=client_data['data_di_nascita'],
                    genere=client_data['genere'],
                    numero_telefono=client_data['numero_telefono'],
                    indirizzo=client_data['indirizzo'],
                    professione=client_data['professione'],
                    paese=client_data['paese'],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
                batch_clients.append(cliente)

            db.session.bulk_save_objects(batch_clients)
            db.session.commit()

            created += len(batch_clients)
            progress = (created / TOTAL_CLIENTS) * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = created / elapsed if elapsed > 0 else 0
            eta = (TOTAL_CLIENTS - created) / rate if rate > 0 else 0

            print(f"  ✅ {created:,}/{TOTAL_CLIENTS:,} ({progress:.1f}%) - {rate:.0f}/sec - ETA: {eta:.0f}s")

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        total_clients = Cliente.query.count()
        donne = Cliente.query.filter_by(genere='donna').count()
        uomini = Cliente.query.filter_by(genere='uomo').count()

        print(f"\n📊 Statistiche:")
        print(f"   Clienti totali: {total_clients:,}")
        print(f"   Donne: {donne:,} ({donne/total_clients*100:.1f}%)")
        print(f"   Uomini: {uomini:,} ({uomini/total_clients*100:.1f}%)")
        print(f"\n⏱️  Tempo totale: {elapsed_total:.1f} secondi")
        print(f"   Rate: {total_clients/elapsed_total:.0f} clienti/secondo")

        print("\n✅ STEP 1 COMPLETATO!")
        print("\n📝 Prossimi step:")
        print("   - Step 2: Abbonamento e programma")
        print("   - Step 3: Assegnazione professionisti")
        print("   - Step 4: Stati e storico")
        print("   - Step 5: Piani nutrizionali e allenamento")


if __name__ == '__main__':
    main()
