import asyncio
import logging
import os
import uuid
import json
from collections.abc import Awaitable, Callable
from fastapi import WebSocket
from typing import List, Dict, Any

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import InMemoryVectorStore
from gpt_researcher.memory import Memory
from gpt_researcher.config.config import Config
from gpt_researcher.utils.llm import create_chat_completion
from gpt_researcher.utils.tools import create_chat_completion_with_tools, create_search_tool
from gpt_researcher.retrievers.tavily.key_pool import (
    get_current_tavily_key,
    get_tavily_keys,
    mark_tavily_key_exhausted,
    should_rotate_tavily_key,
    with_tavily_key_rotation,
)
from datetime import datetime

# Setup logging
# Get logger instance
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler()  # Only log to console
    ]
)

# Note: LLM client is now handled through GPT Researcher's unified LLM system
# This supports all configured providers (OpenAI, Google Gemini, Anthropic, etc.)


def _latest_user_text(messages: list) -> str:
    for msg in reversed(messages or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content") or "").strip()
    return ""


def _messages_for_model(messages: list, *, research_id: str | None) -> list:
    """Bound persisted-session history; older turns are recalled through Child memory."""
    if not research_id:
        return list(messages or [])
    try:
        turns = max(1, int(os.getenv("CHAT_RECENT_TURNS", "6")))
    except ValueError:
        turns = 6
    return list(messages or [])[-(turns * 2) :]


def get_tools():
    """Define tools for LLM function calling (primarily for OpenAI-compatible providers)"""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "quick_search",
                "description": "Search the web for current information. Always available during chat — use before or after a report is generated whenever web results would improve the answer.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query"
                        }
                    },
                    "required": ["query"]
                }
            }
        }
    ]
    return tools

class ChatAgentWithMemory:
    def __init__(
        self,
        report: str,
        config_path="default",
        headers=None,
        vector_store=None,
        report_request_callback: Callable[[str, str], Awaitable[dict[str, Any]]] | None = None,
    ):
        self.report = report
        self.headers = headers
        self.config = Config(config_path)
        self.vector_store = vector_store
        self.retriever = None
        self.search_metadata = None
        # The chat model may request a report, but session creation and job
        # submission remain controlled by the application layer.
        self.report_request_callback = report_request_callback
        
        # Initialize Tavily client (optional - only if API key is available)
        if get_tavily_keys():
            self.tavily_enabled = True
        else:
            self.tavily_enabled = False
            logger.warning(
                "TAVILY_API_KEYS/TAVILY_API_KEY not set - web search in chat will be disabled"
            )
        
        # Process document and create vector store if not provided
        if not self.vector_store and False:
            self._setup_vector_store()
    
    def _setup_vector_store(self):
        """Setup vector store for document retrieval"""
        # Process document into chunks
        documents = self._process_document(self.report)
        
        # Create unique thread ID
        self.thread_id = str(uuid.uuid4())
        
        # Setup embeddings and vector store
        cfg = Config()
        self.embedding = Memory(
            cfg.embedding_provider,
            cfg.embedding_model,
            **cfg.embedding_kwargs
        ).get_embeddings()
        
        # Create vector store and retriever
        self.vector_store = InMemoryVectorStore(self.embedding)
        self.vector_store.add_texts(documents)
        self.retriever = self.vector_store.as_retriever(k=4)
        
    def _process_document(self, report):
        """Split Report into Chunks"""
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1024,
            chunk_overlap=20,
            length_function=len,
            is_separator_regex=False,
        )
        documents = text_splitter.split_text(report)
        return documents

    def quick_search(self, query):
        """Perform a web search for current information using Tavily"""
        try:
            # Check if Tavily client is available
            if not self.tavily_enabled:
                logger.warning(f"Tavily client not available, skipping web search for: {query}")
                self.search_metadata = {
                    "query": query,
                    "sources": [],
                    "error": "Web search is disabled - TAVILY_API_KEYS not configured"
                }
                return {
                    "error": "Web search is disabled - TAVILY_API_KEYS not configured",
                    "results": []
                }
            
            logger.info(f"Performing web search for: {query}")

            def _search_with_key(api_key: str):
                from tavily import TavilyClient

                client = TavilyClient(api_key=api_key)
                return client.search(query=query, max_results=5)

            results = with_tavily_key_rotation(_search_with_key)
            
            # Store search metadata for frontend
            self.search_metadata = {
                "query": query,
                "sources": [
                    {"title": result.get("title", ""), 
                     "url": result.get("url", ""),
                     "content": result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", "")}
                    for result in results.get("results", [])
                ]
            }
            
            return results
        except Exception as e:
            current_key = get_current_tavily_key()
            if current_key and should_rotate_tavily_key(
                error_message=str(e), exception=e
            ):
                mark_tavily_key_exhausted(current_key, reason=str(e))
            logger.error(f"Error performing web search: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "results": []
            }


    async def process_chat_completion(
        self,
        messages: List[Dict[str, str]],
        *,
        allow_report_creation: bool = True,
        forced_quick_search_query: str = "",
    ):
        """Process chat completion using configured LLM provider with tool calling support"""
        forced_query = " ".join((forced_quick_search_query or "").split()).strip()
        if forced_query:
            # Once the policy selects quick_search, execution is deterministic:
            # run exactly one search, then let the answer model synthesize it.
            search_result = await asyncio.to_thread(self.quick_search, forced_query)
            evidence = json.dumps(search_result, ensure_ascii=False, default=str)[:12000]
            answer_messages = [
                *messages,
                {
                    "role": "system",
                    "content": (
                        "The policy selected a web search for this turn. Answer from "
                        "the search evidence below, mention uncertainty when evidence "
                        "is insufficient, and do not claim a report was created.\n\n"
                        f"Search query: {forced_query}\nSearch evidence: {evidence}"
                    ),
                },
            ]
            response = await create_chat_completion(
                messages=answer_messages,
                model=self.config.smart_llm_model,
                temperature=0.2,
                max_tokens=4000,
                llm_provider=self.config.smart_llm_provider,
                llm_kwargs=self.config.llm_kwargs,
            )
            return response, [
                {
                    "tool": "quick_search",
                    "query": forced_query,
                    "search_metadata": self.search_metadata,
                }
            ]

        # Create a search tool using the utility function
        search_tool = create_search_tool(self.quick_search)
        tools = [search_tool]

        if self.report_request_callback is not None and allow_report_creation:
            from langchain_core.tools import tool

            callback = self.report_request_callback

            @tool
            async def create_research_report(task: str, requirements: str = "") -> str:
                """Create a separate asynchronous report task for an explicit new report request.

                Use only when the user asks to write, generate, research, or submit a
                new report. Do not use for ordinary questions or a revision to the
                current chat reply. The report worker retrieves private knowledge first
                and decides whether web search is needed.
                """
                clean_task = " ".join((task or "").split()).strip()
                if not clean_task:
                    return json.dumps({"action": "create_report", "error": "task is required"})
                result = callback(clean_task, (requirements or "").strip())
                if hasattr(result, "__await__"):
                    result = await result
                return json.dumps(result, ensure_ascii=False)

            tools.append(create_research_report)
        
        # Use the tool-enabled chat completion utility
        response, tool_calls_metadata = await create_chat_completion_with_tools(
            messages=messages,
            tools=tools,
            model=self.config.smart_llm_model,
            llm_provider=self.config.smart_llm_provider,
            llm_kwargs=self.config.llm_kwargs,
        )
        
        # Process metadata to match the expected format for the chat system
        processed_metadata = []
        for metadata in tool_calls_metadata:
            if metadata.get("tool") == "search_tool":
                # Extract query from args
                query = metadata.get("args", {}).get("query", "")
                
                processed_metadata.append({
                    "tool": "quick_search",
                    "query": query,
                    "search_metadata": self.search_metadata
                })
            elif metadata.get("tool") == "create_research_report":
                # Tool execution metadata differs by provider.  Some models
                # return an empty/partial result even though their tool arguments
                # are correct.  The UI needs a canonical action + task to create
                # the separate report Job, so repair incomplete tool results here.
                args = metadata.get("args")
                args = args if isinstance(args, dict) else {}
                task = " ".join(str(args.get("task") or "").split()).strip()
                requirements = str(args.get("requirements") or "").strip()
                try:
                    result = json.loads(metadata.get("result") or "{}")
                except (TypeError, json.JSONDecodeError):
                    result = {}
                if not isinstance(result, dict):
                    result = {}

                if (
                    result.get("action") != "create_report"
                    and task
                    and self.report_request_callback is not None
                ):
                    logger.warning(
                        "Report tool result incomplete; rebuilding canonical report request"
                    )
                    repaired = self.report_request_callback(task, requirements)
                    if hasattr(repaired, "__await__"):
                        repaired = await repaired
                    if isinstance(repaired, dict):
                        result = repaired

                if result.get("action") == "create_report":
                    # Preserve a valid tool argument if a provider omitted it in
                    # its textual tool result.
                    if task and not str(result.get("task") or "").strip():
                        result["task"] = task
                    processed_metadata.append({
                        "tool": "create_research_report",
                        **result,
                    })
        
        return response, processed_metadata


    async def chat(
        self,
        messages,
        websocket=None,
        research_topic="",
        research_context="",
        report_language="chinese",
        research_id: str | None = None,
        tenant_id: str = "anonymous",
        user_id: str = "anonymous",
    ):
        """Chat with configured LLM provider (supports OpenAI, Google Gemini, Anthropic, etc.)
        
        Args:
            messages: List of chat messages with role and content
            websocket: Optional websocket for streaming responses
            research_topic: Original research question / report topic
            research_context: Gathered sources, sub-queries, and search snippets
            report_language: Preferred output language for chat replies (english or chinese)
            research_id: Optional session id for hybrid RAG (tenant-scoped)
            tenant_id / user_id: Isolation filters for retrieval
        
        Returns:
            tuple: (str: The AI response message, dict: metadata about tools/citations)
        """
        try:
            has_report = bool(self.report and self.report.strip())
            topic = (research_topic or "").strip()
            context = (research_context or "").strip()
            citations: list[dict] = []
            rag_degraded = False

            # Semantic understanding is separated from execution.  The router
            # returns a validated intent; the policy decides whether a report
            # side-effect may even be requested.  Permission/concurrency/budget
            # remain enforced by POST /api/jobs/research.
            from chat.intent_router import (
                apply_intent_policy,
                classify_chat_intent,
                report_creation_allowed_by_text,
                route_metadata,
            )

            latest_user = _latest_user_text(messages)
            router_model = (
                os.getenv("CHAT_INTENT_ROUTER_MODEL") or self.config.fast_llm_model
            )
            router_provider = (
                os.getenv("CHAT_INTENT_ROUTER_PROVIDER")
                or self.config.fast_llm_provider
            )
            intent = await classify_chat_intent(
                latest_message=latest_user,
                has_report=has_report,
                report_topic=topic,
                messages=list(messages or []),
                model=router_model,
                llm_provider=router_provider,
                llm_kwargs=self.config.llm_kwargs,
            )
            decision = apply_intent_policy(
                intent,
                has_report=has_report,
                report_creation_available=self.report_request_callback is not None,
                side_effects_allowed=report_creation_allowed_by_text(latest_user),
            )
            intent_meta = route_metadata(intent, decision)
            logger.info(
                "Chat intent action=%s target=%s confidence=%.3f source=%s "
                "policy=%s allow_report_side_effect=%s",
                intent.action.value,
                intent.target.value,
                intent.confidence,
                intent.source,
                decision.action,
                decision.allow_report_side_effect,
            )

            if decision.action == "clarify":
                return decision.message, intent_meta

            if decision.action == "request_report_creation":
                callback_result = self.report_request_callback(
                    decision.query or latest_user,
                    "",
                )
                if hasattr(callback_result, "__await__"):
                    callback_result = await callback_result
                if not isinstance(callback_result, dict):
                    callback_result = {}
                if callback_result.get("action") != "create_report":
                    # A failed application callback must never be presented as
                    # successful report submission.
                    failed_decision = decision.model_copy(
                        update={
                            "action": "clarify",
                            "allow_report_side_effect": False,
                            "message": (
                                "当前无法创建独立报告。我可以先在对话中帮助你梳理需求。"
                            ),
                            "reason": "report_callback_rejected",
                        }
                    )
                    return failed_decision.message, route_metadata(intent, failed_decision)
                meta = {
                    **intent_meta,
                    "tool_calls": [
                        {
                            "tool": "create_research_report",
                            **callback_result,
                        }
                    ],
                }
                return (
                    "已确认创建独立研究报告。左侧将显示任务进度；"
                    "当前对话仍可继续使用。",
                    meta,
                )

            # Hybrid RAG: FTS + vector (RRF), tenant/session scoped
            if research_id:
                try:
                    from rag.pipeline import citations_as_metadata, retrieve_for_chat

                    query_text = latest_user or topic
                    assembled = retrieve_for_chat(
                        query_text,
                        tenant_id=tenant_id or "anonymous",
                        user_id=None if user_id == "anonymous" else user_id,
                        session_id=research_id,
                        messages=list(messages or []),
                        base_context=context,
                    )
                    if assembled.evidence_block.strip():
                        context = assembled.evidence_block
                    citations = citations_as_metadata(assembled)
                    rag_degraded = bool(assembled.rag_degraded)
                except Exception as enrich_exc:
                    logger.debug("Hybrid RAG enrich skipped (non-fatal): %s", enrich_exc)
                    rag_degraded = True

            normalized_language = (report_language or "chinese").lower()
            language_label = "Chinese" if normalized_language in ("chinese", "zh", "zh-cn", "zh-tw") else "English"

            if decision.action == "quick_search":
                routing_note = (
                    "The intent router selected quick_search. Use quick_search before "
                    "answering, and do not create a report."
                )
            elif has_report and decision.reason == "current_report_operation":
                routing_note = (
                    "The intent router selected the current report. Answer, summarize, "
                    "translate, rewrite, explain, or extract directly in chat. Do not "
                    "create a separate report."
                )
            else:
                routing_note = (
                    "The intent router selected an in-chat response. Answer directly; "
                    "use quick_search only if fresh external information is needed. "
                    "Do not create a separate report."
                )

            if has_report:
                context_section = f"""
            Research topic: {topic or "Not specified"}

            Research report:
            {self.report}

            Full session context (preparation conversation, sources, notes, prior searches):
            {context or "None"}
            """
                phase_note = "The user has a completed research report and is continuing the conversation in chat."
                material_list = """
            - The completed research report
            - The original research topic and ALL preparation conversation before the report was generated
            - Research context (sources, sub-queries, gathered notes, prior web search snippets)
            - Recent dialogue plus retrieved relevant historical memory"""
            else:
                context_section = f"""
            Research topic (main report question):
            {topic or "Not specified — infer from conversation if possible"}

            Preparation conversation and gathered context:
            {context or "None yet"}
            """
                phase_note = "The user is preparing a research report. No final report has been generated yet."
                material_list = """
            - The research topic (main report question) — this is what the report will be about
            - Every user refinement in the preparation conversation (e.g. time range, scope, angle) — treat these as constraints ON the research topic, not separate unrelated questions
            - Recent dialogue plus retrieved relevant historical memory
            - Any prior research context (sources, sub-queries, web search snippets from earlier chat)"""

            system_prompt = f"""
            You are GPT Researcher, an autonomous research agent created by an open source community at https://github.com/assafelovic/gpt-researcher, homepage: https://gptr.dev.
            To learn more about GPT Researcher you can suggest to check out: https://docs.gptr.dev.

            {phase_note}

            A separate structured intent router has already decided whether this turn may
            create a research Job. New-report requests are handled before this response call,
            so you must not claim that a report was created or submitted here.

            Turn routing policy:
            {routing_note}

            For normal chat questions, use quick_search whenever live web search would help:
            current events, missing facts, verification, statistics, or anything not fully
            covered by the material below.

            Your job is to give the best possible answer to the user's latest question.
            Look across ALL available material and pick what is most relevant:
            {material_list}
            - Live web results via quick_search (always available)

            Prefer existing report/context when it already answers the question; supplement or override with
            quick_search when fresher or more complete web information is needed.

            Do NOT answer from the latest message alone. Synthesize a direct, helpful chat reply — not a new report.
            When the user adds a short refinement (e.g. "last two years only", "我要近两年的"), combine it with the research topic and answer about that combined intent.

            When Retrieved evidence is present, ground claims in those Child passages only.
            Cite using chunk_id and page/url when available (e.g. [chunk_id=... page=...]).
            If evidence is insufficient or conflicting, explicitly say you are uncertain — do not invent facts.

            Respond in {language_label} only. Match the user's selected report output language even if they write in another language.

            Assume the current time is: {datetime.now()}.

            {context_section}
            """
            
            # Format message history for OpenAI input
            formatted_messages = []
            
            # Add system message first
            formatted_messages.append({
                "role": "system", 
                "content": system_prompt
            })
            
            # Add user/assistant message history - filter out non-essential fields
            for msg in _messages_for_model(messages, research_id=research_id):
                if 'role' in msg and 'content' in msg:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                else:
                    logger.warning(f"Skipping message with missing role or content: {msg}")
            
            # Process the chat using configured LLM provider
            ai_message, tool_calls_metadata = await self.process_chat_completion(
                formatted_messages,
                allow_report_creation=False,
                forced_quick_search_query=(
                    decision.query if decision.action == "quick_search" else ""
                ),
            )

            # process_chat_completion returns a list of tool metadatas — never dict(). :-)
            tool_calls: list[dict] = []
            if isinstance(tool_calls_metadata, list):
                tool_calls = [t for t in tool_calls_metadata if isinstance(t, dict)]
            elif isinstance(tool_calls_metadata, dict):
                nested = tool_calls_metadata.get("tool_calls")
                if isinstance(nested, list):
                    tool_calls = [t for t in nested if isinstance(t, dict)]
                elif tool_calls_metadata.get("tool"):
                    tool_calls = [tool_calls_metadata]

            # Provide fallback response if message is empty
            if not ai_message:
                logger.warning("No AI message content found in response, using fallback message")
                ai_message = "I apologize, but I couldn't generate a proper response. Please try asking your question again."
            
            logger.info(f"Generated response: {ai_message[:100]}..." if len(ai_message) > 100 else f"Generated response: {ai_message}")

            meta: dict[str, Any] = dict(intent_meta)
            if tool_calls:
                meta["tool_calls"] = tool_calls
            if citations:
                meta["citations"] = citations
            if rag_degraded:
                meta["rag_degraded"] = True
            return ai_message, meta or None
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            raise

    def get_context(self):
        """return the current context of the chat"""
        return self.report
