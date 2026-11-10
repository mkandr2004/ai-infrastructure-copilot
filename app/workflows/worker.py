"""Worker asynchrone des workflows d'investigation."""

import time

from app.core.config import get_settings
from app.db.database import SessionLocal
from app.memory.redis_client import create_redis_client
from app.schemas.workflow import WorkflowStatus
from app.workflows.queue import dequeue_workflow
from app.workflows.runner import run_investigation_workflow
from app.workflows.storage import get_workflow


def process_workflow(
    workflow_id: str,
) -> bool:
    """Charge et exécute un workflow mis en file."""

    settings = get_settings()
    redis_client = create_redis_client(settings)

    try:
        workflow = get_workflow(
            redis_client,
            settings,
            workflow_id,
        )

        if workflow is None:
            print(
                "Workflow absent ou expiré : "
                f"{workflow_id}"
            )
            return False

        if workflow.status not in {
            WorkflowStatus.PENDING,
            WorkflowStatus.QUEUED,
        }:
            print(
                "Workflow déjà traité : "
                f"{workflow_id} ({workflow.status})"
            )
            return False

        with SessionLocal() as session:
            run_investigation_workflow(
                redis_client,
                session,
                settings,
                workflow,
            )

        return True
    finally:
        redis_client.close()


def run_worker() -> None:
    """Consomme continuellement la file Redis."""

    settings = get_settings()

    if settings.workflow_worker_poll_seconds < 1:
        raise ValueError(
            "L'intervalle du worker doit être positif."
        )

    print(
        "Worker workflows démarré : file "
        f"{settings.workflow_queue_name}."
    )

    try:
        while True:
            redis_client = create_redis_client(settings)

            try:
                workflow_id = dequeue_workflow(
                    redis_client,
                    settings,
                )
            except Exception as error:
                print(
                    "Erreur de lecture de la file : "
                    f"{type(error).__name__}"
                )
                workflow_id = None
            finally:
                redis_client.close()

            if workflow_id is None:
                time.sleep(
                    settings.workflow_worker_poll_seconds
                )
                continue

            try:
                process_workflow(workflow_id)
            except Exception as error:
                print(
                    "Échec du workflow asynchrone "
                    f"{workflow_id} : {type(error).__name__}"
                )

    except KeyboardInterrupt:
        print("Worker workflows arrêté proprement.")


def main() -> None:
    """Point d'entrée du worker."""

    run_worker()


if __name__ == "__main__":
    main()
