import click
from flask.cli import with_appcontext
from .services import process_focus_data_for_account

@click.command(name='process-costs')
@click.argument('account_id', type=int)
@with_appcontext
def process_costs_command(account_id):
    """
    Aciona o processo de ingestão de dados de custo para uma conta AWS específica.
    Uso: flask process-costs <ID_DA_CONTA_AWS>
    """
    click.echo(f"Starting manual cost processing for AWS Account ID: {account_id}...")
    process_focus_data_for_account(account_id)
    click.echo("Processing finished.")

def init_app(app):
    """Registra os comandos no app Flask."""
    app.cli.add_command(process_costs_command)