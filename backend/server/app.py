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
from server.auth import resolve_user_id, resolve_tenant_id

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    os.makedirs("outputs", exist_ok=True)
    app.mount("/outputs", StaticFiles(directory="outputs"), name="outputs")

    global report_store
    json_path = Path(os.getenv("REPORT_STORE_PATH", os.path.join("data", "reports.json")))
    db_ok = False
    if init_db is not None:
        try:
            db_ok = await init_db()
        except Exception as exc:
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
    filter_user = None if user_id == "anonymous" else user_id
    reports = await report_store.list_reports(report_ids_list, user_id=filter_user)
    return {"reports": reports}


@app.get("/api/reports/{research_id}")
async def get_report_by_id(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = None if user_id == "anonymous" else user_id
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
    filter_user = None if user_id == "anonymous" else user_id
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
    filter_user = None if user_id == "anonymous" else user_id
    existed = await report_store.delete_report(research_id, user_id=filter_user)
    if not existed:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"success": True}


@app.get("/api/reports/{research_id}/chat")
async def get_report_chat(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = None if user_id == "anonymous" else user_id
    report = await report_store.get_report(research_id, user_id=filter_user)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"chatMessages": report.get("chatMessages") or []}


@app.post("/api/reports/{research_id}/chat")
async def add_report_chat_message(research_id: str, request: Request):
    user_id = resolve_user_id(request)
    filter_user = None if user_id == "anonymous" else user_id
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
async def upload_file(file: UploadFile = File(...)):
    return await handle_file_upload(file, DOC_PATH)


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
        filter_user = None if user_id == "anonymous" else user_id
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
            headers=None
        )

        response_content, tool_calls_metadata = await chat_agent.chat(
            messages,
            None,
            research_topic=research_topic,
            research_context=research_context,
            report_language=report_language,
            research_id=session_id,
        )
        logger.info(f"response_content: {response_content}")
        logger.info(f"Got chat response of length: {len(response_content) if response_content else 0}")
        
        if tool_calls_metadata:
            logger.info(f"Tool calls used: {json.dumps(tool_calls_metadata)}")

        # Format response as a ChatMessage object with role, content, timestamp and metadata
        response_message = {
            "role": "assistant",
            "content": response_content,
            "timestamp": int(time.time() * 1000),  # Current time in milliseconds
            "metadata": {
                "tool_calls": tool_calls_metadata
            } if tool_calls_metadata else None
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
    )
    response_content, tool_calls_metadata = await chat_agent.chat(
        data.get("messages", []),
        None,
        research_topic=research_topic,
        research_context=research_context,
        report_language=report_language,
        research_id=research_id,
    )
    response_message = {
        "role": "assistant",
        "content": response_content,
        "timestamp": int(time.time() * 1000),
        "metadata": {"tool_calls": tool_calls_metadata} if tool_calls_metadata else None,
    }
    return {"response": response_message}


@app.get("/api/jobs/{job_id}")
async def get_research_job(job_id: str, request: Request):
    """Poll research job status. PostgreSQL is authoritative when configured."""
    if get_job is None:
        raise HTTPException(status_code=501, detail="Job tracking unavailable")
    user_id = resolve_user_id(request)
    tenant_id = resolve_tenant_id(request, user_id=user_id)
    filter_user = None if user_id == "anonymous" else user_id
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
    filter_user = None if user_id == "anonymous" else user_id
    ok = await cancel_job(job_id, tenant_id=tenant_id, user_id=filter_user)
    if not ok:
        raise HTTPException(status_code=404, detail="Job not found or not cancellable")
    return {"success": True, "job_id": job_id, "status": "cancelled"}


@app.post("/api/jobs/research")
async def submit_research_job(request: Request):
    """
    Enqueue research asynchronously. Job status is stored in PostgreSQL when
    DATABASE_URL is set; Redis is only the queue transport.
    """
    if create_job is None:
        raise HTTPException(status_code=501, detail="Job tracking unavailable")

    import asyncio

    from security import filter_safe_urls, sanitize_mcp_configs, tenant_id_for

    data = await request.json()
    user_id = resolve_user_id(request)
    tenant_id = resolve_tenant_id(request, user_id=user_id) or tenant_id_for(user_id)
    session_id = data.get("session_id") or data.get("research_id")
    mcp_configs = sanitize_mcp_configs(data.get("mcp_configs") or [])
    mcp_enabled = bool(data.get("mcp_enabled", False)) and bool(mcp_configs)
    payload = {
        "task": data.get("task") or data.get("query") or "",
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
        "session_id": session_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
    }
    if not payload["task"]:
        raise HTTPException(status_code=400, detail="task is required")

    job_id = await create_job(
        user_id=user_id,
        tenant_id=tenant_id,
        session_id=session_id,
        payload=payload,
        idempotency_key=data.get("idempotency_key"),
    )
    queued = False
    if enqueue_research_job is not None:
        queued = await enqueue_research_job(job_id, payload)
    if not queued and run_research_job is not None:
        asyncio.create_task(run_research_job({}, job_id, payload))
    return {"job_id": job_id, "queued": queued, "session_id": session_id, "tenant_id": tenant_id}
