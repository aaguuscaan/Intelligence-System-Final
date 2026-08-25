from phoenix.otel import register
from openinference.instrumentation.langchain import LangChainInstrumentor


def setup_phoenix():
    tracer_provider = register(
        project_name="orquestador-multi-agente",
        endpoint="http://localhost:6006/v1/traces",
    )

    LangChainInstrumentor().instrument(
        tracer_provider=tracer_provider
    )

    print("🔭 Phoenix: instrumentación activada")