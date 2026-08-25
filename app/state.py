from typing import Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """
    Estado compartido del sistema multi-agente.

    Hereda de MessagesState para conservar correctamente
    los mensajes de la ejecución de LangGraph.

    El estado también contiene los resultados producidos
    por cada especialista y el estado de aprobación humana.
    """

    research_results: Optional[str]

    analysis_results: Optional[str]

    validation_result: Optional[str]

    next_agent: Optional[str]

    supervisor_reason: Optional[str]

    human_approved: Optional[bool]

    task_completed: bool