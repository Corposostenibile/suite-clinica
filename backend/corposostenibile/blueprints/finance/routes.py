"""
Route per il modulo Finance
============================
"""

from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from decimal import Decimal, InvalidOperation

from corposostenibile.extensions import db
from corposostenibile.models import (
    Package, Cliente, ClienteSubscription,
    ClienteMonthlySnapshot, ClientePackageChange,
    UnmatchedFinanceClient
)
from sqlalchemy import func, desc
from datetime import datetime, date, timedelta
from . import bp

# Import dashboard routes
from . import dashboard


@bp.route('/')
@login_required
def index():
    """Dashboard principale finance."""
    return redirect(url_for('finance.packages_list'))


@bp.route('/packages')
@login_required
def packages_list():
    """Lista di tutti i pacchetti con filtro per listino."""
    # Filtro listino da query parameter (default: tutti)
    listino_filter = request.args.get('listino', 'tutti')

    # Query base
    query = Package.query

    # Applica filtro se specificato
    if listino_filter in ('vecchio', 'nuovo'):
        query = query.filter(Package.listino_type == listino_filter)

    packages = query.order_by(Package.listino_type.desc(), Package.name).all()

    # Calcola statistiche
    total_packages = len(packages)

    # Conta per tipo listino
    count_vecchio = Package.query.filter(Package.listino_type == 'vecchio').count()
    count_nuovo = Package.query.filter(Package.listino_type == 'nuovo').count()

    # Calcola margine medio
    if packages:
        avg_margin = sum(p.margin_percent for p in packages) / len(packages)
    else:
        avg_margin = 0

    return render_template('finance/packages/list.html',
                         packages=packages,
                         total_packages=total_packages,
                         avg_margin=avg_margin,
                         listino_filter=listino_filter,
                         count_vecchio=count_vecchio,
                         count_nuovo=count_nuovo)


@bp.route('/packages/new', methods=['GET', 'POST'])
@login_required
def package_create():
    """Crea un nuovo pacchetto."""
    if request.method == 'POST':
        try:
            package = Package(
                name=request.form.get('name', '').strip(),
                description=request.form.get('description', '').strip(),
                listino_type=request.form.get('listino_type', 'nuovo'),
                price=Decimal(request.form.get('price', '0')),
                duration_months=int(request.form.get('duration_months', '1')),
                nutritionist_cost_monthly=Decimal(request.form.get('nutritionist_cost_monthly', '0')),
                coach_cost_monthly=Decimal(request.form.get('coach_cost_monthly', '0')),
                psychologist_cost_monthly=Decimal(request.form.get('psychologist_cost_monthly', '0')),
                sales_commission_percent=Decimal(request.form.get('sales_commission_percent', '10')),
                notes=request.form.get('notes', '').strip()
            )

            db.session.add(package)
            db.session.commit()

            flash(f'Pacchetto "{package.name}" creato con successo!', 'success')
            return redirect(url_for('finance.package_detail', package_id=package.id))

        except (ValueError, InvalidOperation) as e:
            flash(f'Errore nei dati numerici: {str(e)}', 'danger')
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante la creazione: {str(e)}', 'danger')

    return render_template('finance/packages/form.html',
                         package=None,
                         action='create')


@bp.route('/packages/<int:package_id>')
@login_required
def package_detail(package_id):
    """Visualizza dettagli di un pacchetto."""
    package = Package.query.get_or_404(package_id)
    return render_template('finance/packages/detail.html', package=package)


@bp.route('/packages/<int:package_id>/edit', methods=['GET', 'POST'])
@login_required
def package_edit(package_id):
    """Modifica un pacchetto esistente."""
    package = Package.query.get_or_404(package_id)

    if request.method == 'POST':
        try:
            package.name = request.form.get('name', '').strip()
            package.description = request.form.get('description', '').strip()
            package.listino_type = request.form.get('listino_type', package.listino_type)
            package.price = Decimal(request.form.get('price', '0'))
            package.duration_months = int(request.form.get('duration_months', '1'))
            package.nutritionist_cost_monthly = Decimal(request.form.get('nutritionist_cost_monthly', '0'))
            package.coach_cost_monthly = Decimal(request.form.get('coach_cost_monthly', '0'))
            package.psychologist_cost_monthly = Decimal(request.form.get('psychologist_cost_monthly', '0'))
            package.sales_commission_percent = Decimal(request.form.get('sales_commission_percent', '10'))
            package.notes = request.form.get('notes', '').strip()

            db.session.commit()

            flash(f'Pacchetto "{package.name}" aggiornato con successo!', 'success')
            return redirect(url_for('finance.package_detail', package_id=package.id))

        except (ValueError, InvalidOperation) as e:
            flash(f'Errore nei dati numerici: {str(e)}', 'danger')
            db.session.rollback()
        except Exception as e:
            db.session.rollback()
            flash(f'Errore durante l\'aggiornamento: {str(e)}', 'danger')

    return render_template('finance/packages/form.html',
                         package=package,
                         action='edit')


@bp.route('/packages/<int:package_id>/delete', methods=['POST'])
@login_required
def package_delete(package_id):
    """Elimina un pacchetto."""
    package = Package.query.get_or_404(package_id)
    package_name = package.name
    
    try:
        db.session.delete(package)
        db.session.commit()
        flash(f'Pacchetto "{package_name}" eliminato con successo!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Errore durante l\'eliminazione: {str(e)}', 'danger')
    
    return redirect(url_for('finance.packages_list'))


@bp.route('/api/packages/<int:package_id>/calculate', methods=['POST'])
@login_required
def api_package_calculate(package_id):
    """API per ricalcolo dinamico margini (AJAX)."""
    try:
        data = request.get_json()
        
        price = Decimal(str(data.get('price', 0)))
        duration_months = int(data.get('duration_months', 1))
        nutritionist_cost = Decimal(str(data.get('nutritionist_cost_monthly', 0)))
        coach_cost = Decimal(str(data.get('coach_cost_monthly', 0)))
        psychologist_cost = Decimal(str(data.get('psychologist_cost_monthly', 0)))
        sales_commission = Decimal(str(data.get('sales_commission_percent', 10)))
        
        # Calcoli
        total_monthly_costs = nutritionist_cost + coach_cost + psychologist_cost
        total_costs = total_monthly_costs * duration_months
        margin = price - total_costs
        margin_percent = (margin / price * 100) if price > 0 else 0
        sales_commission_amount = (price * sales_commission / 100) if price > 0 else 0
        margin_post_sales = margin - sales_commission_amount
        margin_post_sales_percent = (margin_post_sales / price * 100) if price > 0 else 0
        net_post_sales = price - sales_commission_amount
        
        return jsonify({
            'success': True,
            'calculations': {
                'total_costs': float(total_costs),
                'margin': float(margin),
                'margin_percent': float(margin_percent),
                'sales_commission_amount': float(sales_commission_amount),
                'margin_post_sales': float(margin_post_sales),
                'margin_post_sales_percent': float(margin_post_sales_percent),
                'net_post_sales': float(net_post_sales)
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


# ===================== ROUTES CLIENTI FINANCE =====================

@bp.route('/clients')
@login_required
def clients_list():
    """Lista clienti con dati finanziari."""
    # Query clienti con aggregazione dati finanziari
    clients = db.session.query(
        Cliente,
        func.count(ClienteSubscription.id).label('sub_count'),
        func.sum(ClienteSubscription.total_amount).label('total_ltv'),
        func.max(ClienteSubscription.end_date).label('last_end_date')
    ).outerjoin(
        ClienteSubscription, Cliente.cliente_id == ClienteSubscription.cliente_id
    ).group_by(Cliente.cliente_id).all()
    
    # Statistiche generali
    total_clients = len(clients)
    active_subs = ClienteSubscription.query.filter_by(status='active').count()
    total_revenue = db.session.query(func.sum(ClienteSubscription.total_amount)).scalar() or 0
    
    # Clienti non matchati dall'Excel
    unmatched_count = UnmatchedFinanceClient.query.filter_by(matched=False).count()
    
    return render_template('finance/clients/list.html',
                         clients=clients,
                         total_clients=total_clients,
                         active_subs=active_subs,
                         total_revenue=float(total_revenue),
                         unmatched_count=unmatched_count,
                         now=date.today())


@bp.route('/clients/<int:cliente_id>')
@login_required
def client_detail(cliente_id):
    """Dettaglio finanziario cliente."""
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Subscriptions ordinate per data
    subscriptions = ClienteSubscription.query.filter_by(
        cliente_id=cliente_id
    ).order_by(desc(ClienteSubscription.start_date)).all()
    
    # Snapshot mensili
    snapshots = ClienteMonthlySnapshot.query.filter_by(
        cliente_id=cliente_id
    ).order_by(ClienteMonthlySnapshot.month).all()
    
    # Cambi pacchetto
    package_changes = ClientePackageChange.query.filter_by(
        cliente_id=cliente_id
    ).order_by(ClientePackageChange.change_date).all()
    
    # Calcola metriche
    total_ltv = sum(s.total_amount or 0 for s in subscriptions)
    total_months = sum(s.duration_months for s in subscriptions)
    avg_monthly = total_ltv / total_months if total_months > 0 else 0
    
    # LTV 90 giorni
    ltv_90 = 0
    for snapshot in snapshots[:3]:  # Primi 3 mesi
        ltv_90 += snapshot.monthly_revenue or 0
    
    # LTGP totale
    total_costs = sum(s.monthly_cost or 0 for s in snapshots)
    ltgp = total_ltv - total_costs
    
    return render_template('finance/clients/detail.html',
                         cliente=cliente,
                         subscriptions=subscriptions,
                         snapshots=snapshots,
                         package_changes=package_changes,
                         total_ltv=total_ltv,
                         ltv_90=ltv_90,
                         ltgp=ltgp,
                         avg_monthly=avg_monthly,
                         total_months=total_months)


@bp.route('/clients/<int:cliente_id>/subscription/new', methods=['GET', 'POST'])
@login_required
def client_subscription_create(cliente_id):
    """Crea nuovo abbonamento per cliente."""
    cliente = Cliente.query.get_or_404(cliente_id)
    packages = Package.query.order_by(Package.name).all()
    
    if request.method == 'POST':
        try:
            # Crea subscription
            subscription = ClienteSubscription(
                cliente_id=cliente_id,
                package_id=int(request.form.get('package_id')),
                start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date(),
                sale_date=datetime.strptime(request.form.get('sale_date'), '%Y-%m-%d').date() if request.form.get('sale_date') else None,
                initial_payment=Decimal(request.form.get('initial_payment', '0')),
                total_amount=Decimal(request.form.get('total_amount', '0')),
                status='active'
            )
            
            # Calcola importo mensile
            if subscription.duration_months > 0:
                subscription.monthly_amount = subscription.total_amount / subscription.duration_months
            
            db.session.add(subscription)
            db.session.flush()  # Per ottenere l'ID
            
            # Genera snapshot mensili
            generate_monthly_snapshots(subscription)
            
            db.session.commit()
            flash(f'Abbonamento creato con successo!', 'success')
            return redirect(url_for('finance.client_detail', cliente_id=cliente_id))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Errore: {str(e)}', 'danger')
    
    return render_template('finance/clients/subscription_form.html',
                         cliente=cliente,
                         packages=packages,
                         subscription=None)


@bp.route('/clients/unmatched')
@login_required
def unmatched_clients():
    """Lista clienti Excel non matchati."""
    unmatched = UnmatchedFinanceClient.query.filter_by(matched=False).all()
    
    # Cerca possibili match nel DB
    suggestions = {}
    for u in unmatched:
        # Cerca per nome simile
        similar = Cliente.query.filter(
            Cliente.nome_cognome.ilike(f'%{u.excel_name.split()[0]}%')
        ).limit(3).all()
        suggestions[u.id] = similar
    
    return render_template('finance/clients/unmatched.html',
                         unmatched=unmatched,
                         suggestions=suggestions)


@bp.route('/api/clients/list')
@login_required
def api_clients_list():
    """API per lista clienti (per autocomplete)."""
    clients = Cliente.query.order_by(Cliente.nome_cognome).all()
    return jsonify({
        'clients': [
            {
                'id': c.cliente_id,
                'nome_cognome': c.nome_cognome,
                'email': c.mail
            } for c in clients
        ]
    })


@bp.route('/clients/unmatched/<int:unmatched_id>/match', methods=['POST'])
@login_required
def match_client(unmatched_id):
    """Associa cliente Excel a cliente DB."""
    unmatched = UnmatchedFinanceClient.query.get_or_404(unmatched_id)
    cliente_id = request.form.get('cliente_id', type=int)
    
    if not cliente_id:
        flash('Seleziona un cliente', 'warning')
        return redirect(url_for('finance.unmatched_clients'))
    
    cliente = Cliente.query.get_or_404(cliente_id)
    
    # Aggiorna unmatched
    unmatched.matched = True
    unmatched.matched_cliente_id = cliente_id
    unmatched.matched_date = datetime.utcnow()
    unmatched.matched_by_user_id = current_user.id
    
    # Aggiorna dati cliente se mancanti
    if not cliente.origine and unmatched.origine:
        cliente.origine = unmatched.origine
    if not cliente.paese and unmatched.paese:
        cliente.paese = unmatched.paese
    if not cliente.genere and unmatched.genere:
        cliente.genere = unmatched.genere
    if not cliente.mail and unmatched.mail:
        cliente.mail = unmatched.mail
    if not cliente.indirizzo and unmatched.indirizzo:
        cliente.indirizzo = unmatched.indirizzo
    if not cliente.deposito_iniziale and unmatched.total_deposito:
        cliente.deposito_iniziale = unmatched.total_deposito
    
    db.session.commit()
    flash(f'Cliente {unmatched.excel_name} associato a {cliente.nome_cognome}', 'success')
    
    return redirect(url_for('finance.unmatched_clients'))


# ===================== FUNZIONI HELPER =====================

def generate_monthly_snapshots(subscription):
    """Genera snapshot mensili per una subscription."""
    if not subscription.package:
        return
    
    package = subscription.package
    current_date = subscription.start_date
    month_number = 1
    
    while current_date <= subscription.end_date:
        # Crea snapshot
        snapshot = ClienteMonthlySnapshot(
            cliente_id=subscription.cliente_id,
            subscription_id=subscription.id,
            month=date(current_date.year, current_date.month, 1),
            month_number=month_number,
            package_id=package.id,
            monthly_revenue=subscription.monthly_amount
        )
        
        # Commissioni primo mese
        if month_number == 1:
            snapshot.comm_sales = subscription.total_amount * Decimal('0.1')  # 10%
            snapshot.comm_setter = Decimal('10')  # 10€
        
        # Costi dal pacchetto
        snapshot.comm_coach = package.coach_cost_monthly
        snapshot.comm_nutriz = package.nutritionist_cost_monthly
        snapshot.comm_psic = package.psychologist_cost_monthly
        
        # Calcola costi e profitti
        snapshot.monthly_cost = snapshot.calculate_monthly_cost()
        snapshot.monthly_profit = (snapshot.monthly_revenue or 0) - snapshot.monthly_cost
        
        # Calcola LTV/LTGP cumulativi
        prev_snapshot = ClienteMonthlySnapshot.query.filter_by(
            cliente_id=subscription.cliente_id,
            month_number=month_number - 1
        ).first()
        
        if prev_snapshot:
            snapshot.ltv_cumulative = prev_snapshot.ltv_cumulative + snapshot.monthly_revenue
            snapshot.ltgp_cumulative = prev_snapshot.ltgp_cumulative + snapshot.monthly_profit
        else:
            snapshot.ltv_cumulative = snapshot.monthly_revenue
            snapshot.ltgp_cumulative = snapshot.monthly_profit
        
        db.session.add(snapshot)

        # Prossimo mese
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, current_date.day)
        else:
            current_date = date(current_date.year, current_date.month + 1, current_date.day)
        month_number += 1


# --------------------------------------------------------------------------- #
#  Finance Analytics                                                          #
# --------------------------------------------------------------------------- #
@bp.route('/analytics')
@login_required
def analytics():
    """Pagina Analytics Finance - panoramica finanziaria."""
    if not current_user.is_admin:
        flash("Accesso non autorizzato", "danger")
        return redirect(url_for('welcome.index'))

    return render_template("finance/analytics.html")