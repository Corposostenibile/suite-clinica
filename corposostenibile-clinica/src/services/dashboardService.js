/**
 * Dashboard Service - API per la dashboard amministrativa
 *
 * Aggrega dati da clientiService e checkService per fornire
 * una panoramica completa per Admin e CCO.
 */

import api from './api';
import checkService from './checkService';
import teamService from './teamService';

const dashboardService = {
  /**
   * Get customer stats (KPI)
   * @returns {Promise} - { total_clienti, nutrizione_attivo, coach_attivo, psicologia_attivo, new_month }
   */
  async getCustomerStats() {
    const response = await api.get('/v1/customers/stats');
    return response.data;
  },

  /**
   * Get check stats for the month with average ratings
   * @returns {Promise} - { stats: { avg_nutrizionista, avg_coach, avg_psicologo }, responses: [] }
   */
  async getCheckStats() {
    return checkService.getAziendaStats('month');
  },

  /**
   * Get HM dashboard stats
   * @returns {Promise} - { kpi: { total, active, ghost, pausa, inScadenza, rinnoviNext15gg } }
   */
  async getHMDashboardStats() {
    const response = await api.get('/v1/customers/hm/dashboard-stats');
    return response.data;
  },

  /**
   * Get all dashboard data in one call
   * @returns {Promise} - Combined stats object
   */
  async getDashboardData() {
    const [customerStats, checkStats] = await Promise.all([
      this.getCustomerStats(),
      this.getCheckStats()
    ]);

    return {
      customers: customerStats,
      checks: checkStats
    };
  },

  /**
   * Filter negative checks (rating < 7)
   * @param {Array} responses - Array of check responses
   * @returns {Array} - Filtered responses with negative ratings
   */
  filterNegativeChecks(responses) {
    if (!responses) return [];

    return responses.filter(r => {
      const hasNegative =
        (r.nutritionist_rating && r.nutritionist_rating < 7) ||
        (r.psychologist_rating && r.psychologist_rating < 7) ||
        (r.coach_rating && r.coach_rating < 7) ||
        (r.progress_rating && r.progress_rating < 7);
      return hasNegative;
    }).map(r => {
      // Identify which ratings are negative with professional info
      const negativeRatings = [];
      if (r.nutritionist_rating && r.nutritionist_rating < 7) {
        negativeRatings.push({
          type: 'Nutrizione',
          value: r.nutritionist_rating,
          professionals: r.nutrizionisti || []
        });
      }
      if (r.coach_rating && r.coach_rating < 7) {
        negativeRatings.push({
          type: 'Coach',
          value: r.coach_rating,
          professionals: r.coaches || []
        });
      }
      if (r.psychologist_rating && r.psychologist_rating < 7) {
        negativeRatings.push({
          type: 'Psicologia',
          value: r.psychologist_rating,
          professionals: r.psicologi || []
        });
      }
      if (r.progress_rating && r.progress_rating < 7) {
        negativeRatings.push({
          type: 'Percorso',
          value: r.progress_rating,
          isProgress: true
        });
      }
      return { ...r, negativeRatings };
    });
  },

  /**
   * Get all teams with their members
   * @returns {Promise} - Array of teams with member details
   */
  async getTeamsWithMembers() {
    try {
      // Get all active teams with members in a single API call
      const teamsResponse = await teamService.getTeams({
        active: '1',
        include_members: '1'
      });
      return teamsResponse.teams || [];
    } catch (error) {
      console.error('Error fetching teams:', error);
      return [];
    }
  },

  /**
   * Calculate ratings per individual team from check responses
   * @param {Array} responses - Array of check responses
   * @param {Array} teams - Array of teams with members
   * @returns {Object} - { nutrizione: [], coach: [], psicologia: [] } grouped by team_type
   */
  calculateTeamRatings(responses, teams) {
    if (!responses || responses.length === 0 || !teams || teams.length === 0) {
      return {
        nutrizione: [],
        coach: [],
        psicologia: []
      };
    }

    // Build a map: user_id -> team info
    const userToTeam = {};
    teams.forEach(team => {
      if (team.members) {
        team.members.forEach(member => {
          userToTeam[member.id] = {
            team_id: team.id,
            team_name: team.name,
            team_type: team.team_type,
            head: team.head
          };
        });
      }
    });

    // Aggregate ratings by team
    const teamStats = {};

    responses.forEach(r => {
      // Nutrizionisti
      if (r.nutrizionisti && r.nutritionist_rating) {
        r.nutrizionisti.forEach(prof => {
          const teamInfo = userToTeam[prof.id];
          if (teamInfo && teamInfo.team_type === 'nutrizione') {
            if (!teamStats[teamInfo.team_id]) {
              teamStats[teamInfo.team_id] = {
                id: teamInfo.team_id,
                name: teamInfo.team_name,
                team_type: teamInfo.team_type,
                head: teamInfo.head,
                total: 0,
                count: 0
              };
            }
            teamStats[teamInfo.team_id].total += r.nutritionist_rating;
            teamStats[teamInfo.team_id].count++;
          }
        });
      }

      // Coach
      if (r.coaches && r.coach_rating) {
        r.coaches.forEach(prof => {
          const teamInfo = userToTeam[prof.id];
          if (teamInfo && teamInfo.team_type === 'coach') {
            if (!teamStats[teamInfo.team_id]) {
              teamStats[teamInfo.team_id] = {
                id: teamInfo.team_id,
                name: teamInfo.team_name,
                team_type: teamInfo.team_type,
                head: teamInfo.head,
                total: 0,
                count: 0
              };
            }
            teamStats[teamInfo.team_id].total += r.coach_rating;
            teamStats[teamInfo.team_id].count++;
          }
        });
      }

      // Psicologi
      if (r.psicologi && r.psychologist_rating) {
        r.psicologi.forEach(prof => {
          const teamInfo = userToTeam[prof.id];
          if (teamInfo && teamInfo.team_type === 'psicologia') {
            if (!teamStats[teamInfo.team_id]) {
              teamStats[teamInfo.team_id] = {
                id: teamInfo.team_id,
                name: teamInfo.team_name,
                team_type: teamInfo.team_type,
                head: teamInfo.head,
                total: 0,
                count: 0
              };
            }
            teamStats[teamInfo.team_id].total += r.psychologist_rating;
            teamStats[teamInfo.team_id].count++;
          }
        });
      }
    });

    // Calculate averages and group by team_type
    const allTeams = Object.values(teamStats).map(t => ({
      ...t,
      average: t.count > 0 ? (t.total / t.count).toFixed(1) : '0.0'
    }));

    // Group by team_type
    return {
      nutrizione: allTeams
        .filter(t => t.team_type === 'nutrizione')
        .sort((a, b) => parseFloat(b.average) - parseFloat(a.average)),
      coach: allTeams
        .filter(t => t.team_type === 'coach')
        .sort((a, b) => parseFloat(b.average) - parseFloat(a.average)),
      psicologia: allTeams
        .filter(t => t.team_type === 'psicologia')
        .sort((a, b) => parseFloat(b.average) - parseFloat(a.average))
    };
  },

  /**
   * Calculate professional rankings from check responses
   * @param {Array} responses - Array of check responses
   * @returns {Object} - { nutrizione: [], coach: [], psicologia: [] } with top and bottom 5
   */
  calculateProfessionalRankings(responses) {
    if (!responses || responses.length === 0) {
      return {
        nutrizione: { top: [], bottom: [] },
        coach: { top: [], bottom: [] },
        psicologia: { top: [], bottom: [] }
      };
    }

    // Aggregate ratings per professional
    const profStats = {
      nutrizione: {},
      coach: {},
      psicologia: {}
    };

    responses.forEach(r => {
      // Nutrizionisti
      if (r.nutrizionisti && r.nutritionist_rating) {
        r.nutrizionisti.forEach(prof => {
          if (!profStats.nutrizione[prof.id]) {
            profStats.nutrizione[prof.id] = {
              id: prof.id,
              nome: prof.nome,
              avatar_path: prof.avatar_path,
              ratings: [],
              total: 0,
              count: 0
            };
          }
          profStats.nutrizione[prof.id].ratings.push(r.nutritionist_rating);
          profStats.nutrizione[prof.id].total += r.nutritionist_rating;
          profStats.nutrizione[prof.id].count++;
        });
      }

      // Coach
      if (r.coaches && r.coach_rating) {
        r.coaches.forEach(prof => {
          if (!profStats.coach[prof.id]) {
            profStats.coach[prof.id] = {
              id: prof.id,
              nome: prof.nome,
              avatar_path: prof.avatar_path,
              ratings: [],
              total: 0,
              count: 0
            };
          }
          profStats.coach[prof.id].ratings.push(r.coach_rating);
          profStats.coach[prof.id].total += r.coach_rating;
          profStats.coach[prof.id].count++;
        });
      }

      // Psicologi
      if (r.psicologi && r.psychologist_rating) {
        r.psicologi.forEach(prof => {
          if (!profStats.psicologia[prof.id]) {
            profStats.psicologia[prof.id] = {
              id: prof.id,
              nome: prof.nome,
              avatar_path: prof.avatar_path,
              ratings: [],
              total: 0,
              count: 0
            };
          }
          profStats.psicologia[prof.id].ratings.push(r.psychologist_rating);
          profStats.psicologia[prof.id].total += r.psychologist_rating;
          profStats.psicologia[prof.id].count++;
        });
      }
    });

    // Calculate averages and sort
    const calculateRanking = (stats) => {
      const professionals = Object.values(stats).map(p => ({
        ...p,
        average: p.count > 0 ? (p.total / p.count).toFixed(1) : 0
      }));

      const sorted = professionals.sort((a, b) => b.average - a.average);

      // Bottom: tutti i professionisti con media <= 7.5 (senza limite)
      const needsImprovement = sorted
        .filter(p => parseFloat(p.average) <= 7.5)
        .sort((a, b) => a.average - b.average);

      return {
        top: sorted.slice(0, 5),
        bottom: needsImprovement
      };
    };

    return {
      nutrizione: calculateRanking(profStats.nutrizione),
      coach: calculateRanking(profStats.coach),
      psicologia: calculateRanking(profStats.psicologia)
    };
  }
};

export default dashboardService;
