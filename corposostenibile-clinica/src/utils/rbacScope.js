export function isAdminOrCco(user) {
  if (!user) return false;
  return Boolean(user.is_admin || user.role === 'admin' || user.specialty === 'cco');
}

export function isTeamLeader(user) {
  return Boolean(user?.role === 'team_leader');
}

export function isHealthManagerUser(user) {
  return Boolean(user?.role === 'health_manager');
}

export function isHealthManagerTeamLeader(user) {
  if (user?.is_health_manager_team_leader === true) return true;
  if (user?.role !== 'team_leader') return false;
  const specialty = String(user?.specialty || '').toLowerCase();
  if (specialty === 'health_manager') return true;
  const departmentName = String(user?.department?.name || '').toLowerCase();
  return departmentName.includes('health') || departmentName.includes('customer success');
}

export function isHealthManagerScopeUser(user) {
  return Boolean(isHealthManagerUser(user) || isHealthManagerTeamLeader(user));
}

export function isTeamLeaderRestricted(user) {
  return Boolean(isTeamLeader(user) && !isAdminOrCco(user) && !isHealthManagerTeamLeader(user));
}

export function isProfessionistaStandard(user) {
  return Boolean(user?.role === 'professionista' && !isAdminOrCco(user));
}

export function normalizeSpecialtyGroup(specialty) {
  const s = String(specialty || '').toLowerCase();
  if (s === 'nutrizione' || s === 'nutrizionista') return 'nutrizione';
  if (s === 'psicologia' || s === 'psicologo') return 'psicologia';
  if (s === 'coach') return 'coach';
  if (s === 'medico') return 'medico';
  return null;
}

export function canAccessGlobalCheckPage(user) {
  // Admin, CCO, Team Leader, e Professionisti standard (nutrizionista/coach/psicologo)
  // Health Manager esclusi
  return !isHealthManagerScopeUser(user);
}

export function canAccessQualityPage(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeaderRestricted(user));
}

export function canAccessTeamLists(user) {
  if (isAdminOrCco(user)) return true;
  if (isHealthManagerTeamLeader(user)) return true;
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessTrialPages(user) {
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessAiAssignments(user) {
  // Admin, CCO, Health Manager (user e TL) possono accedere
  // Team leader nutrizione/coach/psicologia e professionisti standard NO
  return !isProfessionistaStandard(user) && !isTeamLeaderRestricted(user);
}

export function canAccessSpecializzazione(user) {
  // Admin, CCO, Health Manager (user e TL), e Team Leader clinici
  return !isProfessionistaStandard(user) && !isHealthManagerUser(user);
}

export function canAccessCapacity(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeaderRestricted(user) || isHealthManagerTeamLeader(user));
}

export function canViewOtherProfessionalProfile(user) {
  if (isAdminOrCco(user)) return true;
  if (isTeamLeader(user)) return true;
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessTaskPage(user) {
  return !isHealthManagerScopeUser(user);
}

export function canAccessTrainingPage(user) {
  return !isHealthManagerScopeUser(user);
}

export function canAccessSecondaryModules(user) {
  return !isHealthManagerScopeUser(user);
}
