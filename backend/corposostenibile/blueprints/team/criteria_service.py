from typing import List, Dict, Any

class CriteriaService:
    """
    Servizio per gestire le definizioni dei criteri di assegnazione (Schema)
    e la validazione.
    """

    # Criteri comuni per Nutrizione e Psicologia (dal file Excel)
    COMMON_MED_CRITERIA = [
        "UOMINI",
        "DONNE",
        "MINORENNI <15",
        "MINORENNI >15",
        "ETA' 18-55", 
        "ETA' >55",
        "IBS",
        "REFLUSSO",
        "GASTRITE",
        "DCA",
        "INSULINO - RESISTENTE",
        "DIABETE DI TIPO 1",
        "DIABETE DI TIPO 2",
        "DISLIPIDEMIA",
        "STEATOSI EPATICA",
        "IPERTENSIONE",
        "PCOS",
        "ENDOMETRIOSI",
        "OBESITA' - SINDROME METABOLICA",
        "OSTEOPOROSI",
        "DIVERTICOLITE",
        "MORBO DI CROHN",
        "STITICHEZZA",
        "MALATTIE TIROIDEE",
        "CELIACHIA",
        "SPORTIVI",
        "PROBLEMI ORMONALI",
        "DIGIUNO INTERMITTENTE",
        "MENOPAUSA",
        "ALLERGIE E INTOLLERANZE",
        "FAME EMOTIVA",
        "ALIMENTAZIONE VEG",
        "ONCOLOGICO",
        "PATOLOGIE RENALI",
        "EPILESSIA",
        "ARTROSI",
        "SCLEROSI MULTIPLA",
        "FIBROMIALGIA",
        "LIPEDEMA",
        "LINFEDEMA",
        "PROBLEMATICHE DELLA PELLE",
        "MALATTIE METABOLICHE EREDITARIE"
    ]

    # Criteri specifici per Coach
    COACH_CRITERIA = [
        "UOMINI",
        "DONNE",
        "MINORENNI <15",
        "MINORENNI >15",
        "ETA' 18-55",
        "ETA' >55",
        "DCA",
        "IPERTENSIONE",
        "PCOS",
        "OBESITA' - SINDROME METABOLICA",
        "ENDOMETRIOSI",
        "OSTEOPOROSI",
        "SPORTIVI",
        "MENOPAUSA",
        "ARTROSI",
        "SCLEROSI MULTIPLA",
        "FIBROMIALGIA",
        "LIPEDEMA",
        "LINFEDEMA",
        "POSTURALE",
        "GRAVIDANZA",
        "RIABILITAZIONE POST INFORTUNIO"
    ]

    @classmethod
    def get_schema(cls) -> Dict[str, List[str]]:
        """Restituisce lo schema completo dei criteri diviso per ambito."""
        return {
            "nutrizione": cls.COMMON_MED_CRITERIA,
            "psicologia": cls.COMMON_MED_CRITERIA,
            "coach": cls.COACH_CRITERIA
        }

    @classmethod
    def get_criteria_for_role(cls, role: str) -> List[str]:
        """Restituisce la lista dei criteri validi per un dato ruolo/ambito."""
        schema = cls.get_schema()
        # Mappatura ruolo/team -> chiave schema
        # Assumiamo che role sia 'nutrizionista', 'psicologo', 'coach' o simile
        if 'nutri' in role.lower():
            return schema['nutrizione']
        if 'psico' in role.lower():
            return schema['psicologia']
        if 'coach' in role.lower():
            return schema['coach']
        
        # Default fallback (o unione di tutti)
        return list(set(cls.COMMON_MED_CRITERIA + cls.COACH_CRITERIA))

    @classmethod
    def validate_criteria(cls, role: str, criteria: Dict[str, bool]) -> Dict[str, bool]:
        """
        Valida e pulisce i criteri inviati per un utente.
        Rimuove chiavi non valide per il ruolo.
        """
        valid_keys = set(cls.get_criteria_for_role(role))
        return {k: v for k, v in criteria.items() if k in valid_keys}
