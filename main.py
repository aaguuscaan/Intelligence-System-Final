import asyncio

from langchain_core.messages import HumanMessage

from graph import app


async def run():
    initial_state = {
        "messages": [
            HumanMessage(
                content=(
                    "Analizá el impacto de la inteligencia artificial "
                    "en el mercado laboral y elaborá una conclusión."
                )
            )
        ],
        "research_results": None,
        "analysis_results": None,
        "next_agent": None,
        "task_completed": False,
    }

    print("\n" + "=" * 60)
    print("🚀 ORQUESTADOR MULTI-AGENTE")
    print("=" * 60)

    async for state in app.astream(initial_state):

        for node_name, node_state in state.items():

            if node_name == "supervisor":
                print("\n👑 SUPERVISOR")
                print(f"   └── Próximo agente: {node_state.get('next_agent')}")

            elif node_name == "researcher":
                print("\n🔎 RESEARCHER")
                print("   └── Investigación completada")

                if node_state.get("research_results"):
                    print(
                        f"   └── Resultado: "
                        f"{node_state['research_results']}"
                    )

            elif node_name == "analyst":
                print("\n📊 ANALYST")
                print("   └── Análisis completado")

                if node_state.get("analysis_results"):
                    print(
                        f"   └── Resultado: "
                        f"{node_state['analysis_results']}"
                    )

            elif node_name == "validation":
                print("\n✅ VALIDATION")

                if node_state.get("task_completed"):
                    print("   ├── Investigación: OK")
                    print("   ├── Análisis: OK")
                    print("   └── Estado: VÁLIDO")
                else:
                    print("   └── Estado: REQUIERE REVISIÓN")

    print("\n" + "=" * 60)
    print("✅ PROCESO FINALIZADO")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(run())