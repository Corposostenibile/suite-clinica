export function isAdminOrCco(user) {
  if (!user) return false;
  return Boolean(user.is_admin || user.role === 'admin' || user.specialty === 'cco');
}

export function isTeamLeader(user) {
  return Boolean(user?.role === 'team_leader');
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
  return !isProfessionistaStandard(user);
}

export function canAccessQualityPage(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeader(user));
}

export function canAccessTeamLists(user) {
  return !isProfessionistaStandard(user);
}

export function canAccessTrialPages(user) {
  return !isProfessionistaStandard(user);
}

export function canAccessAiAssignments(user) {
  return !isProfessionistaStandard(user);
}

export function canAccessCapacity(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeader(user));
}

export function canViewOtherProfessionalProfile(user) {
  return !isProfessionistaStandard(user);
}

