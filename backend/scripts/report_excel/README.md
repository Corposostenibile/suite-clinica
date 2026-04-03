# Report Statistiche Check (KPI Professionisti)

Script per generare report Excel delle statistiche di check settimanali.

## Descrizione

`generate_stats_prod.py` estrae i dati dal database di produzione e genera un report Excel con tre fogli:

1. **Per Professionista**: statistiche dettagliate per ogni professionista (voti medi, check aspettati/ricevuti, % check saltati, N° clienti unici)
2. **Per Team**: aggregazione delle statistiche per team
3. **Per Dipartimento**: aggregazione delle statistiche per dipartimento (Nutrizione, Coach, Psicologia)

### Metriche Calcolate

- **Voto medio professionista**: media dei voti assegnati al professionista nei check
- **Voto medio percorso**: media dei voti assegnati al percorso/progressi
- **NPS (media dei due)**: media tra voto professionista e voto percorso
- **Check aspettati**: numero di check attesi (1 a settimana, dopo 14 giorni dall'inizio)
- **Check ricevuti**: numero di check effettivamente compilati
- **% Check saltati**: percentuale di check non compilati

## Esecuzione in Produzione (GCP Kubernetes)

**Non serve fare deploy/push!** Lo script viene copiato ed eseguito direttamente sul pod esistente.

### Procedura

Esegui dalla cartella `backend/scripts/report_excel/`:

```bash
# 1. Crea la cartella report_excel sul pod (se non esiste)
kubectl exec deploy/suite-clinica-backend -c backend -- mkdir -p /app/scripts/report_excel

# 2. Copia lo script sul pod
kubectl cp generate_stats_prod.py suite-clinica-backend-6ff4b7494d-qg72b:/app/scripts/report_excel/generate_stats_prod.py -c backend

# 3. Esegui lo script e salva l'Excel in locale
kubectl exec suite-clinica-backend-6ff4b7494d-qg72b -c backend -- bash -lc '
  cd /app/scripts/report_excel
  PYTHONPATH=/app python generate_stats_prod.py --out /tmp >/dev/null 2>&1
  cat /tmp/Report_KPI_Professionisti_*.xlsx
' > ./Report_KPI_Professionisti_$(date +%Y%m%d).xlsx
```

**Nota:** Sostituisci `suite-clinica-backend-6ff4b7494d-qg72b` con il nome attuale del pod. Per trovarlo:
```bash
kubectl get pods | grep backend | grep Running | head -1 | awk '{print $1}'
```

Il comando:
1. Copia lo script locale sul pod backend (senza bisogno di deploy)
2. Genera il report Excel in `/tmp` sul pod
3. Trasferisce il file direttamente in locale tramite redirect stdout

## Output

Il file generato sarà nella cartella corrente con nome:
```
Report_KPI_Professionisti_YYYYMMDD.xlsx
```

Esempio: `Report_KPI_Professionisti_20260403.xlsx`

## Note

- Lo script considera solo clienti con stato "Attivo"
- I check aspettati iniziano 14 giorni dopo la data di inizio servizio
- La percentuale di check saltati può essere 0% se ricevuti > aspettati (non negativo)
