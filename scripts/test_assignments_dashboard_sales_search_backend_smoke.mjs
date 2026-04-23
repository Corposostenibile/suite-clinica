#!/usr/bin/env node

/**
 * Backend smoke (static): verifica supporto ricerca/filtro Sales nell'endpoint
 * /ghl/api/admin/assignments-dashboard
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
  const routePath = path.join(repoRoot, 'backend', 'corposostenibile', 'blueprints', 'ghl_integration', 'routes.py');
  const source = fs.readFileSync(routePath, 'utf8');

  assert(source.includes("sales_user_filter_raw = (request.args.get('sales_user_id') or '').strip()"), 'sales_user_id parsing non trovato');
  assert(source.includes("if sales_user_filter == 'unassigned':"), 'Filtro sales unassigned non trovato');
  assert(source.includes('SalesLead.sales_user_id == sales_user_filter'), 'Filtro sales_user_id numerico non trovato');

  assert(source.includes('User.first_name.ilike(like)'), 'Ricerca per nome sales non trovata (User.first_name)');
  assert(source.includes('User.last_name.ilike(like)'), 'Ricerca per cognome sales non trovata (User.last_name)');
  assert(source.includes('User.email.ilike(like)'), 'Ricerca per email sales non trovata (User.email)');

  console.log('✅ Backend sales-search smoke passed: filtro sales_user_id + ricerca nome/email sales presenti');
}

try {
  main();
} catch (err) {
  console.error('❌ Backend sales-search smoke failed');
  console.error(err.message || err);
  process.exit(1);
}
