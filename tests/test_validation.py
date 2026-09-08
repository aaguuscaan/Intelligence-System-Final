import pytest

from app.agents.validation_agent import (
    ValidationOutput,
    validation_node,
)


@pytest.mark.asyncio
async def test_validation_success():
    """
    Verifica que Validation detecte correctamente
    cuando Researcher y Analyst tienen resultados.
    """

    state = {
        "research_results": "Resultado de investigación.",
        "analysis_results": "Resultado del análisis.",
    }

    result = await validation_node(state)

    output = ValidationOutput(
        validation_result=result["validation_result"],
        task_completed=result["task_completed"],
    )

    assert output.validation_result.startswith(
        "VALIDATION OK"
    )

    assert output.task_completed is False


@pytest.mark.asyncio
async def test_validation_without_research():
    """
    Verifica que Validation rechace un estado
    sin resultado de investigación.
    """

    state = {
        "research_results": "",
        "analysis_results": "Resultado del análisis.",
    }

    result = await validation_node(state)

    output = ValidationOutput(
        validation_result=result["validation_result"],
        task_completed=result["task_completed"],
    )

    assert "No existe resultado de investigación" in (
        output.validation_result
    )

    assert output.task_completed is False
