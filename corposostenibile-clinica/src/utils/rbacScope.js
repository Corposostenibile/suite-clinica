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

export function isMarketingUser(user) {
  return Boolean(user?.role === 'marketing');
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
  if (s === 'psicologia' || s === 'psicologo' || s === 'psicologa') return 'psicologia';
  if (s === 'coach' || s === 'coaching') return 'coach';
  if (s === 'medico') return 'medico';
  return null;
}

export function canAccessMarketingView(user) {
  // Visuale Marketing: accessibile al ruolo marketing + admin/CCO per review
  return Boolean(isMarketingUser(user) || isAdminOrCco(user));
}

export function canAccessClientiListaGenerale(user) {
  // Lista generale clienti: negata al ruolo marketing (ha la sua visuale dedicata)
  if (isMarketingUser(user)) return false;
  return true;
}

export function canAccessGlobalCheckPage(user) {
  if (!user) return false;
  if (user.role === 'influencer') return false;
  if (isMarketingUser(user)) return false;
  return true;
}

export function canAccessQualityPage(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeaderRestricted(user));
}

export function canAccessTeamLists(user) {
  if (isAdminOrCco(user)) return true;
  if (isHealthManagerTeamLeader(user)) return true;
  if (isMarketingUser(user)) return false;
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessTrialPages(user) {
  if (isMarketingUser(user)) return false;
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessAiAssignments(user) {
  // Admin, CCO, Health Manager (user e TL) possono accedere
  // Team leader nutrizione/coach/psicologia e professionisti standard NO
  if (isMarketingUser(user)) return false;
  return !isProfessionistaStandard(user) && !isTeamLeaderRestricted(user);
}

export function canAccessSpecializzazione(user) {
  // Admin, CCO, Health Manager (user e TL), e Team Leader clinici
  if (isMarketingUser(user)) return false;
  return !isProfessionistaStandard(user) && !isHealthManagerUser(user);
}

export function canAccessCapacity(user) {
  return Boolean(isAdminOrCco(user) || isTeamLeaderRestricted(user) || isHealthManagerTeamLeader(user));
}

export function canAccessHmCapacityAdmin(user) {
  return Boolean(isAdminOrCco(user) || isHealthManagerTeamLeader(user));
}

export function canViewOtherProfessionalProfile(user) {
  if (isAdminOrCco(user)) return true;
  if (isTeamLeader(user)) return true;
  if (isMarketingUser(user)) return false;
  return !isProfessionistaStandard(user) && !isHealthManagerScopeUser(user);
}

export function canAccessTaskPage(user) {
  if (isMarketingUser(user)) return false;
  return !isHealthManagerScopeUser(user);
}

export function canAccessTrainingPage(user) {
  // Health Manager standard non accedono alla pagina Formazione standalone
  // (vedono la formazione solo dal profilo del professionista)
  // Ma gli Health Manager Team Leader SÌ (hanno teams_led e gestiscono formazione)
  if (isMarketingUser(user)) return false;
  return !isHealthManagerUser(user);
}

export function canAccessSecondaryModules(user) {
  // Marketing non ha accesso a moduli secondari (chat, profilo-edit, clienti-add/modifica, ecc.)
  if (isMarketingUser(user)) return false;
  return !isHealthManagerScopeUser(user);
}

export function canAccessCalendario(user) {
  if (!user) return false;
  if (user.role === 'influencer') return false;
  if (isMarketingUser(user)) return false;
  return true;
}

export function canAccessLoomLibrary(user) {
  if (!user) return false;
  if (user.role === 'influencer') return false;
  if (isMarketingUser(user)) return false;
  return true;
}
