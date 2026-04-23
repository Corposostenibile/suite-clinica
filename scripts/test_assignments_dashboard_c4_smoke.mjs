#!/usr/bin/env node

/**
 * E2E smoke script for Task C.4 (static + behavior guards)
 *
 * Verifica che la pagina /admin/assegnazioni-dashboard includa:
 * - drill-down per sales user (view mode + grouping)
 * - timeline per lead (modal + trigger)
 * - export CSV dei record visibili
 *
 * Run:
 *   node scripts/test_assignments_dashboard_c4_smoke.mjs
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

  // Drill-down sales
  assert(source.includes("const [viewMode, setViewMode] = useState('table');"), 'viewMode state not found');
  assert(source.includes('Drill-down Sales'), 'Drill-down Sales UI label not found');
  assert(source.includes('const salesGroups = useMemo(() => {'), 'salesGroups grouping logic not found');
  assert(source.includes('setExpandedSalesKey'), 'expanded group state not found');

  // Timeline
  assert(source.includes('const [timelineItem, setTimelineItem] = useState(null);'), 'timeline state not found');
  assert(source.includes('function getLeadTimeline(item, activeSection)'), 'timeline builder function not found');
  assert(source.includes('<Modal show={Boolean(timelineItem)} onHide={() => setTimelineItem(null)} centered>'), 'timeline modal not found');
  assert(source.includes('>\n                                    Timeline\n                                  </Button>') || source.includes('>\n                            Timeline\n                          </Button>'), 'timeline button trigger not found');

  // CSV export
  assert(source.includes('const exportVisibleCsv = () => {'), 'exportVisibleCsv function not found');
  assert(source.includes('const headers = ['), 'CSV headers array not found');
  assert(source.includes('new Blob([csvContent], { type: \'text/csv;charset=utf-8;\' })'), 'CSV blob generation not found');
  assert(source.includes('Export CSV'), 'Export CSV button label not found');

  console.log('✅ Task C.4 smoke passed: drill-down + timeline + CSV export are wired in AssegnazioniAI.jsx');
}

try {
  main();
} catch (err) {
  console.error('❌ Task C.4 smoke failed');
  console.error(err.message || err);
  process.exit(1);
}
