from datetime import timedelta
import textwrap
from uuid import uuid4
from prefect.events.schemas.automations import AutomationCore, Posture, EventTrigger
from prefect.events.actions import SendNotification
from prefect.events.schemas.events import ResourceSpecification
from prefect.client.schemas.objects import FlowRunNotificationPolicy

from prefect_migrate.conversion import (
    convert_flow_run_notification_policy_to_automation,
    DEFAULT_BODY,
)


def test_basic_conversion():
    """Test basic conversion with minimal policy settings"""
    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=True,
        state_names=["Completed", "Failed"],
        tags=[],
        message_template=None,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    assert isinstance(automation, AutomationCore)
    assert automation.name == "Flow Run State Change Notification"
    assert automation.enabled is True
    assert len(automation.actions) == 1
    assert isinstance(automation.actions[0], SendNotification)
    assert automation.actions[0].block_document_id == policy.block_document_id
    assert automation.actions[0].body == DEFAULT_BODY
    assert isinstance(automation.trigger, EventTrigger)
    assert automation.trigger.expect == {
        "prefect.flow-run.Completed",
        "prefect.flow-run.Failed",
    }


def test_conversion_with_default_message():
    """Test conversion with the default message template"""
    LEGACY_DEFAULT_MESSAGE_TEMPLATE = textwrap.dedent("""
    Flow run {flow_name}/{flow_run_name} entered state `{flow_run_state_name}` at {flow_run_state_timestamp}.

    Flow ID: {flow_id}
    Flow run ID: {flow_run_id}
    Flow run URL: {flow_run_url}
    State message: {flow_run_state_message}
    """)

    EXPECTED_MESSAGE = textwrap.dedent("""
    Flow run {{ flow.name }}/{{ flow_run.name }} entered state `{{ flow_run.state.name }}` at {{ flow_run.state.timestamp }}.

    Flow ID: {{ flow.id }}
    Flow run ID: {{ flow_run.id }}
    Flow run URL: {{ flow_run|ui_url }}
    State message: {{ flow_run.state.message }}
    """)

    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=True,
        state_names=["Completed"],
        tags=[],
        message_template=LEGACY_DEFAULT_MESSAGE_TEMPLATE,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    assert isinstance(automation.actions[0], SendNotification)
    assert automation.actions[0].body == EXPECTED_MESSAGE


def test_conversion_with_custom_message():
    """Test conversion with a custom message template"""
    custom_message = "Flow {flow_name} is in state {flow_run_state_name}"
    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=False,
        state_names=["Running"],
        tags=[],
        message_template=custom_message,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    expected_message = "Flow {{ flow.name }} is in state {{ flow_run.state.name }}"
    assert isinstance(automation.actions[0], SendNotification)
    assert automation.actions[0].body == expected_message
    assert automation.enabled is False


def test_conversion_with_tags():
    """Test conversion with tags specified"""
    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=True,
        state_names=["Completed"],
        tags=["production", "critical"],
        message_template=None,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    assert isinstance(automation.trigger, EventTrigger)
    assert automation.trigger.match_related == ResourceSpecification(
        {
            "prefect.resource.id": ["prefect.tag.production", "prefect.tag.critical"],
            "prefect.resource.role": "tag",
        }
    )


def test_conversion_without_state_names():
    """Test conversion when no state names are specified"""
    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=True,
        state_names=[],
        tags=[],
        message_template=None,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    assert isinstance(automation.trigger, EventTrigger)
    assert automation.trigger.expect == {"prefect.flow-run.*"}


def test_trigger_configuration():
    """Test the trigger configuration details"""
    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=True,
        state_names=["Completed"],
        tags=[],
        message_template=None,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    assert isinstance(automation.trigger, EventTrigger)
    assert automation.trigger.match == ResourceSpecification(
        {"prefect.resource.id": "prefect.flow-run.*"}
    )
    assert automation.trigger.within == timedelta(seconds=0)
    assert automation.trigger.posture == Posture.Reactive
    assert automation.trigger.for_each == {"prefect.resource.id"}
    assert automation.trigger.threshold == 1


def test_inactive_policy():
    """Test conversion with an inactive policy"""
    policy = FlowRunNotificationPolicy(
        block_document_id=uuid4(),
        is_active=False,
        state_names=["Completed"],
        tags=[],
        message_template=None,
    )

    automation = convert_flow_run_notification_policy_to_automation(policy)

    assert isinstance(automation, AutomationCore)
    assert automation.enabled is False
