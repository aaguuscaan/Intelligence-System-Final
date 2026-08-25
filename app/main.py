import json
import os
import uuid

from dotenv import load_dotenv

from fastapi import (
    FastAPI,
    HTTPException,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from pydantic import BaseModel

from redis import asyncio as aioredis

from langgraph.types import Command


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
    title="Async Multi-Agent API",
    description=(
        "API REST asíncrona para un sistema "
        "multi-agente con LangGraph, Redis "
        "y Human-in-the-loop."
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
    Crea y encola un trabajo.

    El endpoint NO ejecuta LangGraph.
    Guarda el estado en Redis, coloca el job
    en la cola y devuelve inmediatamente
    un job_id.
    """

    job_id = str(
        uuid.uuid4()
    )

    task_data = {
        "job_id": job_id,
        "query": request.query,
        "status": "pending",
        "result": None,
        "error": None,
    }

    # ============================================================
    # GUARDAR ESTADO EN REDIS
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
        f"🔎 Consulta: {request.query}"
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
    "/tasks/{job_id}"
)
async def get_task(
    job_id: str,
):
    """
    Consulta el estado actual de un trabajo.
    """

    key = (
        f"{STATUS_PREFIX}{job_id}"
    )

    data = await redis_client.get(
        key
    )

    if not data:

        raise HTTPException(
            status_code=404,
            detail="Job not found",
        )

    return json.loads(
        data
    )


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
    Reanuda un LangGraph pausado mediante
    Command(resume=...).

    Este endpoint implementa la segunda parte
    del Human-in-the-loop:

        interrupt()
             ↓
        waiting_approval
             ↓
        decisión humana
             ↓
        Command(resume=...)
             ↓
        LangGraph continúa
    """

    key = (
        f"{STATUS_PREFIX}{job_id}"
    )

    # ============================================================
    # OBTENER ESTADO
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

    if (
        task_data.get("status")
        != "waiting_approval"
    ):

        print()
        print("=" * 60)
        print("⚠️ APROBACIÓN RECHAZADA")
        print("=" * 60)
        print(
            f"🔐 Job ID: {job_id}"
        )
        print(
            f"📊 Estado actual: "
            f"{task_data.get('status')}"
        )
        print("=" * 60)
        print()

        raise HTTPException(
            status_code=400,
            detail=(
                "El trabajo no está esperando "
                "una aprobación humana."
            ),
        )

    # ============================================================
    # MOSTRAR DECISIÓN HUMANA
    # ============================================================

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
        # MISMO THREAD
        # ========================================================

        config = {
            "configurable": {
                "thread_id": job_id,
            }
        }

        print(
            f"🔗 Thread ID utilizado: {job_id}"
        )

        print(
            "📦 Recuperando checkpoint desde Redis..."
        )

        # ========================================================
        # RESUME
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

            task_data["status"] = (
                "completed"
            )

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

            task_data["status"] = (
                "rejected"
            )

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
                "💾 Estado guardado en Redis."
            )
            print("=" * 60)
            print()

        # ========================================================
        # GUARDAR ESTADO FINAL
        # ========================================================

        await redis_client.set(
            key,
            json.dumps(
                task_data,
                ensure_ascii=False,
                default=str,
            ),
        )

        # ========================================================
        # RESPUESTA API
        # ========================================================

        return {
            "job_id": job_id,
            "status": task_data["status"],
            "human_approved": request.approved,
            "task_completed": request.approved,
            "result": task_data["result"],
        }

    # ============================================================
    # ERROR
    # ============================================================

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

        task_data["status"] = (
            "failed"
        )

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
# HEALTH CHECK
# ================================================================

@app.get(
    "/health"
)
async def health_check():

    try:

        await redis_client.ping()

        return {
            "status": "ok",
            "redis": "connected",
        }

    except Exception:

        return {
            "status": "error",
            "redis": "disconnected",
        }

