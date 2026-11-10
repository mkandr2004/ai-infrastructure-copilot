from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.rag.retriever import KnowledgeMatch
from app.schemas.workflow import (
    InvestigationWorkflowRecord,
    WorkflowStatus,
    WorkflowStepName,
    WorkflowStepRecord,
    WorkflowStepStatus,
)
from app.workflows.runner import run_investigation_workflow


def make_workflow(
    *,
    use_knowledge: bool = True,
) -> InvestigationWorkflowRecord:
    now = datetime.now(UTC)

    return InvestigationWorkflowRecord(
        id="workflow-test",
        created_at=now,
        updated_at=now,
        expires_at=now + timedelta(hours=1),
        status=WorkflowStatus.PENDING,
        problem_description="CPU élevé",
        knowledge_requested=use_knowledge,
        steps=[
            WorkflowStepRecord(name=step_name)
            for step_name in WorkflowStepName
        ],
    )


def make_system_data() -> dict:
    return {
        "timestamp": "2026-11-10T12:00:00+00:00",
        "cpu": {"percent": 95.0},
        "memory": {"percent": 40.0},
        "disk": {"percent": 30.0},
        "logs": ["LOG_TEST"],
    }


def identity_save(
    client,
    settings,
    workflow,
):
    return workflow


def test_runner_completes_all_steps_with_knowledge():
    redis_client = MagicMock()
    session = MagicMock()
    settings = SimpleNamespace(
        gemini_model="modele-test",
    )
    qdrant_client = MagicMock()
    history = [
        SimpleNamespace(
            cpu_percent=90.0,
            memory_percent=35.0,
            disk_percent=25.0,
        )
    ]
    matches = [
        KnowledgeMatch(
            point_id="cpu-1",
            score=0.9,
            source="cpu.md",
            title="Diagnostic CPU",
            text="Utiliser top.",
            chunk_index=0,
        )
    ]

    with (
        patch(
            "app.workflows.runner.save_workflow",
            side_effect=identity_save,
        ),
        patch(
            "app.workflows.runner.collect_system_metrics",
            return_value=make_system_data(),
        ),
        patch(
            "app.workflows.runner.list_metric_snapshots",
            return_value=history,
        ),
        patch(
            "app.workflows.runner.list_incidents",
            return_value=[],
        ),
        patch(
            "app.workflows.runner.create_qdrant_client",
            return_value=qdrant_client,
        ),
        patch(
            "app.workflows.runner.search_knowledge",
            return_value=matches,
        ),
        patch(
            "app.workflows.runner.request_diagnostic",
            return_value="Diagnostic final.",
        ) as mock_diagnostic,
    ):
        result = run_investigation_workflow(
            redis_client,
            session,
            settings,
            make_workflow(),
        )

    assert result.status == WorkflowStatus.COMPLETED
    assert result.history_points_analyzed == 1
    assert result.knowledge_sources == ["cpu.md"]
    assert result.diagnosis == "Diagnostic final."
    assert result.diagnostic_model == "modele-test"
    assert len(result.findings) == 3
    assert all(
        step.status == WorkflowStepStatus.COMPLETED
        for step in result.steps
    )
    assert result.metrics is not None
    assert result.metrics.cpu_percent == 95.0
    qdrant_client.close.assert_called_once_with()

    prompt = mock_diagnostic.call_args.args[0]

    assert "<investigation_context>" in prompt
    assert "<knowledge_context>" in prompt
    assert "LOG_TEST" not in prompt


def test_runner_skips_knowledge_when_not_requested():
    redis_client = MagicMock()
    session = MagicMock()
    settings = SimpleNamespace(
        gemini_model="modele-test",
    )

    with (
        patch(
            "app.workflows.runner.save_workflow",
            side_effect=identity_save,
        ),
        patch(
            "app.workflows.runner.collect_system_metrics",
            return_value=make_system_data(),
        ),
        patch(
            "app.workflows.runner.list_metric_snapshots",
            return_value=[],
        ),
        patch(
            "app.workflows.runner.list_incidents",
            return_value=[],
        ),
        patch(
            "app.workflows.runner.create_qdrant_client",
        ) as mock_qdrant,
        patch(
            "app.workflows.runner.request_diagnostic",
            return_value="Diagnostic sans RAG.",
        ),
    ):
        result = run_investigation_workflow(
            redis_client,
            session,
            settings,
            make_workflow(use_knowledge=False),
        )

    knowledge_step = next(
        step
        for step in result.steps
        if step.name == WorkflowStepName.SEARCH_KNOWLEDGE
    )

    assert result.status == WorkflowStatus.COMPLETED
    assert knowledge_step.status == WorkflowStepStatus.SKIPPED
    assert result.knowledge_sources == []
    mock_qdrant.assert_not_called()


def test_runner_persists_failed_workflow():
    redis_client = MagicMock()
    session = MagicMock()
    settings = SimpleNamespace(
        gemini_model="modele-test",
    )
    saved_workflows = []

    def capture_save(
        client,
        current_settings,
        workflow,
    ):
        saved_workflows.append(workflow)
        return workflow

    with (
        patch(
            "app.workflows.runner.save_workflow",
            side_effect=capture_save,
        ),
        patch(
            "app.workflows.runner.collect_system_metrics",
            side_effect=RuntimeError("collecte indisponible"),
        ),
    ):
        with pytest.raises(
            RuntimeError,
            match="collecte indisponible",
        ):
            run_investigation_workflow(
                redis_client,
                session,
                settings,
                make_workflow(),
            )

    failed_workflow = saved_workflows[-1]
    collect_step = next(
        step
        for step in failed_workflow.steps
        if step.name == WorkflowStepName.COLLECT_METRICS
    )

    assert failed_workflow.status == WorkflowStatus.FAILED
    assert collect_step.status == WorkflowStepStatus.FAILED
    assert failed_workflow.error == (
        "Le workflow d'investigation a échoué."
    )
