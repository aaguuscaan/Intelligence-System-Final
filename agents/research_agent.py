from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from llm import llm


KNOWLEDGE_BASE = [
    {
        "topic": "inteligencia artificial",
        "content": "La adopción de herramientas de inteligencia artificial aumentó un 35% en las empresas analizadas."
    },
    {
        "topic": "mercado laboral",
        "content": "El 62% de las empresas incorporaron herramientas de automatización durante el último año."
    },
    {
        "topic": "empleo",
        "content": "La incorporación de inteligencia artificial está modificando principalmente tareas repetitivas y administrativas."
    },
    {
        "topic": "productividad",
        "content": "Las empresas que incorporaron herramientas de inteligencia artificial reportaron mejoras en productividad."
    }
]


@tool
def search_knowledge_base(query: str) -> str:
    """
    Busca información relevante dentro de la base de conocimiento.
    """

    query = query.lower()

    results = []

    for item in KNOWLEDGE_BASE:
        if item["topic"] in query or any(
            word in item["content"].lower()
            for word in query.split()
            if len(word) > 3
        ):
            results.append(item["content"])

    if not results:
        return "No se encontraron resultados relevantes."

    return "\n".join(results)


research_agent = create_react_agent(
    model=llm,
    tools=[search_knowledge_base],
    prompt="""
    Sos un agente especializado en investigación.

    Tu tarea es buscar información relevante utilizando
    la herramienta search_knowledge_base.

    No inventes información.
    Utilizá los resultados encontrados para elaborar
    una investigación clara y concreta.
    """
)


async def research_node(state):
    result = await research_agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    "ROLE: RESEARCHER\n"
                    "Tu tarea es investigar utilizando la herramienta "
                    "search_knowledge_base.\n\n"
                    f"Solicitud: {state['messages'][-1].content}"
                )
            }
        ]
    })

    research_result = result["messages"][-1].content

    return {
        "research_results": research_result
    }