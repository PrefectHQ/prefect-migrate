import typer


app = typer.Typer()


@app.callback()
def callback():
    pass


@app.command()
def migrate() -> None:
    pass


@app.command()
def clear() -> None:
    pass
