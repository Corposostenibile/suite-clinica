"""
Modello per i Report Settimanali del Team
==========================================

Gestisce i report settimanali compilati dai membri del team.
"""
from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Optional

from sqlalchemy import Index, UniqueConstraint, and_, or_, extract
from sqlalchemy.orm import validates

from corposostenibile.extensions import db
from corposostenibile.models import TimestampMixin


class WeeklyReport(TimestampMixin, db.Model):
    """
    Report settimanale compilato dai membri del team.
    
    Permette ad ogni utente di compilare un report a settimana
    con feedback su obiettivi, vittorie, ostacoli e idee.
    """
    __tablename__ = "weekly_reports"
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Foreign Keys
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    department_id = db.Column(
        db.Integer,
        db.ForeignKey("departments.id", ondelete="SET NULL"),
        index=True
    )
    
    # Report Metadata
    week_start = db.Column(db.Date, nullable=False, index=True)
    week_end = db.Column(db.Date, nullable=False)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Report Content - Step by step
    # Step 2: Riflessione OKR Dipartimento (nullable per Sales)
    department_reflection = db.Column(db.Text, nullable=True)
    
    # Step 3: Riflessione OKR Personali (nullable per Sales)
    personal_reflection = db.Column(db.Text, nullable=True)
    
    # Step 4: Vittoria settimanale (nullable per Sales)
    weekly_victory = db.Column(db.Text, nullable=True)
    
    # Step 5: Azioni da migliorare (nullable per Sales)
    areas_to_improve = db.Column(db.Text, nullable=True)
    
    # Step 6: Ostacolo principale (usato da tutti)
    main_obstacle = db.Column(db.Text, nullable=True)
    
    # Step 7: Idee (facoltativo)
    ideas = db.Column(db.Text)
    
    # Campi aggiuntivi per Sales
    # Suggerimenti per sormontare ostacolo (Sales)
    obstacle_suggestions = db.Column(db.Text, nullable=True)
    
    # Punti da migliorare nel lavoro (Sales)
    work_improvements = db.Column(db.Text, nullable=True)
    
    # Report type flag
    report_type = db.Column(db.String(20), nullable=False, default='weekly')
    
    # Status
    is_complete = db.Column(db.Boolean, default=True, nullable=False)
    
    # Relationships
    user = db.relationship(
        "User",
        backref=db.backref("weekly_reports", lazy="dynamic", cascade="all, delete-orphan")
    )
    department = db.relationship(
        "Department",
        backref=db.backref("weekly_reports", lazy="dynamic")
    )
    
    # Constraints
    __table_args__ = (
        # Un solo report per utente per settimana
        UniqueConstraint("user_id", "week_start", name="uq_weekly_report_user_week"),
        # Indici per query comuni
        Index("ix_weekly_report_week_dept", "week_start", "department_id"),
        Index("ix_weekly_report_submission", "submission_date"),
    )
    
    @validates("week_start")
    def validate_week_start(self, key, value):
        """Assicura che week_start sia sempre un lunedì."""
        if isinstance(value, str):
            value = datetime.strptime(value, "%Y-%m-%d").date()
        
        # Calcola il lunedì della settimana
        days_since_monday = value.weekday()
        monday = value - timedelta(days=days_since_monday)
        
        return monday
    
    @validates("week_end")
    def validate_week_end(self, key, value):
        """Calcola automaticamente week_end come domenica."""
        if hasattr(self, "week_start") and self.week_start:
            return self.week_start + timedelta(days=6)
        return value
    
    @property
    def week_number(self) -> int:
        """Numero della settimana nell'anno."""
        return self.week_start.isocalendar()[1]
    
    @property
    def year(self) -> int:
        """Anno del report."""
        return self.week_start.year
    
    @property
    def can_be_edited(self) -> bool:
        """
        Un report può essere modificato solo durante il weekend
        della settimana di riferimento (ven, sab, dom) o il lunedì successivo.
        """
        today = date.today()
        # Venerdì, sabato, domenica della settimana
        friday = self.week_start + timedelta(days=4)
        sunday = self.week_end
        # Lunedì della settimana successiva
        monday_next = self.week_end + timedelta(days=1)
        
        return friday <= today <= monday_next
    
    @classmethod
    def get_current_week_dates(cls) -> tuple[date, date]:
        """Ritorna le date di inizio e fine della settimana corrente.
        Se siamo di lunedì, ritorna la settimana precedente."""
        today = date.today()
        
        # Se è lunedì (weekday() == 0), considera la settimana precedente
        if today.weekday() == 0:
            # Settimana precedente
            monday = today - timedelta(days=7)
            sunday = monday + timedelta(days=6)
        else:
            # Settimana corrente
            monday = today - timedelta(days=today.weekday())
            sunday = monday + timedelta(days=6)
        
        return monday, sunday
    
    @classmethod
    def is_sales_department(cls, department_name: str) -> bool:
        """Verifica se il dipartimento è uno dei Sales."""
        if not department_name:
            return False
        return department_name in ["Consulenti Sales 1", "Consulenti Sales 2"]
    
    @classmethod
    def is_last_saturday_of_month(cls, check_date: date = None) -> bool:
        """Verifica se la data è l'ultimo sabato del mese."""
        if check_date is None:
            check_date = date.today()
        
        # Deve essere sabato
        if check_date.weekday() != 5:  # 5 = sabato
            return False
        
        # Trova l'ultimo giorno del mese
        if check_date.month == 12:
            last_day = date(check_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(check_date.year, check_date.month + 1, 1) - timedelta(days=1)
        
        # Verifica se c'è un altro sabato dopo questa data nel mese
        days_until_end = (last_day - check_date).days
        return days_until_end < 7
    
    @classmethod
    def get_last_saturday_of_month(cls, check_date: date = None) -> date:
        """Trova l'ultimo sabato del mese per una data specifica."""
        if check_date is None:
            check_date = date.today()
        
        # Trova l'ultimo giorno del mese
        if check_date.month == 12:
            last_day = date(check_date.year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = date(check_date.year, check_date.month + 1, 1) - timedelta(days=1)
        
        # Trova l'ultimo sabato partendo dall'ultimo giorno del mese
        while last_day.weekday() != 5:  # 5 = sabato
            last_day -= timedelta(days=1)
        
        return last_day
    
    @classmethod
    def is_in_sales_submission_window(cls, check_date: date = None) -> bool:
        """
        Verifica se la data è nella finestra di compilazione per Sales.
        Sales possono compilare: ultimo sabato del mese + domenica + lunedì
        """
        if check_date is None:
            check_date = date.today()
        
        # Trova l'ultimo sabato del mese corrente
        last_saturday = cls.get_last_saturday_of_month(check_date)
        
        # Verifica se siamo nella finestra di 3 giorni
        # Ultimo sabato, domenica successiva, o lunedì successivo
        return check_date in [
            last_saturday,
            last_saturday + timedelta(days=1),  # Domenica
            last_saturday + timedelta(days=2)   # Lunedì
        ]
    
    @classmethod
    def can_submit_report(cls, user_id: int) -> bool:
        """
        Verifica se l'utente può compilare il report.
        - Sales: ultimo sabato del mese + domenica + lunedì (3 giorni consecutivi)
        - Altri: venerdì, sabato, domenica o lunedì (per settimana precedente)
        """
        from corposostenibile.models import User
        user = User.query.get(user_id)
        if not user:
            return False
        
        today = date.today()
        
        # Se è un dipartimento Sales
        if user.department and cls.is_sales_department(user.department.name):
            return cls.is_in_sales_submission_window(today)
        
        # Per tutti gli altri: venerdì, sabato, domenica o lunedì
        weekday = today.weekday()
        # 0 = lunedì, 4 = venerdì, 5 = sabato, 6 = domenica
        return weekday in [0, 4, 5, 6]
    
    @classmethod
    def user_has_report_this_period(cls, user_id: int) -> bool:
        """Verifica se l'utente ha già compilato il report per il periodo corrente."""
        from corposostenibile.models import User
        user = User.query.get(user_id)
        if not user:
            return False
        
        # Per Sales: verifica se ha già un report questo mese
        if user.department and cls.is_sales_department(user.department.name):
            today = date.today()
            month_start = date(today.year, today.month, 1)
            month_end = date(today.year, today.month + 1, 1) - timedelta(days=1) if today.month < 12 else date(today.year + 1, 1, 1) - timedelta(days=1)
            
            return cls.query.filter(
                cls.user_id == user_id,
                cls.week_start >= month_start,
                cls.week_start <= month_end,
                cls.report_type == 'monthly'
            ).first() is not None
        
        # Per gli altri: verifica settimanale standard
        monday, _ = cls.get_current_week_dates()
        return cls.query.filter_by(
            user_id=user_id,
            week_start=monday,
            report_type='weekly'
        ).first() is not None
    
    @classmethod
    def user_has_report_this_week(cls, user_id: int) -> bool:
        """Alias per compatibilità - usa user_has_report_this_period."""
        return cls.user_has_report_this_period(user_id)
    
    @classmethod
    def get_reports_for_week(cls, week_start: date, user=None, department_id=None):
        """
        Recupera i report per una settimana specifica con filtri opzionali.

        Args:
            week_start: Data di inizio settimana (lunedì)
            user: User object per applicare filtri di visibilità
            department_id: Filtra per dipartimento specifico
        """
        query = cls.query.filter_by(week_start=week_start)

        if department_id:
            query = query.filter_by(department_id=department_id)

        # Applica filtri di visibilità se c'è un utente
        # Admin e department_id 17 vedono tutti i report senza filtri
        if user and not (user.is_admin or (hasattr(user, 'department_id') and user.department_id == 17)):
            from corposostenibile.models import User, Department

            # Se è head of department, vede solo il suo dipartimento + CEO
            if hasattr(user, 'department') and user.department and user.department.head_id == user.id:
                ceo_dept = Department.query.filter_by(name="CEO").first()
                ceo_dept_id = ceo_dept.id if ceo_dept else None

                query = query.filter(
                    or_(
                        cls.department_id == user.department_id,
                        cls.department_id == ceo_dept_id
                    )
                )
            else:
                # Utente normale: vede solo i suoi report + CEO department
                ceo_dept = Department.query.filter_by(name="CEO").first()
                ceo_dept_id = ceo_dept.id if ceo_dept else None

                query = query.filter(
                    or_(
                        cls.user_id == user.id,
                        cls.department_id == ceo_dept_id
                    )
                )

        return query.order_by(cls.submission_date.desc()).all()
    
    def to_dict(self) -> dict:
        """Serializza il report in dizionario."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": self.user.full_name if self.user else "N/A",
            "department_id": self.department_id,
            "department_name": self.department.name if self.department else "N/A",
            "week_start": self.week_start.isoformat(),
            "week_end": self.week_end.isoformat(),
            "week_number": self.week_number,
            "year": self.year,
            "submission_date": self.submission_date.isoformat(),
            "department_reflection": self.department_reflection,
            "personal_reflection": self.personal_reflection,
            "weekly_victory": self.weekly_victory,
            "areas_to_improve": self.areas_to_improve,
            "main_obstacle": self.main_obstacle,
            "ideas": self.ideas,
            "is_complete": self.is_complete,
            "can_be_edited": self.can_be_edited
        }
    
    def __repr__(self) -> str:
        return f"<WeeklyReport {self.user_id} - Week {self.week_number}/{self.year}>"