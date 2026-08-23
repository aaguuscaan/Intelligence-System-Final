from typing import Optional

from langgraph.graph import MessagesState


class AgentState(MessagesState):

    research_results: Optional[str]

    analysis_results: Optional[str]

    validation_result: Optional[str]

    next_agent: Optional[str]

    supervisor_reason: Optional[str]

    task_completed: bool