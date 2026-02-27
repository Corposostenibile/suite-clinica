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
  if (user?.role !== 'team_leader') return false;
  const specialty = String(user?.specialty || '').toLowerCase();
  if (specialty === 'health_manager') return true;
  const departmentName = String(user?.department?.name || '').toLowerCase();
  return departmentName.includes('health') || departmentName.includes('customer success');
}

export function isTeamLeaderRestricted(user) {
  return Boolean(isTeamLeader(user) && !isAdminOrCco(user));
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
  return !isProfessionistaStandard(user) && !isHealthManagerUser(user);
}

export function canAccessQualityPage(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeader(user));
}

export function canAccessTeamLists(user) {
  return !isProfessionistaStandard(user) && !isHealthManagerUser(user);
}

export function canAccessTrialPages(user) {
  return !isProfessionistaStandard(user) && !isHealthManagerUser(user);
}

export function canAccessAiAssignments(user) {
  return !isProfessionistaStandard(user) || isHealthManagerUser(user);
}

export function canAccessCapacity(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeader(user) || isHealthManagerUser(user));
}

export function canViewOtherProfessionalProfile(user) {
  return !isProfessionistaStandard(user) && !isHealthManagerUser(user);
}

export function canAccessTaskPage(user) {
  return !isHealthManagerUser(user);
}

export function canAccessTrainingPage(user) {
  return !isHealthManagerUser(user);
}

export function canAccessSecondaryModules(user) {
  return !isHealthManagerUser(user);
}
