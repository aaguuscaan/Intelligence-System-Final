import asyncio
import json
import os

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


# ================================================================
# CLIENTE REDIS
# ================================================================

redis_client = aioredis.from_url(
    REDIS_URL,
    decode_responses=True,
)


# ================================================================
# ACTUALIZAR ESTADO DEL JOB
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
            f"⚠️ No se encontró el estado del job: {job_id}"
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
# PROCESAR JOB
# ================================================================

async def process_job(
    job_id: str,
):
    """
    Procesa un trabajo mediante:

        Redis Queue
             ↓
           Worker
             ↓
         LangGraph
             ↓
         Supervisor
             ↓
        Researcher
             ↓
          Analyst
             ↓
        Validation
             ↓
           HITL
             ↓
         Redis/API
    """

    key = f"{STATUS_PREFIX}{job_id}"

    # ============================================================
    # OBTENER JOB
    # ============================================================

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

    # ============================================================
    # RUNNING
    # ============================================================

    await update_status(
        job_id,

        status="running",

        error=None,
    )

    try:

        # ========================================================
        # CONFIG LANGGRAPH
        # ========================================================

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        # ========================================================
        # ESTADO INICIAL
        # ========================================================

        initial_state = {
            "messages": [
                HumanMessage(
                    content=query
                )
            ],

            "task_completed": False,
        }

        # ========================================================
        # EJECUCIÓN
        # ========================================================

        result = await app.ainvoke(
            initial_state,
            config=config,
        )

        # ========================================================
        # NODOS EJECUTADOS
        # ========================================================

        if isinstance(result, dict):

            executed_nodes = []

            if result.get(
                "research_results"
            ):

                executed_nodes.append(
                    "researcher"
                )

            if result.get(
                "analysis_results"
            ):

                executed_nodes.append(
                    "analyst"
                )

            if result.get(
                "validation_result"
            ):

                executed_nodes.append(
                    "validation"
                )

            if result.get(
                "human_approved"
            ) is not None:

                executed_nodes.append(
                    "human_approval"
                )

            if executed_nodes:

                print(
                    "📊 Nodos completados: "
                    f"{executed_nodes}"
                )

        # ========================================================
        # DETECTAR INTERRUPCIÓN
        # ========================================================

        interrupts = None

        if isinstance(result, dict):

            interrupts = result.get(
                "__interrupt__"
            )

        if interrupts:

            print()
            print("=" * 60)
            print(
                "⏸️ LANGGRAPH PAUSADO POR HITL"
            )
            print("=" * 60)

            print(
                "👤 Esperando aprobación humana..."
            )

            print(
                f"🔐 Thread ID: {job_id}"
            )

            # ====================================================
            # GUARDAR ESTADO
            # ====================================================

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

            print()

            return

        # ========================================================
        # COMPLETADO
        # ========================================================

        if (
            isinstance(result, dict)
            and result.get(
                "human_approved"
            ) is True
        ):

            await update_status(
                job_id,

                status="completed",

                result=str(
                    result
                ),

                error=None,
            )

            print()
            print("=" * 60)
            print(
                f"✅ JOB APROBADO Y COMPLETADO: {job_id}"
            )
            print("=" * 60)
            print()

            return

        # ========================================================
        # RECHAZADO
        # ========================================================

        if (
            isinstance(result, dict)
            and result.get(
                "human_approved"
            ) is False
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
        # CASO INESPERADO
        # ========================================================

        await update_status(
            job_id,

            status="completed",

            result=str(
                result
            ),

            error=None,
        )

        print()
        print("=" * 60)
        print(
            f"✅ JOB COMPLETADO: {job_id}"
        )
        print("=" * 60)
        print()

    # ============================================================
    # ERROR
    # ============================================================

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

        await update_status(
            job_id,

            status="failed",

            error=str(
                error
            ),
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
    print(
        "👷 WORKER INICIADO"
    )
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
    # REDIS CHECKPOINTER
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