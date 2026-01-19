"""
calendar.cli
============

Comandi Flask CLI per gestire token Google OAuth.

Uso:
    flask calendar refresh-tokens        # Refresh token in scadenza
    flask calendar cleanup-tokens        # Elimina token scaduti
    flask calendar token-status          # Mostra status token
    flask calendar test-scheduler        # Test scheduler
"""

import click
from flask.cli import with_appcontext
from tabulate import tabulate

from .services import GoogleTokenRefreshService
from .tasks import refresh_google_tokens_task, cleanup_expired_tokens_task, monitor_token_health
from .scheduler import get_scheduler_status


@click.group()
def calendar():
    """Comandi per gestione Google Calendar."""
    pass


@calendar.command('refresh-tokens')
@with_appcontext
def refresh_tokens_command():
    """Forza refresh di tutti i token Google OAuth in scadenza."""
    click.echo("🔄 Avvio refresh token...")

    stats = refresh_google_tokens_task()

    click.echo(f"✅ Refresh completato!")
    click.echo(f"   - Refreshed: {stats['refreshed']}")
    click.echo(f"   - Failed:    {stats['failed']}")
    click.echo(f"   - Skipped:   {stats['skipped']}")


@calendar.command('cleanup-tokens')
@with_appcontext
def cleanup_tokens_command():
    """Elimina token Google OAuth scaduti da più di 7 giorni."""
    click.echo("🧹 Avvio cleanup token scaduti...")

    count = cleanup_expired_tokens_task()

    click.echo(f"✅ Cleanup completato!")
    click.echo(f"   - Token eliminati: {count}")


@calendar.command('token-status')
@with_appcontext
@click.option('--verbose', '-v', is_flag=True, help='Mostra dettagli completi')
def token_status_command(verbose):
    """Mostra lo stato di tutti i token Google OAuth."""
    click.echo("📊 Recupero status token...\n")

    # Recupera status
    status_list = GoogleTokenRefreshService.get_token_expiry_status()

    if not status_list:
        click.echo("⚠️  Nessun token trovato")
        return

    # Recupera metriche
    metrics = monitor_token_health()

    # Mostra metriche
    click.echo("📈 METRICHE GLOBALI")
    click.echo("─" * 50)
    click.echo(f"Total Tokens:    {metrics.get('total_tokens', 0)}")
    click.echo(f"Healthy:         {metrics.get('healthy', 0)} (✅)")
    click.echo(f"Expiring Soon:   {metrics.get('expiring_soon', 0)} (⚠️)")
    click.echo(f"Expired:         {metrics.get('expired', 0)} (❌)")
    click.echo()

    # Tabella token
    if verbose:
        click.echo("📋 DETTAGLI TOKEN")
        click.echo("─" * 50)

        table_data = []
        for token in status_list:
            status_icon = "❌" if token['is_expired'] else "⚠️" if token['needs_refresh'] else "✅"

            table_data.append([
                token['user_id'],
                token['user_name'][:20],
                f"{token['expires_in_minutes']} min",
                status_icon
            ])

        headers = ['User ID', 'Nome', 'Scade tra', 'Status']
        click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))
    else:
        # Mostra solo token che richiedono attenzione
        attention_tokens = [t for t in status_list if t['needs_refresh'] or t['is_expired']]

        if attention_tokens:
            click.echo("⚠️  TOKEN CHE RICHIEDONO ATTENZIONE")
            click.echo("─" * 50)

            table_data = []
            for token in attention_tokens:
                status = "EXPIRED" if token['is_expired'] else "EXPIRING SOON"

                table_data.append([
                    token['user_id'],
                    token['user_name'][:20],
                    f"{token['expires_in_minutes']} min",
                    status
                ])

            headers = ['User ID', 'Nome', 'Scade tra', 'Status']
            click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))
            click.echo(f"\nUsa --verbose per vedere tutti i token")
        else:
            click.echo("✅ Tutti i token sono in salute!")


@calendar.command('test-scheduler')
@with_appcontext
def test_scheduler_command():
    """Verifica lo stato dello scheduler APScheduler."""
    click.echo("🔍 Verifico scheduler...\n")

    try:
        status = get_scheduler_status()

        if not status['running']:
            click.echo("❌ Scheduler NON attivo")
            click.echo("   Lo scheduler è disabilitato (probabile debug mode)")
            return

        click.echo(f"✅ Scheduler ATTIVO")
        click.echo(f"   Jobs registrati: {status['num_jobs']}\n")

        if status['jobs']:
            click.echo("📋 JOBS SCHEDULATI")
            click.echo("─" * 80)

            table_data = []
            for job in status['jobs']:
                table_data.append([
                    job['id'][:30],
                    job['name'][:40],
                    job['next_run'] or 'N/A',
                    job['trigger'][:30]
                ])

            headers = ['Job ID', 'Nome', 'Prossima Esecuzione', 'Trigger']
            click.echo(tabulate(table_data, headers=headers, tablefmt='simple'))

    except Exception as e:
        click.echo(f"❌ Errore: {e}")


@calendar.command('force-refresh-user')
@with_appcontext
@click.argument('user_id', type=int)
def force_refresh_user_command(user_id):
    """Forza refresh del token per un utente specifico."""
    from corposostenibile.models import GoogleAuth

    click.echo(f"🔄 Force refresh token per user {user_id}...")

    google_auth = GoogleAuth.query.filter_by(user_id=user_id).first()

    if not google_auth:
        click.echo(f"❌ Nessun token trovato per user {user_id}")
        return

    success = GoogleTokenRefreshService._refresh_token(google_auth)

    if success:
        click.echo(f"✅ Token refreshato con successo!")
        click.echo(f"   Nuova scadenza: {google_auth.expires_at}")
    else:
        click.echo(f"❌ Refresh fallito - controlla i log")


def init_cli(app):
    """Registra i comandi CLI nell'app Flask."""
    app.cli.add_command(calendar)
