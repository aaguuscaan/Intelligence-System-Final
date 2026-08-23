import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult


load_dotenv()


class MockLLM(BaseChatModel):

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
        **kwargs
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
                "La investigación encontró que la adopción de "
                "herramientas de inteligencia artificial aumentó un 35% "
                "en las empresas analizadas. Además, el 62% incorporó "
                "herramientas de automatización durante el último año."
            )

        # ============================================================
        # ANALYST
        # ============================================================

        elif "role: analyst" in conversation:

            response = (
                "El análisis indica una tendencia positiva en la adopción "
                "de inteligencia artificial. El promedio de los valores "
                "analizados es 48.50. Además, la automatización está "
                "creciendo y su impacto se concentra principalmente "
                "en tareas repetitivas y administrativas."
            )

        # ============================================================
        # RESPUESTA POR DEFECTO
        # ============================================================

        else:

            response = (
                "La información fue procesada correctamente."
            )

        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=response)
                )
            ]
        )


# ================================================================
# SELECCIÓN DEL MODELO
# ================================================================

if os.getenv("OPENAI_API_KEY"):

    llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0
    )

    print("🤖 Usando OpenAI LLM")

else:

    llm = MockLLM()

    print("⚠️ Usando MockLLM (modo simulación sin API)")