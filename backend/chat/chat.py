import logging
import os
import uuid
import json
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
        vector_store=None
    ):
        self.report = report
        self.headers = headers
        self.config = Config(config_path)
        self.vector_store = vector_store
        self.retriever = None
        self.search_metadata = None
        
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


    async def process_chat_completion(self, messages: List[Dict[str, str]]):
        """Process chat completion using configured LLM provider with tool calling support"""
        # Create a search tool using the utility function
        search_tool = create_search_tool(self.quick_search)
        
        # Use the tool-enabled chat completion utility
        response, tool_calls_metadata = await create_chat_completion_with_tools(
            messages=messages,
            tools=[search_tool],
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
                
                # Trigger search again to get metadata (the search was already executed by LangChain)
                if query:
                    self.quick_search(query)  # This populates self.search_metadata
                    
                processed_metadata.append({
                    "tool": "quick_search",
                    "query": query,
                    "search_metadata": self.search_metadata
                })
        
        return response, processed_metadata


    async def chat(self, messages, websocket=None, research_topic="", research_context=""):
        """Chat with configured LLM provider (supports OpenAI, Google Gemini, Anthropic, etc.)
        
        Args:
            messages: List of chat messages with role and content
            websocket: Optional websocket for streaming responses
            research_topic: Original research question / report topic
            research_context: Gathered sources, sub-queries, and search snippets
        
        Returns:
            tuple: (str: The AI response message, dict: metadata about tool usage)
        """
        try:
            has_report = bool(self.report and self.report.strip())
            topic = (research_topic or "").strip()
            context = (research_context or "").strip()

            if has_report:
                context_section = f"""
            Research topic: {topic or "Not specified"}

            Research report:
            {self.report}

            Additional research context:
            {context or "None"}
            """
                phase_note = "The user has a completed research report and is continuing the conversation in chat."
                material_list = """
            - The completed research report
            - Research context (sources, sub-queries, gathered notes, prior web search snippets)
            - The full conversation history"""
            else:
                context_section = f"""
            Research topic (main report question):
            {topic or "Not specified — infer from conversation if possible"}

            Prior research context (if any):
            {context or "None yet"}
            """
                phase_note = "The user is preparing a research report. No final report has been generated yet."
                material_list = """
            - The research topic (main report question)
            - The full conversation history
            - Any prior research context (sources, sub-queries, web search snippets from earlier chat)"""

            system_prompt = f"""
            You are GPT Researcher, an autonomous research agent created by an open source community at https://github.com/assafelovic/gpt-researcher, homepage: https://gptr.dev.
            To learn more about GPT Researcher you can suggest to check out: https://docs.gptr.dev.

            {phase_note}

            You ALWAYS have the quick_search tool for live web search — before or after a report is generated.
            Use it whenever web search would help answer better: current events, missing facts, verification,
            statistics, or anything not fully covered by the material below. Do not wait until other sources fail.

            Your job is to give the best possible answer to the user's latest question.
            Look across ALL available material and pick what is most relevant:
            {material_list}
            - Live web results via quick_search (always available)

            Prefer existing report/context when it already answers the question; supplement or override with
            quick_search when fresher or more complete web information is needed.

            Do NOT answer from the latest message alone. Synthesize a direct, helpful chat reply — not a new report.

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
            for msg in messages:
                if 'role' in msg and 'content' in msg:
                    formatted_messages.append({
                        "role": msg["role"],
                        "content": msg["content"]
                    })
                else:
                    logger.warning(f"Skipping message with missing role or content: {msg}")
            
            # Process the chat using configured LLM provider
            ai_message, tool_calls_metadata = await self.process_chat_completion(formatted_messages)
            
            # Provide fallback response if message is empty
            if not ai_message:
                logger.warning("No AI message content found in response, using fallback message")
                ai_message = "I apologize, but I couldn't generate a proper response. Please try asking your question again."
            
            logger.info(f"Generated response: {ai_message[:100]}..." if len(ai_message) > 100 else f"Generated response: {ai_message}")
            
            # Return both the message and any metadata about tools used
            return ai_message, tool_calls_metadata
            
        except Exception as e:
            logger.error(f"Error in chat: {str(e)}", exc_info=True)
            raise

    def get_context(self):
        """return the current context of the chat"""
        return self.report
