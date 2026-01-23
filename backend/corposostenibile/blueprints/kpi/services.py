"""
KPI Services - Calcolo KPI Aziendali e ARR
==========================================

Contiene la logica di business per:
- Calcolo Tasso Rinnovi
- Calcolo Tasso Referral
- Calcolo ARR (Adjusted Renewal Rate) per professionista
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_

from corposostenibile.extensions import db
from corposostenibile.models import (
    Cliente, PagamentoInterno, User, CallBonus,
    KPISnapshot, ProfessionistaBonusSnapshot, KPITypeEnum
)


class KPIService:
    """
    Servizio per il calcolo dei KPI aziendali.
    """

    @staticmethod
    def calcola_tasso_rinnovi(
        periodo_inizio: date,
        periodo_fine: date,
        save_snapshot: bool = True,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Calcola il Tasso Rinnovi nel periodo specificato.

        Formula:
        Tasso Rinnovi = (Clienti che rinnovano / Clienti in scadenza) * 100

        Args:
            periodo_inizio: Data inizio periodo
            periodo_fine: Data fine periodo
            save_snapshot: Se salvare lo snapshot nel DB
            user_id: ID utente che triggera il calcolo

        Returns:
            Dict con numeratore, denominatore, percentuale e dettagli
        """
        # Clienti in scadenza nel periodo (data_scadenza_pacchetto nel range)
        clienti_in_scadenza = Cliente.query.filter(
            and_(
                Cliente.data_scadenza_pacchetto >= periodo_inizio,
                Cliente.data_scadenza_pacchetto <= periodo_fine,
                Cliente.stato_servizio.in_(['attivo', 'in_scadenza'])
            )
        ).count()

        # Clienti che hanno rinnovato (pagamento interno con tipo rinnovo nel periodo)
        clienti_rinnovati = db.session.query(
            func.count(func.distinct(PagamentoInterno.cliente_id))
        ).filter(
            and_(
                PagamentoInterno.data_pagamento >= periodo_inizio,
                PagamentoInterno.data_pagamento <= periodo_fine,
                PagamentoInterno.stato_approvazione == 'approvato',
                PagamentoInterno.servizio_acquistato.ilike('%rinnovo%')
            )
        ).scalar() or 0

        # Calcolo percentuale
        denominatore = clienti_in_scadenza if clienti_in_scadenza > 0 else 1
        percentuale = (clienti_rinnovati / denominatore) * 100

        dettagli = {
            'clienti_in_scadenza': clienti_in_scadenza,
            'clienti_rinnovati': clienti_rinnovati,
            'formula': 'clienti_rinnovati / clienti_in_scadenza * 100'
        }

        # Salva snapshot se richiesto
        if save_snapshot:
            snapshot = KPISnapshot(
                kpi_type=KPITypeEnum.tasso_rinnovi.value,
                periodo_inizio=periodo_inizio,
                periodo_fine=periodo_fine,
                numeratore=clienti_rinnovati,
                denominatore=denominatore,
                valore_percentuale=Decimal(str(round(percentuale, 2))),
                dettagli_calcolo=dettagli,
                calcolato_da_user_id=user_id
            )
            db.session.add(snapshot)
            db.session.commit()

        return {
            'numeratore': clienti_rinnovati,
            'denominatore': denominatore,
            'percentuale': round(percentuale, 2),
            'dettagli': dettagli
        }

    @staticmethod
    def calcola_tasso_referral(
        periodo_inizio: date,
        periodo_fine: date,
        save_snapshot: bool = True,
        user_id: Optional[int] = None
    ) -> Dict:
        """
        Calcola il Tasso Referral nel periodo specificato.

        Formula:
        Tasso Referral = (Referral convertiti / Referral totali) * 100

        Args:
            periodo_inizio: Data inizio periodo
            periodo_fine: Data fine periodo
            save_snapshot: Se salvare lo snapshot nel DB
            user_id: ID utente che triggera il calcolo

        Returns:
            Dict con numeratore, denominatore, percentuale e dettagli
        """
        # Referral totali nel periodo (call bonus con cliente_proveniente_da not null)
        referral_totali = CallBonus.query.filter(
            and_(
                CallBonus.data_bonus >= periodo_inizio,
                CallBonus.data_bonus <= periodo_fine,
                CallBonus.cliente_proveniente_da.isnot(None)
            )
        ).count()

        # Referral convertiti (con convertito=True)
        referral_convertiti = CallBonus.query.filter(
            and_(
                CallBonus.data_bonus >= periodo_inizio,
                CallBonus.data_bonus <= periodo_fine,
                CallBonus.cliente_proveniente_da.isnot(None),
                CallBonus.convertito == True
            )
        ).count()

        # Calcolo percentuale
        denominatore = referral_totali if referral_totali > 0 else 1
        percentuale = (referral_convertiti / denominatore) * 100

        dettagli = {
            'referral_totali': referral_totali,
            'referral_convertiti': referral_convertiti,
            'formula': 'referral_convertiti / referral_totali * 100'
        }

        # Salva snapshot se richiesto
        if save_snapshot:
            snapshot = KPISnapshot(
                kpi_type=KPITypeEnum.tasso_referral.value,
                periodo_inizio=periodo_inizio,
                periodo_fine=periodo_fine,
                numeratore=referral_convertiti,
                denominatore=denominatore,
                valore_percentuale=Decimal(str(round(percentuale, 2))),
                dettagli_calcolo=dettagli,
                calcolato_da_user_id=user_id
            )
            db.session.add(snapshot)
            db.session.commit()

        return {
            'numeratore': referral_convertiti,
            'denominatore': denominatore,
            'percentuale': round(percentuale, 2),
            'dettagli': dettagli
        }


class ARRService:
    """
    Servizio per il calcolo dell'ARR (Adjusted Renewal Rate) per professionisti.

    Formula ARR:
    (Rinnovi + Upgrade_Conv*60% + Upgrade_Ric*40% + Referral_Conv*60% + Referral_Ric*40%)
    / (Clienti_Eleggibili + Upgrade_Totali + Referral_Totali)

    Lo split 60/40:
    - 60% al professionista proponente (chi propone l'upgrade/referral)
    - 40% al professionista ricevente (chi riceve il cliente)
    """

    PESO_PROPONENTE = Decimal('0.6')
    PESO_RICEVENTE = Decimal('0.4')

    @staticmethod
    def get_professionisti() -> List[User]:
        """
        Restituisce la lista dei professionisti attivi.
        Professionisti: nutrizionisti, coach, psicologi.
        """
        return User.query.filter(
            and_(
                User.is_active == True,
                or_(
                    User.is_nutritionist == True,
                    User.is_coach == True,
                    User.is_psychologist == True
                )
            )
        ).all()

    @staticmethod
    def calcola_arr_professionista(
        user_id: int,
        periodo_inizio: date,
        periodo_fine: date,
        save_snapshot: bool = True
    ) -> Dict:
        """
        Calcola l'ARR per un singolo professionista.

        Args:
            user_id: ID del professionista
            periodo_inizio: Data inizio periodo
            periodo_fine: Data fine periodo
            save_snapshot: Se salvare lo snapshot nel DB

        Returns:
            Dict con tutti i contatori e l'ARR calcolato
        """
        user = User.query.get(user_id)
        if not user:
            return {'error': 'Professionista non trovato'}

        # ========== CONTATORI NUMERATORE ==========

        # 1. Rinnovi diretti: pagamenti interni approvati per clienti del professionista
        rinnovi_count = ARRService._conta_rinnovi_diretti(user_id, periodo_inizio, periodo_fine)

        # 2. Upgrade convertiti come proponente (60%)
        upgrade_proponente = ARRService._conta_upgrade_proponente(user_id, periodo_inizio, periodo_fine)

        # 3. Upgrade ricevuti come ricevente (40%)
        upgrade_ricevente = ARRService._conta_upgrade_ricevente(user_id, periodo_inizio, periodo_fine)

        # 4. Referral convertiti come proponente (60%)
        referral_proponente = ARRService._conta_referral_proponente(user_id, periodo_inizio, periodo_fine)

        # 5. Referral ricevuti come ricevente (40%)
        referral_ricevente = ARRService._conta_referral_ricevente(user_id, periodo_inizio, periodo_fine)

        # ========== CONTATORI DENOMINATORE ==========

        # 1. Clienti eleggibili (has_goals_left != False)
        clienti_eleggibili = ARRService._conta_clienti_eleggibili(user_id, periodo_inizio, periodo_fine)

        # 2. Upgrade totali proposti
        upgrade_totali = ARRService._conta_upgrade_totali(user_id, periodo_inizio, periodo_fine)

        # 3. Referral totali
        referral_totali = ARRService._conta_referral_totali(user_id, periodo_inizio, periodo_fine)

        # ========== CALCOLO ARR ==========
        numeratore_pesato = (
            Decimal(rinnovi_count) +
            (Decimal(upgrade_proponente) * ARRService.PESO_PROPONENTE) +
            (Decimal(upgrade_ricevente) * ARRService.PESO_RICEVENTE) +
            (Decimal(referral_proponente) * ARRService.PESO_PROPONENTE) +
            (Decimal(referral_ricevente) * ARRService.PESO_RICEVENTE)
        )

        denominatore_totale = clienti_eleggibili + upgrade_totali + referral_totali

        if denominatore_totale == 0:
            arr_percentuale = Decimal('0')
        else:
            arr_percentuale = (numeratore_pesato / Decimal(denominatore_totale)) * 100

        dettagli = {
            'rinnovi_count': rinnovi_count,
            'upgrade_proponente': upgrade_proponente,
            'upgrade_ricevente': upgrade_ricevente,
            'referral_proponente': referral_proponente,
            'referral_ricevente': referral_ricevente,
            'clienti_eleggibili': clienti_eleggibili,
            'upgrade_totali': upgrade_totali,
            'referral_totali': referral_totali,
            'formula': '(Rinnovi + Upgrade*60% + Referral*60%) / (Eleggibili + Upgrade + Referral)'
        }

        # Salva snapshot se richiesto
        if save_snapshot and denominatore_totale > 0:
            snapshot = ProfessionistaBonusSnapshot(
                user_id=user_id,
                periodo_inizio=periodo_inizio,
                periodo_fine=periodo_fine,
                rinnovi_count=rinnovi_count,
                upgrade_convertiti_proponente=upgrade_proponente,
                upgrade_convertiti_ricevente=upgrade_ricevente,
                referral_convertiti_proponente=referral_proponente,
                referral_convertiti_ricevente=referral_ricevente,
                clienti_eleggibili=clienti_eleggibili,
                upgrade_totali=upgrade_totali,
                referral_totali=referral_totali,
                numeratore_pesato=numeratore_pesato,
                denominatore_totale=denominatore_totale,
                arr_percentuale=arr_percentuale.quantize(Decimal('0.01')),
                dettagli_calcolo=dettagli
            )
            db.session.add(snapshot)
            db.session.commit()

        return {
            'user_id': user_id,
            'user_name': user.full_name or user.email,
            'periodo_inizio': periodo_inizio.isoformat(),
            'periodo_fine': periodo_fine.isoformat(),
            'numeratore_pesato': float(numeratore_pesato),
            'denominatore_totale': denominatore_totale,
            'arr_percentuale': float(arr_percentuale.quantize(Decimal('0.01'))),
            'dettagli': dettagli
        }

    @staticmethod
    def _conta_rinnovi_diretti(user_id: int, inizio: date, fine: date) -> int:
        """Conta i rinnovi dei clienti assegnati al professionista."""
        # Trova i clienti assegnati a questo professionista
        clienti_ids = db.session.query(Cliente.cliente_id).filter(
            or_(
                Cliente.nutrizionista_id == user_id,
                Cliente.coach_id == user_id,
                Cliente.psicologa_id == user_id
            )
        ).subquery()

        # Conta i pagamenti interni di tipo rinnovo per questi clienti
        count = db.session.query(func.count(PagamentoInterno.id)).filter(
            and_(
                PagamentoInterno.cliente_id.in_(clienti_ids),
                PagamentoInterno.data_pagamento >= inizio,
                PagamentoInterno.data_pagamento <= fine,
                PagamentoInterno.stato_approvazione == 'approvato',
                PagamentoInterno.servizio_acquistato.ilike('%rinnovo%')
            )
        ).scalar() or 0

        return count

    @staticmethod
    def _conta_upgrade_proponente(user_id: int, inizio: date, fine: date) -> int:
        """Conta gli upgrade convertiti proposti dal professionista."""
        # CallBonus dove il professionista è il proponente e c'è stata conversione
        count = CallBonus.query.filter(
            and_(
                CallBonus.user_propone_id == user_id,
                CallBonus.data_bonus >= inizio,
                CallBonus.data_bonus <= fine,
                CallBonus.convertito == True
            )
        ).count()
        return count

    @staticmethod
    def _conta_upgrade_ricevente(user_id: int, inizio: date, fine: date) -> int:
        """Conta gli upgrade convertiti ricevuti dal professionista."""
        # CallBonus dove il professionista è il ricevente e c'è stata conversione
        count = CallBonus.query.filter(
            and_(
                CallBonus.user_riceve_id == user_id,
                CallBonus.data_bonus >= inizio,
                CallBonus.data_bonus <= fine,
                CallBonus.convertito == True
            )
        ).count()
        return count

    @staticmethod
    def _conta_referral_proponente(user_id: int, inizio: date, fine: date) -> int:
        """Conta i referral convertiti proposti dal professionista."""
        # CallBonus con cliente_proveniente_da (referral) dove professionista è proponente
        count = CallBonus.query.filter(
            and_(
                CallBonus.user_propone_id == user_id,
                CallBonus.data_bonus >= inizio,
                CallBonus.data_bonus <= fine,
                CallBonus.cliente_proveniente_da.isnot(None),
                CallBonus.convertito == True
            )
        ).count()
        return count

    @staticmethod
    def _conta_referral_ricevente(user_id: int, inizio: date, fine: date) -> int:
        """Conta i referral convertiti ricevuti dal professionista."""
        # CallBonus con cliente_proveniente_da (referral) dove professionista è ricevente
        count = CallBonus.query.filter(
            and_(
                CallBonus.user_riceve_id == user_id,
                CallBonus.data_bonus >= inizio,
                CallBonus.data_bonus <= fine,
                CallBonus.cliente_proveniente_da.isnot(None),
                CallBonus.convertito == True
            )
        ).count()
        return count

    @staticmethod
    def _conta_clienti_eleggibili(user_id: int, inizio: date, fine: date) -> int:
        """
        Conta i clienti eleggibili per il denominatore.
        Eleggibili = clienti attivi con has_goals_left != False (True o NULL)
        """
        count = Cliente.query.filter(
            and_(
                or_(
                    Cliente.nutrizionista_id == user_id,
                    Cliente.coach_id == user_id,
                    Cliente.psicologa_id == user_id
                ),
                Cliente.stato_servizio.in_(['attivo', 'in_scadenza']),
                or_(
                    Cliente.has_goals_left == True,
                    Cliente.has_goals_left.is_(None)
                )
            )
        ).count()
        return count

    @staticmethod
    def _conta_upgrade_totali(user_id: int, inizio: date, fine: date) -> int:
        """Conta tutti gli upgrade proposti dal professionista nel periodo."""
        count = CallBonus.query.filter(
            and_(
                CallBonus.user_propone_id == user_id,
                CallBonus.data_bonus >= inizio,
                CallBonus.data_bonus <= fine
            )
        ).count()
        return count

    @staticmethod
    def _conta_referral_totali(user_id: int, inizio: date, fine: date) -> int:
        """Conta tutti i referral del professionista nel periodo."""
        count = CallBonus.query.filter(
            and_(
                CallBonus.user_propone_id == user_id,
                CallBonus.data_bonus >= inizio,
                CallBonus.data_bonus <= fine,
                CallBonus.cliente_proveniente_da.isnot(None)
            )
        ).count()
        return count

    @staticmethod
    def calcola_arr_tutti_professionisti(
        periodo_inizio: date,
        periodo_fine: date,
        save_snapshot: bool = True
    ) -> List[Dict]:
        """
        Calcola l'ARR per tutti i professionisti attivi.

        Args:
            periodo_inizio: Data inizio periodo
            periodo_fine: Data fine periodo
            save_snapshot: Se salvare gli snapshot nel DB

        Returns:
            Lista di Dict con ARR per ogni professionista
        """
        professionisti = ARRService.get_professionisti()
        risultati = []

        for prof in professionisti:
            arr = ARRService.calcola_arr_professionista(
                user_id=prof.id,
                periodo_inizio=periodo_inizio,
                periodo_fine=periodo_fine,
                save_snapshot=save_snapshot
            )
            risultati.append(arr)

        # Ordina per ARR decrescente
        risultati.sort(key=lambda x: x.get('arr_percentuale', 0), reverse=True)

        return risultati


class KPIDashboardService:
    """
    Servizio per la dashboard KPI con dati aggregati.
    """

    @staticmethod
    def get_dashboard_data(periodo_inizio: date, periodo_fine: date) -> Dict:
        """
        Restituisce tutti i dati per la dashboard KPI.
        """
        # Calcola KPI aziendali
        tasso_rinnovi = KPIService.calcola_tasso_rinnovi(
            periodo_inizio, periodo_fine, save_snapshot=False
        )
        tasso_referral = KPIService.calcola_tasso_referral(
            periodo_inizio, periodo_fine, save_snapshot=False
        )

        # Calcola ARR per tutti i professionisti
        arr_professionisti = ARRService.calcola_arr_tutti_professionisti(
            periodo_inizio, periodo_fine, save_snapshot=False
        )

        # Statistiche aggregate
        arr_values = [p['arr_percentuale'] for p in arr_professionisti if p.get('arr_percentuale')]
        arr_medio = sum(arr_values) / len(arr_values) if arr_values else 0

        return {
            'periodo': {
                'inizio': periodo_inizio.isoformat(),
                'fine': periodo_fine.isoformat()
            },
            'kpi_aziendali': {
                'tasso_rinnovi': tasso_rinnovi,
                'tasso_referral': tasso_referral
            },
            'arr': {
                'professionisti': arr_professionisti,
                'arr_medio': round(arr_medio, 2),
                'totale_professionisti': len(arr_professionisti)
            }
        }

    @staticmethod
    def get_storico_kpi(kpi_type: str, limit: int = 12) -> List[Dict]:
        """
        Restituisce lo storico degli snapshot KPI.

        Args:
            kpi_type: Tipo di KPI (tasso_rinnovi, tasso_referral)
            limit: Numero massimo di record

        Returns:
            Lista di snapshot ordinati per data decrescente
        """
        snapshots = KPISnapshot.query.filter(
            KPISnapshot.kpi_type == kpi_type
        ).order_by(
            KPISnapshot.periodo_fine.desc()
        ).limit(limit).all()

        return [{
            'id': s.id,
            'periodo_inizio': s.periodo_inizio.isoformat(),
            'periodo_fine': s.periodo_fine.isoformat(),
            'numeratore': s.numeratore,
            'denominatore': s.denominatore,
            'percentuale': float(s.valore_percentuale),
            'target': float(s.target_percentuale) if s.target_percentuale else None,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in snapshots]

    @staticmethod
    def get_storico_arr_professionista(user_id: int, limit: int = 12) -> List[Dict]:
        """
        Restituisce lo storico ARR per un professionista.

        Args:
            user_id: ID del professionista
            limit: Numero massimo di record

        Returns:
            Lista di snapshot ARR ordinati per data decrescente
        """
        snapshots = ProfessionistaBonusSnapshot.query.filter(
            ProfessionistaBonusSnapshot.user_id == user_id
        ).order_by(
            ProfessionistaBonusSnapshot.periodo_fine.desc()
        ).limit(limit).all()

        return [{
            'id': s.id,
            'periodo_inizio': s.periodo_inizio.isoformat(),
            'periodo_fine': s.periodo_fine.isoformat(),
            'arr_percentuale': float(s.arr_percentuale),
            'rinnovi': s.rinnovi_count,
            'upgrade_proponente': s.upgrade_convertiti_proponente,
            'upgrade_ricevente': s.upgrade_convertiti_ricevente,
            'referral_proponente': s.referral_convertiti_proponente,
            'referral_ricevente': s.referral_convertiti_ricevente,
            'target': float(s.target_arr) if s.target_arr else None,
            'bonus_raggiunto': s.bonus_raggiunto,
            'importo_bonus': float(s.importo_bonus) if s.importo_bonus else None,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in snapshots]
