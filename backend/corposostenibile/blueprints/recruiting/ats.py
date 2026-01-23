"""
ATS (Applicant Tracking System) - Sistema di screening automatico
"""

import re
import os
from datetime import datetime
from typing import List, Dict, Any
from flask import current_app
from werkzeug.utils import secure_filename
from corposostenibile.extensions import db
from corposostenibile.models import (
    JobApplication, ApplicationAnswer, ApplicationStatusEnum,
    KanbanStage, KanbanStageTypeEnum
)

# Importa AI CV Analyzer se disponibile
try:
    from .services.ai_cv_analyzer import ai_cv_analyzer
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    current_app.logger.warning("AI CV Analyzer not available")

# Import OCR e text processing
try:
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    current_app.logger.warning("pytesseract not available, OCR disabled")

try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False
    current_app.logger.warning("pdfplumber not available, PDF text extraction disabled")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    current_app.logger.warning("scikit-learn not available, advanced text matching disabled")


class ATSAnalyzer:
    """Analizzatore ATS per candidature."""
    
    def __init__(self, application: JobApplication):
        current_app.logger.error(f"[ATS] Inizializzazione ATSAnalyzer per candidatura ID: {application.id}")
        current_app.logger.error(f"[ATS] Candidato: {application.first_name} {application.last_name}")
        current_app.logger.error(f"[ATS] Email: {application.email}")
        current_app.logger.error(f"[ATS] Telefono: {application.phone}")
        current_app.logger.error(f"[ATS] Status attuale: {application.status}")
        current_app.logger.error(f"[ATS] Data candidatura: {application.created_at}")
        
        self.application = application
        self.job_offer = application.job_offer
        
        current_app.logger.error(f"[ATS] Job Offer ID: {self.job_offer.id}")
        current_app.logger.error(f"[ATS] Job Offer Title: {self.job_offer.title}")
        current_app.logger.error(f"[ATS] Job Offer Department: {self.job_offer.department.name if self.job_offer.department else 'N/A'}")
        current_app.logger.error(f"[ATS] Job Offer Location: {self.job_offer.location}")
        current_app.logger.error(f"[ATS] Job Offer Status: {self.job_offer.status}")
        
        # Log informazioni CV
        if application.cv_file_path:
            current_app.logger.error(f"[ATS] CV file presente: {application.cv_file_path}")
            # Verifica se il file esiste fisicamente
            cv_file_path = application.cv_file_path
            if cv_file_path.startswith('uploads/'):
                cv_file_path = cv_file_path[8:]  # Rimuove "uploads/" per evitare duplicazione
            full_cv_path = os.path.join(current_app.config['UPLOAD_FOLDER'], cv_file_path)
            if os.path.exists(full_cv_path):
                file_size = os.path.getsize(full_cv_path)
                current_app.logger.error(f"[ATS] CV file size: {file_size} bytes")
            else:
                current_app.logger.warning(f"[ATS] CV file non trovato sul filesystem: {full_cv_path}")
        else:
            current_app.logger.warning(f"[ATS] Nessun CV file associato alla candidatura")
        
        # Log informazioni testo CV già estratto
        if application.cv_text:
            cv_text_length = len(application.cv_text)
            current_app.logger.error(f"[ATS] CV text già presente, lunghezza: {cv_text_length} caratteri")
            current_app.logger.error(f"[ATS] CV text preview (primi 200 char): {application.cv_text[:200]}...")
        else:
            current_app.logger.error(f"[ATS] Nessun testo CV estratto precedentemente")
        
        # Log informazioni risposte questionario
        answers_count = len(application.answers)
        current_app.logger.error(f"[ATS] Numero risposte questionario: {answers_count}")
        for i, answer in enumerate(application.answers):
            current_app.logger.error(f"[ATS] Risposta {i+1}: Domanda ID {answer.question_id}, Testo: {answer.answer_text[:100] if answer.answer_text else 'N/A'}...")
        
        # Log informazioni job requirements
        if self.job_offer.what_we_search:
            requirements_length = len(self.job_offer.what_we_search)
            current_app.logger.error(f"[ATS] Job requirements presenti, lunghezza: {requirements_length} caratteri")
            current_app.logger.error(f"[ATS] Job requirements preview: {self.job_offer.what_we_search[:200]}...")
        else:
            current_app.logger.warning(f"[ATS] Nessun requirement specificato per il job offer")
        
        # Log disponibilità librerie
        current_app.logger.error(f"[ATS] OCR disponibile: {OCR_AVAILABLE}")
        current_app.logger.error(f"[ATS] PDF processing disponibile: {PDF_AVAILABLE}")
        current_app.logger.error(f"[ATS] ML/Similarity disponibile: {ML_AVAILABLE}")
        
        self.results = {
            'form_analysis': {},
            'cv_analysis': {},
            'scores': {},
            'recommendations': []
        }
        
        current_app.logger.error(f"[ATS] ATSAnalyzer inizializzato con successo per candidatura {application.id}")
    
    def analyze(self) -> Dict[str, Any]:
        """Esegue l'analisi completa della candidatura."""
        current_app.logger.error(f"[ATS] ===== INIZIO ANALISI COMPLETA per candidatura {self.application.id} =====")
        
        try:
            # 1. Analizza risposte del form
            current_app.logger.error(f"[ATS] STEP 1: Analisi risposte questionario")
            self._analyze_form_answers()
            current_app.logger.error(f"[ATS] STEP 1 completato - Form analysis: {self.results.get('form_analysis', {})}")
            
            # 2. Estrai testo dal CV
            current_app.logger.error(f"[ATS] STEP 2: Estrazione testo CV")
            if self.application.cv_file_path:
                current_app.logger.error(f"[ATS] CV file presente, avvio estrazione testo")
                self._extract_cv_text()
                current_app.logger.error(f"[ATS] STEP 2 completato - CV text estratto: {len(self.application.cv_text or '') > 0}")
                if self.application.cv_text:
                    current_app.logger.error(f"[ATS] CV text length dopo estrazione: {len(self.application.cv_text)} caratteri")
            else:
                current_app.logger.warning(f"[ATS] STEP 2 saltato - Nessun CV file presente")
            
            # 3. Analizza CV vs requisiti
            current_app.logger.error(f"[ATS] STEP 3: Analisi CV vs requisiti job")
            if self.application.cv_text and self.job_offer.what_we_search:
                current_app.logger.error(f"[ATS] CV text e requirements presenti, avvio analisi matching")
                self._analyze_cv_content()
                current_app.logger.error(f"[ATS] STEP 3 completato - CV analysis: {self.results.get('cv_analysis', {})}")
            else:
                current_app.logger.warning(f"[ATS] STEP 3 saltato - CV text: {bool(self.application.cv_text)}, Requirements: {bool(self.job_offer.what_we_search)}")
            
            # 4. Calcola punteggi finali
            current_app.logger.error(f"[ATS] STEP 4: Calcolo punteggi finali")
            self._calculate_final_scores()
            current_app.logger.error(f"[ATS] STEP 4 completato - Scores: {self.results.get('scores', {})}")
            
            # 5. Genera raccomandazioni
            current_app.logger.error(f"[ATS] STEP 5: Generazione raccomandazioni")
            self._generate_recommendations()
            current_app.logger.error(f"[ATS] STEP 5 completato - Recommendations count: {len(self.results.get('recommendations', []))}")
            
            # 6. Salva risultati nel database
            current_app.logger.error(f"[ATS] STEP 6: Salvataggio risultati nel database")
            self._save_results()
            current_app.logger.error(f"[ATS] STEP 6 completato - Risultati salvati")
            
            current_app.logger.error(f"[ATS] ===== ANALISI COMPLETATA CON SUCCESSO per candidatura {self.application.id} =====")
            current_app.logger.error(f"[ATS] Risultati finali: {self.results}")
            
            return self.results
            
        except Exception as e:
            current_app.logger.error(f"[ATS] ERRORE durante analisi candidatura {self.application.id}: {str(e)}")
            current_app.logger.error(f"[ATS] Exception type: {type(e).__name__}")
            current_app.logger.error(f"[ATS] Exception args: {e.args}")
            import traceback
            current_app.logger.error(f"[ATS] Traceback completo: {traceback.format_exc()}")
            raise
    
    def _analyze_form_answers(self):
        """Analizza le risposte del questionario."""
        total_score = 0
        total_weight = 0
        answer_details = []
        
        for answer in self.application.answers:
            if not answer.question:
                continue
            
            # Calcola score per questa risposta
            answer.calculate_score()
            score = answer.score or 0
            weight = answer.question.weight or 0
            
            answer_details.append({
                'question': answer.question.question_text,
                'answer': answer.answer_text or answer.answer_json,
                'expected': answer.question.expected_answer or answer.question.expected_options,
                'score': score,
                'weight': weight,
                'weighted_score': score * weight / 100
            })
            
            total_score += score * weight
            total_weight += weight
        
        # Calcola score medio pesato
        if total_weight > 0:
            form_score = total_score / total_weight
        else:
            form_score = 0
        
        self.results['form_analysis'] = {
            'answers': answer_details,
            'total_score': form_score,
            'total_weight': total_weight
        }
        
        # Salva score nel modello
        self.application.form_score = form_score
    
    def _extract_cv_text(self):
        """Estrae testo dal CV caricato."""
        # Rimuovi "uploads/" dal path se presente per evitare duplicazione
        cv_file_path = self.application.cv_file_path
        if cv_file_path.startswith('uploads/'):
            cv_file_path = cv_file_path[8:]  # Rimuove "uploads/"

        cv_path = os.path.join(
            current_app.config['UPLOAD_FOLDER'],
            cv_file_path
        )

        if not os.path.exists(cv_path):
            error_msg = f"CV file not found: {cv_path}"
            current_app.logger.error(f"[ATS] {error_msg}")
            # Solleva un'eccezione per interrompere il flusso
            raise FileNotFoundError(error_msg)
        
        extracted_text = ""
        file_ext = os.path.splitext(cv_path)[1].lower()
        
        try:
            if file_ext == '.pdf' and PDF_AVAILABLE:
                # Estrai testo da PDF
                with pdfplumber.open(cv_path) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            extracted_text += page_text + "\n"
            
            elif file_ext in ['.jpg', '.jpeg', '.png'] and OCR_AVAILABLE:
                # OCR su immagine
                image = Image.open(cv_path)
                extracted_text = pytesseract.image_to_string(image, lang='ita+eng')
            
            elif file_ext in ['.txt', '.text']:
                # File di testo semplice
                with open(cv_path, 'r', encoding='utf-8', errors='ignore') as f:
                    extracted_text = f.read()
            
            # Pulizia testo
            extracted_text = self._clean_text(extracted_text)
            
            # Salva nel database
            self.application.cv_text = extracted_text
            
            self.results['cv_analysis']['text_extracted'] = True
            self.results['cv_analysis']['text_length'] = len(extracted_text)
            
        except Exception as e:
            error_msg = f"Error extracting CV text: {e}"
            current_app.logger.error(f"[ATS] {error_msg}")
            # Solleva un'eccezione per interrompere il flusso
            raise Exception(error_msg)
    
    def _clean_text(self, text: str) -> str:
        """Pulisce il testo estratto."""
        # Rimuovi caratteri speciali mantenendo punteggiatura base
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\@\+\(\)\/]', ' ', text)
        # Rimuovi spazi multipli
        text = re.sub(r'\s+', ' ', text)
        # Trim
        return text.strip()
    
    def _analyze_cv_content(self):
        """Analizza il contenuto del CV rispetto ai requisiti."""
        current_app.logger.error(f"[ATS] _analyze_cv_content: Inizio analisi CV content per candidatura {self.application.id}")
        
        if not self.application.cv_text:
            current_app.logger.warning(f"[ATS] _analyze_cv_content: Nessun testo CV disponibile, impostazione valori default")
            # Se non c'è testo CV, imposta valori di default
            self.results['cv_analysis']['keywords'] = {
                'total': 0,
                'found': [],
                'missing': [],
                'score': 0
            }
            self.results['cv_analysis']['skills'] = {
                'programming_languages': [],
                'frameworks': [],
                'databases': [],
                'tools': [],
                'soft_skills': [],
                'languages': []
            }
            self.results['cv_analysis']['experience'] = {
                'years': 0,
                'companies': [],
                'roles': [],
                'education': []
            }
            self.application.cv_score = 0
            self.results['cv_analysis']['final_score'] = 0
            current_app.logger.error(f"[ATS] _analyze_cv_content: Completato con valori default (nessun CV text)")
            return
            
        cv_text = self.application.cv_text.lower()
        requirements = (self.job_offer.what_we_search or "").lower()
        
        current_app.logger.error(f"[ATS] _analyze_cv_content: CV text length: {len(cv_text)} caratteri")
        current_app.logger.error(f"[ATS] _analyze_cv_content: Requirements length: {len(requirements)} caratteri")
        current_app.logger.error(f"[ATS] _analyze_cv_content: CV text preview: {cv_text[:300]}...")
        current_app.logger.error(f"[ATS] _analyze_cv_content: Requirements preview: {requirements[:300]}...")
        
        # Analisi base: keyword matching
        current_app.logger.error(f"[ATS] _analyze_cv_content: Estrazione keywords dai requirements")
        keywords = self._extract_keywords(requirements)
        current_app.logger.error(f"[ATS] _analyze_cv_content: Keywords estratte: {keywords}")
        current_app.logger.error(f"[ATS] _analyze_cv_content: Numero keywords totali: {len(keywords)}")
        
        found_keywords = []
        missing_keywords = []
        
        current_app.logger.error(f"[ATS] _analyze_cv_content: Ricerca keywords nel CV text")
        for i, keyword in enumerate(keywords):
            if keyword in cv_text:
                found_keywords.append(keyword)
                current_app.logger.error(f"[ATS] _analyze_cv_content: Keyword {i+1}/{len(keywords)} TROVATA: '{keyword}'")
            else:
                missing_keywords.append(keyword)
                current_app.logger.error(f"[ATS] _analyze_cv_content: Keyword {i+1}/{len(keywords)} MANCANTE: '{keyword}'")
        
        # Calcola score base
        if keywords:
            keyword_score = (len(found_keywords) / len(keywords)) * 100
            current_app.logger.error(f"[ATS] _analyze_cv_content: Keyword score calcolato: {keyword_score}% ({len(found_keywords)}/{len(keywords)})")
        else:
            keyword_score = 0
            current_app.logger.warning(f"[ATS] _analyze_cv_content: Nessuna keyword estratta, score = 0")
        
        self.results['cv_analysis']['keywords'] = {
            'total': len(keywords),
            'found': found_keywords,
            'missing': missing_keywords,
            'score': keyword_score
        }
        
        current_app.logger.error(f"[ATS] _analyze_cv_content: Keywords analysis completata: {self.results['cv_analysis']['keywords']}")
        
        # Analisi avanzata con ML (se disponibile)
        if ML_AVAILABLE and len(cv_text) > 100:
            current_app.logger.error(f"[ATS] _analyze_cv_content: ML disponibile, calcolo similarity score")
            similarity_score = self._calculate_text_similarity(cv_text, requirements)
            self.results['cv_analysis']['similarity_score'] = similarity_score * 100
            current_app.logger.error(f"[ATS] _analyze_cv_content: Similarity score: {similarity_score * 100}%")
            
            # Media tra keyword score e similarity
            cv_score = (keyword_score + similarity_score * 100) / 2
            current_app.logger.error(f"[ATS] _analyze_cv_content: CV score finale (media keyword + similarity): {cv_score}%")
        else:
            cv_score = keyword_score
            if not ML_AVAILABLE:
                current_app.logger.warning(f"[ATS] _analyze_cv_content: ML non disponibile, uso solo keyword score")
            else:
                current_app.logger.warning(f"[ATS] _analyze_cv_content: CV text troppo corto ({len(cv_text)} char), uso solo keyword score")
        
        # Analisi competenze specifiche
        current_app.logger.error(f"[ATS] _analyze_cv_content: Analisi skills nel CV")
        skills_analysis = self._analyze_skills(cv_text)
        self.results['cv_analysis']['skills'] = skills_analysis
        current_app.logger.error(f"[ATS] _analyze_cv_content: Skills analysis completata: {skills_analysis}")
        
        # Analisi esperienza
        current_app.logger.error(f"[ATS] _analyze_cv_content: Analisi esperienza nel CV")
        experience_analysis = self._analyze_experience(cv_text)
        self.results['cv_analysis']['experience'] = experience_analysis
        current_app.logger.error(f"[ATS] _analyze_cv_content: Experience analysis completata: {experience_analysis}")
        
        # ===== NUOVA ANALISI AI CON GEMINI =====
        current_app.logger.error(f"[ATS] _analyze_cv_content: Avvio analisi AI con Gemini")
        ai_analysis = self._analyze_cv_with_ai(self.application.cv_text, requirements)
        self.results['cv_analysis']['ai_analysis'] = ai_analysis
        current_app.logger.error(f"[ATS] _analyze_cv_content: AI analysis completata: {ai_analysis}")
        
        # Combina score OCR e AI
        if ai_analysis.get('ai_available', False):
            ai_score = ai_analysis.get('relevance_score', 0)
            # Peso: 60% AI, 40% OCR tradizionale
            # combined_score = (ai_score * 0.6) + (cv_score * 0.4)
            #current_app.logger.error(f"[ATS] _analyze_cv_content: Score combinato: AI({ai_score}) * 0.6 + OCR({cv_score}) * 0.4 = {combined_score}")
            current_app.logger.error(f"[ATS] _analyze_cv_content: Score AI finale: {ai_score}%")
            cv_score = ai_score
        else:
            current_app.logger.warning(f"[ATS] _analyze_cv_content: AI non disponibile, uso solo score OCR")
        
        # Score finale CV
        self.application.cv_score = cv_score
        self.results['cv_analysis']['final_score'] = cv_score
        
        current_app.logger.error(f"[ATS] _analyze_cv_content: COMPLETATA - CV score finale: {cv_score}%")
        current_app.logger.error(f"[ATS] _analyze_cv_content: Risultati completi CV analysis: {self.results['cv_analysis']}")
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Estrae keywords dal testo."""
        # Keywords tecniche comuni
        tech_patterns = [
            r'\b(python|java|javascript|typescript|react|angular|vue|node|django|flask|spring)\b',
            r'\b(sql|mysql|postgresql|mongodb|redis|elasticsearch)\b',
            r'\b(aws|azure|gcp|docker|kubernetes|ci/cd|devops)\b',
            r'\b(git|github|gitlab|bitbucket|jira|confluence)\b',
            r'\b(agile|scrum|kanban|lean)\b',
        ]
        
        keywords = []
        
        # Estrai parole chiave tecniche
        for pattern in tech_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            keywords.extend(matches)
        
        # Estrai anche termini specifici dal testo dei requisiti
        # (nomi, verbi importanti, etc.)
        important_words = re.findall(r'\b[a-z]{4,}\b', text)
        
        # Filtra stop words base
        stop_words = {'come', 'cosa', 'quando', 'dove', 'molto', 'sono', 'essere', 
                     'avere', 'fare', 'dire', 'andare', 'potere', 'dovere', 'volere',
                     'questo', 'quello', 'quale', 'tanto', 'poco', 'tutto', 'niente'}
        
        keywords.extend([w for w in important_words if w not in stop_words][:20])
        
        # Rimuovi duplicati mantenendo l'ordine
        seen = set()
        unique_keywords = []
        for k in keywords:
            if k.lower() not in seen:
                seen.add(k.lower())
                unique_keywords.append(k.lower())
        
        return unique_keywords
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcola similarità tra due testi usando TF-IDF e cosine similarity."""
        if not ML_AVAILABLE:
            return 0.0
        
        try:
            # Crea TF-IDF vectorizer
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words=None,  # Useremo stop words italiane/inglesi custom
                ngram_range=(1, 2)  # Unigrams e bigrams
            )
            
            # Fit e transform
            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            
            # Calcola cosine similarity
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            
            return float(similarity)
            
        except Exception as e:
            current_app.logger.error(f"Error calculating text similarity: {e}")
            return 0.0
    
    def _analyze_skills(self, cv_text: str) -> Dict[str, Any]:
        """Analizza le competenze tecniche nel CV."""
        skills = {
            'programming_languages': [],
            'frameworks': [],
            'databases': [],
            'tools': [],
            'soft_skills': [],
            'languages': []
        }
        
        # Pattern per diverse categorie
        patterns = {
            'programming_languages': r'\b(python|java|c\+\+|c#|javascript|typescript|php|ruby|go|rust|kotlin|swift|r|matlab)\b',
            'frameworks': r'\b(django|flask|fastapi|spring|react|angular|vue|svelte|express|laravel|rails|asp\.net)\b',
            'databases': r'\b(mysql|postgresql|mongodb|redis|cassandra|elasticsearch|oracle|sql server|dynamodb)\b',
            'tools': r'\b(git|docker|kubernetes|jenkins|terraform|ansible|aws|azure|gcp|jira|confluence)\b',
            'languages': r'\b(inglese|english|francese|french|spagnolo|spanish|tedesco|german|cinese|chinese)\b'
        }
        
        for category, pattern in patterns.items():
            matches = re.findall(pattern, cv_text, re.IGNORECASE)
            skills[category] = list(set(matches))
        
        # Soft skills (più complesso, usa frasi)
        soft_patterns = [
            (r'team\s*work|lavoro\s*di\s*squadra', 'teamwork'),
            (r'problem\s*solving', 'problem solving'),
            (r'leadership', 'leadership'),
            (r'comunicazione|communication', 'communication'),
            (r'gestione\s*del\s*tempo|time\s*management', 'time management'),
        ]
        
        for pattern, skill in soft_patterns:
            if re.search(pattern, cv_text, re.IGNORECASE):
                skills['soft_skills'].append(skill)
        
        return skills
    
    def _analyze_experience(self, cv_text: str) -> Dict[str, Any]:
        """Analizza l'esperienza lavorativa nel CV."""
        experience = {
            'years': 0,
            'companies': [],
            'roles': [],
            'education': []
        }
        
        # Cerca anni di esperienza
        years_patterns = [
            r'(\d+)\+?\s*anni?\s*di\s*esperienza',
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'esperienza\s*di\s*(\d+)\s*anni',
        ]
        
        for pattern in years_patterns:
            match = re.search(pattern, cv_text, re.IGNORECASE)
            if match:
                experience['years'] = int(match.group(1))
                break
        
        # Cerca ruoli
        role_patterns = [
            r'(developer|sviluppatore|programmer|engineer|analyst|manager|designer|architect)',
            r'(senior|junior|lead|principal|staff)',
        ]
        
        for pattern in role_patterns:
            matches = re.findall(pattern, cv_text, re.IGNORECASE)
            experience['roles'].extend(matches)
        
        experience['roles'] = list(set(experience['roles']))
        
        # Cerca titoli di studio
        education_patterns = [
            r'(laurea|diploma|master|phd|dottorato|bachelor|degree)',
            r'(università|university|politecnico|academy)',
        ]
        
        for pattern in education_patterns:
            matches = re.findall(pattern, cv_text, re.IGNORECASE)
            experience['education'].extend(matches)
        
        experience['education'] = list(set(experience['education']))
        
        return experience
    
    def _analyze_cv_with_ai(self, cv_text: str, requirements: str) -> Dict[str, Any]:
        """Analizza il CV usando AI (Gemini) tramite LangChain."""
        current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Inizio analisi AI")
        
        if not AI_AVAILABLE:
            current_app.logger.warning(f"[ATS] _analyze_cv_with_ai: AI non disponibile")
            return {
                'ai_available': False,
                'relevance_score': 0,
                'recommendation': 'NON_CONSIGLIATO',
                'summary': 'Analisi AI non disponibile',
                'error': 'AI service not available'
            }
        
        if not ai_cv_analyzer.is_available():
            current_app.logger.warning(f"[ATS] _analyze_cv_with_ai: AI analyzer non inizializzato")
            return {
                'ai_available': False,
                'relevance_score': 0,
                'recommendation': 'NON_CONSIGLIATO',
                'summary': 'AI analyzer non inizializzato',
                'error': 'AI analyzer not initialized'
            }
        
        try:
            # Ottieni il titolo del lavoro se disponibile
            job_title = getattr(self.job_offer, 'title', '') or getattr(self.job_offer, 'name', '')
            
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Chiamata AI analyzer")
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Job title: {job_title}")
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: CV text length: {len(cv_text)} chars")
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Requirements length: {len(requirements)} chars")
            
            # Chiama l'analizzatore AI
            ai_result = ai_cv_analyzer.analyze_cv_relevance(
                cv_text=cv_text,
                job_requirements=requirements,
                job_title=job_title
            )
            
            # Aggiungi flag di disponibilità
            ai_result['ai_available'] = True
            
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: AI analysis completata")
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Relevance score: {ai_result.get('relevance_score', 0)}")
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Recommendation: {ai_result.get('recommendation', 'N/A')}")
            
            return ai_result
            
        except Exception as e:
            current_app.logger.error(f"[ATS] _analyze_cv_with_ai: Errore durante analisi AI: {str(e)}")
            return {
                'ai_available': False,
                'relevance_score': 0,
                'recommendation': 'NON_CONSIGLIATO',
                'summary': f'Errore durante analisi AI: {str(e)}',
                'error': str(e)
            }
    
    def _calculate_final_scores(self):
        """Calcola i punteggi finali pesati."""
        form_score = self.application.form_score or 0
        cv_score = self.application.cv_score or 0
        
        form_weight = self.job_offer.form_weight or 50
        cv_weight = self.job_offer.cv_weight or 50
        
        # Calcola score totale pesato
        total_score = (form_score * form_weight + cv_score * cv_weight) / 100
        
        self.application.total_score = total_score
        
        self.results['scores'] = {
            'form': form_score,
            'cv': cv_score,
            'total': total_score,
            'weights': {
                'form': form_weight,
                'cv': cv_weight
            }
        }
    
    def _generate_recommendations(self):
        """Genera raccomandazioni basate sull'analisi."""
        recommendations = []
        score = self.application.total_score or 0
        
        # Raccomandazioni base su score
        if score >= 80:
            recommendations.append({
                'type': 'success',
                'message': 'Candidato eccellente - Consigliato per colloquio immediato',
                'priority': 'high'
            })
        elif score >= 60:
            recommendations.append({
                'type': 'info',
                'message': 'Candidato qualificato - Valutare per colloquio',
                'priority': 'medium'
            })
        elif score >= 40:
            recommendations.append({
                'type': 'warning',
                'message': 'Candidato parzialmente qualificato - Necessita valutazione approfondita',
                'priority': 'low'
            })
        else:
            recommendations.append({
                'type': 'danger',
                'message': 'Candidato non qualificato - Non soddisfa i requisiti minimi',
                'priority': 'reject'
            })
        
        # Raccomandazioni specifiche su CV
        if 'keywords' in self.results.get('cv_analysis', {}):
            missing = self.results['cv_analysis']['keywords'].get('missing', [])
            if missing:
                recommendations.append({
                    'type': 'warning',
                    'message': f"Competenze mancanti: {', '.join(missing[:5])}",
                    'priority': 'info'
                })
        
        # Raccomandazioni su esperienza
        if 'experience' in self.results.get('cv_analysis', {}):
            years = self.results['cv_analysis']['experience'].get('years', 0)
            if years > 5:
                recommendations.append({
                    'type': 'success',
                    'message': f"Esperienza significativa: {years} anni",
                    'priority': 'info'
                })
        
        self.results['recommendations'] = recommendations
    
    def _save_results(self):
        """Salva i risultati dell'analisi nel database."""
        self.application.ats_analysis = self.results
        self.application.screened_at = datetime.utcnow()
        
        # Aggiorna stato se necessario
        if self.application.status == ApplicationStatusEnum.new:
            self.application.status = ApplicationStatusEnum.screening
        
        # Commit sarà fatto dal chiamante
        # db.session.commit()


def run_screening(applications: List[JobApplication], min_score: float = 60) -> Dict[str, Any]:
    """
    Esegue lo screening ATS su una lista di candidature.
    
    Args:
        applications: Lista di candidature da analizzare
        min_score: Punteggio minimo per passare lo screening
    
    Returns:
        Dizionario con risultati dello screening
    """
    current_app.logger.error(f"[ATS] ===== INIZIO BATCH SCREENING =====")
    current_app.logger.error(f"[ATS] Numero candidature da processare: {len(applications)}")
    current_app.logger.error(f"[ATS] Punteggio minimo richiesto: {min_score}")
    
    # Log dettagli candidature
    for i, app in enumerate(applications):
        current_app.logger.error(f"[ATS] Candidatura {i+1}/{len(applications)}: ID {app.id}, {app.first_name} {app.last_name}, Status: {app.status}")
    
    results = {
        'processed': [],
        'passed': [],
        'failed': [],
        'errors': []
    }
    
    for i, application in enumerate(applications):
        current_app.logger.error(f"[ATS] ===== PROCESSING CANDIDATURA {i+1}/{len(applications)} - ID {application.id} =====")
        current_app.logger.error(f"[ATS] Candidato: {application.first_name} {application.last_name}")
        current_app.logger.error(f"[ATS] Email: {application.email}")
        current_app.logger.error(f"[ATS] Status iniziale: {application.status}")
        
        try:
            # Crea analyzer
            current_app.logger.error(f"[ATS] Creazione ATSAnalyzer per candidatura {application.id}")
            analyzer = ATSAnalyzer(application)
            
            # Esegui analisi
            current_app.logger.error(f"[ATS] Avvio analisi completa per candidatura {application.id}")
            analysis_results = analyzer.analyze()
            current_app.logger.error(f"[ATS] Analisi completata per candidatura {application.id}")
            
            # Salva punteggi
            current_app.logger.error(f"[ATS] Calcolo punteggi finali per candidatura {application.id}")
            application.calculate_scores()
            current_app.logger.error(f"[ATS] Punteggio totale calcolato: {application.total_score}")
            current_app.logger.error(f"[ATS] Punteggio CV: {application.cv_score}")
            current_app.logger.error(f"[ATS] Punteggio form: {application.form_score}")
            
            # Determina se passa lo screening
            current_app.logger.error(f"[ATS] Valutazione screening: {application.total_score} >= {min_score}?")
            if application.total_score >= min_score:
                current_app.logger.error(f"[ATS] ✅ CANDIDATURA PASSATA - Score: {application.total_score}% >= {min_score}%")
                application.status = ApplicationStatusEnum.reviewed
                results['passed'].append(application)
                
                # Se c'è un kanban, sposta alla fase di screening
                if application.job_offer.kanban:
                    current_app.logger.error(f"[ATS] Kanban presente, ricerca stage di screening")
                    screening_stage = KanbanStage.query.filter_by(
                        kanban_id=application.job_offer.kanban_id,
                        stage_type=KanbanStageTypeEnum.screening
                    ).first()
                    
                    if screening_stage:
                        current_app.logger.error(f"[ATS] Stage di screening trovato (ID: {screening_stage.id}), spostamento candidatura")
                        application.kanban_stage_id = screening_stage.id
                    else:
                        current_app.logger.warning(f"[ATS] Stage di screening non trovato nel kanban")
                else:
                    current_app.logger.error(f"[ATS] Nessun kanban associato al job offer")
            else:
                current_app.logger.error(f"[ATS] ❌ CANDIDATURA FALLITA - Score: {application.total_score}% < {min_score}%")
                results['failed'].append(application)
            
            results['processed'].append(application)
            current_app.logger.error(f"[ATS] Candidatura {application.id} processata con successo")
            
        except Exception as e:
            current_app.logger.error(f"[ATS] ❌ ERRORE durante screening candidatura {application.id}: {str(e)}")
            current_app.logger.error(f"[ATS] Exception type: {type(e).__name__}")
            current_app.logger.error(f"[ATS] Exception args: {e.args}")
            import traceback
            current_app.logger.error(f"[ATS] Traceback: {traceback.format_exc()}")
            
            results['errors'].append({
                'application_id': application.id,
                'error': str(e)
            })
    
    current_app.logger.error(f"[ATS] ===== BATCH SCREENING COMPLETATO =====")
    current_app.logger.error(f"[ATS] Candidature processate: {len(results['processed'])}")
    current_app.logger.error(f"[ATS] Candidature passate: {len(results['passed'])}")
    current_app.logger.error(f"[ATS] Candidature fallite: {len(results['failed'])}")
    current_app.logger.error(f"[ATS] Errori: {len(results['errors'])}")
    
    # Salva tutto in database
    current_app.logger.error(f"[ATS] Salvataggio risultati nel database")
    try:
        db.session.commit()
        current_app.logger.error(f"[ATS] ✅ Database commit completato con successo")
    except Exception as e:
        current_app.logger.error(f"[ATS] ❌ ERRORE durante salvataggio database: {str(e)}")
        current_app.logger.error(f"[ATS] Rollback in corso...")
        db.session.rollback()
        current_app.logger.error(f"[ATS] Rollback completato")
    
    current_app.logger.error(f"[ATS] Risultati finali batch screening: {results}")
    return results


def extract_cv_keywords(cv_text: str, job_requirements: str) -> Dict[str, Any]:
    """
    Estrae e confronta keywords tra CV e requisiti.
    
    Utility function per uso esterno.
    """
    analyzer = ATSAnalyzer(None)  # Usiamo solo i metodi utility
    
    # Estrai keywords dai requisiti
    required_keywords = analyzer._extract_keywords(job_requirements)
    
    # Cerca keywords nel CV
    cv_text_lower = cv_text.lower()
    found = []
    missing = []
    
    for keyword in required_keywords:
        if keyword in cv_text_lower:
            found.append(keyword)
        else:
            missing.append(keyword)
    
    # Estrai anche skills dal CV
    skills = analyzer._analyze_skills(cv_text)
    
    return {
        'required': required_keywords,
        'found': found,
        'missing': missing,
        'match_rate': len(found) / len(required_keywords) if required_keywords else 0,
        'skills': skills
    }