#!/usr/bin/env node

/**
 * Smoke Task C.7: drawer "Perché questo professionista" in dashboard admin
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

  assert(source.includes("const [whyDrawerItem, setWhyDrawerItem] = useState(null);"), 'State drawer non trovato');
  assert(source.includes('Perché questo professionista'), 'Label bottone/titolo drawer non trovata');
  assert(source.includes('<Offcanvas show={Boolean(whyDrawerItem)}'), 'Offcanvas drawer non trovato');
  assert(source.includes('function buildWhySections(analysis)'), 'Parser sezioni motivazioni non trovato');
  assert(source.includes('onClick={() => setWhyDrawerItem(item)}'), 'Trigger apertura drawer non trovato');

  console.log('✅ Task C.7 smoke passed: drawer motivazioni AI presente e cablato');
}

try {
  main();
} catch (err) {
  console.error('❌ Task C.7 smoke failed');
  console.error(err.message || err);
  process.exit(1);
}
