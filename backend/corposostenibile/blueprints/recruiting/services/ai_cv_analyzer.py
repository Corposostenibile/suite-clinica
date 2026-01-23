"""
AI CV Analyzer Service using LangChain and Google Gemini.

This service provides AI-powered CV analysis to complement the existing OCR screening.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from flask import current_app

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain.schema import HumanMessage, SystemMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logging.error("LangChain or Google Generative AI not available")


class AICVAnalyzer:
    """AI-powered CV analyzer using Google Gemini via LangChain."""
    
    def __init__(self):
        """Initialize the AI CV analyzer."""
        self.logger = logging.getLogger(__name__)
        self.logger.error("Initializing AI CV Analyzer...")
        self.llm = None
        
        if LANGCHAIN_AVAILABLE:
            self.logger.error("LangChain is available, attempting to initialize Google Gemini")
            try:
                api_key = os.getenv('GOOGLE_API_KEY')
                if not api_key:
                    self.logger.error("GOOGLE_API_KEY not found in environment variables")
                    self.logger.error("AI CV analysis will be disabled due to missing API key")
                    return
                
                self.logger.error("GOOGLE_API_KEY found, initializing ChatGoogleGenerativeAI...")
                self.llm = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash-lite",
                    temperature=0.1,
                    google_api_key=api_key
                )
                self.logger.error("AI CV Analyzer initialized successfully with Gemini model: gemini-2.0-flash-lite")
                self.logger.error(f"Model temperature set to: 0.1")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize AI CV Analyzer: {str(e)}")
                self.logger.error(f"Exception type: {type(e).__name__}")
                self.logger.error("AI CV analysis will be disabled due to initialization error")
                self.llm = None
        else:
            self.logger.error("LangChain not available, AI analysis disabled")
            self.logger.error("Install langchain-google-genai to enable AI CV analysis")
    
    def is_available(self) -> bool:
        """Check if AI analysis is available."""
        is_available = self.llm is not None
        self.logger.error(f"AI analysis availability check: {is_available}")
        return is_available
    
    def analyze_cv_relevance(self, cv_text: str, job_requirements: str, job_title: str = "") -> Dict[str, Any]:
        """
        Analyze CV relevance to job requirements using AI.
        
        Args:
            cv_text: Extracted text from CV
            job_requirements: Job requirements and description
            job_title: Job title for context
            
        Returns:
            Dictionary with AI analysis results
        """
        self.logger.error("Starting CV relevance analysis")
        self.logger.error(f"Job title: {job_title}")
        self.logger.error(f"CV text length: {len(cv_text)} characters")
        self.logger.error(f"Job requirements length: {len(job_requirements)} characters")
        
        if not self.is_available():
            self.logger.error("AI analysis not available, returning default values")
            self.logger.error("Reason: AI service not initialized or unavailable")
            return self._get_default_analysis()
        
        try:
            self.logger.error("AI service is available, proceeding with analysis")
            
            # Prepare the prompt for AI analysis
            self.logger.error("Creating system prompt...")
            system_prompt = self._create_system_prompt()
            self.logger.error(f"System prompt created, length: {len(system_prompt)} characters")
            
            self.logger.error("Creating human prompt...")
            human_prompt = self._create_human_prompt(cv_text, job_requirements, job_title)
            self.logger.error(f"Human prompt created, length: {len(human_prompt)} characters")
            
            # Create messages
            self.logger.error("Creating message objects for AI request...")
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=human_prompt)
            ]
            self.logger.error(f"Created {len(messages)} messages for AI analysis")
            
            # Get AI response with timeout (usando concurrent.futures per compatibilità gunicorn)
            self.logger.error("Sending CV analysis request to Gemini...")
            self.logger.error("Invoking LLM with prepared messages (timeout: 30 seconds)")

            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
            import time

            try:
                # Usa ThreadPoolExecutor per gestire timeout in modo thread-safe
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.llm.invoke, messages)
                    try:
                        response = future.result(timeout=30)  # 30 seconds timeout
                        self.logger.error("Received response from Gemini")
                        self.logger.error(f"Response content length: {len(response.content)} characters")
                    except FuturesTimeoutError:
                        self.logger.error("Gemini API timeout after 30 seconds")
                        self.logger.error("Falling back to default analysis due to timeout")
                        return self._get_default_analysis()

            except Exception as e:
                self.logger.error(f"Gemini API error: {str(e)}")
                self.logger.error(f"Exception type: {type(e).__name__}")
                self.logger.error("Falling back to default analysis due to error")
                return self._get_default_analysis()
            
            # Parse the response
            self.logger.error("Parsing AI response...")
            analysis = self._parse_ai_response(response.content)
            
            relevance_score = analysis.get('relevance_score', 0)
            recommendation = analysis.get('recommendation', 'NON_CONSIGLIATO')
            self.logger.error(f"AI analysis completed successfully")
            self.logger.error(f"Relevance score: {relevance_score}")
            self.logger.error(f"Recommendation: {recommendation}")
            self.logger.error(f"Analysis keys: {list(analysis.keys())}")
            
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error during AI CV analysis: {str(e)}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            self.logger.error(f"Exception args: {e.args}")
            self.logger.error("Falling back to default analysis due to error")
            return self._get_default_analysis()
    
    def _create_system_prompt(self) -> str:
        """Create the system prompt for AI analysis."""
        return """Sei un esperto HR e recruiter specializzato nell'analisi di curriculum vitae.
Il tuo compito è analizzare la pertinenza di un CV rispetto a un'offerta di lavoro specifica.

Devi fornire una valutazione oggettiva e strutturata che includa:
1. Un punteggio di pertinenza da 0 a 100
2. I punti di forza del candidato
3. Le competenze mancanti o aree di miglioramento
4. Una raccomandazione finale (CONSIGLIATO/VALUTARE/NON_CONSIGLIATO)
5. Un breve riassunto delle competenze chiave trovate

Rispondi SEMPRE in formato JSON valido con questa struttura:
{
    "relevance_score": <numero da 0 a 100>,
    "strengths": ["<punto di forza 1>", "<punto di forza 2>", ...],
    "weaknesses": ["<debolezza 1>", "<debolezza 2>", ...],
    "missing_skills": ["<skill mancante 1>", "<skill mancante 2>", ...],
    "key_skills_found": ["<skill trovata 1>", "<skill trovata 2>", ...],
    "recommendation": "<CONSIGLIATO|VALUTARE|NON_CONSIGLIATO>",
    "summary": "<breve riassunto dell'analisi>",
    "experience_match": <numero da 0 a 100>,
    "skills_match": <numero da 0 a 100>
}

Sii preciso, obiettivo e professionale nella tua analisi."""
    
    def _create_human_prompt(self, cv_text: str, job_requirements: str, job_title: str) -> str:
        """Create the human prompt with CV and job details."""
        return f"""Analizza questo CV rispetto all'offerta di lavoro:

POSIZIONE LAVORATIVA:
{job_title}

REQUISITI E DESCRIZIONE LAVORO:
{job_requirements}

TESTO DEL CV:
{cv_text}

Fornisci la tua analisi in formato JSON come specificato nelle istruzioni di sistema."""
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response and extract structured data."""
        self.logger.error("Starting AI response parsing")
        self.logger.error(f"Raw response length: {len(response_text)} characters")
        
        try:
            import json
            
            self.logger.error("Attempting to parse JSON from AI response")
            
            # Try to find JSON in the response
            response_text = response_text.strip()
            self.logger.error(f"Response after strip: {len(response_text)} characters")
            
            # Remove markdown code blocks if present
            original_text = response_text
            if response_text.startswith('```json'):
                response_text = response_text[7:]
                self.logger.error("Removed '```json' prefix from response")
            if response_text.startswith('```'):
                response_text = response_text[3:]
                self.logger.error("Removed '```' prefix from response")
            if response_text.endswith('```'):
                response_text = response_text[:-3]
                self.logger.error("Removed '```' suffix from response")
            
            if original_text != response_text:
                self.logger.error(f"Cleaned response length: {len(response_text)} characters")
            
            # Parse JSON
            self.logger.error("Attempting JSON parsing...")
            analysis = json.loads(response_text.strip())
            self.logger.error("Successfully parsed AI response as JSON")
            self.logger.error(f"Parsed analysis keys: {list(analysis.keys())}")
            
            # Validate required fields
            required_fields = ['relevance_score', 'recommendation', 'summary']
            self.logger.error(f"Validating required fields: {required_fields}")
            
            missing_fields = []
            for field in required_fields:
                if field not in analysis:
                    self.logger.error(f"Missing required field: {field}")
                    missing_fields.append(field)
                    analysis[field] = self._get_default_value(field)
                    self.logger.error(f"Set default value for missing field '{field}': {analysis[field]}")
            
            if missing_fields:
                self.logger.error(f"Total missing fields: {len(missing_fields)}")
            else:
                self.logger.error("All required fields present in response")
            
            # Ensure score is within bounds
            if 'relevance_score' in analysis:
                original_score = analysis['relevance_score']
                analysis['relevance_score'] = max(0, min(100, analysis['relevance_score']))
                if original_score != analysis['relevance_score']:
                    self.logger.error(f"Relevance score adjusted from {original_score} to {analysis['relevance_score']} (bounds: 0-100)")
                else:
                    self.logger.error(f"Relevance score within bounds: {analysis['relevance_score']}")
            
            self.logger.error("AI response parsing completed successfully")
            return analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response as JSON: {str(e)}")
            self.logger.error(f"JSON error line: {e.lineno}, column: {e.colno}")
            self.logger.error(f"JSON error message: {e.msg}")
            self.logger.error(f"Problematic response text (first 500 chars): {response_text[:500]}...")
            if len(response_text) > 500:
                self.logger.error(f"Response text (last 200 chars): ...{response_text[-200:]}")
            return self._get_default_analysis()
        except Exception as e:
            self.logger.error(f"Error parsing AI response: {str(e)}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            self.logger.error(f"Response text sample: {response_text[:200]}...")
            return self._get_default_analysis()
    
    def _get_default_value(self, field: str) -> Any:
        """Get default value for a field."""
        self.logger.error(f"Getting default value for field: {field}")
        defaults = {
            'relevance_score': 0,
            'strengths': [],
            'weaknesses': [],
            'missing_skills': [],
            'key_skills_found': [],
            'recommendation': 'NON_CONSIGLIATO',
            'summary': 'Analisi AI non disponibile',
            'experience_match': 0,
            'skills_match': 0
        }
        default_value = defaults.get(field, None)
        self.logger.error(f"Default value for '{field}': {default_value}")
        return default_value
    
    def _get_default_analysis(self) -> Dict[str, Any]:
        """Get default analysis when AI is not available."""
        self.logger.error("Returning default analysis (AI not available)")
        default_analysis = {
            'relevance_score': 0,
            'strengths': [],
            'weaknesses': ['Analisi AI non disponibile'],
            'missing_skills': [],
            'key_skills_found': [],
            'recommendation': 'NON_CONSIGLIATO',
            'summary': 'Analisi AI non disponibile - utilizzare solo screening OCR',
            'experience_match': 0,
            'skills_match': 0,
            'ai_available': False
        }
        self.logger.error(f"Default analysis keys: {list(default_analysis.keys())}")
        return default_analysis
    
    def get_recommendation_priority(self, recommendation: str) -> str:
        """Convert AI recommendation to priority level."""
        self.logger.error(f"Converting recommendation '{recommendation}' to priority level")
        mapping = {
            'CONSIGLIATO': 'high',
            'VALUTARE': 'medium',
            'NON_CONSIGLIATO': 'low'
        }
        priority = mapping.get(recommendation, 'low')
        self.logger.error(f"Recommendation '{recommendation}' mapped to priority: {priority}")
        return priority
    
    def combine_with_ocr_analysis(self, ai_analysis: Dict[str, Any], ocr_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Combine AI analysis with existing OCR analysis.
        
        Args:
            ai_analysis: Results from AI analysis
            ocr_analysis: Results from OCR analysis
            
        Returns:
            Combined analysis results
        """
        self.logger.error("Starting combination of AI and OCR analysis")
        self.logger.error(f"AI analysis keys: {list(ai_analysis.keys())}")
        self.logger.error(f"OCR analysis keys: {list(ocr_analysis.keys())}")
        
        try:
            # Calculate combined score (weighted average)
            ai_score = ai_analysis.get('relevance_score', 0)
            ocr_score = ocr_analysis.get('final_score', 0)
            
            self.logger.error(f"AI relevance score: {ai_score}")
            self.logger.error(f"OCR final score: {ocr_score}")
            
            # Weight: 60% AI, 40% OCR if AI is available, otherwise 100% OCR
            ai_available = ai_analysis.get('ai_available', True)
            self.logger.error(f"AI availability for scoring: {ai_available}")
            
            if ai_available:
                combined_score = (ai_score * 0.6) + (ocr_score * 0.4)
                self.logger.error(f"Using weighted combination: AI(60%) + OCR(40%) = {combined_score}")
            else:
                combined_score = ocr_score
                self.logger.error(f"AI not available, using OCR score only: {combined_score}")
            
            # Combine recommendations
            recommendations = []
            self.logger.error("Building combined recommendations list")
            
            # Add AI recommendation
            if ai_analysis.get('recommendation'):
                ai_recommendation = {
                    'type': 'ai',
                    'recommendation': ai_analysis['recommendation'],
                    'summary': ai_analysis.get('summary', ''),
                    'score': ai_score,
                    'priority': self.get_recommendation_priority(ai_analysis['recommendation'])
                }
                recommendations.append(ai_recommendation)
                self.logger.error(f"Added AI recommendation: {ai_analysis['recommendation']}")
            
            # Add OCR-based recommendations from existing analysis
            if 'recommendations' in ocr_analysis:
                ocr_recommendations_count = len(ocr_analysis['recommendations'])
                self.logger.error(f"Adding {ocr_recommendations_count} OCR recommendations")
                for rec in ocr_analysis['recommendations']:
                    rec['type'] = 'ocr'
                    recommendations.append(rec)
            
            final_recommendation = ai_analysis.get('recommendation', 'NON_CONSIGLIATO')
            analysis_methods = ['ai', 'ocr'] if ai_available else ['ocr']
            
            self.logger.error(f"Final recommendation: {final_recommendation}")
            self.logger.error(f"Analysis methods used: {analysis_methods}")
            self.logger.error(f"Total recommendations: {len(recommendations)}")
            
            combined_result = {
                'combined_score': round(combined_score, 2),
                'ai_analysis': ai_analysis,
                'ocr_analysis': ocr_analysis,
                'recommendations': recommendations,
                'final_recommendation': final_recommendation,
                'analysis_methods': analysis_methods
            }
            
            self.logger.error("Successfully combined AI and OCR analysis")
            self.logger.error(f"Combined result keys: {list(combined_result.keys())}")
            return combined_result
            
        except Exception as e:
            self.logger.error(f"Error combining AI and OCR analysis: {str(e)}")
            self.logger.error(f"Exception type: {type(e).__name__}")
            self.logger.error("Falling back to OCR-only analysis due to combination error")
            
            fallback_result = {
                'combined_score': ocr_analysis.get('final_score', 0),
                'ai_analysis': ai_analysis,
                'ocr_analysis': ocr_analysis,
                'recommendations': ocr_analysis.get('recommendations', []),
                'final_recommendation': 'NON_CONSIGLIATO',
                'analysis_methods': ['ocr'],
                'error': 'Failed to combine analyses'
            }
            
            self.logger.error("Returned fallback analysis result")
            return fallback_result


# Global instance
ai_cv_analyzer = AICVAnalyzer()


def analyze_cv_with_ai(cv_text: str, job_requirements: str, job_title: str = "") -> Dict[str, Any]:
    """
    Convenience function to analyze CV with AI.
    
    Args:
        cv_text: Extracted text from CV
        job_requirements: Job requirements and description
        job_title: Job title for context
        
    Returns:
        AI analysis results
    """
    logger = logging.getLogger(__name__)
    logger.error(f"Convenience function called for CV analysis - Job: {job_title}")
    logger.error(f"CV text length: {len(cv_text)}, Requirements length: {len(job_requirements)}")
    
    result = ai_cv_analyzer.analyze_cv_relevance(cv_text, job_requirements, job_title)
    
    logger.error("Convenience function completed CV analysis")
    logger.error(f"Result keys: {list(result.keys())}")
    
    return result