import pytest

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from app.graph import (
    app,
    setup_checkpointer,
)


@pytest.mark.asyncio
async def test_human_in_the_loop():

    thread_id = "test-hitl-pytest-001"

    config = {
        "configurable": {
            "thread_id": thread_id,
        }
    }

    initial_state = {
        "messages": [
            HumanMessage(
                content=(
                    "Analizá el impacto de la inteligencia "
                    "artificial en el mercado laboral."
                )
            )
        ],
        "research_results": None,
        "analysis_results": None,
        "validation_result": None,
        "next_agent": None,
        "supervisor_reason": None,
        "task_completed": False,
        "human_approved": None,
    }

    await setup_checkpointer()

    interrupted = False

    # ============================================================
    # PRIMERA EJECUCIÓN
    # ============================================================

    async for state in app.astream(
        initial_state,
        config=config,
    ):

        if "__interrupt__" in state:

            interrupted = True

            break

    assert interrupted, (
        "El grafo no llegó al interrupt de HITL."
    )

    # ============================================================
    # SIMULAR APROBACIÓN
    # ============================================================

    async for _ in app.astream(
        Command(
            resume=True
        ),
        config=config,
    ):
        pass

    # ============================================================
    # RECUPERAR ESTADO
    # ============================================================

    final_state = await app.aget_state(
        config
    )

    assert (
        final_state.values.get(
            "human_approved"
        ) is True
    )

    assert (
        final_state.values.get(
            "task_completed"
        ) is True
    )