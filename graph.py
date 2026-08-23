from typing import Literal

from langgraph.graph import StateGraph, END

from llm import llm
from state import AgentState

from agents.research_agent import research_node
from agents.analyst_agent import analyst_node
from agents.validation_agent import validation_node


async def supervisor_node(state: AgentState):
    """
    Supervisor del sistema multi-agente.

    Analiza el estado actual y decide dinámicamente
    cuál debe ser el próximo agente en ejecutarse.
    """

    research_results = state.get("research_results")
    analysis_results = state.get("analysis_results")
    validation_result = state.get("validation_result")

    # ============================================================
    # DETERMINAR EL ESTADO ACTUAL
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

    else:

        available_state = (
            "La investigación, el análisis y la validación "
            "están completos."
        )

    # ============================================================
    # PROMPT DEL SUPERVISOR
    # ============================================================

    prompt = f"""
ROLE: SUPERVISOR

Sos el Supervisor de un sistema multi-agente
de análisis e investigación.

Tu función es analizar el estado actual del proceso
y decidir cuál agente debe intervenir a continuación.

Los agentes disponibles son:

- researcher: realiza la investigación y obtiene información.
- analyst: analiza los resultados obtenidos por researcher.
- validation: valida los resultados de investigación y análisis.
- FINISH: finaliza el proceso cuando todos los resultados
  fueron completados y validados.

Estado actual:

{available_state}

Investigación:
{research_results or "PENDIENTE"}

Análisis:
{analysis_results or "PENDIENTE"}

Validación:
{validation_result or "PENDIENTE"}

Respondé únicamente con una de estas opciones:

researcher
analyst
validation
FINISH
"""

    # ============================================================
    # CONSULTA AL MODELO
    # ============================================================

    response = await llm.ainvoke(prompt)

    decision = response.content.strip().lower()

    # ============================================================
    # VALIDACIÓN DE LA DECISIÓN
    # ============================================================

    valid_decisions = {
        "researcher",
        "analyst",
        "validation",
        "finish",
    }

    # Si el modelo devuelve algo inesperado,
    # utilizamos un fallback determinístico.

    if decision not in valid_decisions:

        if not research_results:
            decision = "researcher"

        elif not analysis_results:
            decision = "analyst"

        elif not validation_result:
            decision = "validation"

        else:
            decision = "finish"

    # Normalizamos FINISH para utilizarlo
    # en las Conditional Edges.

    if decision == "finish":
        decision = "FINISH"

    reason = (
        f"El Supervisor determinó que el próximo paso "
        f"es {decision}."
    )

    return {
        "next_agent": decision,
        "supervisor_reason": reason,
        "task_completed": decision == "FINISH",
    }


# ================================================================
# ROUTER DEL SUPERVISOR
# ================================================================

def route_supervisor(
    state: AgentState,
) -> Literal[
    "researcher",
    "analyst",
    "validation",
    "FINISH",
]:
    """
    Define la ruta del grafo según la decisión
    tomada por el Supervisor.
    """

    return state["next_agent"]


# ================================================================
# CONSTRUCCIÓN DEL GRAFO
# ================================================================

workflow = StateGraph(AgentState)


# ================================================================
# NODOS
# ================================================================

workflow.add_node(
    "supervisor",
    supervisor_node
)

workflow.add_node(
    "researcher",
    research_node
)

workflow.add_node(
    "analyst",
    analyst_node
)

workflow.add_node(
    "validation",
    validation_node
)


# ================================================================
# PUNTO DE ENTRADA
# ================================================================

workflow.set_entry_point("supervisor")


# ================================================================
# RETORNO DE LOS ESPECIALISTAS AL SUPERVISOR
# ================================================================

workflow.add_edge(
    "researcher",
    "supervisor"
)

workflow.add_edge(
    "analyst",
    "supervisor"
)

workflow.add_edge(
    "validation",
    "supervisor"
)


# ================================================================
# RUTEO DINÁMICO DEL SUPERVISOR
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

app = workflow.compile()