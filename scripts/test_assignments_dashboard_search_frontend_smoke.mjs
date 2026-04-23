#!/usr/bin/env node

/**
 * Frontend smoke test: ricerca AssegnazioniAI
 *
 * Verifica wiring della ricerca (lead + sales):
 * - input search presente con placeholder corretto
 * - query `q` inviata al backend tramite getAssignmentsDashboard
 * - filtro sales con input testo + dropdown presente
 * - debounce effect su search attivo solo in tab sales_ghl
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function main() {
  const pagePath = path.join(repoRoot, 'corposostenibile-clinica', 'src', 'pages', 'team', 'AssegnazioniAI.jsx');
  const source = fs.readFileSync(pagePath, 'utf8');

  assert(
    source.includes('placeholder="Nome lead, email lead/sales, telefono, pacchetto o codice"'),
    'Placeholder ricerca lead/sales non trovato'
  );

  assert(
    source.includes('placeholder="Cerca nome/email sales nel filtro"'),
    'Input testo filtro sales non trovato'
  );

  assert(
    source.includes('q: effectiveSearch,'),
    'Param q non inviato a getAssignmentsDashboard'
  );

  assert(
    source.includes("sales_user_id: nextSection === 'sales_ghl' && nextSalesFilter !== 'all' ? nextSalesFilter : undefined"),
    'Param sales_user_id non inviato a getAssignmentsDashboard'
  );

  assert(
    source.includes('const filteredSalesOptions = useMemo(() => {'),
    'Filtro dropdown sales (testo) non trovato'
  );

  assert(
    source.includes("if (activeSection === 'hm_legacy') return undefined;"),
    'Guard tab HM per ricerca non trovato'
  );

  assert(
    source.includes('}, [search, activeSection]);'),
    'Dipendenze debounce ricerca non trovate'
  );

  console.log('✅ Frontend search smoke passed: ricerca lead/sales + filtro sales dropdown + debounce sono cablati');
}

try {
  main();
} catch (err) {
  console.error('❌ Frontend search smoke failed');
  console.error(err.message || err);
  process.exit(1);
}
