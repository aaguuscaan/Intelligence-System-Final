import logging

from pydantic import BaseModel, Field

from app.llm import llm
from app.state import AgentState
from app.rag.rag_system import create_rag_system


logger = logging.getLogger(__name__)


# ================================================================
# MODELO PYDANTIC
# ================================================================


class ResearchOutput(BaseModel):
    """
    Salida estructurada del agente Researcher.
    """

    research_results: str = Field(
        ...,
        min_length=1,
        description=(
            "Resultado de la investigación "
            "generada a partir del contexto RAG."
        ),
    )


# ================================================================
# RESEARCHER NODE
# ================================================================


async def research_node(
    state: AgentState,
) -> dict:
    """
    Agente especializado en investigación.

    Flujo:

    1. Obtiene la consulta del usuario.
    2. Recupera información mediante RAG.
    3. Utiliza el contexto recuperado.
    4. Genera la investigación.
    5. Valida la salida mediante Pydantic.
    """

    messages = state.get(
        "messages",
        [],
    )

    query = ""

    if messages:
        query = str(
            messages[0].content
        ).strip()

    # ============================================================
    # VALIDAR CONSULTA
    # ============================================================

    if not query:

        logger.warning(
            "Researcher recibió una consulta vacía."
        )

        output = ResearchOutput(
            research_results=(
                "No se recibió una consulta válida "
                "para realizar la investigación."
            )
        )

        return {
            "research_results": output.research_results,
        }

    logger.info(
        "🔎 Researcher: consulta recibida: %s",
        query[:100],
    )

    # ============================================================
    # INICIALIZAR RAG
    # ============================================================

    rag = await create_rag_system()

    # ============================================================
    # RECUPERAR DOCUMENTOS
    # ============================================================

    retrieved_documents = await rag.retrieve(
        query=query,
        k=5,
    )

    logger.info(
        "📚 Researcher: documentos recuperados: %s",
        len(retrieved_documents),
    )

    # ============================================================
    # CONSTRUIR CONTEXTO
    # ============================================================

    if retrieved_documents:

        context_parts = []

        for index, document in enumerate(
            retrieved_documents,
            start=1,
        ):

            metadata = document.metadata or {}

            source = metadata.get(
                "source",
                "fuente desconocida",
            )

            context_parts.append(
                f"""
FUENTE {index}: {source}

{document.page_content}
"""
            )

        context = "\n".join(
            context_parts
        )

    else:

        context = (
            "No se recuperaron documentos relevantes "
            "desde la base de conocimiento."
        )

    # ============================================================
    # PROMPT
    # ============================================================

    prompt = f"""
ROLE: RESEARCHER

Sos el agente especializado en investigación
de un sistema multi-agente con arquitectura RAG.

Tu tarea es investigar la consulta del usuario
utilizando EXCLUSIVAMENTE el contexto recuperado
desde la base de conocimiento.

CONSULTA DEL USUARIO:

{query}

CONTEXTO RECUPERADO MEDIANTE RAG:

{context}

INSTRUCCIONES:

- Analizá el contexto recuperado.
- Generá una investigación clara y concreta.
- No inventes datos, estadísticas ni fuentes.
- No agregues información externa que no esté
  respaldada por el contexto.
- Si el contexto no contiene información suficiente,
  indicá explícitamente esa limitación.
- Cuando sea relevante, mencioná qué documento
  respalda la información.
- Priorizá precisión y trazabilidad.
"""

    # ============================================================
    # LLAMADA ASÍNCRONA AL LLM
    # ============================================================

    logger.info(
        "🤖 Researcher: generando investigación "
        "a partir del contexto RAG."
    )

    response = await llm.ainvoke(
        prompt
    )

    content = response.content

    # ============================================================
    # NORMALIZAR RESPUESTA
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

    output = ResearchOutput(
        research_results=str(
            content
        ).strip()
    )

    logger.info(
        "✅ Researcher: investigación generada "
        "y validada mediante Pydantic."
    )

    # ============================================================
    # DEVOLVER RESULTADO
    # ============================================================

    return {
        "research_results": output.research_results,
    }
