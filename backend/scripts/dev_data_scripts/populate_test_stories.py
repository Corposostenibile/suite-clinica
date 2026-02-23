import os
import sys
from datetime import datetime

# Aggiunge la root del progetto al path per gli import
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from corposostenibile import create_app
from corposostenibile.extensions import db
from corposostenibile.models import GHLOpportunityData

# 3 Storie realistiche e complete
STORIES = [
    """**Profilo: Atleta Crossfit con Fame Emotiva**
    
    Marco è un uomo di 32 anni che si allena intensamente in palestra (Crossfit 4-5 volte a settimana) ma non riesce a vedere i risultati estetici sperati. 
    Lavora in un ambiente molto stressante come sviluppatore software.
    
    **Problematiche principali:**
    - Soffre di attacchi di fame nervosa la sera dopo il lavoro.
    - Sente un costante gonfiore addominale nonostante mangi "pulito" durante il giorno.
    - Ha difficoltà a dormire profondamente, il che influisce sul suo recupero muscolare.
    
    **Obiettivi:**
    - Ridurre la massa grassa mantenendo la forza.
    - Imparare a gestire lo stress senza ricorrere al cibo spazzatura la sera.
    - Ottimizzare la digestione.
    - Superare il senso di inadeguatezza nonostante l'impegno in palestra.""",

    """**Profilo: Salute Femminile e Perdita Peso (PCOS)**
    
    Giulia, 28 anni, soffre di Sindrome dell'Ovaio Policistico (PCOS) e resistenza insulinica. 
    Ha provato decine di diete ipocaloriche senza mai riuscire a mantenere il peso perso.
    
    **Problematiche principali:**
    - Difficoltà estrema a perdere peso nella zona addominale.
    - Ciclo irregolare e problemi di acne adulta.
    - Rapporto conflittuale con lo specchio e scarsa autostima.
    - Si sente spesso stanca e senza energia già a metà pomeriggio.
    
    **Obiettivi:**
    - Regolare il ciclo attraverso l'alimentazione e lo stile di vita.
    - Perdere 10 kg in modo sostenibile.
    - Trovare un tipo di allenamento che non la esaurisca ma che sia efficace.
    - Migliorare il rapporto con il proprio corpo.""",

    """**Profilo: Ansia e Alimentazione Restrittiva**
    
    Elena, 45 anni, ha una storia di diete molto restrittive e un approccio "tutto o nulla" con l'alimentazione. 
    Conduce una vita sedentaria ma vorrebbe iniziare a muoversi.
    
    **Problematiche principali:**
    - Tendenza a saltare i pasti (soprattutto il pranzo per il lavoro) per poi esagerare a cena.
    - Livelli di ansia elevati che si ripercuotono sullo stomaco (gastrite nervosa).
    - Totale mancanza di tono muscolare e dolori alla schiena dovuti alla postura.
    - Paura patologica dei carboidrati.
    
    **Obiettivi:**
    - Riconciliarsi con il cibo e smettere di averne paura.
    - Iniziare un percorso di attività fisica dolce per rinforzare la schiena e scaricare l'ansia.
    - Risolvere i problemi di gastrite attraverso una routine alimentare regolare.
    - Gestire l'ansia quotidiana con strumenti pratici."""
]

def populate():
    app = create_app()
    with app.app_context():
        print("--- Inizio popolamento storie test (GHLOpportunityData) ---")
        
        leads = GHLOpportunityData.query.all()
        if not leads:
            print("Nessun record trovato nella tabella ghl_opportunity_data.")
            return

        print(f"Trovati {len(leads)} record da aggiornare.")
        
        count = 0
        for i, lead in enumerate(leads):
            # Assegna una delle 3 storie a rotazione
            story = STORIES[i % len(STORIES)]
            lead.storia = story
            count += 1
            
        db.session.commit()
        print(f"Aggiornati {count} record con storie complete.")
        print("--- Fine popolamento ---")

if __name__ == "__main__":
    populate()
