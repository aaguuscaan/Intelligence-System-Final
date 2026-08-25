import os

from dotenv import load_dotenv

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_openai import ChatOpenAI


load_dotenv()


class MockLLM(BaseChatModel):
    """
    Modelo simulado utilizado cuando no existe OPENAI_API_KEY.

    Permite probar toda la arquitectura sin depender
    de una API externa.

    El MockLLM NO inventa información de investigación.
    Cuando no dispone de información real, lo indica
    explícitamente.
    """

    @property
    def _llm_type(self) -> str:
        return "mock-llm"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(
        self,
        messages,
        stop=None,
        run_manager=None,
        **kwargs,
    ) -> ChatResult:

        conversation = "\n".join(
            str(message.content)
            for message in messages
        ).lower()

        # ============================================================
        # SUPERVISOR
        # ============================================================

        if "role: supervisor" in conversation:

            if "no existe investigación todavía" in conversation:

                response = "researcher"

            elif "todavía no existe un análisis" in conversation:

                response = "analyst"

            elif "todavía no fueron validados" in conversation:

                response = "validation"

            else:

                response = "FINISH"

        # ============================================================
        # RESEARCHER
        # ============================================================

        elif "role: researcher" in conversation:

            response = (
                "No se encontró información suficiente para responder "
                "la consulta con el modelo simulado. "
                "El MockLLM no dispone de acceso a fuentes externas "
                "ni realiza búsquedas web, por lo que no debe inventar "
                "datos o resultados de investigación."
            )

        # ============================================================
        # ANALYST
        # ============================================================

        elif "role: analyst" in conversation:

            response = (
                "No es posible realizar un análisis confiable porque "
                "la investigación no contiene información suficiente. "
                "El modelo simulado no dispone de datos verificables "
                "para analizar."
            )

        # ============================================================
        # VALIDATION
        # ============================================================

        elif "role: validation" in conversation:

            response = (
                "VALIDACIÓN: la investigación no contiene información "
                "suficiente para respaldar una respuesta verificable. "
                "No se consideran válidos resultados que no puedan "
                "ser sustentados por información disponible."
            )

        # ============================================================
        # DEFAULT
        # ============================================================

        else:

            response = (
                "La información fue procesada correctamente."
            )

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(
                        content=response
                    )
                )
            ]
        )


# ================================================================
# SELECCIÓN DEL MODELO
# ================================================================

if os.getenv("OPENAI_API_KEY"):

    llm = ChatOpenAI(
        model=os.getenv(
            "OPENAI_MODEL",
            "gpt-4o-mini",
        ),
        temperature=0,
    )

    print("🤖 Usando OpenAI LLM")

else:

    llm = MockLLM()

    print(
        "⚠️ Usando MockLLM "
        "(modo simulación sin API)"
    )