import asyncio
import hashlib
import logging
import os
import time
from typing import List, Dict, Set, Optional, Any
from fastapi import WebSocket

from gpt_researcher import GPTResearcher

logger = logging.getLogger(__name__)


def _chapter_max_attempts() -> int:
    raw = (os.getenv("RESEARCH_CHAPTER_MAX_ATTEMPTS") or "2").strip()
    try:
        return max(1, min(5, int(raw)))
    except ValueError:
        return 2


def _chapter_parallelism() -> int:
    """Max concurrent chapter research tasks (writes stay ordered). :-)"""
    raw = (os.getenv("RESEARCH_CHAPTER_PARALLELISM") or "2").strip()
    try:
        return max(1, min(4, int(raw)))
    except ValueError:
        return 2


class DetailedReport:
    def __init__(
        self,
        query: str,
        report_type: str,
        report_source: str,
        source_urls: List[str] = [],
        document_urls: List[str] = [],
        query_domains: List[str] = [],
        config_path: str = None,
        tone: Any = "",
        websocket: WebSocket = None,
        subtopics: List[Dict] = [],
        headers: Optional[Dict] = None,
        complement_source_urls: bool = False,
        mcp_configs=None,
        mcp_strategy=None,
        max_search_results=None,
        total_words=None,
        report_language=None,
        documents=None,
    ):
        self.query = query
        self.report_type = report_type
        self.report_source = report_source
        self.source_urls = source_urls
        self.document_urls = document_urls
        self.query_domains = query_domains
        self.config_path = config_path
        self.tone = tone
        self.websocket = websocket
        self.subtopics = subtopics
        self.headers = headers or {}
        self.complement_source_urls = complement_source_urls
        self.max_search_results = max_search_results
        self.total_words = total_words
        self.research_id = self._generate_research_id(query)
        
        # Initialize researcher with optional MCP parameters
        gpt_researcher_params = {
            "query": self.query,
            "query_domains": self.query_domains,
            "report_type": "research_report",
            "report_source": self.report_source,
            "source_urls": self.source_urls,
            "document_urls": self.document_urls,
            "config_path": self.config_path,
            "tone": self.tone,
            "websocket": self.websocket,
            "headers": self.headers,
            "complement_source_urls": self.complement_source_urls,
            "documents": documents,
        }

        # Add MCP parameters if provided
        if mcp_configs is not None:
            gpt_researcher_params["mcp_configs"] = mcp_configs
        if mcp_strategy is not None:
            gpt_researcher_params["mcp_strategy"] = mcp_strategy

        self.gpt_researcher = GPTResearcher(**gpt_researcher_params)

        # Override max_search_results_per_query if provided by user
        if max_search_results is not None:
            self.gpt_researcher.cfg.max_search_results_per_query = int(max_search_results)
        if total_words is not None:
            self.gpt_researcher.cfg.total_words = int(total_words)
        if report_language is not None:
            self.gpt_researcher.cfg.report_language = str(report_language).lower()
        self.existing_headers: List[Dict] = []
        self.global_context: List[str] = []
        self.global_written_sections: List[str] = []
        self.global_urls: Set[str] = set(
            self.source_urls) if self.source_urls else set()

    def _generate_research_id(self, query: str) -> str:
        """Generate a unique research ID from query and timestamp."""
        timestamp = str(int(time.time()))
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"detailed_{timestamp}_{query_hash}"

    async def run(self) -> str:
        await self._initial_research()
        subtopics = await self._get_all_subtopics()
        try:
            from jobs.runtime import check_abort, get_abort_runtime

            await check_abort(where="pre_subtopics")
            runtime = get_abort_runtime()
            if runtime is not None and runtime.budget is not None:
                subtopics = runtime.budget.clamp_subtopics(subtopics)
        except ImportError:
            pass
        report_introduction = await self._load_or_write_introduction()
        _, report_body = await self._generate_subtopic_reports(subtopics)
        self.gpt_researcher.visited_urls.update(self.global_urls)
        report = await self._construct_detailed_report(report_introduction, report_body)
        return report

    async def _initial_research(self) -> None:
        await self.gpt_researcher.conduct_research()
        self.global_context = self.gpt_researcher.context
        self.global_urls = self.gpt_researcher.visited_urls

    async def _get_all_subtopics(self) -> List[Dict]:
        subtopics_data = await self.gpt_researcher.get_subtopics()

        all_subtopics = []
        if subtopics_data and subtopics_data.subtopics:
            for subtopic in subtopics_data.subtopics:
                all_subtopics.append({"task": subtopic.task})
        else:
            print(f"Unexpected subtopics data format: {subtopics_data}")

        return all_subtopics

    async def _load_or_write_introduction(self) -> str:
        """Reuse checkpointed introduction when present."""
        try:
            from jobs import get_job
            from jobs.runtime import get_abort_runtime

            runtime = get_abort_runtime()
            if runtime is not None:
                job = await get_job(runtime.job_id) or {}
                cp = job.get("checkpoint_json") or {}
                intro = cp.get("introduction")
                if isinstance(intro, str) and intro.strip():
                    logger.info("Resuming from checkpointed introduction")
                    return intro
        except Exception:
            pass

        introduction = await self.gpt_researcher.write_introduction()
        await self._checkpoint_update(introduction=introduction or "")
        return introduction or ""

    async def _checkpoint_update(self, **fields) -> None:
        try:
            from jobs.runtime import get_abort_runtime

            runtime = get_abort_runtime()
            if runtime is not None:
                await runtime.save_checkpoint(**fields)
        except Exception as exc:
            logger.debug("chapter checkpoint skipped: %s", exc)

    async def _load_chapter_checkpoints(self) -> dict:
        try:
            from jobs import get_job
            from jobs.runtime import get_abort_runtime

            runtime = get_abort_runtime()
            if runtime is None:
                return {}
            job = await get_job(runtime.job_id) or {}
            cp = job.get("checkpoint_json") or {}
            chapters = cp.get("chapters") or {}
            return chapters if isinstance(chapters, dict) else {}
        except Exception:
            return {}

    async def _generate_subtopic_reports(self, subtopics: List[Dict]) -> tuple:
        """Research chapters in parallel; write in order for section dedup. :-)"""
        subtopic_reports = []
        subtopics_report_body = ""
        chapters = await self._load_chapter_checkpoints()
        max_attempts = _chapter_max_attempts()
        parallelism = _chapter_parallelism()
        pending: List[tuple[int, Dict]] = []
        cached_reports: Dict[int, Dict] = {}

        for idx, subtopic in enumerate(subtopics):
            task = (subtopic.get("task") or "").strip()
            key = str(idx)
            cached = chapters.get(key) or {}
            if (
                cached.get("status") == "completed"
                and cached.get("report")
                and cached.get("task") == task
            ):
                logger.info("Skipping completed chapter %s from checkpoint", idx)
                cached_reports[idx] = {"topic": subtopic, "report": cached["report"]}
            else:
                pending.append((idx, subtopic))

        researched: Dict[int, Any] = {}
        research_errors: Dict[int, str] = {}
        research_attempts: Dict[int, int] = {}

        if pending:
            sem = asyncio.Semaphore(parallelism)
            logger.info(
                "Researching %s chapter(s) with parallelism=%s",
                len(pending),
                parallelism,
            )

            async def _research_with_retry(idx: int, subtopic: Dict):
                task = (subtopic.get("task") or "").strip()
                last_err = None
                async with sem:
                    try:
                        from jobs.runtime import check_abort

                        await check_abort(where=f"pre_chapter_research:{task[:40]}")
                    except ImportError:
                        pass

                    for attempt in range(1, max_attempts + 1):
                        try:
                            assistant = await self._research_subtopic(subtopic)
                            if assistant is not None:
                                return idx, assistant, attempt, None
                            last_err = "empty_chapter_research"
                        except Exception as exc:
                            last_err = str(exc)
                            logger.warning(
                                "Chapter %s research attempt %s/%s failed: %s",
                                idx, attempt, max_attempts, exc,
                            )
                            try:
                                from jobs.runtime import get_abort_runtime

                                runtime = get_abort_runtime()
                                if runtime is not None:
                                    runtime.record_llm_event(
                                        "chapter_retry",
                                        chapter=idx,
                                        task=task[:120],
                                        attempt=attempt,
                                        error=str(exc)[:300],
                                    )
                            except Exception:
                                pass
                            if attempt < max_attempts:
                                await asyncio.sleep(min(2 ** (attempt - 1), 8))
                return idx, None, max_attempts, last_err or "unknown"

            gathered = await asyncio.gather(
                *[_research_with_retry(i, s) for i, s in pending]
            )
            for idx, assistant, attempt, err in gathered:
                research_attempts[idx] = attempt
                if assistant is not None:
                    researched[idx] = assistant
                else:
                    research_errors[idx] = err or "unknown"

        for idx, subtopic in enumerate(subtopics):
            task = (subtopic.get("task") or "").strip()
            key = str(idx)

            if idx in cached_reports:
                result = cached_reports[idx]
                subtopic_reports.append(result)
                subtopics_report_body += f"\n\n\n{result['report']}"
                self.global_written_sections.extend(
                    self.gpt_researcher.extract_sections(result["report"])
                )
                self.existing_headers.append({
                    "subtopic task": task,
                    "headers": self.gpt_researcher.extract_headers(result["report"]),
                })
                continue

            assistant = researched.get(idx)
            if assistant is None:
                chapters[key] = {
                    "task": task,
                    "status": "failed",
                    "error": (research_errors.get(idx) or "unknown")[:500],
                    "attempts": research_attempts.get(idx, max_attempts),
                }
                logger.error(
                    "Chapter %s failed after %s attempts — continuing without it",
                    idx, research_attempts.get(idx, max_attempts),
                )
                await self._checkpoint_update(
                    chapters=chapters,
                    writing_progress={"chapter_index": idx, "total": len(subtopics)},
                )
                continue

            try:
                from jobs.runtime import check_abort

                await check_abort(where=f"pre_chapter_write:{task[:40]}")
            except ImportError:
                pass

            result = None
            last_err = None
            attempt = research_attempts.get(idx, 1)
            try:
                result = await self._write_subtopic_report(subtopic, assistant)
                if not result.get("report"):
                    last_err = "empty_chapter_report"
                    result = None
            except Exception as exc:
                last_err = str(exc)
                logger.warning("Chapter %s write failed: %s", idx, exc)

            if result and result.get("report"):
                subtopic_reports.append(result)
                subtopics_report_body += f"\n\n\n{result['report']}"
                chapters[key] = {
                    "task": task,
                    "status": "completed",
                    "report": result["report"],
                    "attempts": attempt,
                }
            else:
                chapters[key] = {
                    "task": task,
                    "status": "failed",
                    "error": (last_err or "unknown")[:500],
                    "attempts": attempt,
                }
                logger.error("Chapter %s write failed — continuing without it", idx)

            await self._checkpoint_update(
                chapters=chapters,
                writing_progress={"chapter_index": idx, "total": len(subtopics)},
            )

        return subtopic_reports, subtopics_report_body

    def _hashable_context(self, input_context: List[str] | List[dict]):
        # Convert context to strings to ensure hashability (handle both strings and dicts from MCP)
        context_items = []
        
        for item in input_context:
            if isinstance(item, dict):
                # Convert dict context to string format
                title = item.get("title", "No title")
                content = item.get("body", item.get("content", ""))
                context_str = f"Title: {title}\nContent: {content}"
                context_items.append(context_str)
            else:
                context_items.append(str(item))
        
        return context_items

    def _build_subtopic_assistant(self, subtopic: Dict) -> GPTResearcher:
        current_subtopic_task = subtopic.get("task")
        # Snapshot URLs so parallel chapter research does not race. :-)
        seed_urls = set(self.global_urls)
        subtopic_assistant = GPTResearcher(
            query=current_subtopic_task,
            query_domains=self.query_domains,
            report_type="subtopic_report",
            report_source=self.report_source,
            websocket=self.websocket,
            headers=self.headers,
            parent_query=self.query,
            subtopics=self.subtopics,
            visited_urls=seed_urls,
            agent=self.gpt_researcher.agent,
            role=self.gpt_researcher.role,
            tone=self.tone,
            complement_source_urls=self.complement_source_urls,
            source_urls=self.source_urls,
            mcp_configs=self.gpt_researcher.mcp_configs,
            mcp_strategy=self.gpt_researcher.mcp_strategy,
        )
        if self.max_search_results is not None:
            subtopic_assistant.cfg.max_search_results_per_query = int(self.max_search_results)
        if self.total_words is not None:
            subtopic_assistant.cfg.total_words = int(self.total_words)
        subtopic_assistant.context = list(set(self._hashable_context(self.global_context)))
        return subtopic_assistant

    async def _research_subtopic(self, subtopic: Dict) -> GPTResearcher:
        subtopic_assistant = self._build_subtopic_assistant(subtopic)
        await subtopic_assistant.conduct_research()
        return subtopic_assistant

    async def _write_subtopic_report(
        self, subtopic: Dict, subtopic_assistant: GPTResearcher
    ) -> Dict[str, str]:
        current_subtopic_task = subtopic.get("task")
        draft_section_titles = await subtopic_assistant.get_draft_section_titles(
            current_subtopic_task
        )
        if not isinstance(draft_section_titles, str):
            draft_section_titles = str(draft_section_titles)

        parse_draft_section_titles = self.gpt_researcher.extract_headers(draft_section_titles)
        parse_draft_section_titles_text = [
            header.get("text", "") for header in parse_draft_section_titles
        ]
        relevant_contents = await subtopic_assistant.get_similar_written_contents_by_draft_section_titles(
            current_subtopic_task,
            parse_draft_section_titles_text,
            self.global_written_sections,
        )
        subtopic_report = await subtopic_assistant.write_report(
            existing_headers=self.existing_headers,
            relevant_written_contents=relevant_contents,
        )

        self.gpt_researcher.add_research_sources(
            subtopic_assistant.get_research_sources()
        )
        self.global_written_sections.extend(
            self.gpt_researcher.extract_sections(subtopic_report)
        )
        self.global_context = list(
            set(
                self._hashable_context(self.global_context)
                + self._hashable_context(subtopic_assistant.context)
            )
        )
        self.global_urls.update(subtopic_assistant.visited_urls)
        self.existing_headers.append({
            "subtopic task": current_subtopic_task,
            "headers": self.gpt_researcher.extract_headers(subtopic_report),
        })
        return {"topic": subtopic, "report": subtopic_report}

    async def _get_subtopic_report(self, subtopic: Dict) -> Dict[str, str]:
        assistant = await self._research_subtopic(subtopic)
        return await self._write_subtopic_report(subtopic, assistant)

    async def _construct_detailed_report(self, introduction: str, report_body: str) -> str:
        toc = self.gpt_researcher.table_of_contents(report_body)
        conclusion = await self.gpt_researcher.write_report_conclusion(report_body)
        conclusion_with_references = self.gpt_researcher.add_references(
            conclusion, self.gpt_researcher.visited_urls)
        report = f"{introduction}\n\n{toc}\n\n{report_body}\n\n{conclusion_with_references}"
        
        # Note: Images are now pre-generated during conduct_research() and embedded during write_report()
        return report
