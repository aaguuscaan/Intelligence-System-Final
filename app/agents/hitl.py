from langgraph.types import interrupt

from app.state import AgentState


def human_approval_node(
    state: AgentState,
) -> dict:
    """
    Nodo Human-in-the-loop.

    Pausa la ejecución del grafo mediante interrupt()
    hasta recibir una decisión humana externa.
    """

    approval = interrupt(
        {
            "type": "human_approval",
            "message": (
                "La investigación, el análisis y la validación "
                "fueron completados. Se requiere aprobación "
                "humana para finalizar la ejecución."
            ),
        }
    )

    if approval is True or approval == "approve":
        return {
            "human_approved": True,
            "task_completed": True,
        }

    return {
        "human_approved": False,
        "task_completed": False,
    }