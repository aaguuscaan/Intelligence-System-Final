import pytest

from langchain_core.messages import HumanMessage

from app.graph import (
    app,
    setup_checkpointer,
    checkpointer,
)


@pytest.mark.asyncio
async def test_persistencia_redis():

    thread_id = "test-persistence-pytest-001"

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

    try:

        # ========================================================
        # EJECUTAR HASTA HITL
        # ========================================================

        interrupted = False

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

        # ========================================================
        # RECUPERAR ESTADO
        # ========================================================

        recovered_state = await app.aget_state(
            config
        )

        assert recovered_state.values

        assert recovered_state.values.get(
            "messages"
        )

        assert (
            recovered_state.values["messages"][0].content
            == "Analizá el impacto de la inteligencia "
            "artificial en el mercado laboral."
        )

    finally:

        # ========================================================
        # CERRAR REDIS CHECKPOINTER
        # ========================================================

        redis_client = getattr(
            checkpointer,
            "redis_client",
            None,
        )

        if redis_client is not None:

            await redis_client.aclose()