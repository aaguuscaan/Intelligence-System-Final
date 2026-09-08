from typing import Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):
    """
    Estado compartido del sistema multi-agente.
    """

    research_results: Optional[str] = None

    analysis_results: Optional[str] = None

    validation_result: Optional[str] = None

    next_agent: Optional[str] = None

    supervisor_reason: Optional[str] = None

    human_approved: Optional[bool] = None

    task_completed: bool = False