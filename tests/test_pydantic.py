import pytest
from pydantic import ValidationError

from app.agents.analyst_agent import AnalystOutput

def test_analyst_output_valid():
    """
    Verifica que AnalystOutput acepte una salida válida.
    """

    output = AnalystOutput(
        analysis_results="Análisis generado correctamente."
    )

    assert output.analysis_results == (
        "Análisis generado correctamente."
    )


def test_analyst_output_rejects_empty_result():
    """
    Verifica que Pydantic rechace un resultado vacío.
    """

    with pytest.raises(ValidationError):
        AnalystOutput(
            analysis_results=""
        )
