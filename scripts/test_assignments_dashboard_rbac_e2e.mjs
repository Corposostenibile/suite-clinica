#!/usr/bin/env node

/**
 * E2E smoke script for Task C.5
 * - verifies RBAC helper canAccessAssignmentsDashboard
 * - verifies sidebar entry for /admin/assegnazioni-dashboard exists (label "Assegnazioni")
 *
 * Run from repository root:
 *   node scripts/test_assignments_dashboard_rbac_e2e.mjs
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '..');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

async function loadRbacModule() {
  const rbacPath = path.join(repoRoot, 'corposostenibile-clinica', 'src', 'utils', 'rbacScope.js');
  return import(pathToFileURL(rbacPath).href);
}

function checkSidebarEntry() {
  const menuPath = path.join(repoRoot, 'corposostenibile-clinica', 'src', 'jsx', 'layouts', 'nav', 'Menu.jsx');
  const sidebarPath = path.join(repoRoot, 'corposostenibile-clinica', 'src', 'jsx', 'layouts', 'nav', 'SideBar.jsx');

  const menuSource = fs.readFileSync(menuPath, 'utf8');
  const sidebarSource = fs.readFileSync(sidebarPath, 'utf8');

  assert(
    menuSource.includes("title: 'Assegnazioni'") && menuSource.includes("to: 'admin/assegnazioni-dashboard'"),
    'Sidebar menu entry Assegnazioni -> /admin/assegnazioni-dashboard not found in Menu.jsx'
  );

  assert(
    sidebarSource.includes("item.title === 'Assegnazioni' && !canAccessAssignmentsDashboard(user)"),
    'RBAC gate for Assegnazioni sidebar entry not found in SideBar.jsx'
  );
}

async function checkRbacMatrix() {
  const { canAccessAssignmentsDashboard } = await loadRbacModule();

  const cases = [
    {
      name: 'admin role',
      user: { role: 'admin', is_admin: false },
      expected: true,
    },
    {
      name: 'admin flag',
      user: { role: 'professionista', is_admin: true },
      expected: true,
    },
    {
      name: 'CCO specialty',
      user: { role: 'operations', specialty: 'cco' },
      expected: true,
    },
    {
      name: 'health manager',
      user: { role: 'health_manager' },
      expected: true,
    },
    {
      name: 'health manager team leader flag',
      user: { role: 'team_leader', is_health_manager_team_leader: true },
      expected: true,
    },
    {
      name: 'team leader clinico (restricted)',
      user: { role: 'team_leader', specialty: 'nutrizione' },
      expected: false,
    },
    {
      name: 'professionista standard',
      user: { role: 'professionista', specialty: 'coach' },
      expected: false,
    },
    {
      name: 'influencer',
      user: { role: 'influencer' },
      expected: false,
    },
  ];

  for (const t of cases) {
    const actual = Boolean(canAccessAssignmentsDashboard(t.user));
    assert(actual === t.expected, `[${t.name}] expected ${t.expected}, got ${actual}`);
  }
}

async function main() {
  checkSidebarEntry();
  await checkRbacMatrix();
  console.log('✅ Task C.5 E2E smoke passed: RBAC + sidebar entry are aligned');
}

main().catch((err) => {
  console.error('❌ Task C.5 E2E smoke failed');
  console.error(err.message || err);
  process.exit(1);
});
