import {
  isAdminOrCco as isAdminOrCcoUser,
  isProfessionistaStandard,
  isTeamLeaderRestricted,
  normalizeSpecialtyGroup,
} from './rbacScope';

export const TOUR_SPECIALTY_META = {
  all: {
    key: 'all',
    label: 'Tutte le aree',
    roleLabel: 'professionista',
    scopeLabel: 'area clinica',
  },
  nutrizione: {
    key: 'nutrizione',
    label: 'Nutrizione',
    roleLabel: 'nutrizionista',
    scopeLabel: 'area nutrizione',
  },
  coaching: {
    key: 'coaching',
    label: 'Coaching',
    roleLabel: 'coach',
    scopeLabel: 'area coaching',
  },
  psicologia: {
    key: 'psicologia',
    label: 'Psicologia',
    roleLabel: 'psicologo',
    scopeLabel: 'area psicologia',
  },
};

export function normalizeTourSpecialtyKey(specialty) {
  return specialty === 'coach' ? 'coaching' : specialty;
}

export function getTourSpecialtyMeta(specialty) {
  if (!specialty) return null;
  return TOUR_SPECIALTY_META[normalizeTourSpecialtyKey(specialty)] || null;
}

export const DOCUMENTATION_SPECIALTY_OPTIONS = [
  TOUR_SPECIALTY_META.all,
  TOUR_SPECIALTY_META.nutrizione,
  TOUR_SPECIALTY_META.coaching,
  TOUR_SPECIALTY_META.psicologia,
];

export function getRequestedSpecialty(searchParams) {
  const requestedSpecialty = normalizeTourSpecialtyKey(searchParams.get('specialty'));
  if (requestedSpecialty === 'all') return 'all';
  return TOUR_SPECIALTY_META[requestedSpecialty] ? requestedSpecialty : null;
}

export function getRequestedTourAudience(searchParams) {
  const requestedAudience = searchParams.get('tourAudience');
  return requestedAudience === 'team_leader' || requestedAudience === 'professionista'
    ? requestedAudience
    : null;
}

export function getTourContext(user, audienceOverride = null) {
  const isAdminOrCco = isAdminOrCcoUser(user);
  const isRestrictedTeamLeader = isTeamLeaderRestricted(user);
  const isProfessionista = isProfessionistaStandard(user);
  const specialtyGroup = normalizeSpecialtyGroup(user?.specialty);
  const specialtyKey = normalizeTourSpecialtyKey(specialtyGroup);
  const specialtyMeta = getTourSpecialtyMeta(specialtyGroup);
  const audience = isAdminOrCco
    ? (audienceOverride === 'team_leader' ? 'team_leader' : 'professionista')
    : (isRestrictedTeamLeader ? 'team_leader' : 'professionista');

  return {
    isAdminOrCco,
    isRestrictedTeamLeader,
    isProfessionista,
    specialtyGroup,
    specialtyKey,
    specialtyMeta,
    audience,
    isTeamLeaderTour: audience === 'team_leader',
  };
}
