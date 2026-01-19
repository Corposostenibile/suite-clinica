"""
Routes per il blueprint Manual
"""

from flask import render_template, redirect, url_for
from flask_login import login_required
from . import manual_bp


@manual_bp.route("/")
@login_required
def index():
    """Homepage del manuale - lista moduli disponibili."""
    return render_template("manual/index.html")


@manual_bp.route("/recruiting")
@login_required
def recruiting_index():
    """Index recruiting - selezione HR o Finance."""
    return render_template("manual/recruiting/index.html")


@manual_bp.route("/recruiting/hr")
@login_required
def recruiting_hr():
    """Manuale recruiting per HR - pipeline, offerte, ATS, kanban, onboarding."""
    return render_template("manual/recruiting/hr.html")


@manual_bp.route("/recruiting/finance")
@login_required
def recruiting_finance():
    """Manuale recruiting per Finance - costi, ROI, analytics."""
    return render_template("manual/recruiting/finance.html")


@manual_bp.route("/leads")
@login_required
def leads_index():
    """Index leads - selezione Sales, Finance o Health Manager."""
    return render_template("manual/leads/index.html")


@manual_bp.route("/leads/sales")
@login_required
def leads_sales():
    """Manuale leads per Sales - dashboard, gestione lead, pagamenti."""
    return render_template("manual/leads/sales.html")


@manual_bp.route("/leads/finance")
@login_required
def leads_finance():
    """Manuale leads per Finance - approvazione pagamenti, verifica."""
    return render_template("manual/leads/finance.html")


@manual_bp.route("/leads/health-manager")
@login_required
def leads_health_manager():
    """Manuale leads per Health Manager - assegnazione professionisti."""
    return render_template("manual/leads/health_manager.html")


@manual_bp.route("/checks/professionals")
@login_required
def checks_professionals():
    """Manuale check per professionisti - nutrizionisti, coach e psicologi."""
    return render_template("manual/checks/professionals.html")
