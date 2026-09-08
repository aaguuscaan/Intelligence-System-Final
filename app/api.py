import json
import os
import uuid

from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel, Field, ConfigDict

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
    version="2.1.0",
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
# MODELOS PYDANTIC
# ================================================================


class TaskRequest(BaseModel):
    """
    Input para crear una nueva tarea.
    """

    query: str = Field(
        ...,
        min_length=1,
        description="Consulta que será procesada por el sistema multi-agente.",
        examples=["¿Qué es un sistema RAG?"],
    )


class TaskResponse(BaseModel):
    """
    Respuesta al crear una tarea.
    """

    job_id: str = Field(
        ...,
        description="Identificador único de la tarea.",
    )

    status: str = Field(
        ...,
        description="Estado actual de la tarea.",
    )


class ApprovalRequest(BaseModel):
    """
    Input para la aprobación humana.
    """

    approved: bool = Field(
        ...,
        description="Indica si la ejecución fue aprobada.",
    )


class TaskStatusResponse(BaseModel):
    """
    Estado completo de una tarea.
    """

    job_id: str

    query: str

    status: str

    result: str | None = None

    error: str | None = None


class ApprovalResponse(BaseModel):
    """
    Resultado de una decisión Human-in-the-loop.
    """

    job_id: str

    status: str

    human_approved: bool

    task_completed: bool

    result: str | None = None


class HealthResponse(BaseModel):
    """
    Estado de salud de la API.
    """

    status: str

    redis: str

    error: str | None = None


# ================================================================
# POST /tasks
# ================================================================

@app.post(
    "/tasks",
    response_model=TaskResponse,
)
async def create_task(
    request: TaskRequest,
) -> TaskResponse:

    query = request.query.strip()

    if not query:

        raise HTTPException(
            status_code=400,
            detail="La consulta no puede estar vacía.",
        )

    job_id = str(
        uuid.uuid4()
    )

    task_data = {
        "job_id": job_id,
        "query": query,
        "status": "pending",
        "result": None,
        "error": None,
    }

    # ============================================================
    # GUARDAR JOB EN REDIS
    # ============================================================

    await redis_client.set(
        f"{STATUS_PREFIX}{job_id}",
        json.dumps(
            task_data,
            ensure_ascii=False,
        ),
    )

    # ============================================================
    # ENCOLAR JOB
    # ============================================================

    await redis_client.rpush(
        QUEUE_NAME,
        job_id,
    )

    print()
    print("=" * 60)
    print("📥 NUEVO JOB CREADO")
    print("=" * 60)
    print(
        f"🔐 Job ID: {job_id}"
    )
    print(
        f"🔎 Consulta: {query}"
    )
    print(
        "📤 Estado: pending"
    )
    print(
        "📨 Job enviado a Redis Queue."
    )
    print("=" * 60)
    print()

    return TaskResponse(
        job_id=job_id,
        status="pending",
    )


# ================================================================
# GET /tasks/{job_id}
# ================================================================

@app.get(
    "/tasks/{job_id}",
    response_model=TaskStatusResponse,
)
async def get_task(
    job_id: str,
) -> TaskStatusResponse:

    key = f"{STATUS_PREFIX}{job_id}"

    data = await redis_client.get(
        key
    )

    if not data:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    task_data = json.loads(
        data
    )

    return TaskStatusResponse(
        **task_data
    )


# ================================================================
# POST /tasks/{job_id}/approve
# ================================================================

@app.post(
    "/tasks/{job_id}/approve",
    response_model=ApprovalResponse,
)
async def approve_task(
    job_id: str,
    request: ApprovalRequest,
) -> ApprovalResponse:

    key = f"{STATUS_PREFIX}{job_id}"

    # ============================================================
    # OBTENER JOB
    # ============================================================

    data = await redis_client.get(
        key
    )

    if not data:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    task_data = json.loads(
        data
    )

    # ============================================================
    # VERIFICAR HITL
    # ============================================================

    if task_data.get(
        "status"
    ) != "waiting_approval":

        raise HTTPException(
            status_code=400,
            detail=(
                "El trabajo no está esperando "
                "una aprobación humana."
            ),
        )

    decision_text = (
        "APROBADO"
        if request.approved
        else "RECHAZADO"
    )

    print()
    print("=" * 60)
    print("👤 DECISIÓN HUMANA RECIBIDA")
    print("=" * 60)
    print(
        f"🔐 Job ID: {job_id}"
    )
    print(
        f"👤 Decisión: {decision_text}"
    )
    print(
        "▶️ Reanudando LangGraph..."
    )
    print("=" * 60)
    print()

    try:

        # ========================================================
        # IMPORTAR GRAFO
        # ========================================================

        from app.graph import app as graph_app

        # ========================================================
        # MISMO THREAD ID
        # ========================================================

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        print(
            f"🔗 Thread ID utilizado: {job_id}"
        )

        # ========================================================
        # RESUME LANGGRAPH
        # ========================================================

        result = await graph_app.ainvoke(
            Command(
                resume=request.approved
            ),
            config=config,
        )

        print(
            "▶️ LangGraph reanudado correctamente."
        )

        # ========================================================
        # APROBADO
        # ========================================================

        if request.approved:

            task_data["status"] = "completed"

            task_data["result"] = str(
                result
            )

            task_data["error"] = None

            print()
            print("=" * 60)
            print("✅ JOB COMPLETADO")
            print("=" * 60)
            print(
                f"🔐 Job ID: {job_id}"
            )
            print(
                "👤 Aprobación humana: TRUE"
            )
            print(
                "🧠 LangGraph: FINALIZADO"
            )
            print(
                "💾 Estado guardado en Redis."
            )
            print("=" * 60)
            print()

        # ========================================================
        # RECHAZADO
        # ========================================================

        else:

            task_data["status"] = "rejected"

            task_data["result"] = (
                "La ejecución fue rechazada "
                "por aprobación humana."
            )

            task_data["error"] = None

            print()
            print("=" * 60)
            print("🛑 JOB RECHAZADO")
            print("=" * 60)
            print(
                f"🔐 Job ID: {job_id}"
            )
            print(
                "👤 Aprobación humana: FALSE"
            )
            print(
                "🛑 Ejecución detenida."
            )
            print(
                "💾 Estado guardado en Redis."
            )
            print("=" * 60)
            print()

        # ========================================================
        # GUARDAR ESTADO EN REDIS
        # ========================================================

        await redis_client.set(
            key,
            json.dumps(
                task_data,
                ensure_ascii=False,
                default=str,
            ),
        )

        return ApprovalResponse(
            job_id=job_id,
            status=task_data["status"],
            human_approved=request.approved,
            task_completed=request.approved,
            result=task_data["result"],
        )

    except Exception as error:

        print()
        print("=" * 60)
        print("❌ ERROR AL REANUDAR JOB")
        print("=" * 60)
        print(
            f"🔐 Job ID: {job_id}"
        )
        print(
            f"❌ Error: {repr(error)}"
        )
        print("=" * 60)
        print()

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
    "/health",
    response_model=HealthResponse,
)
async def health_check() -> HealthResponse:

    try:

        await redis_client.ping()

        return HealthResponse(
            status="ok",
            redis="connected",
        )

    except Exception as error:

        return HealthResponse(
            status="error",
            redis="disconnected",
            error=str(error),
        )
