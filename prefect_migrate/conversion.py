from datetime import timedelta
from typing import TYPE_CHECKING
from uuid import uuid4
from prefect.events.schemas.automations import AutomationCore, EventTrigger, Posture
from prefect.events.schemas.events import ResourceSpecification
from prefect.events.actions import SendNotification

if TYPE_CHECKING:
    from prefect.client.schemas.objects import (
        FlowRunNotificationPolicy,
    )  # pragma: no cover


import textwrap

DEFAULT_BODY = textwrap.dedent("""
Flow run {{ flow.name }}/{{ flow_run.name }} observed in state `{{ flow_run.state.name }}` at {{ flow_run.state.timestamp }}.
Flow ID: {{ flow_run.flow_id }}
Flow run ID: {{ flow_run.id }}
Flow run URL: {{ flow_run|ui_url }}
State message: {{ flow_run.state.message }}
""")

PLACEHOLDER_MAP = {
    "flow_run_notification_policy_id": "Event ID {{ event.id }}",
    "flow_id": "{{ flow.id }}",
    "flow_name": "{{ flow.name }}",
    "flow_run_url": "{{ flow_run|ui_url }}",
    "flow_run_id": "{{ flow_run.id }}",
    "flow_run_name": "{{ flow_run.name }}",
    "flow_run_parameters": "{{ flow_run.parameters }}",
    "flow_run_state_type": "{{ flow_run.state.type }}",
    "flow_run_state_name": "{{ flow_run.state.name }}",
    "flow_run_state_timestamp": "{{ flow_run.state.timestamp }}",
    "flow_run_state_message": "{{ flow_run.state.message }}",
}


def convert_flow_run_notification_policy_to_automation(
    policy: "FlowRunNotificationPolicy",
) -> AutomationCore:
    return AutomationCore(
        name="Flow Run State Change Notification",
        description="Migrated from a flow run notification policy using prefect-migrate",
        enabled=policy.is_active,
        actions=[
            SendNotification(
                block_document_id=policy.block_document_id,
                subject="Prefect flow run notification",
                body=policy.message_template.format(**PLACEHOLDER_MAP)
                if policy.message_template
                else DEFAULT_BODY,
            )
        ],
        trigger=EventTrigger(
            match=ResourceSpecification({"prefect.resource.id": "prefect.flow-run.*"}),
            expect={
                f"prefect.flow-run.{state_name}" for state_name in policy.state_names
            }
            if policy.state_names
            else {"prefect.flow-run.*"},
            within=timedelta(seconds=0),
            posture=Posture.Reactive,
            for_each={"prefect.resource.id"},
            threshold=1,
            match_related=ResourceSpecification(
                {
                    "prefect.resource.id": [
                        f"prefect.tag.{tag}" for tag in policy.tags
                    ],
                    "prefect.resource.role": "tag",
                }
            )
            if policy.tags
            else ResourceSpecification({}),
        ),
    )
