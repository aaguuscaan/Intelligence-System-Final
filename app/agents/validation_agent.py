from app.state import AgentState


async def validation_node(
    state: AgentState,
) -> dict:
    """
    Nodo determinístico de validación.

    Verifica que Researcher y Analyst hayan
    producido resultados antes de permitir
    llegar al Human-in-the-loop.
    """

    research = state.get(
        "research_results"
    )

    analysis = state.get(
        "analysis_results"
    )

    # ============================================================
    # VALIDACIÓN
    # ============================================================

    if not research:

        return {
            "validation_result": (
                "VALIDATION FAILED: "
                "No existe resultado de investigación."
            ),

            "task_completed": False,
        }

    if not analysis:

        return {
            "validation_result": (
                "VALIDATION FAILED: "
                "No existe resultado de análisis."
            ),

            "task_completed": False,
        }

    # ============================================================
    # TODO CORRECTO
    # ============================================================

    return {
        "validation_result": (
            "VALIDATION OK: "
            "investigación y análisis disponibles."
        ),

        "task_completed": False,
    }