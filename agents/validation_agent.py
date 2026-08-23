async def validation_node(state):
    """
    Valida que los especialistas hayan producido
    los resultados necesarios antes de finalizar.
    """

    research_results = state.get("research_results")
    analysis_results = state.get("analysis_results")

    errors = []

    # ============================================================
    # VALIDACIÓN DE INVESTIGACIÓN
    # ============================================================

    if not research_results:
        errors.append(
            "Falta el resultado de investigación."
        )

    # ============================================================
    # VALIDACIÓN DE ANÁLISIS
    # ============================================================

    if not analysis_results:
        errors.append(
            "Falta el resultado del análisis."
        )

    # ============================================================
    # RESULTADO DE VALIDACIÓN
    # ============================================================

    if errors:

        validation_message = (
            "VALIDATION ERROR: "
            + " ".join(errors)
        )

        return {
            "validation_result": validation_message,
            "task_completed": False,
            "next_agent": "analyst",
        }

    validation_message = (
        "VALIDATION OK: Los resultados de investigación "
        "y análisis están completos."
    )

    return {
        "validation_result": validation_message,
        "task_completed": True,
        "next_agent": "FINISH",
    }