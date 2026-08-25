from app.llm import llm
from app.state import AgentState


async def research_node(
    state: AgentState,
) -> dict:
    """
    Agente especializado en investigación.
    """

    messages = state.get(
        "messages",
        [],
    )

    query = ""

    if messages:

        query = str(
            messages[0].content
        )

    prompt = f"""
ROLE: RESEARCHER

Sos el agente especializado en investigación.

Tu objetivo es investigar la consulta del usuario
y producir resultados relevantes.

Consulta:

{query}

Generá una investigación clara y concreta.

No inventes fuentes, datos ni estadísticas.
Si no disponés de información verificable,
indicá explícitamente la limitación.
"""

    response = await llm.ainvoke(
        prompt
    )

    return {
        "research_results": response.content,
    }