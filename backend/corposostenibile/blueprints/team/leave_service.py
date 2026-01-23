"""
leave_service.py
================

Servizio per la gestione della logica business ferie/permessi.
"""

from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional
from sqlalchemy import func, and_, or_, extract
from sqlalchemy.orm import Session

from corposostenibile.extensions import db
from corposostenibile.models import (
    LeaveRequest, LeavePolicy, ItalianHoliday, User,
    LeaveTypeEnum, LeaveStatusEnum
)


class LeaveService:
    """Servizio per la gestione ferie e permessi."""
    
    @staticmethod
    def get_or_create_policy(year: int) -> LeavePolicy:
        """Ottiene o crea la policy per l'anno specificato."""
        policy = LeavePolicy.query.filter_by(year=year).first()
        if not policy:
            # Crea una policy di default
            policy = LeavePolicy(
                year=year,
                annual_leave_days=22,  # Default italiano
                annual_permission_hours=32,  # Default ROL
                min_consecutive_days=3,
                max_consecutive_days=15
            )
            db.session.add(policy)
            db.session.commit()
        return policy
    
    @staticmethod
    def calculate_working_days(start_date: date, end_date: date, user_id: int = None) -> float:
        """
        Calcola i giorni lavorativi tra due date, escludendo:
        - Weekend
        - Festività italiane
        - Giorni non lavorativi dell'utente (se specificato)
        """
        if start_date > end_date:
            return 0
            
        # Ottieni festività nell'intervallo
        holidays = ItalianHoliday.query.filter(
            ItalianHoliday.date >= start_date,
            ItalianHoliday.date <= end_date
        ).all()
        holiday_dates = {h.date for h in holidays}
        
        # Conta i giorni lavorativi
        working_days = 0
        current_date = start_date
        
        while current_date <= end_date:
            # Escludi weekend (5=sabato, 6=domenica)
            if current_date.weekday() < 5:
                # Escludi festività
                if current_date not in holiday_dates:
                    # Se specificato un utente, controlla il suo orario di lavoro
                    if user_id:
                        user = User.query.get(user_id)
                        if user and user.work_schedule:
                            # Mappa giorni settimana ai giorni nel work_schedule
                            day_map = ['lun', 'mar', 'mer', 'gio', 'ven', 'sab', 'dom']
                            current_day = day_map[current_date.weekday()]
                            
                            # Verifica se è un giorno lavorativo per l'utente
                            if current_day in user.work_schedule.get('days', []):
                                working_days += 1
                        else:
                            # Se non ha orario specifico, conta come lavorativo
                            working_days += 1
                    else:
                        working_days += 1
            
            current_date += timedelta(days=1)
            
        return working_days
    
    @staticmethod
    def get_user_leave_balance(user_id: int, year: int) -> dict:
        """
        Calcola il saldo ferie/permessi di un utente per l'anno specificato.
        
        Returns:
            dict: {
                'leave_days_total': int,
                'leave_days_used': float,
                'leave_days_available': float,
                'permission_hours_total': int,
                'permission_hours_used': float,
                'permission_hours_available': float,
                'sick_days_used': float
            }
        """
        policy = LeaveService.get_or_create_policy(year)
        
        # Query per le richieste approvate dell'anno
        approved_requests = LeaveRequest.query.filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status == LeaveStatusEnum.approvata,
            extract('year', LeaveRequest.start_date) == year
        ).all()
        
        # Calcola utilizzo
        leave_days_used = sum(
            req.working_days for req in approved_requests 
            if req.leave_type == LeaveTypeEnum.ferie
        )
        
        permission_hours_used = sum(
            req.hours or 0 for req in approved_requests 
            if req.leave_type == LeaveTypeEnum.permesso
        )
        
        sick_days_used = sum(
            req.working_days for req in approved_requests 
            if req.leave_type == LeaveTypeEnum.malattia
        )
        
        return {
            'leave_days_total': policy.annual_leave_days,
            'leave_days_used': leave_days_used,
            'leave_days_available': policy.annual_leave_days - leave_days_used,
            'permission_hours_total': policy.annual_permission_hours,
            'permission_hours_used': permission_hours_used,
            'permission_hours_available': policy.annual_permission_hours - permission_hours_used,
            'sick_days_used': sick_days_used
        }
    
    @staticmethod
    def check_overlapping_requests(user_id: int, start_date: date, end_date: date, 
                                   exclude_request_id: Optional[int] = None) -> List[LeaveRequest]:
        """Verifica se ci sono richieste sovrapposte."""
        query = LeaveRequest.query.filter(
            LeaveRequest.user_id == user_id,
            LeaveRequest.status.in_([LeaveStatusEnum.richiesta, LeaveStatusEnum.approvata]),
            or_(
                and_(
                    LeaveRequest.start_date <= start_date,
                    LeaveRequest.end_date >= start_date
                ),
                and_(
                    LeaveRequest.start_date <= end_date,
                    LeaveRequest.end_date >= end_date
                ),
                and_(
                    LeaveRequest.start_date >= start_date,
                    LeaveRequest.end_date <= end_date
                )
            )
        )
        
        if exclude_request_id:
            query = query.filter(LeaveRequest.id != exclude_request_id)
            
        return query.all()
    
    @staticmethod
    def validate_leave_request(user_id: int, leave_type: LeaveTypeEnum, 
                               start_date: date, end_date: date, 
                               hours: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """
        Valida una richiesta di ferie/permessi.
        
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        # Verifica date
        if start_date > end_date:
            return False, "La data di inizio deve essere prima della data di fine"
            
        if start_date < date.today():
            return False, "Non puoi richiedere ferie/permessi per date passate"
            
        # Verifica sovrapposizioni
        overlapping = LeaveService.check_overlapping_requests(user_id, start_date, end_date)
        if overlapping:
            return False, "Hai già richieste per questo periodo"
            
        year = start_date.year
        policy = LeaveService.get_or_create_policy(year)
        
        # Validazioni specifiche per tipo
        if leave_type == LeaveTypeEnum.ferie:
            # Calcola giorni lavorativi
            working_days = LeaveService.calculate_working_days(start_date, end_date, user_id)
            
            # Verifica limiti consecutivi
            if working_days < policy.min_consecutive_days:
                return False, f"Le ferie devono essere di almeno {policy.min_consecutive_days} giorni lavorativi consecutivi"
                
            if working_days > policy.max_consecutive_days:
                return False, f"Le ferie non possono superare {policy.max_consecutive_days} giorni lavorativi consecutivi"
                
            # Verifica disponibilità
            balance = LeaveService.get_user_leave_balance(user_id, year)
            if working_days > balance['leave_days_available']:
                return False, f"Giorni ferie insufficienti. Disponibili: {balance['leave_days_available']}"
                
        elif leave_type == LeaveTypeEnum.permesso:
            if not hours or hours <= 0:
                return False, "Devi specificare le ore di permesso"
                
            # Verifica disponibilità
            balance = LeaveService.get_user_leave_balance(user_id, year)
            if hours > balance['permission_hours_available']:
                return False, f"Ore permesso insufficienti. Disponibili: {balance['permission_hours_available']}"
                
        return True, None
    
    @staticmethod
    def get_team_calendar_data(month: int, year: int, department_id: Optional[int] = None) -> dict:
        """
        Ottiene i dati per il calendario team delle assenze.
        """
        # Query base - specifica la join con user (chi fa la richiesta)
        query = db.session.query(LeaveRequest).join(User, LeaveRequest.user_id == User.id).filter(
            LeaveRequest.status == LeaveStatusEnum.approvata,
            or_(
                and_(
                    extract('month', LeaveRequest.start_date) == month,
                    extract('year', LeaveRequest.start_date) == year
                ),
                and_(
                    extract('month', LeaveRequest.end_date) == month,
                    extract('year', LeaveRequest.end_date) == year
                ),
                and_(
                    LeaveRequest.start_date < date(year, month, 1),
                    LeaveRequest.end_date >= date(year, month, 1)
                )
            )
        )
        
        # Filtro per dipartimento se specificato
        if department_id:
            query = query.filter(User.department_id == department_id)
            
        requests = query.all()
        
        # Raggruppa per giorno
        calendar_data = {}
        for req in requests:
            current = max(req.start_date, date(year, month, 1))
            # Calcola ultimo giorno del mese
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)
            end = min(req.end_date, last_day)
            
            while current <= end:
                day_key = current.day
                if day_key not in calendar_data:
                    calendar_data[day_key] = []
                    
                calendar_data[day_key].append({
                    'user': req.user,
                    'type': req.leave_type,
                    'request_id': req.id
                })
                current += timedelta(days=1)
                
        return calendar_data
    
    @staticmethod
    def populate_italian_holidays(year: int) -> None:
        """Popola le festività italiane per l'anno specificato."""
        from datetime import date
        from dateutil.easter import easter
        
        # Verifica se già esistono
        existing = ItalianHoliday.query.filter_by(year=year).count()
        if existing > 0:
            return
            
        holidays = []
        
        # Festività fisse
        fixed_holidays = [
            (date(year, 1, 1), "Capodanno"),
            (date(year, 1, 6), "Epifania"),
            (date(year, 4, 25), "Festa della Liberazione"),
            (date(year, 5, 1), "Festa del Lavoro"),
            (date(year, 6, 2), "Festa della Repubblica"),
            (date(year, 8, 15), "Ferragosto"),
            (date(year, 11, 1), "Ognissanti"),
            (date(year, 12, 8), "Immacolata Concezione"),
            (date(year, 12, 25), "Natale"),
            (date(year, 12, 26), "Santo Stefano"),
        ]
        
        for holiday_date, name in fixed_holidays:
            holidays.append(ItalianHoliday(
                date=holiday_date,
                name=name,
                year=year,
                is_company_bridge=False
            ))
        
        # Festività mobili (Pasqua e Pasquetta)
        easter_date = easter(year)
        holidays.append(ItalianHoliday(
            date=easter_date,
            name="Pasqua",
            year=year,
            is_company_bridge=False
        ))
        holidays.append(ItalianHoliday(
            date=easter_date + timedelta(days=1),
            name="Lunedì dell'Angelo",
            year=year,
            is_company_bridge=False
        ))
        
        # Salva nel database
        for holiday in holidays:
            db.session.add(holiday)
        db.session.commit()