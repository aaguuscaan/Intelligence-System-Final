import os

from dotenv import load_dotenv
from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor


load_dotenv()


PHOENIX_ENDPOINT = os.getenv(
    "PHOENIX_ENDPOINT",
    "http://localhost:6006/v1/traces",
)

PHOENIX_PROJECT = os.getenv(
    "PHOENIX_PROJECT",
    "pre-entrega-7",
)


_phoenix_initialized = False
_tracer_provider = None


def setup_observability():
    """
    Inicializa Phoenix y la instrumentación de LangChain.
    """

    global _phoenix_initialized
    global _tracer_provider

    if _phoenix_initialized:
        return True

    print()
    print("=" * 60)
    print("🔭 CONFIGURANDO OBSERVABILIDAD")
    print("=" * 60)

    try:

        _tracer_provider = register(
            project_name=PHOENIX_PROJECT,
            endpoint=PHOENIX_ENDPOINT,
            auto_instrument=False,
            batch=False,
        )

        print(
            "✅ TracerProvider de Phoenix creado."
        )

        LangChainInstrumentor().instrument(
            tracer_provider=_tracer_provider
        )

        print(
            "✅ Instrumentación LangChain activada."
        )

        _phoenix_initialized = True

        print(
            "✅ Arize Phoenix configurado correctamente."
        )

        print(
            f"🌐 Phoenix: http://localhost:6006"
        )

        print(
            f"📊 Proyecto: {PHOENIX_PROJECT}"
        )

        print("=" * 60)
        print()

        return True

    except Exception as error:

        print(
            "❌ Error configurando Phoenix:"
        )

        print(
            repr(error)
        )

        return False


def print_observability_status():

    print()

    if _phoenix_initialized:

        print(
            "🔭 Observabilidad: Phoenix ACTIVO"
        )

        print(
            f"🌐 Endpoint: {PHOENIX_ENDPOINT}"
        )

        print(
            f"📊 Proyecto: {PHOENIX_PROJECT}"
        )

    else:

        print(
            "⚠️ Observabilidad: Phoenix NO inicializado"
        )

        print(
            f"🌐 Endpoint: {PHOENIX_ENDPOINT}"
        )

    print()


def get_observability_status():

    return {
        "phoenix_enabled": _phoenix_initialized,
        "endpoint": PHOENIX_ENDPOINT,
        "project": PHOENIX_PROJECT,
    }