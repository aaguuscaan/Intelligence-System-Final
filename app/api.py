import json
import os
import uuid

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel

from redis import asyncio as aioredis

from langgraph.types import Command


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
# REDIS
# ================================================================

redis_client = aioredis.from_url(
    REDIS_URL,
    decode_responses=True,
)


# ================================================================
# FASTAPI
# ================================================================

app = FastAPI(
    title="Pre-entrega 7 - Multi-Agent API",
    description=(
        "API REST asíncrona para un sistema "
        "multi-agente con LangGraph, Redis, "
        "Worker y Human-in-the-loop."
    ),
    version="2.0.0",
)


# ================================================================
# CORS
# ================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================================================================
# MODELOS
# ================================================================

class TaskRequest(BaseModel):
    query: str


class TaskResponse(BaseModel):
    job_id: str
    status: str


class ApprovalRequest(BaseModel):
    approved: bool


# ================================================================
# POST /tasks
# ================================================================

@app.post(
    "/tasks",
    response_model=TaskResponse,
)
async def create_task(
    request: TaskRequest,
):
    """
    Crea un nuevo trabajo y lo coloca en Redis.

    El endpoint no ejecuta LangGraph directamente.
    El Worker será responsable de procesarlo.
    """

    if not request.query.strip():
        raise HTTPException(
            status_code=400,
            detail="La consulta no puede estar vacía.",
        )

    job_id = str(uuid.uuid4())

    task_data = {
        "job_id": job_id,
        "query": request.query,
        "status": "pending",
        "result": None,
        "error": None,
    }

    # ------------------------------------------------------------
    # GUARDAR ESTADO
    # ------------------------------------------------------------

    await redis_client.set(
        f"{STATUS_PREFIX}{job_id}",
        json.dumps(
            task_data,
            ensure_ascii=False,
        ),
    )

    # ------------------------------------------------------------
    # ENCOLAR JOB
    # ------------------------------------------------------------

    await redis_client.rpush(
        QUEUE_NAME,
        job_id,
    )

    print(
        f"📥 Job creado: {job_id}"
    )

    return TaskResponse(
        job_id=job_id,
        status="pending",
    )


# ================================================================
# GET /tasks/{job_id}
# ================================================================

@app.get(
    "/tasks/{job_id}"
)
async def get_task(
    job_id: str,
):
    """
    Consulta el estado actual de un trabajo.
    """

    key = f"{STATUS_PREFIX}{job_id}"

    data = await redis_client.get(
        key
    )

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return json.loads(data)


# ================================================================
# POST /tasks/{job_id}/approve
# ================================================================

@app.post(
    "/tasks/{job_id}/approve"
)
async def approve_task(
    job_id: str,
    request: ApprovalRequest,
):
    """
    Reanuda un grafo de LangGraph pausado mediante interrupt().

    approved=True:
        continúa y finaliza la ejecución.

    approved=False:
        rechaza la ejecución.
    """

    key = f"{STATUS_PREFIX}{job_id}"

    # ------------------------------------------------------------
    # OBTENER JOB
    # ------------------------------------------------------------

    raw = await redis_client.get(key)

    if not raw:
        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    task_data = json.loads(raw)

    # ------------------------------------------------------------
    # VERIFICAR ESTADO HITL
    # ------------------------------------------------------------

    if task_data.get("status") != "waiting_approval":

        raise HTTPException(
            status_code=400,
            detail=(
                "El trabajo no está esperando "
                "una aprobación humana."
            ),
        )

    try:

        # --------------------------------------------------------
        # IMPORTAR GRAFO
        # --------------------------------------------------------

        from app.graph import app as graph_app

        # --------------------------------------------------------
        # CONFIGURACIÓN
        # --------------------------------------------------------

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        print()
        print("=" * 60)
        print(
            f"👤 APROBACIÓN HUMANA: {job_id}"
        )
        print(
            f"➡️ Decisión: "
            f"{'APROBADO' if request.approved else 'RECHAZADO'}"
        )
        print("=" * 60)

        # --------------------------------------------------------
        # REANUDAR LANGGRAPH
        # --------------------------------------------------------

        result = await graph_app.ainvoke(
            Command(
                resume=request.approved
            ),
            config=config,
        )

        # --------------------------------------------------------
        # APROBADO
        # --------------------------------------------------------

        if request.approved:

            task_data["status"] = "completed"

            task_data["result"] = str(
                result
            )

            task_data["error"] = None

            print(
                "✅ HITL aprobado. "
                "Ejecución finalizada."
            )

        # --------------------------------------------------------
        # RECHAZADO
        # --------------------------------------------------------

        else:

            task_data["status"] = "rejected"

            task_data["result"] = (
                "La ejecución fue rechazada "
                "por aprobación humana."
            )

            task_data["error"] = None

            print(
                "❌ HITL rechazado. "
                "Ejecución detenida."
            )

        # --------------------------------------------------------
        # GUARDAR ESTADO
        # --------------------------------------------------------

        await redis_client.set(
            key,
            json.dumps(
                task_data,
                ensure_ascii=False,
                default=str,
            ),
        )

        return {
            "job_id": job_id,
            "status": task_data["status"],
            "result": task_data["result"],
        }

    except Exception as error:

        print(
            f"❌ Error reanudando job: {error}"
        )

        task_data["status"] = "failed"

        task_data["error"] = str(
            error
        )

        await redis_client.set(
            key,
            json.dumps(
                task_data,
                ensure_ascii=False,
                default=str,
            ),
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "Error al reanudar "
                "el trabajo."
            ),
        )


# ================================================================
# GET /health
# ================================================================

@app.get(
    "/health"
)
async def health_check():
    """
    Verifica que la API pueda comunicarse con Redis.
    """

    try:

        await redis_client.ping()

        return {
            "status": "ok",
            "redis": "connected",
        }

    except Exception as error:

        return {
            "status": "error",
            "redis": "disconnected",
            "error": str(error),
        }