from uuid import uuid4
import pytest
from typer.testing import CliRunner
from unittest.mock import patch, MagicMock, AsyncMock
import prefect.client.base
import prefect.client.schemas.filters
from prefect_migrate.cli.flow_run_notifications import app
from typing import Generator
from prefect.client.schemas.objects import FlowRunNotificationPolicy

from prefect_migrate.conversion import (
    convert_flow_run_notification_policy_to_automation,
)

runner = CliRunner()


@pytest.fixture
def mock_client() -> Generator[AsyncMock, None, None]:
    with patch("prefect.get_client") as mock_get_client:
        mock_client_instance = AsyncMock()
        mock_get_client.return_value.__aenter__.return_value = mock_client_instance
        yield mock_client_instance


def test_migrate_command_cloud_server(mock_client: AsyncMock) -> None:
    """Test migrate command when connected to Prefect Cloud."""
    # Setup mock to return cloud server type
    mock_client.server_type = prefect.client.base.ServerType.CLOUD

    # Run the command
    result = runner.invoke(app, ["migrate"])

    # Check output
    assert result.exit_code == 0
    assert "Currently connected to Prefect Cloud. No migration needed." in result.stdout


def test_migrate_command_no_policies(mock_client: AsyncMock) -> None:
    """Test migrate command when no policies exist."""
    # Setup mock to return server type and empty policies
    mock_client.server_type = prefect.client.base.ServerType.SERVER
    mock_client.read_flow_run_notification_policies.return_value = []

    # Run the command with auto-confirm
    with patch("rich.prompt.Confirm.ask", return_value=True):
        result = runner.invoke(app, ["migrate"])

    # Check output
    assert result.exit_code == 0
    assert (
        "No flow run notification policies found. No migration needed." in result.stdout
    )


def test_migrate_command_with_policies(mock_client: AsyncMock) -> None:
    """Test migrate command when policies exist and user confirms migration."""
    # Setup mock to return server type and policies
    mock_client.server_type = prefect.client.base.ServerType.SERVER
    mock_policy = FlowRunNotificationPolicy(
        id=uuid4(), state_names=[], tags=[], block_document_id=uuid4()
    )
    mock_client.read_flow_run_notification_policies.return_value = [mock_policy]

    # Run the command with auto-confirm
    with patch("rich.prompt.Confirm.ask", return_value=True):
        result = runner.invoke(app, ["migrate"])

    # Check output
    assert result.exit_code == 0
    assert "Found 1 flow run notification policies." in result.stdout
    assert f"Migrating policy {mock_policy.id}..." in result.stdout
    assert "Migration complete." in result.stdout

    # Verify client calls
    mock_client.read_flow_run_notification_policies.assert_called_once()
    mock_client.create_automation.assert_called_once_with(
        convert_flow_run_notification_policy_to_automation(mock_policy)
    )


def test_migrate_command_user_cancels(mock_client: AsyncMock) -> None:
    """Test migrate command when user cancels the migration."""
    # Setup mock to return server type and policies
    mock_client.server_type = prefect.client.base.ServerType.SERVER
    mock_policy = MagicMock()
    mock_policy.id = "test-policy-id"
    mock_client.read_flow_run_notification_policies.return_value = [mock_policy]

    # Run the command with user cancellation
    with patch("rich.prompt.Confirm.ask", return_value=False):
        result = runner.invoke(app, ["migrate"])

    # Check output
    assert result.exit_code == 0
    assert "Found 1 flow run notification policies." in result.stdout
    assert "Migration cancelled." in result.stdout

    # Verify client calls
    mock_client.read_flow_run_notification_policies.assert_called_once()
    mock_client.create_automation.assert_not_called()


def test_clear_command_no_policies(mock_client: AsyncMock) -> None:
    """Test clear command when no policies exist."""
    # Setup mock to return empty policies
    mock_client.read_flow_run_notification_policies.return_value = []

    # Run the command
    result = runner.invoke(app, ["clear"])

    # Check output
    assert result.exit_code == 0
    assert (
        "No flow run notification policies found. No deletion needed." in result.stdout
    )


def test_clear_command_with_policies_user_confirms(mock_client: AsyncMock) -> None:
    """Test clear command when policies exist and user confirms deletion."""
    # Setup mock to return policies
    mock_policy = MagicMock()
    mock_policy.id = "test-policy-id"
    mock_client.read_flow_run_notification_policies.return_value = [mock_policy]

    # Run the command with auto-confirm
    with patch(
        "rich.prompt.Confirm.ask",
        side_effect=lambda *args, **kwargs: print(args[0]) or True,
    ):
        result = runner.invoke(app, ["clear"])

    # Check output
    assert result.exit_code == 0
    assert (
        "Are you sure you want to delete [bold]all[/bold] flow run notification policies?"
        in result.stdout
    )
    assert "Deletion complete." in result.stdout

    # Verify client calls
    mock_client.read_flow_run_notification_policies.assert_called_once()
    mock_client.delete_flow_run_notification_policy.assert_called_once_with(
        "test-policy-id"
    )


def test_clear_command_user_cancels(mock_client: AsyncMock) -> None:
    """Test clear command when user cancels the deletion."""
    # Setup mock to return policies
    mock_policy = MagicMock()
    mock_policy.id = "test-policy-id"
    mock_client.read_flow_run_notification_policies.return_value = [mock_policy]

    # Run the command with user cancellation
    with patch("rich.prompt.Confirm.ask", return_value=False):
        result = runner.invoke(app, ["clear"])

    # Check output
    assert result.exit_code == 0
    assert "Deletion cancelled." in result.stdout

    # Verify client calls
    mock_client.read_flow_run_notification_policies.assert_called_once()
    mock_client.delete_flow_run_notification_policy.assert_not_called()
