from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from src.agents.llm import llm
from src.agents.prompts import SYNTHESIS_PROMPT
from src.agents.state import AgentState
from src.utils.logger import logger


class Evidence(BaseModel):
    claim: str
    source: str
    url: str
    confidence: float = Field(ge=0.0, le=1.0)


class ClaimPerspective(BaseModel):
    stance: str
    title: str
    evidence: list[Evidence]


class Disagreement(BaseModel):
    topic: str
    left_position: str
    right_position: str
    reason: str


class SynthesisReport(BaseModel):
    summary: str
    claim_a: ClaimPerspective
    claim_b: ClaimPerspective
    agreements: list[str]
    disagreements: list[Disagreement]
    uncertainties: list[str]


def _emit_progress(writer, agent: str, status: str, message: str, **extra):
    event = {
        "type": "progress",
        "agent": agent,
        "status": status,
        "message": message,
        "timestamp": datetime.now(UTC).isoformat(),
        **extra,
    }
    if writer:
        writer(event)
    return event


def _format_results(results: list[dict]) -> str:
    if not results:
        return "No results available"

    formatted = []
    for r in results:
        formatted.append(
            f"- Title: {r.get('title', 'Unknown')}\n"
            f"  Source: {r.get('source_name', 'Unknown')}\n"
            f"  URL: {r.get('url', 'N/A')}\n"
            f"  Snippet: {r.get('snippet', 'N/A')}\n"
            f"  Published: {r.get('published_date', 'Unknown')}"
        )
    return "\n".join(formatted)


def _extract_citations(report: SynthesisReport) -> list[dict]:
    citations = []
    seen_urls = set()

    for evidence in report.claim_a.evidence:
        if evidence.url not in seen_urls:
            citations.append({
                "source": evidence.source,
                "url": evidence.url,
                "claim": evidence.claim,
                "confidence": evidence.confidence,
                "perspective": "left",
            })
            seen_urls.add(evidence.url)

    for evidence in report.claim_b.evidence:
        if evidence.url not in seen_urls:
            citations.append({
                "source": evidence.source,
                "url": evidence.url,
                "claim": evidence.claim,
                "confidence": evidence.confidence,
                "perspective": "right",
            })
            seen_urls.add(evidence.url)

    return citations


async def synthesis_node(state: AgentState) -> dict:
    writer = get_stream_writer()
    query = state.get("refined_query") or state.get("query", "")

    left_results = state.get("left_results", [])
    right_results = state.get("right_results", [])
    academic_results = state.get("academic_results", [])

    total_results = len(left_results) + len(right_results) + len(academic_results)

    _emit_progress(
        writer,
        "synthesis",
        "starting",
        f"Synthesizing report from {total_results} sources...",
    )

    if total_results == 0:
        logger.warning("synthesis called with no research results")
        _emit_progress(writer, "synthesis", "error", "No research results to synthesize")

        return {
            "error": "no research results to synthesize",
            "report": None,
        }

    _emit_progress(
        writer,
        "synthesis",
        "analyzing",
        "Generating balanced analysis with LLM...",
    )

    prompt = SYNTHESIS_PROMPT.format(
        query=query,
        left_results=_format_results(left_results),
        right_results=_format_results(right_results),
        academic_results=_format_results(academic_results),
    )

    try:
        structured_llm = llm.with_structured_output(SynthesisReport)
        report: SynthesisReport = await structured_llm.ainvoke(prompt)
        citations = _extract_citations(report)

        logger.info(
            f"synthesis complete: {len(report.agreements)} agreements, "
            f"{len(report.disagreements)} disagreements, {len(citations)} citations"
        )

        _emit_progress(
            writer,
            "synthesis",
            "complete",
            f"Report generated with {len(citations)} citations",
            citation_count=len(citations),
        )

        report_dict = {
            "summary": report.summary,
            "claim_a": {
                "stance": report.claim_a.stance,
                "title": report.claim_a.title,
                "evidence": [e.model_dump() for e in report.claim_a.evidence],
            },
            "claim_b": {
                "stance": report.claim_b.stance,
                "title": report.claim_b.title,
                "evidence": [e.model_dump() for e in report.claim_b.evidence],
            },
            "agreements": report.agreements,
            "disagreements": [d.model_dump() for d in report.disagreements],
            "uncertainties": report.uncertainties,
        }

        _emit_progress(
            writer,
            "report",
            "complete",
            "Research report ready",
            report=report_dict,
        )

        return {
            "summary": report.summary,
            "claim_a": report_dict["claim_a"],
            "claim_b": report_dict["claim_b"],
            "agreements": report.agreements,
            "disagreements": report_dict["disagreements"],
            "uncertainties": report.uncertainties,
            "citations": citations,
            "report": report_dict,
            "current_agent": "synthesis",
        }

    except Exception as e:
        logger.error(f"synthesis failed: {e}")
        _emit_progress(writer, "synthesis", "error", f"Synthesis failed: {e!s}")

        return {
            "error": str(e),
            "report": None,
            "current_agent": "synthesis",
        }

