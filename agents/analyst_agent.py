from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from llm import llm


@tool
def calculate_average(values: str) -> str:
    """
    Calcula el promedio de una lista de números separados por comas.
    """

    try:
        numbers = [
            float(value.strip())
            for value in values.split(",")
        ]

        if not numbers:
            return "No se recibieron valores para analizar."

        average = sum(numbers) / len(numbers)

        return f"El promedio de los valores analizados es {average:.2f}."

    except ValueError:
        return "Error: los valores deben ser números separados por comas."


analyst_agent = create_react_agent(
    model=llm,
    tools=[calculate_average],
    prompt="""
    Sos un agente especializado en análisis de datos.

    Tu tarea es analizar la información proporcionada por
    el agente de investigación.

    Los resultados de investigación pueden contener porcentajes
    numéricos. Cuando recibas porcentajes que puedan compararse,
    utilizá la herramienta calculate_average para obtener
    un promedio.

    Por ejemplo, si recibís 35% y 62%, utilizá la herramienta
    con los valores 35,62.

    No inventes datos.
    Basá tus conclusiones únicamente en la información recibida.
    Presentá el resultado de forma clara y concreta.
    """
)


async def analyst_node(state):
    research_results = state.get("research_results", "")

    # Modo Mock: ejecutamos la herramienta directamente
    if type(llm).__name__ == "MockLLM":

        average_result = calculate_average.invoke("35,62")

        analysis_result = (
            "El análisis indica una tendencia positiva en la adopción "
            "de inteligencia artificial. "
            f"{average_result} "
            "Además, la automatización está creciendo y su impacto "
            "se concentra principalmente en tareas repetitivas y "
            "administrativas."
        )

        return {
            "analysis_results": analysis_result
        }

    # Modo OpenAI: el agente ReAct decide cuándo utilizar la tool
    result = await analyst_agent.ainvoke({
        "messages": [
            {
                "role": "user",
                "content": (
                    "ROLE: ANALYST\n"
                    "Analizá los resultados de investigación.\n\n"
                    f"Datos de investigación: {research_results}"
                )
            }
        ]
    })

    analysis_result = result["messages"][-1].content

    return {
        "analysis_results": analysis_result
    }