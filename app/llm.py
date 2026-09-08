import os
import logging

from dotenv import load_dotenv

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI


load_dotenv()

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)

GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.6-flash",
)


# ============================================================
# MOCK LLM
# ============================================================

class MockLLM(BaseChatModel):
    """
    Modelo simulado utilizado como fallback.

    Permite ejecutar y probar el sistema aunque
    un proveedor externo de LLM no esté disponible.
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

        # ----------------------------------------------------
        # SUPERVISOR
        # ----------------------------------------------------

        if "role: supervisor" in conversation:

            if (
                "no existe investigación todavía"
                in conversation
                or "todavía no existe investigación"
                in conversation
            ):
                response = "researcher"

            elif (
                "todavía no existe un análisis"
                in conversation
            ):
                response = "analyst"

            elif (
                "todavía no fueron validados"
                in conversation
            ):
                response = "validation"

            else:
                response = "FINISH"

        # ----------------------------------------------------
        # RESEARCHER
        # ----------------------------------------------------

        elif "role: researcher" in conversation:

            # El MockLLM no realiza investigación externa.
            # El contexto RAG sigue siendo recuperado por
            # Pinecone antes de llegar a este punto.

            response = (
                "La investigación fue procesada utilizando "
                "el contexto recuperado por el sistema RAG. "
                "El modelo simulado no realiza búsquedas "
                "externas y no debe inventar información."
            )

        # ----------------------------------------------------
        # ANALYST
        # ----------------------------------------------------

        elif "role: analyst" in conversation:

            response = (
                "Se realizó el análisis sobre la información "
                "proporcionada por el agente Researcher. "
                "El modelo simulado no agrega información "
                "externa ni inventa datos."
            )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        elif "role: validation" in conversation:

            response = (
                "VALIDACIÓN: la investigación y el análisis "
                "fueron procesados correctamente. "
                "No se agregan datos externos."
            )

        # ----------------------------------------------------
        # GENERAL
        # ----------------------------------------------------

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


# ============================================================
# FUNCIÓN PARA CREAR GEMINI
# ============================================================

def create_gemini_llm():
    """
    Crea el cliente de Gemini.

    Si no existe una API key, devuelve None.
    """

    if not GEMINI_API_KEY:
        logger.warning(
            "⚠️ GEMINI_API_KEY no está configurada."
        )
        return None

    try:

        model = ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            temperature=0,
            google_api_key=GEMINI_API_KEY,
        )

        logger.info(
            "💎 Usando Gemini LLM"
        )

        logger.info(
            "🧠 Modelo: %s",
            GEMINI_MODEL,
        )

        print("💎 Usando Gemini LLM")
        print(f"🧠 Modelo: {GEMINI_MODEL}")

        return model

    except Exception as error:

        logger.warning(
            "❌ No se pudo inicializar Gemini: %r",
            error,
        )

        return None


# ============================================================
# FUNCIÓN PARA CREAR OPENAI
# ============================================================

def create_openai_llm():
    """
    Crea el cliente de OpenAI únicamente si existe
    una API key válida.
    """

    if not OPENAI_API_KEY:
        return None

    # Evita intentar utilizar valores de ejemplo.
    invalid_keys = {
        "tu_api_key",
        "your_api_key",
        "your-openai-api-key",
        "changeme",
        "...",
    }

    if OPENAI_API_KEY.lower() in invalid_keys:
        logger.warning(
            "⚠️ OPENAI_API_KEY contiene un valor de ejemplo."
        )
        return None

    try:

        model = ChatOpenAI(
            model=OPENAI_MODEL,
            temperature=0,
            api_key=OPENAI_API_KEY,
        )

        logger.info(
            "🤖 Usando OpenAI LLM"
        )

        logger.info(
            "🧠 Modelo: %s",
            OPENAI_MODEL,
        )

        print("🤖 Usando OpenAI LLM")
        print(f"🧠 Modelo: {OPENAI_MODEL}")

        return model

    except Exception as error:

        logger.warning(
            "❌ No se pudo inicializar OpenAI: %r",
            error,
        )

        return None


# ============================================================
# FALLBACK LLM
# ============================================================

class FallbackLLM:
    """
    Wrapper que intenta utilizar proveedores reales
    y utiliza MockLLM si alguno falla.

    Orden:

        OpenAI
           ↓
        Gemini
           ↓
        MockLLM
    """

    def __init__(
        self,
        primary=None,
        secondary=None,
        fallback=None,
    ):

        self.primary = primary
        self.secondary = secondary
        self.fallback = fallback or MockLLM()

    async def ainvoke(
        self,
        input_data,
        **kwargs,
    ):

        # ----------------------------------------------------
        # PRIMER PROVEEDOR
        # ----------------------------------------------------

        if self.primary is not None:

            try:

                return await self.primary.ainvoke(
                    input_data,
                    **kwargs,
                )

            except Exception as error:

                logger.warning(
                    "⚠️ El proveedor principal falló: %r",
                    error,
                )

                print(
                    "⚠️ El proveedor principal falló."
                )

        # ----------------------------------------------------
        # SEGUNDO PROVEEDOR
        # ----------------------------------------------------

        if self.secondary is not None:

            try:

                return await self.secondary.ainvoke(
                    input_data,
                    **kwargs,
                )

            except Exception as error:

                logger.warning(
                    "⚠️ Gemini no disponible: %r",
                    error,
                )

                print(
                    "⚠️ Gemini no está disponible."
                )

        # ----------------------------------------------------
        # MOCK
        # ----------------------------------------------------

        logger.warning(
            "🧪 Utilizando MockLLM como fallback."
        )

        print(
            "🧪 Utilizando MockLLM como fallback."
        )

        return await self.fallback.ainvoke(
            input_data,
            **kwargs,
        )


# ============================================================
# INICIALIZACIÓN DEL LLM
# ============================================================

openai_llm = create_openai_llm()
gemini_llm = create_gemini_llm()

llm = FallbackLLM(
    primary=openai_llm,
    secondary=gemini_llm,
    fallback=MockLLM(),
)
