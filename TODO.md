# TODO - Health Manager Team Fixes

## ✅ Completato
- [x] Team Leaders HM possono filtrare i pazienti dei propri HM (filtro `health_manager_id` aggiunto)

## Da Implementare

### 1. Capienza HM (1 a 1 il valore) ✅
- Implementare un campo "capienza" per gli Health Manager ✅
- Valore numerico che indica quanti pazienti può gestire un HM ✅
- Relazione 1 a 1 tra HM e capienza ✅
- **Nota**: La struttura base esisteva già (`ProfessionistCapacity` con `role_type='health_manager'`). Aggiunte colonne specifiche HM nel profilo (clienti_convertiti, lead_in_attesa) e permessi per visualizzazione HM.

### 2. Team HM con 2 Leader
- Modificare la struttura del team HM per supportare 2 team leader invece di 1
- Modificare il modello Team o la relazione per gestire più head
- Aggiornare i controlli RBAC per entrambi i leader

### 3. Filtri nella visuale HM per i Team Leader HM
- Implementare i filtri specifici nella pagina pazienti per i TL di team HM
- Filtro per HM specifico (dropdown con membri HM del team)
- Contatori/paginator che mostrano il numero di pazienti per HM
