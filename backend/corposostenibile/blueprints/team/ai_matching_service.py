
import os
import json
import logging
from typing import List, Dict, Any, Optional

from flask import current_app
from corposostenibile.extensions import db
from corposostenibile.models import User, UserSpecialtyEnum
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
    def extract_lead_criteria(cls, story: str) -> List[str]:
        """
        Uses Gemini to extract criteria tags from the lead's story.
        Returns a list of strings (tags found in the story).
        """
        if not story:
            return []

        client = cls._get_client()
        schema = CriteriaService.get_schema()
        
        # Flatten schema to a set of unique labels for the prompt
        all_criteria = set()
        for valid_list in schema.values():
            all_criteria.update(valid_list)
        all_criteria_list = sorted(list(all_criteria))

        # Mock response if no client or key
        if not client:
            logger.info("AI Client unavailable, using keyword matching mock.")
            # Simple keyword matching as fallback
            found = []
            story_lower = story.lower()
            for tag in all_criteria_list:
                if tag.lower() in story_lower:
                    found.append(tag)
            return found

        try:
            # Construct Prompt
            prompt = f"""
            You are an expert medical and fitness data analyst.
            Analyze the following patient/client story and identify which of the following criteria tags apply.
            
            Valid Criteria Tags:
            {json.dumps(all_criteria_list, indent=2)}
            
            Client Story:
            "{story}"
            
            Return ONLY a JSON array of strings containing the exact tags identified. 
            Example: ["IBS", "DONNE", "ANSIA"]
            If no tags match, return [].
            """
            
            # Call Gemini
            # Using the model requested by user or latest available
            model_name = "gemini-2.0-flash-exp" 
            
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )
            
            if response.text:
                try:
                    extracted_tags = json.loads(response.text)
                    # Verify tags are valid
                    valid_tags = [tag for tag in extracted_tags if tag in all_criteria]
                    return valid_tags
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from AI response: {response.text}")
                    return []
            
            return []

        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return []

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
        
        # 2. Score Matching
        for prof in professionals:
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
            
            # Valid criteria for this prof's role
            role_valid_criteria = CriteriaService.get_criteria_for_role(spec_val)
            
            score = 0
            matches = []
            
            # Only count matches that are relevant to THIS professional's role
            # (e.g. a Coach shouldn't get points for IBS if it's not in coach schema, 
            # though usually keys are shared or specific)
            
            for tag in criteria_list:
                # Check if tag is in professional's criteria AND is true
                if tag in prof_criteria and prof_criteria[tag] is True:
                     # Check if it's a valid criteria for their role (double check)
                     if tag in role_valid_criteria:
                         score += 1
                         matches.append(tag)
            
            # Penalties? Maybe if they are NOT available?
            # For now, just boolean availability check in frontend or separate flag.
            
            # Append result
            results[category].append({
                'id': prof.id,
                'name': f"{prof.first_name} {prof.last_name}",
                'avatar_url': prof.avatar_path.replace('avatars/', '/uploads/avatars/', 1) if prof.avatar_path and prof.avatar_path.startswith('avatars/') else '/static/assets/immagini/logo_user.png',
                'score': score,
                'matched_tags': matches,
                'total_criteria': len(criteria_list),
                'match_percentage': int((score / len(criteria_list) * 100)) if criteria_list else 0,
                'is_available': True # TODO: check specific availability field if exists
            })
            
        # 3. Sort by Score DESC
        for cat in results:
            results[cat].sort(key=lambda x: x['score'], reverse=True)
            
        return results
