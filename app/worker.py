import asyncio
import json
import os
import re

from dotenv import load_dotenv

from langchain_core.messages import HumanMessage

from redis import asyncio as aioredis

from app.graph import (
    app,
    setup_checkpointer,
)

from app.observability import (
    setup_observability,
    print_observability_status,
)


# ================================================================
# VARIABLES DE ENTORNO
# ================================================================

load_dotenv()


# ================================================================
# CONFIGURACIÓN
# ================================================================

REDIS_URL = os.getenv(
    "REDIS_URL",
    "redis://localhost:6376",
)

QUEUE_NAME = os.getenv(
    "QUEUE_NAME",
    "ai_tasks_queue",
)

STATUS_PREFIX = os.getenv(
    "STATUS_PREFIX",
    "task_status:",
)

MAX_RETRIES = 3

RETRY_DELAY = 10


# ================================================================
# CLIENTE REDIS
# ================================================================

redis_client = aioredis.from_url(
    REDIS_URL,
    decode_responses=True,
)


# ================================================================
# ACTUALIZAR ESTADO
# ================================================================

async def update_status(
    job_id: str,
    **updates,
):
    """
    Actualiza el estado del trabajo en Redis.
    """

    key = f"{STATUS_PREFIX}{job_id}"

    raw = await redis_client.get(
        key
    )

    if not raw:

        print(
            f"⚠️ No se encontró el estado "
            f"del job: {job_id}"
        )

        return

    data = json.loads(
        raw
    )

    data.update(
        updates
    )

    await redis_client.set(
        key,
        json.dumps(
            data,
            ensure_ascii=False,
            default=str,
        ),
    )


# ================================================================
# DETECTAR 429
# ================================================================

def is_rate_limit_error(
    error: Exception,
) -> bool:

    error_text = str(
        error
    ).lower()

    return (
        "429" in error_text
        or "resource_exhausted" in error_text
        or "rate limit" in error_text
        or "quota exceeded" in error_text
    )


# ================================================================
# RETRY DELAY
# ================================================================

def get_retry_delay(
    error: Exception,
    attempt: int,
) -> int:

    error_text = str(
        error
    )

    match = re.search(
        r"retryDelay.*?(\d+)s",
        error_text,
        re.IGNORECASE,
    )

    if match:

        return max(
            int(match.group(1)),
            5,
        )

    return RETRY_DELAY * attempt


# ================================================================
# EJECUTAR LANGGRAPH
# ================================================================

async def execute_graph_with_retry(
    initial_state,
    config,
):

    for attempt in range(
        1,
        MAX_RETRIES + 1,
    ):

        try:

            print(
                f"🧠 Ejecutando LangGraph "
                f"(intento {attempt}/{MAX_RETRIES})..."
            )

            result = await app.ainvoke(
                initial_state,
                config=config,
            )

            return result

        except Exception as error:

            if not is_rate_limit_error(
                error
            ):

                raise

            print()
            print("=" * 60)
            print("⚠️ LÍMITE DE GEMINI DETECTADO")
            print("=" * 60)
            print(
                f"🔄 Intento: "
                f"{attempt}/{MAX_RETRIES}"
            )
            print(
                f"❌ Error: {repr(error)}"
            )

            if attempt >= MAX_RETRIES:

                print(
                    "❌ Se alcanzó el máximo "
                    "de reintentos."
                )

                raise

            delay = get_retry_delay(
                error,
                attempt,
            )

            print(
                f"⏳ Esperando {delay} segundos "
                "antes de reintentar..."
            )

            print("=" * 60)
            print()

            await asyncio.sleep(
                delay
            )


# ================================================================
# PROCESAR JOB
# ================================================================

async def process_job(
    job_id: str,
):

    key = f"{STATUS_PREFIX}{job_id}"

    raw = await redis_client.get(
        key
    )

    if not raw:

        print(
            f"❌ Job inexistente: {job_id}"
        )

        return

    task = json.loads(
        raw
    )

    query = task.get(
        "query",
        "",
    )

    print()
    print("=" * 60)
    print(
        f"🚀 PROCESANDO JOB: {job_id}"
    )
    print(
        f"🔎 CONSULTA: {query}"
    )
    print("=" * 60)

    await update_status(
        job_id,
        status="running",
        error=None,
    )

    try:

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        initial_state = {
            "messages": [
                HumanMessage(
                    content=query
                )
            ],
            "research_results": None,
            "analysis_results": None,
            "validation_result": None,
            "next_agent": None,
            "supervisor_reason": None,
            "human_approved": None,
            "task_completed": False,
        }

        result = await execute_graph_with_retry(
            initial_state,
            config,
        )

        # ========================================================
        # DETECTAR INTERRUPCIÓN
        # ========================================================

        interrupts = None

        if isinstance(
            result,
            dict,
        ):

            interrupts = result.get(
                "__interrupt__"
            )

        if interrupts:

            print()
            print("=" * 60)
            print("⏸️ LANGGRAPH PAUSADO POR HITL")
            print("=" * 60)
            print(
                "👤 Esperando aprobación humana..."
            )
            print(
                f"🔐 Thread ID: {job_id}"
            )
            print("=" * 60)
            print()

            await update_status(
                job_id,

                status="waiting_approval",

                result=(
                    "La investigación, el análisis "
                    "y la validación fueron completados. "
                    "La ejecución está esperando "
                    "aprobación humana."
                ),

                error=None,
            )

            print(
                "💾 Estado HITL guardado en Redis."
            )

            return

        # ========================================================
        # APROBADO
        # ========================================================

        if (
            isinstance(result, dict)
            and result.get("human_approved") is True
        ):

            await update_status(
                job_id,

                status="completed",

                result=str(result),

                error=None,
            )

            print()
            print("=" * 60)
            print(
                f"✅ JOB APROBADO Y COMPLETADO: "
                f"{job_id}"
            )
            print("=" * 60)
            print()

            return

        # ========================================================
        # RECHAZADO
        # ========================================================

        if (
            isinstance(result, dict)
            and result.get("human_approved") is False
        ):

            await update_status(
                job_id,

                status="rejected",

                result=(
                    "La ejecución fue "
                    "rechazada por aprobación humana."
                ),

                error=None,
            )

            print()
            print("=" * 60)
            print(
                f"❌ JOB RECHAZADO: {job_id}"
            )
            print("=" * 60)
            print()

            return

        # ========================================================
        # CASO NORMAL
        # ========================================================

        await update_status(
            job_id,

            status="completed",

            result=str(result),

            error=None,
        )

        print()
        print("=" * 60)
        print(
            f"✅ JOB COMPLETADO: {job_id}"
        )
        print("=" * 60)
        print()

    except Exception as error:

        print()
        print("=" * 60)
        print(
            f"❌ ERROR EN JOB: {job_id}"
        )
        print("=" * 60)

        print(
            repr(error)
        )

        if is_rate_limit_error(
            error
        ):

            error_message = (
                "Se agotó la cuota de Gemini "
                "para este modelo. "
                "El sistema realizó los reintentos "
                "configurados sin éxito."
            )

        else:

            error_message = str(
                error
            )

        await update_status(
            job_id,

            status="failed",

            error=error_message,
        )

        print(
            "💾 Estado FAILED guardado en Redis."
        )

        print()


# ================================================================
# WORKER
# ================================================================

async def worker():

    print()
    print("=" * 60)
    print("👷 WORKER INICIADO")
    print("=" * 60)

    print(
        f"📡 Redis: {REDIS_URL}"
    )

    print(
        f"📥 Cola: {QUEUE_NAME}"
    )

    print()

    # ============================================================
    # PHOENIX
    # ============================================================

    try:

        setup_observability()

    except Exception as error:

        print(
            "❌ Error inicializando Phoenix:"
        )

        print(
            repr(error)
        )

        print(
            "⚠️ El worker continuará funcionando."
        )

    print_observability_status()

    # ============================================================
    # CHECKPOINTER
    # ============================================================

    print(
        "🔧 Configurando RedisSaver..."
    )

    try:

        await setup_checkpointer()

        print(
            "✅ RedisSaver configurado."
        )

    except Exception as error:

        print(
            "❌ No se pudo configurar RedisSaver."
        )

        print(
            repr(error)
        )

        raise

    # ============================================================
    # LOOP
    # ============================================================

    while True:

        try:

            item = await redis_client.blpop(
                QUEUE_NAME,
                timeout=5,
            )

            if not item:

                await asyncio.sleep(
                    0.2
                )

                continue

            _, job_id = item

            print()
            print(
                f"📥 Nuevo Job recibido: {job_id}"
            )

            await process_job(
                job_id
            )

        except asyncio.CancelledError:

            print()
            print(
                "🛑 Worker detenido."
            )

            break

        except Exception as error:

            print()
            print(
                "❌ Error del worker:"
            )

            print(
                repr(error)
            )

            await asyncio.sleep(
                1
            )


# ================================================================
# ENTRY POINT
# ================================================================

if __name__ == "__main__":

    try:

        asyncio.run(
            worker()
        )

    except KeyboardInterrupt:

        print()
        print(
            "🛑 Worker detenido manualmente."
        )