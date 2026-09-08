from langgraph.types import interrupt

from app.state import AgentState


def human_approval_node(
    state: AgentState,
) -> dict:
    """
    Nodo Human-in-the-loop.

    Pausa el grafo hasta recibir una decisión humana.

    True:
        ejecución aprobada.

    False:
        ejecución rechazada.
    """

    print()
    print("=" * 60)
    print("⏸️ HUMAN-IN-THE-LOOP")
    print("=" * 60)
    print("👤 Esperando aprobación humana...")
    print("=" * 60)
    print()

    approval = interrupt(
        {
            "type": "human_approval",
            "message": (
                "La investigación, el análisis y la validación "
                "fueron completados. Se requiere aprobación "
                "humana para finalizar la ejecución."
            ),
        }
    )

    # ============================================================
    # APROBADO
    # ============================================================

    if approval is True or approval == "approve":

        print()
        print("=" * 60)
        print("👤 HUMAN APPROVAL")
        print("=" * 60)
        print("✅ Decisión: APROBADO")
        print("🏁 Ejecución autorizada para finalizar.")
        print("=" * 60)
        print()

        return {
            "human_approved": True,
            "task_completed": True,
        }

    # ============================================================
    # RECHAZADO
    # ============================================================

    print()
    print("=" * 60)
    print("👤 HUMAN APPROVAL")
    print("=" * 60)
    print("❌ Decisión: RECHAZADO")
    print("🛑 Ejecución detenida.")
    print("=" * 60)
    print()

    return {
        "human_approved": False,
        "task_completed": False,
    }