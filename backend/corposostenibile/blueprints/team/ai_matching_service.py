
import os
import json
import logging
from typing import List, Dict, Any, Optional

from flask import current_app
from corposostenibile.extensions import db
from corposostenibile.models import User, UserSpecialtyEnum, ProfessionistCapacity
from .criteria_service import CriteriaService

logger = logging.getLogger(__name__)

# Try importing google-genai
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False
    logger.warning("google-genai library not found. AI features will be mocked.")

class AIMatchingService:
    """
    Service for AI-powered lead analysis and professional matching.
    """

    @staticmethod
    def _get_client():
        if not HAS_GENAI:
            return None
        
        api_key = current_app.config.get("GOOGLE_API_KEY") or os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            logger.warning("GOOGLE_API_KEY not set.")
            return None
            
        return genai.Client(api_key=api_key)

    @classmethod
    def extract_lead_criteria(cls, story: str, target_role: str = None) -> Dict[str, Any]:
        """
        Uses Gemini to extract criteria tags from the lead's story.
        If target_role is provided ('nutrition', 'coach', 'psychology'), 
        analyzes specifically for that domain.
        """
        if not story:
            return {}

        client = cls._get_client()
        schema = CriteriaService.get_schema()
        
        # Determine valid criteria subset
        allowed_criteria = set()
        role_prompt_context = ""
        
        if target_role == 'nutrition':
            allowed_criteria.update(schema.get('nutrizione', []))
            role_prompt_context = "Focalizzati esclusivamente sugli aspetti nutrizionali, abitudini alimentari e obiettivi di peso."
        elif target_role == 'coach':
            allowed_criteria.update(schema.get('coach', []))
            role_prompt_context = "Focalizzati esclusivamente sugli obiettivi di allenamento, fitness, stile di vita e motivazione."
        elif target_role == 'psychology':
            allowed_criteria.update(schema.get('psicologia', []))
            role_prompt_context = "Focalizzati esclusivamente sugli aspetti psicologici, emotivi, stress e relazione con il cibo."
        else:
            # Fallback (legacy or full): include all
            for valid_list in schema.values():
                allowed_criteria.update(valid_list)
            role_prompt_context = "Fornisci un'analisi generale del profilo."

        all_criteria_list = sorted(list(allowed_criteria))

        # Mock response if no client or key
        if not client:
            logger.info("AI Client unavailable, using keyword matching mock.")
            # Simple keyword matching as fallback
            found = []
            story_lower = story.lower()
            for tag in all_criteria_list:
                if tag.lower() in story_lower:
                    found.append(tag)
            
            return {
                'summary': f"Analisi mock ({target_role or 'generale'})",
                'criteria': found,
                'suggested_focus': ['Mock focus 1', 'Mock focus 2']
            }

        try:
            # Construct Prompt
            prompt = f"""
            Analizza la seguente storia di un cliente per un servizio di nutrizione e benessere.
            {role_prompt_context}
            
            Storia Cliente:
            "{story}"
            
            Estrai le seguenti informazioni in formato JSON:
            1. "summary": Una breve sintesi (2-3 frasi) del profilo focalizzata sul dominio richiesto.
            2. "criteria": Una lista di tag selezionati ESCLUSIVAMENTE da questo set di criteri validi: {json.dumps(all_criteria_list)}.
            3. "suggested_focus": Una lista di 2-3 punti chiave su cui il professionista ({target_role or 'team'}) dovrebbe concentrarsi.

            Formatta la risposta come un oggetto JSON valido con chiavi: "summary", "criteria", "suggested_focus".
            """
            
            # Call Gemini
            # Override via env/config: GEMINI_LEAD_CRITERIA_MODEL
            # Default: gemini-flash-latest (più compatibile con quota free-tier in diversi progetti)
            model_name = (
                current_app.config.get("GEMINI_LEAD_CRITERIA_MODEL")
                or os.environ.get("GEMINI_LEAD_CRITERIA_MODEL")
                or "gemini-flash-latest"
            )

            def _call(model: str):
                return client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    ),
                )

            try:
                response = _call(model_name)
            except Exception as exc:
                # Fallback automatico se il modello scelto ha quota 0/non disponibile.
                fallback_model = "gemini-flash-latest"
                if model_name != fallback_model:
                    logger.warning(
                        "Gemini call failed for model=%s (%s). Retrying with %s",
                        model_name,
                        str(exc)[:200],
                        fallback_model,
                    )
                    response = _call(fallback_model)
                else:
                    raise
            
            if response.text:
                try:
                    analysis = json.loads(response.text)
                    # Verify criteria are valid
                    extracted = analysis.get('criteria', [])
                    valid_extracted = [tag for tag in extracted if tag in allowed_criteria]
                    
                    return {
                        'summary': analysis.get('summary', 'Sintesi non disponibile'),
                        'criteria': valid_extracted,
                        'suggested_focus': analysis.get('suggested_focus', [])
                    }
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from AI response: {response.text}")
                    return {'summary': 'Errore analisi', 'criteria': [], 'suggested_focus': []}
            
            return {'summary': 'Nessuna risposta dall\'AI', 'criteria': [], 'suggested_focus': []}

        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return {'summary': 'Errore sistemico', 'criteria': [], 'suggested_focus': []}

    @classmethod
    def match_professionals(cls, criteria_list: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Matches professionals against the provided list of criteria tags.
        Returns grouped results: { 'nutrizione': [...], 'coach': [...], 'psicologia': [...] }
        """
        results = {
            'nutrizione': [],
            'coach': [],
            'psicologia': []
        }
        
        if not criteria_list:
             # If no criteria, return empty or maybe all? Returning empty specific matches.
             # Or we could return trending/random. For now, empty matches.
             pass

        # 1. Fetch relevant professionals
        specialties_map = {
            'nutrizione': ['nutrizionista', 'nutrizione'],
            'coach': ['coach'],
            'psicologia': ['psicologo', 'psicologia']
        }
        
        all_target_specialties = []
        for s_list in specialties_map.values():
            all_target_specialties.extend(s_list)
            
        professionals = User.query.filter(
            User.specialty.in_(all_target_specialties),
            User.is_active == True
        ).all()

        logger.info(
            f"match_professionals: criteria={len(criteria_list)} tags, "
            f"fetched {len(professionals)} active professionals across target specialties"
        )

        # 1b. Fetch capacity data for all professionals
        prof_ids = [p.id for p in professionals]
        capacities = ProfessionistCapacity.query.filter(
            ProfessionistCapacity.user_id.in_(prof_ids)
        ).all() if prof_ids else []
        capacity_map = {(c.user_id, c.role_type): c for c in capacities}

        # 1c. Fetch active client counts & type breakdown for capacity %
        from .api import (
            _get_assigned_clients_count_map_active_by_role,
            _get_assigned_clients_by_type,
            _get_capacity_weights_by_role,
            _calculate_capacity_metrics,
            CAPACITY_SUPPORT_TYPES,
        )
        assigned_map = _get_assigned_clients_count_map_active_by_role(prof_ids)
        type_breakdown_map = _get_assigned_clients_by_type(prof_ids)
        weights_by_role = _get_capacity_weights_by_role()

        # Map specialty → capacity role_type
        def _cap_role(spec_val):
            if spec_val in ('nutrizionista', 'nutrizione'):
                return 'nutrizionista'
            if spec_val == 'coach':
                return 'coach'
            if spec_val in ('psicologo', 'psicologia'):
                return 'psicologa'
            return None

        # 2. Score Matching (skip professionals marked as unavailable)
        for prof in professionals:
            ai_notes = prof.assignment_ai_notes or {}
            if isinstance(ai_notes, str):
                try:
                    ai_notes = json.loads(ai_notes) or {}
                except (json.JSONDecodeError, TypeError):
                    ai_notes = {}
            if not isinstance(ai_notes, dict):
                ai_notes = {}
            if not ai_notes.get('disponibile_assegnazioni', True):
                continue
            # Determine category
            category = 'other'
            spec_val = prof.specialty.value if hasattr(prof.specialty, 'value') else str(prof.specialty)
            
            if spec_val in specialties_map['nutrizione']:
                category = 'nutrizione'
            elif spec_val in specialties_map['coach']:
                category = 'coach'
            elif spec_val in specialties_map['psicologia']:
                category = 'psicologia'
                
            if category == 'other':
                continue
                
            # Calculate Score
            prof_criteria = prof.assignment_criteria or {}
            if isinstance(prof_criteria, str):
                try:
                    prof_criteria = json.loads(prof_criteria) or {}
                except (json.JSONDecodeError, TypeError):
                    prof_criteria = {}
            if not isinstance(prof_criteria, dict):
                prof_criteria = {}
            
            # Valid criteria for this prof's role
            role_valid_criteria = CriteriaService.get_criteria_for_role(spec_val)
            
            points = 0
            matches = []
            
            for tag in criteria_list:
                # Check if tag is in professional's criteria AND is true
                if tag in prof_criteria and prof_criteria[tag] is True:
                     # Check if it's a valid criteria for their role (double check)
                     if tag in role_valid_criteria:
                         points += 1
                         matches.append(tag)
            
            # Calculate percentage
            percentage = int((points / len(criteria_list) * 100)) if criteria_list else 0
            
            # Capacity data
            cap_role = _cap_role(spec_val)
            cap = capacity_map.get((prof.id, cap_role))
            assigned_clients = assigned_map.get((prof.id, cap_role), 0)
            contractual = (cap.max_clients if cap else 0) or 0
            type_counts = type_breakdown_map.get((prof.id, cap_role), {})
            cap_metrics = _calculate_capacity_metrics(
                role_type=cap_role or '',
                assigned_clients=assigned_clients,
                contractual_capacity=contractual,
                type_counts=type_counts,
                weights_by_role=weights_by_role,
            )

            # Append result
            results[category].append({
                'id': prof.id,
                'name': f"{prof.first_name} {prof.last_name}",
                'avatar_url': prof.avatar_path.replace('avatars/', '/uploads/avatars/', 1) if prof.avatar_path and prof.avatar_path.startswith('avatars/') else '/static/assets/immagini/logo_user.png',
                'score': percentage,
                'points': points,
                'match_reasons': matches,
                'total_criteria': len(criteria_list),
                'match_percentage': percentage,
                'is_available': ai_notes.get('disponibile_assegnazioni', True),
                'capacity': {
                    'assigned': assigned_clients,
                    'max': contractual,
                    'percentage': cap_metrics['percentuale_capienza'],
                    'weighted_load': cap_metrics['capienza_ponderata'],
                    'is_over': cap_metrics['is_over_capacity'],
                },
            })
            
        # 3. Sort by Score DESC
        for cat in results:
            results[cat].sort(key=lambda x: x['score'], reverse=True)

        logger.info(
            f"match_professionals result: nutrizione={len(results['nutrizione'])}, "
            f"coach={len(results['coach'])}, psicologia={len(results['psicologia'])}"
        )

        return results
