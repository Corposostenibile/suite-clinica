"""
Activity-Log (changelog per campo)
=================================

Registra ogni variazione *field-level* sui clienti, così è possibile
interrogare velocemente chi ha cambiato cosa e quando – senza dover
scandagliare la tabella delle versioni Continuum.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import relationship

from corposostenibile.extensions import db


class ActivityLog(db.Model):
    __tablename__ = "activity_log"

    id = db.Column(db.Integer, primary_key=True)

    # — chi / cosa / quando -------------------------------------------------
    cliente_id = db.Column(
        db.BigInteger, db.ForeignKey("clienti.cliente_id", ondelete="CASCADE"), nullable=False
    )
    field = db.Column(db.String(255), nullable=False)
    before = db.Column(db.Text)          # valore precedente (stringificato)
    after = db.Column(db.Text)           # nuovo valore
    ts = db.Column(
        db.DateTime, default=datetime.utcnow, nullable=False, index=True
    )
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))

    # — relationships (lazy='noload' per evitare costi inutili) -------------
    cliente = relationship("Cliente", lazy="noload")
    user = relationship("User", lazy="noload")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<ActivityLog #{self.id} cliente={self.cliente_id} "
            f"field={self.field} ts={self.ts:%Y-%m-%d %H:%M:%S}>"
        )
