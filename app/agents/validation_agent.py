from pydantic import BaseModel, Field

from app.state import AgentState


# ================================================================
# MODELO PYDANTIC
# ================================================================


class ValidationOutput(BaseModel):
    """
    Salida estructurada del agente Validation.
    """

    validation_result: str = Field(
        ...,
        min_length=1,
        description="Resultado de la validación del flujo.",
    )

    task_completed: bool = Field(
        ...,
        description="Indica si la validación permitió continuar.",
    )


# ================================================================
# VALIDATION NODE
# ================================================================


async def validation_node(
    state: AgentState,
) -> dict:
    """
    Nodo determinístico de validación.

    Verifica que Researcher y Analyst hayan
    producido resultados antes de llegar al HITL.

    La salida es validada mediante Pydantic.
    """

    research = state.get(
        "research_results"
    )

    analysis = state.get(
        "analysis_results"
    )

    # ============================================================
    # VALIDAR RESEARCHER
    # ============================================================

    if not research:

        output = ValidationOutput(
            validation_result=(
                "VALIDATION FAILED: "
                "No existe resultado de investigación."
            ),
            task_completed=False,
        )

        return {
            "validation_result": output.validation_result,
            "task_completed": output.task_completed,
        }

    # ============================================================
    # VALIDAR ANALYST
    # ============================================================

    if not analysis:

        output = ValidationOutput(
            validation_result=(
                "VALIDATION FAILED: "
                "No existe resultado de análisis."
            ),
            task_completed=False,
        )

        return {
            "validation_result": output.validation_result,
            "task_completed": output.task_completed,
        }

    # ============================================================
    # VALIDACIÓN EXITOSA
    # ============================================================

    output = ValidationOutput(
        validation_result=(
            "VALIDATION OK: "
            "investigación y análisis disponibles."
        ),
        task_completed=False,
    )

    return {
        "validation_result": output.validation_result,
        "task_completed": output.task_completed,
    }
