import os

from typing import Literal

from dotenv import load_dotenv

from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from langgraph.graph import (
    StateGraph,
    END,
)

from app.state import AgentState

from app.agents.research_agent import research_node
from app.agents.analyst_agent import analyst_node
from app.agents.validation_agent import validation_node
from app.agents.hitl import human_approval_node


# ================================================================
# VARIABLES DE ENTORNO
# ================================================================

load_dotenv()


# ================================================================
# CONFIGURACIÓN
# ================================================================

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6376",
)


# ================================================================
# CHECKPOINTER
# ================================================================

checkpointer = AsyncRedisSaver(
    redis_url=REDIS_URL,
)


async def setup_checkpointer():
    """
    Inicializa RedisSaver.
    """

    await checkpointer.asetup()


# ================================================================
# SUPERVISOR
# ================================================================

async def supervisor_node(
    state: AgentState,
) -> dict:
    """
    Supervisor central del sistema multi-agente.

    Flujo:

        supervisor
            ↓
        researcher
            ↓
        supervisor
            ↓
        analyst
            ↓
        supervisor
            ↓
        validation
            ↓
        human_approval
            ↓
        END
    """

    research_results = state.get(
        "research_results"
    )

    analysis_results = state.get(
        "analysis_results"
    )

    validation_result = state.get(
        "validation_result"
    )

    # ============================================================
    # ROUTING
    # ============================================================

    if not research_results:

        decision = "researcher"

        reason = (
            "Todavía no existe una investigación. "
            "Debe ejecutarse Researcher."
        )

    elif not analysis_results:

        decision = "analyst"

        reason = (
            "La investigación está disponible, "
            "pero todavía no existe un análisis. "
            "Debe ejecutarse Analyst."
        )

    elif not validation_result:

        decision = "validation"

        reason = (
            "La investigación y el análisis están disponibles, "
            "pero todavía no fueron validados. "
            "Debe ejecutarse Validation."
        )

    else:

        decision = "human_approval"

        reason = (
            "La investigación, el análisis y la validación "
            "están completos. Debe solicitarse aprobación humana."
        )

    # ============================================================
    # LOG
    # ============================================================

    print()
    print("🧠 SUPERVISOR")
    print(
        f"➡️ Próximo agente: {decision}"
    )
    print(
        f"📝 Motivo: {reason}"
    )
    print()

    return {
        "next_agent": decision,
        "supervisor_reason": reason,
        "task_completed": False,
    }


# ================================================================
# ROUTER
# ================================================================

def route_supervisor(
    state: AgentState,
) -> Literal[
    "researcher",
    "analyst",
    "validation",
    "human_approval",
]:

    return state[
        "next_agent"
    ]


# ================================================================
# WORKFLOW
# ================================================================

workflow = StateGraph(
    AgentState
)


# ================================================================
# NODOS
# ================================================================

workflow.add_node(
    "supervisor",
    supervisor_node,
)

workflow.add_node(
    "researcher",
    research_node,
)

workflow.add_node(
    "analyst",
    analyst_node,
)

workflow.add_node(
    "validation",
    validation_node,
)

workflow.add_node(
    "human_approval",
    human_approval_node,
)


# ================================================================
# ENTRY POINT
# ================================================================

workflow.set_entry_point(
    "supervisor"
)


# ================================================================
# EDGES
# ================================================================

workflow.add_edge(
    "researcher",
    "supervisor",
)

workflow.add_edge(
    "analyst",
    "supervisor",
)

workflow.add_edge(
    "validation",
    "human_approval",
)

workflow.add_edge(
    "human_approval",
    END,
)


# ================================================================
# ROUTING DEL SUPERVISOR
# ================================================================

workflow.add_conditional_edges(
    "supervisor",

    route_supervisor,

    {
        "researcher": "researcher",
        "analyst": "analyst",
        "validation": "validation",
        "human_approval": "human_approval",
    },
)


# ================================================================
# COMPILAR
# ================================================================

app = workflow.compile(
    checkpointer=checkpointer,
)