import json
import os
from typing import Dict, List, Any
import time
import logging
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")

# Suppress Pydantic V2 migration warnings
warnings.filterwarnings("ignore", message="Valid config keys have changed in V2")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, File, UploadFile, BackgroundTasks, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict

# Add the parent directory to sys.path to make sure we can import from server
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from server.websocket_manager import WebSocketManager
from server.server_utils import (
    get_config_dict, sanitize_filename,
    update_environment_variables, handle_file_upload, handle_file_deletion,
    execute_multi_agents, handle_websocket_communication
)
from server.agent_discovery import build_agent_discovery_document

from server.websocket_manager import run_agent
from utils import write_md_to_word, write_md_to_pdf
from gpt_researcher.utils.enum import Tone
from chat.chat import ChatAgentWithMemory

from server.report_store import ReportStore
from server.auth import (
    apply_identity_cookie,
    attach_auth_cookie,
    owner_filter,
    resolve_identity,
    resolve_tenant_id,
    resolve_user_id,
)
from server.identity_store import ensure_user
from server.auth_routes import router as auth_router

# Optional SaaS persistence (falls back to JSON when DATABASE_URL unset)
try:
    from db.report_store_factory import create_report_store
    from db.session import init_db, close_db, is_db_enabled
except ImportError:
    create_report_store = None  # type: ignore
    init_db = None  # type: ignore
    close_db = None  # type: ignore
    def is_db_enabled() -> bool:  # type: ignore
        return False

try:
    from jobs import create_job, get_job, update_job, cancel_job
    from jobs.worker import enqueue_research_job, run_research_job
except ImportError:
    create_job = None  # type: ignore
    get_job = None  # type: ignore
    update_job = None  # type: ignore
    cancel_job = None  # type: ignore
    enqueue_research_job = None  # type: ignore
    run_research_job = None  # type: ignore

try:
    from storage import get_object_store
except ImportError:
    get_object_store = None  # type: ignore

# MongoDB services removed - optional PostgreSQL via DATABASE_URL

# Setup logging
logger = logging.getLogger(__name__)

# Don't override parent logger settings
logger.propagate = True

# Silence uvicorn reload logs
logging.getLogger("uvicorn.supervisors.ChangeReload").setLevel(logging.WARNING)

# Models


class ResearchRequest(BaseModel):
    task: str
    report_type: str
    report_source: str
    tone: str
    headers: dict | None = None
    repo_name: str
    branch_name: str
    generate_in_background: bool = True


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="allow")  # Allow extra fields in the request
    
    report: str = ""
    messages: List[Dict[str, Any]]
    research_topic: str = ""
    research_context: str = ""
    report_language: str = "chinese"
    session_id: str | None = None
    research_id: str | None = None


from server.chat_report_request import chat_report_request as _chat_report_request


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs("outputs", exist_ok=True)
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

    from server.health import check_readiness, is_production_env

    # Production fail-fast: required env + migrations (no schema mutation here)
    ok, issues = check_readiness()
    if is_production_env() and not ok:
        raise RuntimeError(f"API readiness failed: {', '.join(issues)}")

    global report_store
    json_path = Path(os.getenv("REPORT_STORE_PATH", os.path.join("data", "reports.json")))
    db_ok = False
    if init_db is not None:
        try:
            db_ok = await init_db()
        except Exception as exc:
            if is_production_env():
                raise
            logger.warning("DB init failed — falling back to JSON store: %s", exc)
            db_ok = False

    if create_report_store is not None and db_ok:
        report_store = create_report_store(json_path)
    else:
        report_store = ReportStore(json_path)

    if get_object_store is not None:
        try:
            get_object_store()
        except Exception as exc:
            logger.warning("Object store init skipped: %s", exc)

    # Shared Redis/ARQ pool — never create_pool per request
    try:
        from jobs.redis_pool import init_arq_pool, get_redis

        await init_arq_pool()
        await get_redis()
        from jobs.slots import rebuild_slots_from_pg_if_needed

        restored = await rebuild_slots_from_pg_if_needed()
        if restored:
            logger.info("Restored %s concurrency slot(s) from PostgreSQL", restored)
    except Exception as exc:
        if is_production_env():
            raise
        logger.warning("ARQ/Redis pool init skipped: %s", exc)

    # Background dispatcher + reaper (multi-instance safe via SKIP LOCKED / version)
    stop_bg = __import__("asyncio").Event()
    bg_tasks = []
    try:
        from jobs.dispatcher import dispatcher_loop
        from jobs.reaper import reaper_loop

        bg_tasks = [
            __import__("asyncio").create_task(dispatcher_loop(stop_bg)),
            __import__("asyncio").create_task(reaper_loop(stop_bg)),
        ]
    except Exception as exc:
        logger.warning("Dispatcher/reaper loops not started: %s", exc)

    mode = "postgresql" if db_ok else "local JSON"
    logger.info("GPT Researcher API ready — persistence mode: %s", mode)
    logger.info(
        "LLM config: FAST=%s SMART=%s EMBEDDING=%s",
        os.getenv("FAST_LLM", "(default)"),
        os.getenv("SMART_LLM", "(default)"),
        os.getenv("EMBEDDING", "(default)"),
    )
    yield
    # Shutdown
    stop_bg.set()
    for t in bg_tasks:
        t.cancel()
    try:
        from jobs.redis_pool import close_arq_pool as _close_pool

        await _close_pool()
    except Exception:
        pass
    if close_db is not None:
        try:
            await close_db()
        except Exception:
            pass
    logger.info("Research API shutting down")

# App initialization
app = FastAPI(lifespan=lifespan)

# Configure allowed origins for CORS
allowed_origins_env = os.getenv("CORS_ALLOW_ORIGINS")
ALLOWED_ORIGINS = (
    [o.strip() for o in allowed_origins_env.split(",") if o.strip()]
    if allowed_origins_env
    else [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "https://app.gptr.dev",
    ]
)

# Standard JSON response - no custom MongoDB encoding needed

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)


@app.middleware("http")
async def visitor_cookie_middleware(request: Request, call_next):
    """Ensure every API caller has a durable visitor/registered cookie. :-)"""
    path = request.url.path or ""
    if path.startswith(("/docs", "/openapi", "/redoc", "/outputs")):
        return await call_next(request)
    ident = resolve_identity(request)
    if ident.is_new:
        await ensure_user(ident.user_id, kind=ident.kind)
    response = await call_next(request)
    if ident.set_cookie_value:
        attach_auth_cookie(response, ident.set_cookie_value)
    return response


# Use default JSON response class

# WebSocket manager
manager = WebSocketManager()

# Lazily replaced in lifespan; JSON fallback so imports never break report path
report_store = ReportStore(Path(os.getenv("REPORT_STORE_PATH", os.path.join("data", "reports.json"))))

# Constants
DOC_PATH = os.getenv("DOC_PATH", "./my-docs")

# Startup event


# Lifespan events now handled in the lifespan context manager above


# Routes
@app.get("/health/live")
async def health_live():
    """Liveness: process is up."""
    return {"status": "live"}


@app.get("/health/ready")
async def health_ready():
    """Readiness: PG, Redis, migrations, queue — never leaks secrets."""
    from fastapi.responses import JSONResponse
    from server.health import build_ready_payload

    payload = await build_ready_payload()
    code = 200 if payload.get("status") == "ready" else 503
    return JSONResponse(status_code=code, content=payload)


@app.get("/health")
async def health_compat():
    """Backward-compatible health alias → readiness."""
    return await health_ready()


@app.get("/")
async def api_root():
    """API-only root. Use the Next.js app (default http://localhost:3000) for the UI."""
    return {
        "service": "GPT Researcher API",
        "ui": os.getenv("NEXT_PUBLIC_APP_URL", "http://localhost:3000"),
        "docs": "/docs",
        "websocket": "/ws",
        "chat": "/api/chat",
    }


@app.get("/.well-known/agent-discovery.json")
async def agent_discovery(request: Request):
    """Advertise GPT Researcher services via the Agent Discovery Protocol."""
    origin = str(request.base_url).rstrip("/")
    domain = request.url.hostname or request.headers.get("host", "")
    contact = os.getenv("AGENT_DISCOVERY_CONTACT")

    document = build_agent_discovery_document(origin=origin, domain=domain, contact=contact)
    response = JSONResponse(content=document)
    response.headers["Access-Control-Allow-Origin"] = "*"
    return response

@app.get("/report/{research_id}")
async def read_report(request: Request, research_id: str):
    docx_path = os.path.join('outputs', f"{research_id}.docx")
    if not os.path.exists(docx_path):
        return {"message": "Report not found."}
    return FileResponse(docx_path)


# Report routes — user isolation via X-User-Id when provided
@app.get("/api/reports")
async def get_all_reports(request: Request, report_ids: str = None):
    user_id = resolve_user_id(request)
    report_ids_list = report_ids.split(",") if report_ids else None
    # anonymous lists all (legacy); named users see only their reports
    filter_user = owner_filter(user_id)
    reports = await report_store.list_reports(report_ids_list, user_id=filter_user)
    return {"reports": reports}


@app.get("/api/reports/{research_id}")
async def get_report_by_id(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = owner_filter(user_id)
    report = await report_store.get_report(research_id, user_id=filter_user)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}


@app.post("/api/reports")
async def create_or_update_report(request: Request):
    try:
        data = await request.json()
        research_id = data.get("id", "temp_id")
        user_id = resolve_user_id(request)

        now_ms = int(time.time() * 1000)
        existing = await report_store.get_report(research_id)
        incoming_timestamp = data.get("timestamp")
        timestamp = incoming_timestamp if isinstance(incoming_timestamp, int) else now_ms
        if existing and isinstance(existing.get("timestamp"), int):
            timestamp = max(timestamp, existing["timestamp"])

        report = {
            "id": research_id,
            "question": data.get("question"),
            "answer": data.get("answer"),
            "orderedData": data.get("orderedData") or [],
            "chatMessages": data.get("chatMessages") or [],
            "timestamp": timestamp,
            "user_id": user_id,
            "report_language": data.get("report_language")
            or (existing or {}).get("report_language")
            or "chinese",
            "status": data.get("status") or (existing or {}).get("status") or "completed",
            "job_id": data.get("job_id") or (existing or {}).get("job_id"),
        }

        await report_store.upsert_report(research_id, report, user_id=user_id)
        return {"success": True, "id": research_id}
    except Exception as e:
        logger.error(f"Error processing report creation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/reports/{research_id}")
async def update_report(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = owner_filter(user_id)
    existing = await report_store.get_report(research_id, user_id=filter_user)
    if existing is None:
        raise HTTPException(status_code=404, detail="Report not found")

    data = await request.json()
    now_ms = int(time.time() * 1000)

    updated = {
        **existing,
        **{k: v for k, v in data.items() if v is not None},
        "id": research_id,
        "timestamp": now_ms,
        "user_id": existing.get("user_id") or user_id,
    }

    await report_store.upsert_report(research_id, updated, user_id=filter_user)
    return {"success": True, "id": research_id}


@app.delete("/api/reports/{research_id}")
async def delete_report(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = owner_filter(user_id)
    existed = await report_store.delete_report(research_id, user_id=filter_user)
    if not existed:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True}


@app.get("/api/reports/{research_id}/chat")
async def get_report_chat(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = owner_filter(user_id)
    report = await report_store.get_report(research_id, user_id=filter_user)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"chatMessages": report.get("chatMessages") or []}


@app.post("/api/reports/{research_id}/chat")
async def add_report_chat_message(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = owner_filter(user_id)
    report = await report_store.get_report(research_id, user_id=filter_user)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    message = await request.json()
    # If body looks like a chat completion request (has messages), run chat agent
    if isinstance(message, dict) and "messages" in message:
        return await _run_session_chat(research_id, message, user_id=filter_user)

    chat_messages = report.get("chatMessages") or []
    if isinstance(chat_messages, list):
        chat_messages = [*chat_messages, message]
    else:
        chat_messages = [message]

    now_ms = int(time.time() * 1000)
    updated = {
        **report,
        "chatMessages": chat_messages,
        "timestamp": now_ms,
    }

    await report_store.upsert_report(research_id, updated, user_id=filter_user)
    return {"success": True, "id": research_id}


async def write_report(research_request: ResearchRequest, research_id: str = None):
    report_information = await run_agent(
        task=research_request.task,
        report_type=research_request.report_type,
        report_source=research_request.report_source,
        source_urls=[],
        document_urls=[],
        tone=Tone[research_request.tone],
        websocket=None,
        stream_output=None,
        headers=research_request.headers,
        query_domains=[],
        config_path="",
        return_researcher=True
    )

    docx_path = await write_md_to_word(report_information[0], research_id)
    pdf_path = await write_md_to_pdf(report_information[0], research_id)
    if research_request.report_type != "multi_agents":
        report, researcher = report_information
        response = {
            "research_id": research_id,
            "research_information": {
                "source_urls": researcher.get_source_urls(),
                "research_costs": researcher.get_costs(),
                "visited_urls": list(researcher.visited_urls),
                "research_images": researcher.get_research_images(),
                # "research_sources": researcher.get_research_sources(),  # Raw content of sources may be very large
            },
            "report": report,
            "docx_path": docx_path,
            "pdf_path": pdf_path
        }
    else:
        response = { "research_id": research_id, "report": "", "docx_path": docx_path, "pdf_path": pdf_path }

    return response

@app.post("/report/")
async def generate_report(research_request: ResearchRequest, background_tasks: BackgroundTasks):
    research_id = sanitize_filename(f"task_{int(time.time())}_{research_request.task}")

    if research_request.generate_in_background:
        background_tasks.add_task(write_report, research_request=research_request, research_id=research_id)
        return {"message": "Your report is being generated in the background. Please check back later.",
                "research_id": research_id}
    else:
        response = await write_report(research_request, research_id)
        return response


@app.get("/files/")
async def list_files():
    if not os.path.exists(DOC_PATH):
        os.makedirs(DOC_PATH, exist_ok=True)
    files = os.listdir(DOC_PATH)
    print(f"Files in {DOC_PATH}: {files}")
    return {"files": files}


@app.post("/api/multi_agents")
async def run_multi_agents():
    return await execute_multi_agents(manager)


@app.post("/upload/")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    session_id: str | None = None,
):
    result = await handle_file_upload(file, DOC_PATH)
    # Best-effort RAG ingest (tenant/session scoped when provided)
    try:
        from rag.ingest import ingest_upload_file

        user_id = resolve_user_id(request)
        tenant_id = resolve_tenant_id(request, user_id=user_id)
        doc_id = await ingest_upload_file(
            file_path=result.get("path") or "",
            filename=result.get("filename") or file.filename or "upload",
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
        if doc_id:
            result["document_id"] = doc_id
    except Exception as ingest_exc:
        logger.debug("Upload RAG ingest skipped: %s", ingest_exc)
    return result


@app.delete("/files/{filename}")
async def delete_file(filename: str):
    return await handle_file_deletion(filename, DOC_PATH)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await handle_websocket_communication(websocket, manager)
    except WebSocketDisconnect as e:
        # Disconnect with more detailed logging about the WebSocket disconnect reason
        logger.info(f"WebSocket disconnected with code {e.code} and reason: '{e.reason}'")
        await manager.disconnect(websocket)
    except Exception as e:
        # More general exception handling
        logger.error(f"Unexpected WebSocket error: {str(e)}")
        await manager.disconnect(websocket)

@app.post("/api/chat")
async def chat(chat_request: ChatRequest, request: Request):
    """Process a chat request with a report and message history.

    When session_id/research_id is set, server-side report/context is loaded and
    merged without discarding client-provided context (append/enrich only).
    """
    try:
        logger.info(f"Received chat request with {len(chat_request.messages)} messages")
        user_id = resolve_user_id(request)
        filter_user = owner_filter(user_id)
        session_id = chat_request.session_id or chat_request.research_id

        report_text = chat_request.report or ""
        research_topic = chat_request.research_topic or ""
        research_context = chat_request.research_context or ""
        report_language = chat_request.report_language or "chinese"
        messages = chat_request.messages

        if session_id:
            try:
                ctx = await report_store.get_session_context(session_id, user_id=filter_user)
                if ctx:
                    stored_report = (ctx.get("report") or {}).get("answer") or ""
                    if stored_report and not report_text.strip():
                        report_text = stored_report
                    if not research_topic.strip():
                        research_topic = ctx.get("research_topic") or research_topic
                    # Append server sources to client context; never wipe client context
                    server_ctx = (ctx.get("research_context") or "").strip()
                    if server_ctx:
                        research_context = (
                            f"{research_context}\n\n{server_ctx}".strip()
                            if research_context.strip()
                            else server_ctx
                        )
                    report_language = ctx.get("report_language") or report_language
                    if not messages and ctx.get("messages"):
                        messages = ctx["messages"]
            except Exception as ctx_exc:
                logger.warning("Session context load failed (using request body): %s", ctx_exc)

        chat_agent = ChatAgentWithMemory(
            report=report_text,
            config_path="default",
            headers=None,
            report_request_callback=_chat_report_request,
        )
        tenant_id = resolve_tenant_id(request, user_id=user_id)

        response_content, tool_calls_metadata = await chat_agent.chat(
            messages,
            None,
            research_topic=research_topic,
            research_context=research_context,
            report_language=report_language,
            research_id=session_id,
            tenant_id=tenant_id,
            user_id=user_id,
        )
        logger.info(f"response_content: {response_content}")
        logger.info(f"Got chat response of length: {len(response_content) if response_content else 0}")
        
        if tool_calls_metadata:
            logger.info(f"Tool calls used: {json.dumps(tool_calls_metadata)}")

        # ChatAgent returns a rich metadata dict (tool calls + RAG citations).
        # Preserve it as-is instead of nesting tool_calls inside tool_calls.
        meta = None
        if tool_calls_metadata:
            if isinstance(tool_calls_metadata, dict):
                meta = tool_calls_metadata
            else:
                meta = {"tool_calls": tool_calls_metadata}

        # Format response as a ChatMessage object with role, content, timestamp and metadata
        response_message = {
            "role": "assistant",
            "content": response_content,
            "timestamp": int(time.time() * 1000),  # Current time in milliseconds
            "metadata": meta,
        }

        logger.info(f"Returning formatted response: {json.dumps(response_message)[:100]}...")
        return {"response": response_message}
    except Exception as e:
        logger.error(f"Error processing chat request: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def _run_session_chat(research_id: str, data: dict, user_id: str | None = None):
    """Shared chat path for /api/reports/{id}/chat completion bodies."""
    ctx = {}
    try:
        ctx = await report_store.get_session_context(research_id, user_id=user_id) or {}
    except Exception as exc:
        logger.warning("Session context unavailable: %s", exc)

    stored = ctx.get("report") or {}
    report_text = data.get("report") or stored.get("answer") or ""
    research_topic = data.get("research_topic") or ctx.get("research_topic") or stored.get("question") or ""
    research_context = data.get("research_context") or ""
    server_ctx = (ctx.get("research_context") or "").strip()
    if server_ctx:
        research_context = (
            f"{research_context}\n\n{server_ctx}".strip()
            if research_context.strip()
            else server_ctx
        )
    report_language = data.get("report_language") or ctx.get("report_language") or "chinese"

    chat_agent = ChatAgentWithMemory(
        report=report_text,
        config_path="default",
        headers=None,
        report_request_callback=_chat_report_request,
    )
    tenant_id = (
        data.get("tenant_id")
        or stored.get("tenant_id")
        or ctx.get("tenant_id")
        or "anonymous"
    )
    chat_user = user_id or stored.get("user_id") or "anonymous"
    response_content, tool_calls_metadata = await chat_agent.chat(
        data.get("messages", []),
        None,
        research_topic=research_topic,
        research_context=research_context,
        report_language=report_language,
        research_id=research_id,
        tenant_id=str(tenant_id),
        user_id=str(chat_user),
    )
    # Ingest latest user turn into RAG (best-effort)
    try:
        from rag.ingest import ingest_text_document

        latest_user = ""
        for msg in reversed(data.get("messages") or []):
            if isinstance(msg, dict) and msg.get("role") == "user":
                latest_user = str(msg.get("content") or "")
                break
        if latest_user.strip():
            await ingest_text_document(
                text=latest_user,
                title="chat_user_turn",
                uri=f"chat:{research_id}",
                source_type="chat",
                tenant_id=str(tenant_id),
                user_id=str(chat_user),
                session_id=research_id,
                metadata={"role": "user"},
            )
    except Exception as chat_ingest_exc:
        logger.debug("Chat turn ingest skipped: %s", chat_ingest_exc)

    meta = None
    if tool_calls_metadata:
        # tool_calls_metadata may already be the full meta dict (citations etc.)
        if isinstance(tool_calls_metadata, dict) and (
            "tool_calls" in tool_calls_metadata
            or "citations" in tool_calls_metadata
            or "rag_degraded" in tool_calls_metadata
        ):
            meta = tool_calls_metadata
        else:
            meta = {"tool_calls": tool_calls_metadata}
    response_message = {
        "role": "assistant",
        "content": response_content,
        "timestamp": int(time.time() * 1000),
        "metadata": meta,
    }
    return {"response": response_message}


@app.get("/api/jobs/{job_id}")
async def get_research_job(job_id: str, request: Request):
    """Poll research job status. PostgreSQL is authoritative when configured."""
    if get_job is None:
        raise HTTPException(status_code=501, detail="Job tracking unavailable")
    user_id = resolve_user_id(request)
    tenant_id = resolve_tenant_id(request, user_id=user_id)
    filter_user = owner_filter(user_id)
    job = await get_job(job_id, tenant_id=tenant_id, user_id=filter_user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {"job": job}


@app.post("/api/jobs/{job_id}/cancel")
async def cancel_research_job(job_id: str, request: Request):
    if cancel_job is None:
        raise HTTPException(status_code=501, detail="Job cancel unavailable")
    user_id = resolve_user_id(request)
    tenant_id = resolve_tenant_id(request, user_id=user_id)
    filter_user = owner_filter(user_id)
    ok = await cancel_job(job_id, tenant_id=tenant_id, user_id=filter_user)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    job = await get_job(job_id, tenant_id=tenant_id, user_id=filter_user) if get_job else None
    status = (job or {}).get("status") or "cancel_requested"
    return {"success": True, "job_id": job_id, "status": status}


@app.post("/api/research/intent")
async def resolve_research_intent(request: Request):
    """
    Pre-flight intent / disambiguation before creating a research Job.

    Returns action=proceed|clarify with expanded_task / options.
    """
    from jobs.planning_context import resolve_report_intent

    data = await request.json()
    ident = resolve_identity(request)
    user_id = ident.user_id
    await ensure_user(user_id, kind=ident.kind)
    task = (data.get("task") or data.get("query") or "").strip()
    if not task:
        raise HTTPException(status_code=400, detail="task is required")

    client_msgs = data.get("recent_chat_messages") or data.get("chat_messages") or []
    if not isinstance(client_msgs, list):
        client_msgs = []

    try:
        result = await resolve_report_intent(
            task=task,
            user_id=user_id,
            report_store=report_store,
            parent_chat_id=data.get("parent_chat_id") or data.get("parent_session_id"),
            client_messages=client_msgs,
            force_domain=data.get("force_domain"),
            force_sense=data.get("force_sense"),
        )
    except Exception as exc:
        logger.exception("resolve_research_intent failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return result


@app.post("/api/jobs/research")
async def submit_research_job(request: Request):
    """
    Create ResearchSession (if needed) + ResearchJob, then enqueue Redis/ARQ.

    On enqueue failure: keep status=pending_dispatch (not failed). Dispatcher recovers.
    In-process fallback only when ALLOW_IN_PROCESS_RESEARCH_FALLBACK=true (never in prod).
    """
    if create_job is None or enqueue_research_job is None or update_job is None:
        raise HTTPException(status_code=501, detail="Job tracking unavailable")

    from security import filter_safe_urls, sanitize_mcp_configs, tenant_id_for
    from jobs import allow_in_process_research_fallback, find_job_by_idempotency
    from jobs.session_bootstrap import ensure_research_session

    data = await request.json()
    ident = resolve_identity(request)
    user_id = ident.user_id
    tenant_id = ident.tenant_id or tenant_id_for(user_id)
    await ensure_user(user_id, kind=ident.kind)
    idempotency_key = data.get("idempotency_key")
    task = data.get("task") or data.get("query") or ""
    if not task:
        raise HTTPException(status_code=400, detail="task is required")

    if not os.getenv("REDIS_URL", "").strip():
        raise HTTPException(
            status_code=503,
            detail="REDIS_URL is required to enqueue research jobs",
        )
    if not os.getenv("DATABASE_URL", "").strip():
        raise HTTPException(
            status_code=503,
            detail=(
                "DATABASE_URL is required so PostgreSQL can be the authoritative "
                "job store for the research worker"
            ),
        )

    # DB-level idempotency: reuse existing job+session before creating anything new
    if idempotency_key:
        existing = await find_job_by_idempotency(
            tenant_id, idempotency_key, user_id=user_id
        )
        if existing:
            return {
                "job_id": existing["id"],
                "queued": existing.get("status") == "queued",
                "status": existing.get("status"),
                "stage": existing.get("stage"),
                "session_id": existing.get("session_id"),
                "tenant_id": tenant_id,
                "reused": True,
            }

    # Capacity + daily budget gates (do not create job when over limit)
    from jobs.slots import (
        SlotAcquireError,
        acquire_slots,
        http_429_detail,
        precheck_capacity,
    )
    from jobs.daily_budget import DailyBudgetReject, check_daily_budget, record_job_started

    reject = await precheck_capacity(tenant_id=tenant_id, user_id=user_id)
    if reject is not None:
        return JSONResponse(
            status_code=429,
            content=http_429_detail(reject),
            headers={"Retry-After": str(reject.retry_after)},
        )
    try:
        await check_daily_budget(tenant_id=tenant_id, user_id=user_id)
    except DailyBudgetReject as budget_exc:
        return JSONResponse(
            status_code=429,
            content={
                "message": budget_exc.message,
                "error_code": budget_exc.code,
                "retry_after": budget_exc.retry_after,
            },
            headers={"Retry-After": str(budget_exc.retry_after)},
        )

    session_id = data.get("session_id") or data.get("research_id")
    session_created = False
    if not session_id:
        if report_store is None:
            raise HTTPException(status_code=503, detail="Report store unavailable")
        try:
            session_id = await ensure_research_session(
                report_store=report_store,
                user_id=user_id,
                tenant_id=tenant_id,
                task=task,
                session_id=None,
                idempotency_key=idempotency_key,
                report_language=data.get("report_language") or "chinese",
            )
            session_created = True
        except Exception as exc:
            logger.exception("Failed to auto-create research session")
            raise HTTPException(
                status_code=503, detail=f"Failed to create research session: {exc}"
            ) from exc

    mcp_configs = sanitize_mcp_configs(data.get("mcp_configs") or [])
    mcp_enabled = bool(data.get("mcp_enabled", False)) and bool(mcp_configs)

    # Per-user planning context: recent chat/reports + tech-first acronym bias. :-)
    planning_meta: dict = {}
    try:
        from jobs.planning_context import resolve_report_intent

        client_msgs = data.get("recent_chat_messages") or data.get("chat_messages") or []
        if not isinstance(client_msgs, list):
            client_msgs = []
        # Job create assumes UI already clarified; force_sense/domain skip ask. :-)
        planning_meta = await resolve_report_intent(
            task=task,
            user_id=user_id,
            report_store=report_store,
            parent_chat_id=data.get("parent_chat_id") or data.get("parent_session_id"),
            client_messages=client_msgs,
            force_domain=data.get("force_domain"),
            force_sense=data.get("force_sense"),
        )
        if planning_meta.get("action") == "clarify":
            # Safety net: never block enqueue mid-create; fall back tech-first. :-)
            planning_meta = await resolve_report_intent(
                task=task,
                user_id=user_id,
                report_store=report_store,
                parent_chat_id=data.get("parent_chat_id") or data.get("parent_session_id"),
                client_messages=client_msgs,
                force_domain="tech",
            )
        if data.get("expanded_task"):
            planning_meta["expanded_task"] = str(data.get("expanded_task"))
    except Exception as plan_ctx_exc:
        logger.warning("Planning user context skipped: %s", plan_ctx_exc)
        planning_meta = {}

    display_task = task
    research_task = str(planning_meta.get("expanded_task") or task)

    payload = {
        "task": research_task,
        "display_task": display_task,
        "report_type": data.get("report_type", "research_report"),
        "report_source": data.get("report_source", "web"),
        "tone": data.get("tone", "Objective"),
        "source_urls": filter_safe_urls(data.get("source_urls") or []),
        "document_urls": filter_safe_urls(data.get("document_urls") or []),
        "headers": data.get("headers"),
        "query_domains": data.get("query_domains") or [],
        "mcp_enabled": mcp_enabled,
        "mcp_strategy": data.get("mcp_strategy") or "fast",
        "mcp_configs": mcp_configs,
        "max_search_results": data.get("max_search_results"),
        "total_words": data.get("total_words"),
        "report_language": data.get("report_language") or "chinese",
        "knowledge_policy": data.get("knowledge_policy") or "web_first",
        "session_id": session_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        # Review/ops only; worker honors when TRUSTED_REPORT_ALLOW_FORCE_SAMPLE=true. :-)
        "force_trusted_sample": bool(data.get("force_trusted_sample")),
        "parent_chat_id": data.get("parent_chat_id") or data.get("parent_session_id"),
        "planning_context": planning_meta,
        "expanded_task": research_task,
        "planning_hint": planning_meta.get("planning_hint") or "",
        "force_domain": data.get("force_domain") or planning_meta.get("domain_preference"),
        "force_sense": data.get("force_sense"),
    }

    # 1) Persist job in PostgreSQL first
    try:
        job_id = await create_job(
            user_id=user_id,
            tenant_id=tenant_id,
            session_id=session_id,
            payload=payload,
            idempotency_key=idempotency_key,
        )
    except Exception as exc:
        # Best-effort cleanup if we created a brand-new session then job failed
        if session_created and report_store is not None and hasattr(
            report_store, "delete_report"
        ):
            try:
                await report_store.delete_report(
                    session_id, user_id=None if user_id == "anonymous" else user_id
                )
            except Exception:
                logger.warning("Orphan session cleanup failed for %s", session_id)
        raise HTTPException(status_code=503, detail=f"Failed to create job: {exc}") from exc

    # Bind Redis concurrency lease (race-safe); reject cancels the just-created job
    try:
        await acquire_slots(tenant_id=tenant_id, user_id=user_id, job_id=job_id)
    except SlotAcquireError as slot_exc:
        await update_job(
            job_id,
            status="cancelled",
            progress="rejected_capacity",
            error=slot_exc.reject.message,
            last_error_code=slot_exc.reject.code,
            tenant_id=tenant_id,
        )
        return JSONResponse(
            status_code=429,
            content={**http_429_detail(slot_exc.reject), "job_id": job_id},
            headers={"Retry-After": str(slot_exc.reject.retry_after)},
        )

    try:
        await record_job_started(tenant_id=tenant_id, user_id=user_id)
    except Exception as usage_exc:
        logger.debug("jobs_started audit skipped: %s", usage_exc)

    # Link session → job for page-refresh recovery
    try:
        if report_store is not None:
            existing = await report_store.get_report(session_id) or {}
            await report_store.upsert_report(
                session_id,
                {
                    **existing,
                    "id": session_id,
                    "question": payload["task"] or existing.get("question", ""),
                    "job_id": job_id,
                    # A just-created sidebar entry may default to "completed";
                    # submitting a Job must still expose it as active.
                    "status": (
                        "running"
                        if existing.get("status") in (None, "", "completed", "failed", "cancelled")
                        else existing.get("status")
                    ),
                    "user_id": user_id,
                    "tenant_id": tenant_id,
                    "report_language": payload.get("report_language")
                    or existing.get("report_language", "chinese"),
                },
                user_id=None if user_id == "anonymous" else user_id,
            )
    except Exception as link_exc:
        logger.warning("Failed to link session to job_id (non-fatal): %s", link_exc)

    # Idempotent reuse: if already queued/running/completed, do not re-enqueue blindly
    existing_job = await get_job(job_id, tenant_id=tenant_id) if get_job else None
    if existing_job and existing_job.get("status") in (
        "queued",
        "running",
        "retrying",
        "completed",
        "cancel_requested",
        "cancelling",
    ):
        return {
            "job_id": job_id,
            "queued": existing_job.get("status") == "queued",
            "status": existing_job.get("status"),
            "stage": existing_job.get("stage"),
            "session_id": session_id,
            "tenant_id": tenant_id,
            "reused": True,
        }

    # 2) Enqueue to Redis/ARQ via shared pool
    queued = await enqueue_research_job(job_id, payload)
    if queued:
        from datetime import datetime, timezone

        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        await update_job(
            job_id,
            status="queued",
            stage="planning",
            progress="queued",
            tenant_id=tenant_id,
        )
        # Best-effort enqueued_at via memory/DB fields on next update path
        mem = None
        try:
            from jobs import _MEMORY_JOBS

            mem = _MEMORY_JOBS.get(job_id)
            if mem is not None:
                mem["enqueued_at"] = now_ms
        except Exception:
            pass
        return {
            "job_id": job_id,
            "queued": True,
            "status": "queued",
            "stage": "planning",
            "session_id": session_id,
            "tenant_id": tenant_id,
        }

    # Enqueue failed: keep pending_dispatch for Dispatcher recovery
    await update_job(
        job_id,
        status="pending_dispatch",
        stage="planning",
        progress="pending_dispatch",
        error="Failed to enqueue to Redis/ARQ; job remains pending_dispatch",
        last_error_code="enqueue_failed",
        tenant_id=tenant_id,
    )

    if allow_in_process_research_fallback() and run_research_job is not None:
        import asyncio

        logger.warning(
            "ALLOW_IN_PROCESS_RESEARCH_FALLBACK — running job %s in API process (dev only)",
            job_id,
        )
        await update_job(
            job_id,
            status="queued",
            stage="planning",
            progress="in_process_fallback",
            tenant_id=tenant_id,
        )
        asyncio.create_task(run_research_job({}, job_id, payload))
        return {
            "job_id": job_id,
            "queued": False,
            "in_process": True,
            "status": "queued",
            "session_id": session_id,
            "tenant_id": tenant_id,
        }

    # Still return job_id so clients can poll; Dispatcher will re-enqueue
    return JSONResponse(
        status_code=202,
        content={
            "job_id": job_id,
            "queued": False,
            "status": "pending_dispatch",
            "stage": "planning",
            "session_id": session_id,
            "tenant_id": tenant_id,
            "message": (
                "Job persisted as pending_dispatch; dispatcher will enqueue when Redis recovers"
            ),
        },
    )


@app.post("/api/jobs/{job_id}/redispatch")
async def redispatch_research_job(job_id: str, request: Request):
    """Re-enqueue a pending_dispatch job (ops / recovery)."""
    if get_job is None or enqueue_research_job is None or update_job is None:
        raise HTTPException(status_code=501, detail="Job tracking unavailable")
    user_id = resolve_user_id(request)
    tenant_id = resolve_tenant_id(request, user_id=user_id)
    filter_user = owner_filter(user_id)
    job = await get_job(job_id, tenant_id=tenant_id, user_id=filter_user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.get("status") not in ("pending_dispatch", "queued"):
        raise HTTPException(
            status_code=409,
            detail=f"Job status {job.get('status')} cannot be redispatched",
        )
    payload = job.get("payload") or {}
    queued = await enqueue_research_job(job_id, payload)
    if not queued:
        raise HTTPException(status_code=503, detail="Redis enqueue failed again")
    await update_job(
        job_id,
        status="queued",
        stage="planning",
        progress="queued",
        error=None,
        tenant_id=tenant_id,
    )
    return {"job_id": job_id, "queued": True, "status": "queued"}


@app.get("/api/jobs/{job_id}/events")
async def stream_research_job_events(job_id: str, request: Request):
    """SSE observer for a research job. PostgreSQL is authoritative for terminal state."""
    if get_job is None:
        raise HTTPException(status_code=501, detail="Job tracking unavailable")

    from fastapi.responses import StreamingResponse
    from jobs.progress import subscribe_job_events

    user_id = resolve_user_id(request)
    tenant_id = resolve_tenant_id(request, user_id=user_id)
    filter_user = owner_filter(user_id)
    job = await get_job(job_id, tenant_id=tenant_id, user_id=filter_user)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        try:
            async for event in subscribe_job_events(job_id, tenant_id=tenant_id):
                if await request.is_disconnected():
                    break
                yield f"data: {json.dumps(event, ensure_ascii=False, default=str)}\n\n"
        except Exception as exc:
            logger.warning("SSE job stream ended: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'output': str(exc)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
