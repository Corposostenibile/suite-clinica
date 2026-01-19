"""
Routes per questionari anonimi
"""
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from functools import wraps
from corposostenibile.extensions import db
from corposostenibile.models import AnonymousSurvey, AnonymousSurveyResponse, User
from . import team_bp


def admin_required(f):
    """Decorator per richiedere privilegi admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Accesso non autorizzato', 'error')
            return redirect(url_for('team.anonymous_surveys_list'))
        return f(*args, **kwargs)
    return decorated_function


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES PER UTENTI - Compilazione Questionario
# ═══════════════════════════════════════════════════════════════════════════

@team_bp.route('/questionari-anonimi')
@login_required
def anonymous_surveys_list():
    """Lista questionari anonimi disponibili"""
    surveys = AnonymousSurvey.query.filter_by(is_active=True).all()

    # Per ogni questionario, controlla se l'utente corrente ha già risposto
    surveys_data = []
    for survey in surveys:
        has_responded = AnonymousSurveyResponse.query.filter_by(
            survey_id=survey.id,
            user_id=current_user.id
        ).first() is not None

        surveys_data.append({
            'survey': survey,
            'has_responded': has_responded
        })

    return render_template(
        'team/anonymous_surveys/list.html',
        surveys_data=surveys_data
    )


@team_bp.route('/questionari-anonimi/<int:survey_id>')
@login_required
def view_anonymous_survey(survey_id):
    """Visualizza un questionario specifico"""
    survey = AnonymousSurvey.query.get_or_404(survey_id)

    if not survey.is_active:
        flash('Questo questionario non è più attivo', 'warning')
        return redirect(url_for('team.anonymous_surveys_list'))

    # Controlla se l'utente ha già risposto
    existing_response = AnonymousSurveyResponse.query.filter_by(
        survey_id=survey_id,
        user_id=current_user.id
    ).first()

    if existing_response:
        flash('Hai già compilato questo questionario. Grazie!', 'info')
        return redirect(url_for('team.anonymous_surveys_list'))

    return render_template(
        'team/anonymous_surveys/survey_form.html',
        survey=survey
    )


@team_bp.route('/questionari-anonimi/<int:survey_id>/submit', methods=['POST'])
@login_required
def submit_anonymous_survey(survey_id):
    """Salva la risposta al questionario"""
    survey = AnonymousSurvey.query.get_or_404(survey_id)

    if not survey.is_active:
        return jsonify({'success': False, 'message': 'Questionario non più attivo'}), 400

    # Controlla se l'utente ha già risposto
    existing_response = AnonymousSurveyResponse.query.filter_by(
        survey_id=survey_id,
        user_id=current_user.id
    ).first()

    if existing_response:
        return jsonify({'success': False, 'message': 'Hai già risposto a questo questionario'}), 400

    # Ottieni tutte le risposte dal form
    responses_data = request.get_json()

    if not responses_data:
        return jsonify({'success': False, 'message': 'Nessuna risposta ricevuta'}), 400

    # Crea la risposta
    response = AnonymousSurveyResponse(
        survey_id=survey_id,
        user_id=current_user.id,
        responses=responses_data
    )

    db.session.add(response)
    db.session.commit()

    return jsonify({
        'success': True,
        'message': 'Grazie per aver compilato il questionario!'
    })


# ═══════════════════════════════════════════════════════════════════════════
# ROUTES PER ADMIN - Visualizzazione Risposte
# ═══════════════════════════════════════════════════════════════════════════

@team_bp.route('/admin/questionari-anonimi')
@login_required
@admin_required
def admin_anonymous_surveys():
    """Dashboard admin per gestire questionari"""
    surveys = AnonymousSurvey.query.order_by(AnonymousSurvey.created_at.desc()).all()

    return render_template(
        'team/anonymous_surveys/admin_dashboard.html',
        surveys=surveys
    )


@team_bp.route('/admin/questionari-anonimi/<int:survey_id>/risposte')
@login_required
@admin_required
def admin_view_responses(survey_id):
    """Visualizza le risposte aggregate a un questionario"""
    survey = AnonymousSurvey.query.get_or_404(survey_id)

    # Carica tutte le risposte (SENZA mostrare user_id per garantire anonimato)
    responses = AnonymousSurveyResponse.query.filter_by(survey_id=survey_id).all()

    # Aggrega le risposte per domanda
    aggregated_data = _aggregate_responses(responses)

    # Mappa dei testi delle domande
    question_labels = _get_question_labels()

    return render_template(
        'team/anonymous_surveys/admin_responses.html',
        survey=survey,
        responses=responses,
        aggregated_data=aggregated_data,
        total_responses=len(responses),
        question_labels=question_labels
    )


def _get_question_labels():
    """Restituisce la mappa delle domande del questionario"""
    return {
        # SEZIONE 1
        'q1_1': '1.1 Da quanto tempo lavori in Corposostenibile?',
        'q1_2': '1.2 In quale dipartimento lavori?',

        # SEZIONE 2
        'q2_1': '2.1 Il tuo team di lavoro promuove un ambiente collaborativo?',
        'q2_2': '2.2 Ti senti accolto/a e incluso/a nel tuo gruppo di lavoro?',
        'q2_3': '2.3 Con quanta facilità riesci a parlare apertamente con i colleghi?',
        'q2_4': '2.4 Come definiresti il livello di fiducia reciproca tra colleghi?',
        'q2_5': '2.5 Hai mai assistito o vissuto episodi di discriminazione, esclusione o disagio relazionale?',
        'q2_5_other': '2.5 Dettagli episodi di discriminazione (facoltativo)',

        # SEZIONE 3
        'q3_1': '3.1 Ricevi informazioni chiare e puntuali riguardo agli obiettivi dell\'azienda?',
        'q3_2': '3.2 I tuoi responsabili comunicano in modo trasparente e aperto?',
        'q3_3': '3.3 Ritieni che i feedback (positivi o correttivi) siano espressi in modo costruttivo?',
        'q3_4': '3.4 Hai spazi, canali o momenti per esprimere le tue opinioni sul lavoro?',

        # SEZIONE 4
        'q4_1': '4.1 Il tuo responsabile diretto si interessa al tuo benessere lavorativo?',
        'q4_2': '4.2 Ti senti supportato/a nella gestione di eventuali difficoltà lavorative?',
        'q4_3': '4.3 Le decisioni del management ti sembrano coerenti con i valori aziendali?',
        'q4_4': '4.4 Come valuti la chiarezza degli obiettivi che ti vengono assegnati?',

        # SEZIONE 5
        'q5_1': '5.1 Ti senti motivato/a nello svolgere il tuo lavoro quotidiano?',
        'q5_2': '5.2 Hai l\'opportunità di sviluppare nuove competenze?',
        'q5_3': '5.3 Ti viene riconosciuto il merito per i risultati ottenuti?',
        'q5_4': '5.4 Quali strumenti o iniziative riterresti utili per favorire la tua crescita professionale?',

        # SEZIONE 6
        'q6_1': '6.1 Come valuti il tuo equilibrio tra vita lavorativa e vita privata?',
        'q6_2': '6.2 Il carico di lavoro è sostenibile?',
        'q6_3': '6.3 La tua salute psicofisica viene presa in considerazione in azienda?',
        'q6_4': '6.4 Ritieni che l\'azienda favorisca il benessere individuale attraverso iniziative concrete?',

        # SEZIONE 7
        'q7_1': '7.1 Ti riconosci nei valori dichiarati dall\'azienda?',
        'q7_2': '7.2 L\'azienda agisce in modo coerente con ciò che comunica?',
        'q7_3': '7.3 Quanto ti senti orgoglioso/a di far parte di questa organizzazione?',

        # SEZIONE 8
        'q8_1': '8.1 Quali aspetti dell\'ambiente lavorativo apprezzi di più?',
        'q8_2': '8.2 Cosa miglioreresti, se potessi, nel clima o nella cultura aziendale?',
        'q8_3': '8.3 Hai proposte concrete per migliorare il benessere o la motivazione delle persone?',
    }


def _aggregate_responses(responses):
    """
    Aggrega le risposte per generare statistiche
    """
    if not responses:
        return {}

    aggregated = {}

    for response in responses:
        for question_key, answer in response.responses.items():
            if question_key not in aggregated:
                aggregated[question_key] = []
            aggregated[question_key].append(answer)

    # Calcola statistiche per ogni domanda
    stats = {}
    for question_key, answers in aggregated.items():
        # Conta le occorrenze di ogni risposta
        answer_counts = {}
        numeric_answers = []

        for answer in answers:
            if answer is None or answer == '':
                continue

            # Se la risposta è numerica (scala 1-5), salva per calcolare media
            try:
                numeric_val = float(answer)
                numeric_answers.append(numeric_val)
            except (ValueError, TypeError):
                pass

            # Conta le occorrenze
            answer_str = str(answer)
            answer_counts[answer_str] = answer_counts.get(answer_str, 0) + 1

        stats[question_key] = {
            'counts': answer_counts,
            'total': len([a for a in answers if a]),
            'average': sum(numeric_answers) / len(numeric_answers) if numeric_answers else None,
            'all_answers': [a for a in answers if a]  # Per risposte aperte
        }

    return stats
