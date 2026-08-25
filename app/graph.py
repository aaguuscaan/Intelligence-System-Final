import os

from typing import Literal

from dotenv import load_dotenv

from langgraph.checkpoint.redis.aio import AsyncRedisSaver

from langgraph.graph import (
    StateGraph,
    END,
)

from app.llm import llm
from app.state import AgentState

from app.agents.research_agent import research_node
from app.agents.analyst_agent import analyst_node
from app.agents.validation_agent import validation_node
from app.agents.hitl import human_approval_node

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
    Inicializa los índices necesarios de Redis.

    Debe ejecutarse antes de procesar jobs.
    """

    await checkpointer.asetup()


# ================================================================
# SUPERVISOR
# ================================================================

async def supervisor_node(
    state: AgentState,
):
    """
    Supervisor central del sistema.

    Determina qué especialista debe intervenir
    según el estado actual del workflow.
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

    human_approved = state.get(
        "human_approved"
    )

    # ============================================================
    # ESTADO ACTUAL
    # ============================================================

    if not research_results:

        available_state = (
            "No existe investigación todavía."
        )

    elif not analysis_results:

        available_state = (
            "La investigación está disponible, "
            "pero todavía no existe un análisis."
        )

    elif not validation_result:

        available_state = (
            "La investigación y el análisis están disponibles, "
            "pero todavía no fueron validados."
        )

    elif human_approved is None:

        available_state = (
            "La investigación, el análisis y la validación "
            "están completos, pero todavía falta la aprobación humana."
        )

    elif human_approved is True:

        available_state = (
            "La ejecución fue aprobada por una persona."
        )

    else:

        available_state = (
            "La ejecución fue rechazada por una persona."
        )

    # ============================================================
    # PROMPT
    # ============================================================

    prompt = f"""
ROLE: SUPERVISOR

Sos el Supervisor de un sistema multi-agente
de análisis e investigación.

Tu función es decidir cuál agente debe intervenir
a continuación.

Agentes disponibles:

- researcher
- analyst
- validation
- FINISH

IMPORTANTE:

La aprobación humana NO es responsabilidad del Supervisor.
La aprobación humana ocurre después de Validation.

Estado actual:

{available_state}

Investigación:

{research_results or "PENDIENTE"}

Análisis:

{analysis_results or "PENDIENTE"}

Validación:

{validation_result or "PENDIENTE"}

Aprobación humana:

{human_approved}

Respondé únicamente con una de estas opciones:

researcher
analyst
validation
FINISH
"""

    response = await llm.ainvoke(
        prompt
    )

    decision = (
        response.content
        .strip()
        .lower()
    )

    valid_decisions = {
        "researcher",
        "analyst",
        "validation",
        "finish",
    }

    # ============================================================
    # FALLBACK DETERMINÍSTICO
    # ============================================================

    if decision not in valid_decisions:

        if not research_results:

            decision = "researcher"

        elif not analysis_results:

            decision = "analyst"

        elif not validation_result:

            decision = "validation"

        else:

            decision = "finish"

    # ============================================================
    # NORMALIZACIÓN
    # ============================================================

    if decision == "finish":

        decision = "FINISH"

    return {
        "next_agent": decision,

        "supervisor_reason": (
            "El Supervisor determinó que el próximo "
            f"paso es {decision}."
        ),

        "task_completed": (
            decision == "FINISH"
        ),
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
    "FINISH",
]:

    return state[
        "next_agent"
    ]

# ================================================================
# CONSTRUCCIÓN DEL GRAFO
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

        "FINISH": END,
    },
)


# ================================================================
# COMPILACIÓN
# ================================================================

app = workflow.compile(
    checkpointer=checkpointer,
)