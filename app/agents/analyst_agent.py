from pydantic import BaseModel, Field

from app.llm import llm
from app.state import AgentState


# ================================================================
# MODELO PYDANTIC
# ================================================================


class AnalystOutput(BaseModel):
    """
    Salida estructurada del agente Analyst.
    """

    analysis_results: str = Field(
        ...,
        min_length=1,
        description="Resultado del análisis realizado sobre la investigación.",
    )


# ================================================================
# ANALYST NODE
# ================================================================


async def analyst_node(
    state: AgentState,
) -> dict:
    """
    Agente especializado en análisis.

    Analiza exclusivamente los resultados
    obtenidos por Researcher.

    La salida es validada mediante Pydantic.
    """

    research = state.get(
        "research_results",
        "",
    )

    prompt = f"""
ROLE: ANALYST

Sos el agente especializado en análisis.

Analizá exclusivamente los resultados obtenidos
por el investigador.

Investigación:

{research}

Generá un análisis claro y concreto.

No inventes datos que no estén presentes
en la investigación.

No agregues información externa que no aparezca
en los resultados proporcionados.
"""

    response = await llm.ainvoke(
        prompt
    )

    content = response.content

    # ============================================================
    # NORMALIZAR RESPUESTA DEL LLM
    # ============================================================

    if isinstance(content, list):
        content = " ".join(
            item.get("text", "")
            if isinstance(item, dict)
            else str(item)
            for item in content
        )

    # ============================================================
    # VALIDACIÓN PYDANTIC
    # ============================================================

    output = AnalystOutput(
        analysis_results=str(content).strip()
    )

    # ============================================================
    # DEVOLVER RESULTADO VALIDADO
    # ============================================================

    return {
        "analysis_results": output.analysis_results,
    }

