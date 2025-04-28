import prefect.client.orchestration
import typer
import prefect
import prefect.settings
import prefect.client.base
import rich.console
import rich.prompt
import asyncio
import prefect.client.schemas.filters
from prefect_migrate.conversion import (
    convert_flow_run_notification_policy_to_automation,
)

app = typer.Typer()
console = rich.console.Console()


@app.callback()
def callback():
    pass


async def _migrate():
    async with prefect.get_client() as client:
        if client.server_type == prefect.client.base.ServerType.CLOUD:
            console.print("Currently connected to Prefect Cloud. No migration needed.")
            return

        console.print(f"Connecting to Prefect server at [bold]{client.api_url}[/bold]")

        policies = await client.read_flow_run_notification_policies(
            flow_run_notification_policy_filter=prefect.client.schemas.filters.FlowRunNotificationPolicyFilter(
                is_active=None
            )
        )

        if len(policies) == 0:
            console.print(
                "No flow run notification policies found. No migration needed."
            )
            return

        console.print(
            f"Found [bold]{len(policies)}[/bold] flow run notification policies."
        )

        if rich.prompt.Confirm.ask(
            "Do you want to migrate these policies to automations?",
        ):
            for policy in policies:
                console.print(f"Migrating policy [bold]{policy.id}[/bold]...")
                automation = convert_flow_run_notification_policy_to_automation(policy)
                await client.create_automation(automation)

            console.print(
                "Migration complete. Once you've verified the created automations, you can delete the old policies with `prefect-migration flow-run-notification-policies clear`"
            )
        else:
            console.print("Migration cancelled.")


@app.command()
def migrate() -> None:
    """Migrates all flow run notification policies to automations."""
    asyncio.run(_migrate())


async def _clear():
    async with prefect.get_client() as client:
        policies = await client.read_flow_run_notification_policies(
            flow_run_notification_policy_filter=prefect.client.schemas.filters.FlowRunNotificationPolicyFilter(
                is_active=None
            )
        )

        if len(policies) == 0:
            console.print(
                "No flow run notification policies found. No deletion needed."
            )
            return

        if rich.prompt.Confirm.ask(
            "Are you sure you want to delete [bold]all[/bold] flow run notification policies?",
            console=console,
        ):
            for policy in policies:
                await client.delete_flow_run_notification_policy(policy.id)

            console.print("Deletion complete.")
        else:
            console.print("Deletion cancelled.")


@app.command()
def clear() -> None:
    """Deletes all flow run notification policies. Please ensure you have migrated all policies to automations before running this command."""
    asyncio.run(_clear())
