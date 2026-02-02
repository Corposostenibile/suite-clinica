# Suite Clinica - Test Data Seed Script

## Overview

Script unificato per popolare il database di sviluppo con dati di test completi e realistici.

## Utilizzo

### Comando Base

```bash
cd /home/samu/suite-clinica/backend
python scripts/seed_test_data.py
```

### Con Opzioni

```bash
# Seed veloce (50 pazienti, 10 professionisti per tipo)
python scripts/seed_test_data.py

# Seed completo con pulizia database
python scripts/seed_test_data.py --clean --patients 100 --professionals 20

# Solo pulire e seed minimale
python scripts/seed_test_data.py --clean --patients 20 --professionals 5
```

## Opzioni Disponibili

| Opzione | Descrizione | Default |
|---------|-------------|---------|
| `--clean` | Elimina tutti i dati esistenti prima di seed | false |
| `--patients N` | Numero di pazienti da creare | 50 |
| `--professionals N` | Numero di professionisti per tipo | 10 |

## Dati Generati

### Dipartimenti
- ✅ Amministrazione
- ✅ Nutrizione
- ✅ Coaching
- ✅ Psicologia

### Utenti

#### Admin
- **Email**: `admin@test.local`
- **Password**: `Test1234!`
- **Ruolo**: Amministratore sistema

#### Professionisti

Per ogni tipologia (Nutrizionista, Coach, Psicologo):
- 1 Team Leader
- N-1 Professionisti membri
- Tutti assegnati a un team

**Email pattern**: `[nome].[cognome][idx]@[specialty].test.local`  
**Password**: `Test1234!`  

Esempi:
- `giulia.rossi0@nutrizione.test.local`
- `marco.bianchi1@coaching.test.local`
- `sara.verdi2@psico.test.local`

### Team

1 team per ogni specialità:
- Team Nutrition Alpha (Nutrizione)
- Team Coach Alpha (Coaching)
- Team Psico Alpha (Psicologia)

### Pazienti

Generati con dati realistici italiani:

#### Tipologie (con pesi)
- **20% VIP** (tipologia `a`) - Clienti premium con servizi completi
- **30% Premium** (tipologia `b`) - Clienti con servizi estesi
- **50% Standard** (tipologia `c`) - Clienti standard

#### Stati (con pesi)
- **70% Attivo**
- **15% Ghost**
- **10% Pausa**
- **5% Stop**

#### Dati Generati
- Nome e cognome realistici italiani
- Email univoca (`@patient.test.local`)
- Data di nascita (18-75 anni)
- Genere (60% donne, 40% uomini)
- Numero di telefono italiano
- Indirizzo italiano completo
- Professione
- Programma attivo (3, 6 o 12 mesi)
- Assegnazione casuale a professionisti (80% nutrizionista, 60% coach, 30% psicologo)

## Estensione dello Script

Lo script è progettato per essere facilmente estendibile. Per aggiungere nuovi dati:

### 1. Aggiungi una nuova funzione seed

```python
def seed_my_new_data(db, MyModel, related_data):
    """Crea i tuoi nuovi dati"""
    print("\n🆕 Creazione nuovi dati...")
    
    # Logica di creazione
    for i in range(count):
        item = MyModel(
            # ... campi
        )
        db.session.add(item)
    
    db.session.commit()
    print(f"  ✅ Creati {count} items")
    return items
```

### 2. Chiama la funzione nel main

```python
def main():
    # ... after existing seeds
    my_new_data = seed_my_new_data(db, MyModel, some_data)
```

## File di Riferimento

Lo script si ispira agli script esistenti:
- `seed_fake_clients.py` - Generazione clienti con dati realistici
- `seed_fake_professionals.py` - Generazione professionisti e team
- `seed_clients_step*.py` - Pipeline multistepper per seed complessi

## Troubleshooting

### Errore: "Admin volpara non trovato"

Assicurati che esista l'admin di sistema. Lo script crea automaticamente `admin@test.local`.

### Errore: Foreign Key Constraint

Usa l'opzione `--clean` per pulire completamente il database prima di seed:

```bash
python scripts/seed_test_data.py --clean
```

### Performance Lente

Per seed più veloci, riduci il numero di pazienti:

```bash
python scripts/seed_test_data.py --patients 20 --professionals 5
```

## Verificanno i Dati

Dopo aver eseguito lo script:

1. **Login Admin**
   - URL: http://localhost:5000
   - Email: `admin@test.local`
   - Password: `Test1234!`

2. **Verifica Pazienti**
   - Vai su `/clienti`
   - Controlla i filtri per tipologia (VIP, Premium, Standard)
   - Verifica le badge colorate

3. **Verifica Professionisti**
   - Vai su `/team`
   - Verifica che ci siano i 3 team
   - Controlla che ogni team abbia i membri assegnati

## Note

⚠️ **SOLO PER SVILUPPO**: Questo script è pensato SOLO per ambienti di sviluppo. Non usare in produzione!

📌 **Password di default**: Tutti gli utenti hanno password `Test1234!` per facilità di testing.

🔄 **Idempotenza parziale**: Il flag `--clean` garantisce un ambiente pulito. Senza il flag, potrebbero esserci duplicati.
