from app.llm import llm
from app.state import AgentState


async def analyst_node(
    state: AgentState,
) -> dict:
    """
    Agente especializado en análisis.
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
"""

    response = await llm.ainvoke(
        prompt
    )

    return {
        "analysis_results": response.content,
    }