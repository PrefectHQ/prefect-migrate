import typer

from prefect_migrate.cli import flow_run_notifications


app = typer.Typer()
app.add_typer(flow_run_notifications.app, name="flow-run-notifications")


@app.callback()
def callback():
    pass
