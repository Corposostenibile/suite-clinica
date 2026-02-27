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
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessQualityPage(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeaderRestricted(user));
}

export function canAccessTeamLists(user) {
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessTrialPages(user) {
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessAiAssignments(user) {
  return !isProfessionistaStandard(user) || isHealthManagerScopeUser(user);
}

export function canAccessCapacity(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeaderRestricted(user) || isHealthManagerTeamLeader(user));
}

export function canViewOtherProfessionalProfile(user) {
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
