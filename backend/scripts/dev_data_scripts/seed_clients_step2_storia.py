#!/usr/bin/env python3
"""
Script di seed per aggiornare i 50.000 clienti con:
- storia_cliente
- problema
- paure
- conseguenze

Contenuti coerenti per percorso nutrizionale/coaching/psicologico
"""

import sys
import os
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ============================================================
# CONFIGURAZIONE
# ============================================================

BATCH_SIZE = 500

# ============================================================
# PROBLEMI - Motivi per cui si rivolgono alla clinica
# ============================================================

PROBLEMI_PESO = [
    "Ho provato diverse diete nel corso degli anni ma non riesco mai a mantenere i risultati. Perdo peso e poi lo riprendo tutto, spesso con gli interessi.",
    "Il mio peso è aumentato costantemente negli ultimi 5 anni. Ho provato a fare da solo ma non funziona.",
    "Dopo la gravidanza non sono più riuscita a tornare al mio peso forma. Sono passati 3 anni e la situazione peggiora.",
    "Ho sempre avuto un rapporto difficile con il cibo. Mangio per stress, per noia, per consolazione.",
    "Il lavoro sedentario e lo stress mi hanno fatto prendere 20 kg in pochi anni. Non mi riconosco più.",
    "Soffro di fame nervosa, soprattutto la sera. Non riesco a controllarmi.",
    "Ho un metabolismo lento e faccio fatica a perdere peso anche mangiando poco.",
    "Dopo i 40 anni il mio corpo è cambiato completamente. Quello che funzionava prima ora non funziona più.",
    "Ho provato palestra, dietologo, nutrizionista... niente funziona a lungo termine.",
    "Il mio peso influisce sulla mia salute: colesterolo alto, pressione alta, prediabete.",
    "Non riesco a seguire una dieta per più di qualche settimana. Poi mollo tutto.",
    "Mangio in modo disordinato: salto i pasti e poi abbuffo la sera.",
    "Ho un rapporto ossessivo con la bilancia e con le calorie.",
    "Il cibo è diventato il mio nemico. Non so più cosa mangiare.",
    "Voglio perdere peso per la mia salute, non solo per l'estetica.",
]

PROBLEMI_EMOTIVI = [
    "Uso il cibo per gestire le emozioni. Quando sono triste, stressato o ansioso mangio.",
    "Ho un rapporto complicato con il mio corpo. Non mi piaccio e questo influisce su tutto.",
    "Soffro di abbuffate compulsive seguite da sensi di colpa terribili.",
    "La mia autostima è legata al mio peso. Quando ingrasso mi sento un fallimento.",
    "Ho sviluppato comportamenti alimentari disfunzionali dopo un periodo di forte stress.",
    "Non riesco a distinguere la fame fisica da quella emotiva.",
    "Il cibo è la mia valvola di sfogo. So che è sbagliato ma non riesco a smettere.",
    "Ho paura di mangiare certi cibi perché li considero 'cattivi' o 'proibiti'.",
    "Alterno periodi di restrizione estrema a periodi di abbuffate.",
    "Il mio umore dipende da quello che mangio e da quanto peso.",
    "Mi vergogno di mangiare in pubblico. Preferisco mangiare di nascosto.",
    "Ho provato tante diete restrittive che hanno peggiorato il mio rapporto col cibo.",
    "Non ho più fiducia nel mio corpo. Non so ascoltarlo.",
    "Il cibo occupa troppo spazio nei miei pensieri quotidiani.",
    "Ho bisogno di aiuto per uscire da questo circolo vizioso.",
]

PROBLEMI_SALUTE = [
    "Mi è stata diagnosticata l'insulino-resistenza e devo cambiare alimentazione.",
    "Ho il diabete di tipo 2 e voglio provare a gestirlo anche con l'alimentazione.",
    "Soffro di PCOS e il medico mi ha consigliato di perdere peso.",
    "Ho problemi di tiroide che rendono difficile il controllo del peso.",
    "Soffro di colon irritabile e non so più cosa mangiare.",
    "Ho il reflusso gastroesofageo cronico e devo rivedere la mia alimentazione.",
    "Mi hanno diagnosticato la steatosi epatica e devo perdere peso.",
    "Ho la pressione alta e voglio provare a ridurre i farmaci con lo stile di vita.",
    "Soffro di endometriosi e voglio provare un approccio alimentare antinfiammatorio.",
    "Ho problemi digestivi costanti: gonfiore, pesantezza, irregolarità intestinale.",
    "Il colesterolo è troppo alto nonostante non mangi grassi.",
    "Ho carenze nutrizionali nonostante mangi 'normalmente'.",
    "Soffro di emicranie frequenti che potrebbero essere legate all'alimentazione.",
    "Ho disturbi del sonno che peggiorano con certi cibi.",
    "Voglio prevenire malattie che hanno colpito i miei familiari.",
]

PROBLEMI_LIFESTYLE = [
    "Non ho tempo per cucinare e mangio sempre fuori o cibo pronto.",
    "Il mio lavoro prevede pranzi e cene di lavoro che sabotano ogni dieta.",
    "Viaggio spesso per lavoro e non riesco a mantenere una routine alimentare.",
    "Lavoro su turni e questo sconvolge completamente i miei ritmi.",
    "Non so cucinare e mi nutro sempre delle stesse cose.",
    "In famiglia ognuno mangia cose diverse e io finisco per non seguire niente.",
    "Lo stress lavorativo mi porta a mangiare male e a non fare attività fisica.",
    "Non ho motivazione per allenarmi e mangiare bene. Mi sento sempre stanco.",
    "Ho smesso di fumare e ho preso 15 kg. Non riesco a togliermeli.",
    "Dopo il lockdown ho preso peso e cambiato completamente abitudini.",
    "Non riesco a organizzarmi: faccio la spesa ma poi butto via tutto.",
    "Mangio troppo velocemente, non mastico, non mi godo il cibo.",
    "Bevo poco, salto la colazione, mangio tardi la sera... so che sbaglio tutto.",
    "La mia vita sociale ruota intorno al cibo e all'alcol.",
    "Non riesco a dire di no quando mi offrono del cibo.",
]

# ============================================================
# PAURE - Cosa temono
# ============================================================

PAURE_FALLIMENTO = [
    "Ho paura di fallire ancora una volta e confermare che non sono capace.",
    "Temo di non riuscire a mantenere i risultati come tutte le altre volte.",
    "Ho paura che sia l'ennesimo tentativo andato male.",
    "Temo di sprecare tempo e soldi per niente.",
    "Ho paura di deludere me stesso e chi mi sta intorno.",
    "Temo di non avere la forza di volontà necessaria.",
    "Ho paura di mollare alla prima difficoltà come faccio sempre.",
    "Temo che il mio corpo non risponda più a nessun cambiamento.",
    "Ho paura di scoprire che il problema sono io, non le diete.",
    "Temo di non meritare di stare bene.",
]

PAURE_CAMBIAMENTO = [
    "Ho paura di dover rinunciare a tutti i cibi che amo.",
    "Temo una dieta troppo restrittiva che non riuscirò a seguire.",
    "Ho paura di sentirmi sempre affamato e insoddisfatto.",
    "Temo di dover stravolgere completamente la mia vita.",
    "Ho paura di non poter più partecipare a cene e aperitivi.",
    "Temo di diventare 'quello strano' che non mangia niente.",
    "Ho paura che sarà tutto complicato e faticoso.",
    "Temo di dover pesare e misurare tutto per sempre.",
    "Ho paura di perdere il piacere del cibo.",
    "Temo che la mia vita sociale ne risentirà.",
]

PAURE_SALUTE = [
    "Ho paura che il mio peso causi problemi di salute gravi.",
    "Temo di sviluppare il diabete come mia madre.",
    "Ho paura che il sovrappeso riduca la mia aspettativa di vita.",
    "Temo di non poter giocare con i miei figli/nipoti per il peso.",
    "Ho paura che i miei problemi di salute peggiorino.",
    "Temo di dover prendere farmaci per il resto della vita.",
    "Ho paura di non arrivare a vedere crescere i miei figli.",
    "Temo che il mio cuore non regga questo peso.",
    "Ho paura di quello che dicono le analisi del sangue.",
    "Temo di essere già andato troppo oltre per rimediare.",
]

PAURE_PSICOLOGICHE = [
    "Ho paura di non piacere a nessuno con questo corpo.",
    "Temo il giudizio degli altri quando mangio.",
    "Ho paura di non trovare mai un equilibrio con il cibo.",
    "Temo di trasmettere il mio rapporto malato col cibo ai miei figli.",
    "Ho paura di restare intrappolato in questo corpo per sempre.",
    "Temo di non riuscire mai ad accettarmi.",
    "Ho paura di guardarmi allo specchio.",
    "Temo che il mio partner mi lasci per il mio aspetto.",
    "Ho paura di perdere opportunità a causa del mio peso.",
    "Temo di sprecare la mia vita a pensare al cibo e al peso.",
]

# ============================================================
# CONSEGUENZE - Cosa succederà se non cambiano
# ============================================================

CONSEGUENZE_SALUTE = [
    "La mia salute continuerà a peggiorare. Le analisi sono già al limite.",
    "Rischio di sviluppare diabete, problemi cardiaci o altre patologie.",
    "Dovrò aumentare i farmaci che già prendo.",
    "Il mio corpo non reggerà questo peso ancora per molto.",
    "I dolori articolari e la stanchezza peggioreranno.",
    "Avrò sempre meno energie per fare le cose che amo.",
    "La qualità della mia vita continuerà a deteriorarsi.",
    "Rischio complicazioni che potrebbero essere evitate.",
    "Il mio metabolismo diventerà sempre più lento e resistente.",
    "Sarà sempre più difficile invertire la rotta.",
]

CONSEGUENZE_PSICOLOGICHE = [
    "Continuerò a sentirmi male con me stesso ogni giorno.",
    "La mia autostima toccherà il fondo.",
    "Eviterò sempre più situazioni sociali per vergogna.",
    "Il mio rapporto col cibo diventerà ancora più malato.",
    "Resterò intrappolato in questo circolo vizioso per sempre.",
    "Perderò la speranza di poter cambiare.",
    "Mi isolerò sempre di più dagli altri.",
    "Continuerò a vivere una vita a metà.",
    "Trasmetterò questi problemi ai miei figli.",
    "Guarderò indietro con rimpianto per non aver agito prima.",
]

CONSEGUENZE_RELAZIONALI = [
    "Il mio rapporto di coppia ne risentirà sempre di più.",
    "Eviterò di fare foto, di andare al mare, di vivere.",
    "Non sarò l'esempio che voglio essere per i miei figli.",
    "Le relazioni sociali diventeranno sempre più difficili.",
    "Mi perderò momenti importanti perché mi vergogno del mio corpo.",
    "Continuerò a rifiutare inviti e opportunità.",
    "Il mio partner si stancherà delle mie insicurezze.",
    "Non avrò l'energia per stare dietro ai miei figli.",
    "Mi sentirò sempre inadeguato nelle situazioni sociali.",
    "Perderò la spontaneità e la gioia di vivere.",
]

CONSEGUENZE_PROFESSIONALI = [
    "La stanchezza influirà sempre di più sul mio lavoro.",
    "Perderò opportunità professionali per come mi presento.",
    "Non avrò l'energia per dare il massimo nella mia carriera.",
    "Lo stress continuerà ad accumularsi senza via d'uscita.",
    "La mia produttività continuerà a calare.",
    "Non riuscirò a gestire le responsabilità che ho.",
    "Dovrò rinunciare a viaggi e trasferte di lavoro.",
    "La mia presenza fisica influirà sulle mie possibilità.",
    "Sarò sempre meno performante e motivato.",
    "Il lavoro diventerà un peso invece che una soddisfazione.",
]

# ============================================================
# STORIE - Background del cliente
# ============================================================

STORIE_TEMPLATES = [
    """Sono {professione} e ho {eta} anni. Il mio rapporto con il peso è sempre stato complicato.
Da adolescente ero {stato_adolescenza} e questo ha segnato la mia relazione col cibo.
Nel corso degli anni ho provato {n_diete} diete diverse, {diete_provate}.
{evento_scatenante}
Attualmente peso {peso_attuale} kg e vorrei arrivare a {peso_obiettivo} kg.
{situazione_attuale}""",

    """Ho {eta} anni e faccio {professione}. La mia storia col peso inizia {quando_inizia}.
{background_familiare}
Ho provato di tutto: {tentativi_passati}.
{momento_decisivo}
Oggi mi trovo a pesare {peso_attuale} kg, {differenza_peso} rispetto a {tempo_fa}.
{motivazione_attuale}""",

    """{professione}, {eta} anni. {situazione_familiare}.
Il mio peso ha iniziato ad essere un problema {quando_problema}.
{causa_principale}
Ho tentato {tentativi} ma {risultati_tentativi}.
{punto_rottura}
Peso {peso_attuale} kg e il mio obiettivo è {peso_obiettivo} kg.
{aspettative}""",

    """Mi chiamo {nome} e ho {eta} anni. Lavoro come {professione}.
{storia_peso_giovinezza}
{cambiamento_vita}
Da quel momento il mio peso è {andamento_peso}.
Ho provato a {tentativi} ma {esito}.
Oggi peso {peso_attuale} kg. {stato_emotivo}
{perche_ora}""",
]

STATI_ADOLESCENZA = [
    "normopeso", "leggermente sovrappeso", "molto magro/a", "in sovrappeso",
    "sempre a dieta", "preso/a in giro per il peso"
]

DIETE_PROVATE = [
    "Weight Watchers, Dukan, dieta del gruppo sanguigno",
    "dieta chetogenica, digiuno intermittente, dieta mediterranea",
    "conta calorie, dieta proteica, dieta a zona",
    "Herbalife, tisane dimagranti, integratori vari",
    "diete fai da te trovate online",
    "diete prescritte da nutrizionisti e dietologi",
    "diete lampo pre-estate che non hanno mai funzionato"
]

EVENTI_SCATENANTI = [
    "Tutto è peggiorato dopo la nascita del mio primo figlio.",
    "Il divorzio mi ha fatto perdere completamente il controllo.",
    "Un periodo di forte stress lavorativo ha scatenato tutto.",
    "Dopo aver smesso di fumare ho preso 20 kg.",
    "La menopausa ha cambiato completamente il mio metabolismo.",
    "Un lutto mi ha fatto rifugiare nel cibo.",
    "Il lockdown ha peggiorato drasticamente la situazione.",
    "Un problema di salute mi ha costretto a fermarmi e ho preso peso.",
    "Cambiare lavoro e città ha stravolto le mie abitudini.",
    "Una relazione tossica mi ha fatto sviluppare un rapporto malato col cibo."
]

BACKGROUND_FAMILIARI = [
    "In famiglia siamo tutti in sovrappeso, il cibo è sempre stato al centro di tutto.",
    "Mia madre mi ha messo a dieta a 12 anni. Da lì è iniziato tutto.",
    "I miei genitori usavano il cibo come premio e punizione.",
    "Nella mia famiglia non si parlava di emozioni, si mangiava.",
    "Ho ereditato cattive abitudini alimentari dalla mia famiglia.",
    "I miei erano fissati con le diete e mi hanno trasmesso le loro ossessioni.",
    "A casa mia si buttava via pochissimo, dovevo sempre finire tutto nel piatto."
]

SITUAZIONI_FAMILIARI = [
    "Sposato/a con due figli",
    "Single dopo una separazione",
    "In coppia senza figli",
    "Divorziato/a con figli",
    "Vedovo/a",
    "Convivente",
    "Single per scelta",
    "Sposato/a da poco",
    "In una relazione a distanza",
    "Separato/a in fase di divorzio"
]


def generate_peso_realistico(genere: str, eta: int) -> tuple:
    """Genera peso attuale e obiettivo realistici"""
    if genere == 'donna':
        if eta < 30:
            peso_base = random.randint(55, 65)
            sovrappeso = random.randint(8, 35)
        elif eta < 50:
            peso_base = random.randint(58, 68)
            sovrappeso = random.randint(10, 40)
        else:
            peso_base = random.randint(60, 70)
            sovrappeso = random.randint(8, 35)
    else:  # uomo
        if eta < 30:
            peso_base = random.randint(70, 80)
            sovrappeso = random.randint(10, 40)
        elif eta < 50:
            peso_base = random.randint(75, 85)
            sovrappeso = random.randint(12, 45)
        else:
            peso_base = random.randint(78, 88)
            sovrappeso = random.randint(10, 35)

    peso_attuale = peso_base + sovrappeso
    peso_obiettivo = peso_base + random.randint(0, 8)

    return peso_attuale, peso_obiettivo


def generate_storia(cliente_data: dict) -> str:
    """Genera storia personalizzata per il cliente"""
    nome = cliente_data['nome_cognome'].split()[0]
    eta = cliente_data['eta']
    genere = cliente_data['genere']
    professione = cliente_data['professione']

    peso_attuale, peso_obiettivo = generate_peso_realistico(genere, eta)

    # Scegli template casuale
    template = random.choice(STORIE_TEMPLATES)

    # Genera elementi variabili
    n_diete = random.randint(3, 15)
    tempo_fa = random.choice(["5 anni fa", "10 anni fa", "al liceo", "prima della gravidanza", "prima del matrimonio"])
    differenza = peso_attuale - peso_obiettivo

    replacements = {
        '{nome}': nome,
        '{eta}': str(eta),
        '{professione}': professione.lower(),
        '{stato_adolescenza}': random.choice(STATI_ADOLESCENZA),
        '{n_diete}': str(n_diete),
        '{diete_provate}': random.choice(DIETE_PROVATE),
        '{evento_scatenante}': random.choice(EVENTI_SCATENANTI),
        '{peso_attuale}': str(peso_attuale),
        '{peso_obiettivo}': str(peso_obiettivo),
        '{background_familiare}': random.choice(BACKGROUND_FAMILIARI),
        '{situazione_familiare}': random.choice(SITUAZIONI_FAMILIARI),
        '{quando_inizia}': random.choice(["dall'adolescenza", "dopo i 30 anni", "dopo la prima gravidanza", "negli ultimi 5 anni", "da sempre"]),
        '{quando_problema}': random.choice(["dopo i 25 anni", "con l'inizio del lavoro", "dopo il matrimonio", "negli ultimi anni", "dopo un evento traumatico"]),
        '{causa_principale}': random.choice([
            "La causa principale è lo stress che mi porta a mangiare in modo compulsivo.",
            "Credo che il problema sia emotivo più che fisico.",
            "Ho un metabolismo molto lento e faccio fatica a perdere peso.",
            "Il mio lavoro sedentario e gli orari impossibili non aiutano.",
            "Non ho mai imparato a mangiare in modo sano."
        ]),
        '{tentativi_passati}': random.choice([
            "nutrizionisti, app per contare calorie, palestra",
            "diete drastiche, digiuni, integratori",
            "personal trainer, dietologo, psicologo",
            "di tutto un po', senza mai essere costante"
        ]),
        '{tentativi}': random.choice([
            "diverse volte di mettermi a dieta",
            "di iscrivermi in palestra",
            "di cambiare le mie abitudini da solo",
            "vari percorsi con specialisti"
        ]),
        '{risultati_tentativi}': random.choice([
            "ogni volta perdo qualche chilo e poi li riprendo tutti",
            "non riesco mai ad essere costante per più di qualche settimana",
            "i risultati non durano mai",
            "niente ha funzionato a lungo termine"
        ]),
        '{momento_decisivo}': random.choice([
            "Ho deciso di agire dopo aver visto una mia foto recente.",
            "Le ultime analisi del sangue mi hanno spaventato.",
            "Non riesco più a fare le scale senza affannarmi.",
            "Voglio essere un esempio per i miei figli.",
            "Mi sono reso conto che non posso andare avanti così."
        ]),
        '{punto_rottura}': random.choice([
            "Il punto di rottura è stato quando non sono riuscito/a a entrare nei vestiti dell'anno scorso.",
            "Ho toccato il fondo quando mi sono pesato/a e ho visto il numero più alto di sempre.",
            "Mio figlio mi ha chiesto perché sono sempre stanco/a. Lì ho capito.",
            "Un commento del medico mi ha fatto aprire gli occhi."
        ]),
        '{tempo_fa}': tempo_fa,
        '{differenza_peso}': f"+{differenza} kg" if differenza > 0 else f"{differenza} kg",
        '{motivazione_attuale}': random.choice([
            "Questa volta voglio farlo per me, non per gli altri.",
            "Sono determinato/a a cambiare una volta per tutte.",
            "Ho capito che ho bisogno di aiuto professionale.",
            "Non voglio più rimandare. È il momento giusto."
        ]),
        '{storia_peso_giovinezza}': random.choice([
            "Da bambino/a ero un po' in carne, e le prese in giro dei compagni mi hanno segnato.",
            "Sono sempre stato/a magro/a fino ai 25 anni, poi è iniziato l'incubo.",
            "Ho sempre oscillato tra periodi di magrezza e periodi di sovrappeso.",
            "La mia adolescenza è stata segnata dalle diete imposte da mia madre."
        ]),
        '{cambiamento_vita}': random.choice([
            "Poi è arrivato il lavoro d'ufficio e tutto è cambiato.",
            "Dopo il matrimonio ho iniziato a trascurarmi.",
            "La nascita dei figli ha stravolto la mia vita.",
            "Un periodo di depressione ha fatto precipitare tutto."
        ]),
        '{andamento_peso}': random.choice([
            "aumentato costantemente",
            "diventato una montagna russa",
            "fuori controllo",
            "sempre più difficile da gestire"
        ]),
        '{esito}': random.choice([
            "non ho mai ottenuto risultati duraturi",
            "dopo poche settimane mollavo sempre",
            "il peso tornava sempre, spesso con gli interessi",
            "non riuscivo a trovare la motivazione giusta"
        ]),
        '{stato_emotivo}': random.choice([
            "Mi sento stanco/a e frustrato/a.",
            "Non mi riconosco più allo specchio.",
            "Ho perso fiducia in me stesso/a.",
            "Sono arrivato/a al punto di non poter più ignorare il problema."
        ]),
        '{perche_ora}': random.choice([
            "Ho deciso di agire ora perché non voglio più vivere così.",
            "Questa volta voglio un approccio diverso, più completo.",
            "Ho capito che da solo/a non ce la faccio.",
            "Voglio ritrovare il benessere fisico e mentale."
        ]),
        '{situazione_attuale}': random.choice([
            "Attualmente mi sento bloccato/a e ho bisogno di aiuto.",
            "So che devo cambiare approccio per ottenere risultati diversi.",
            "Spero che questo percorso sia quello giusto.",
            "Sono pronto/a a impegnarmi seriamente questa volta."
        ]),
        '{aspettative}': random.choice([
            "Mi aspetto un percorso impegnativo ma sono motivato/a.",
            "Spero di trovare finalmente un equilibrio.",
            "Voglio imparare a mangiare bene, non solo perdere peso.",
            "Cerco un cambiamento che duri nel tempo."
        ])
    }

    storia = template
    for key, value in replacements.items():
        storia = storia.replace(key, value)

    return storia.strip()


def generate_problema() -> str:
    """Genera il problema principale del cliente"""
    # Mix di diverse categorie di problemi
    categoria = random.choices(
        ['peso', 'emotivo', 'salute', 'lifestyle'],
        weights=[40, 30, 15, 15]
    )[0]

    problemi_map = {
        'peso': PROBLEMI_PESO,
        'emotivo': PROBLEMI_EMOTIVI,
        'salute': PROBLEMI_SALUTE,
        'lifestyle': PROBLEMI_LIFESTYLE
    }

    problema_principale = random.choice(problemi_map[categoria])

    # 40% probabilità di aggiungere un secondo problema
    if random.random() < 0.4:
        altre_categorie = [c for c in problemi_map.keys() if c != categoria]
        seconda_categoria = random.choice(altre_categorie)
        secondo_problema = random.choice(problemi_map[seconda_categoria])
        return f"{problema_principale}\n\nInoltre: {secondo_problema}"

    return problema_principale


def generate_paure() -> str:
    """Genera le paure del cliente"""
    # Seleziona 2-4 paure da diverse categorie
    n_paure = random.randint(2, 4)

    tutte_paure = (
        PAURE_FALLIMENTO +
        PAURE_CAMBIAMENTO +
        PAURE_SALUTE +
        PAURE_PSICOLOGICHE
    )

    paure_selezionate = random.sample(tutte_paure, n_paure)

    return "\n".join([f"• {p}" for p in paure_selezionate])


def generate_conseguenze() -> str:
    """Genera le conseguenze se non cambiano"""
    # Seleziona 2-3 conseguenze da diverse categorie
    n_conseguenze = random.randint(2, 3)

    tutte_conseguenze = (
        CONSEGUENZE_SALUTE +
        CONSEGUENZE_PSICOLOGICHE +
        CONSEGUENZE_RELAZIONALI +
        CONSEGUENZE_PROFESSIONALI
    )

    conseguenze_selezionate = random.sample(tutte_conseguenze, n_conseguenze)

    return "\n".join([f"• {c}" for c in conseguenze_selezionate])


def main():
    from corposostenibile import create_app
    from corposostenibile.extensions import db
    from corposostenibile.models import Cliente
    from datetime import date

    app = create_app()

    with app.app_context():
        print("=" * 60)
        print("SEED CLIENTS - Step 2: Storia, Problema, Paure, Conseguenze")
        print("=" * 60)

        # Conta clienti
        total_clients = Cliente.query.count()
        print(f"\n📊 Clienti da aggiornare: {total_clients:,}")

        if total_clients == 0:
            print("❌ Nessun cliente trovato. Esegui prima seed_fake_clients.py")
            return

        # ============================================================
        # AGGIORNAMENTO CLIENTI
        # ============================================================
        print(f"\n📝 Generazione contenuti per {total_clients:,} clienti...")

        start_time = datetime.now()
        updated = 0

        # Processa a batch per efficienza
        offset = 0
        while offset < total_clients:
            # Carica batch di clienti
            clienti = Cliente.query.order_by(Cliente.cliente_id).offset(offset).limit(BATCH_SIZE).all()

            if not clienti:
                break

            for cliente in clienti:
                # Calcola età
                today = date.today()
                if cliente.data_di_nascita:
                    eta = today.year - cliente.data_di_nascita.year
                    if today.month < cliente.data_di_nascita.month or \
                       (today.month == cliente.data_di_nascita.month and today.day < cliente.data_di_nascita.day):
                        eta -= 1
                else:
                    eta = random.randint(25, 55)

                cliente_data = {
                    'nome_cognome': cliente.nome_cognome,
                    'eta': eta,
                    'genere': cliente.genere or 'donna',
                    'professione': cliente.professione or 'Impiegato/a'
                }

                # Genera contenuti
                cliente.storia_cliente = generate_storia(cliente_data)
                cliente.problema = generate_problema()
                cliente.paure = generate_paure()
                cliente.conseguenze = generate_conseguenze()

            db.session.commit()

            updated += len(clienti)
            progress = (updated / total_clients) * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = updated / elapsed if elapsed > 0 else 0
            eta_time = (total_clients - updated) / rate if rate > 0 else 0

            print(f"  ✅ {updated:,}/{total_clients:,} ({progress:.1f}%) - {rate:.0f}/sec - ETA: {eta_time:.0f}s")

            offset += BATCH_SIZE

        # ============================================================
        # RIEPILOGO
        # ============================================================
        elapsed_total = (datetime.now() - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("RIEPILOGO")
        print("=" * 60)

        # Verifica alcuni record
        sample = Cliente.query.filter(Cliente.storia_cliente.isnot(None)).limit(3).all()

        print(f"\n📊 Statistiche:")
        print(f"   Clienti aggiornati: {updated:,}")
        print(f"   Tempo totale: {elapsed_total:.1f} secondi")
        print(f"   Rate: {updated/elapsed_total:.0f} clienti/secondo")

        print("\n📋 Esempio cliente aggiornato:")
        if sample:
            c = sample[0]
            print(f"\n   Nome: {c.nome_cognome}")
            print(f"\n   STORIA:")
            print(f"   {c.storia_cliente[:300]}...")
            print(f"\n   PROBLEMA:")
            print(f"   {c.problema[:200]}...")
            print(f"\n   PAURE:")
            print(f"   {c.paure[:200]}...")
            print(f"\n   CONSEGUENZE:")
            print(f"   {c.conseguenze[:200]}...")

        print("\n✅ STEP 2 COMPLETATO!")


if __name__ == '__main__':
    main()
