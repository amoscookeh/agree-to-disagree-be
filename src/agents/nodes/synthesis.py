from datetime import UTC, datetime

from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from src.agents.llm import llm
from src.agents.state import AgentState, Draft
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


SYNTHESIS_FROM_DRAFTS_PROMPT = """you are a balanced political analyst synthesizing research from multiple drafts.

original query: {query}

you have collected {draft_count} research drafts covering different angles of this topic.
each draft explored a specific sub-question and gathered evidence from relevant sources.

RESEARCH DRAFTS:
{drafts_summary}

ALL SOURCES FOUND:
LEFT-LEANING SOURCES:
{left_results}

RIGHT-LEANING SOURCES:
{right_results}

your task is to create a comprehensive, balanced report that:
1. synthesizes findings from all drafts into a coherent narrative
2. presents the strongest evidence for each perspective
3. identifies where perspectives agree and disagree
4. acknowledges uncertainties and data limitations
5. cites all sources used

respond with:
- summary: comprehensive overview of the debate (3-5 sentences)
- claim_a: the progressive/liberal perspective with evidence
- claim_b: the conservative perspective with evidence
- agreements: points where both sides agree
- disagreements: specific points of contention with positions and reasons
- uncertainties: areas where data is weak or conflicting
"""


def _emit_progress(
    writer, agent: str, status: str, message: str, details: dict | None = None, **extra
):
    event = {
        "type": "progress",
        "data": {
            "agent": agent,
            "status": status,
            "message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            **({"details": details} if details else {}),
            **extra,
        },
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


def _format_drafts_summary(drafts: list[Draft]) -> str:
    if not drafts:
        return "No drafts available"

    summaries = []
    for d in drafts:
        summaries.append(
            f"### Draft: {d.get('sub_query', 'Unknown')}\n"
            f"Angle: {d.get('angle', 'unknown')}\n"
            f"Summary: {d.get('summary', 'N/A')}\n"
            f"Key Findings:\n"
            + "\n".join(f"  - {f}" for f in d.get("key_findings", []))
        )
    return "\n\n".join(summaries)


def _collect_all_results(drafts: list[Draft]) -> tuple[list[dict], list[dict]]:
    left_results = []
    right_results = []
    seen_urls: set[str] = set()

    for draft in drafts:
        for r in draft.get("left_results", []):
            url = r.get("url", "")
            if url and url not in seen_urls:
                left_results.append(r)
                seen_urls.add(url)

        for r in draft.get("right_results", []):
            url = r.get("url", "")
            if url and url not in seen_urls:
                right_results.append(r)
                seen_urls.add(url)

    return left_results, right_results


def _extract_citations(report: SynthesisReport) -> list[dict]:
    citations = []
    seen_urls: set[str] = set()

    for evidence in report.claim_a.evidence:
        if evidence.url not in seen_urls:
            citations.append(
                {
                    "source": evidence.source,
                    "url": evidence.url,
                    "claim": evidence.claim,
                    "confidence": evidence.confidence,
                    "perspective": "left",
                }
            )
            seen_urls.add(evidence.url)

    for evidence in report.claim_b.evidence:
        if evidence.url not in seen_urls:
            citations.append(
                {
                    "source": evidence.source,
                    "url": evidence.url,
                    "claim": evidence.claim,
                    "confidence": evidence.confidence,
                    "perspective": "right",
                }
            )
            seen_urls.add(evidence.url)

    return citations


async def synthesis_node(state: AgentState) -> dict:
    writer = get_stream_writer()
    query = state.get("refined_query") or state.get("query", "")
    drafts = state.get("drafts", [])
    cycles_used = state.get("supervisor_cycle", 1)

    left_results, right_results = _collect_all_results(drafts)
    total_results = len(left_results) + len(right_results)

    _emit_progress(
        writer,
        "synthesis",
        "starting",
        f"synthesizing final report from {len(drafts)} drafts...",
        details={
            "drafts_count": len(drafts),
            "left_sources": len(left_results),
            "right_sources": len(right_results),
            "total_sources": total_results,
            "cycles_used": cycles_used,
        },
    )

    if not drafts and total_results == 0:
        logger.warning("synthesis called with no drafts or results")
        _emit_progress(
            writer,
            "synthesis",
            "error",
            "No research results to synthesize",
            details={"error": "empty results", "query": query},
        )

        return {
            "error": "no research results to synthesize",
            "report": None,
        }

    _emit_progress(
        writer,
        "synthesis",
        "processing",
        "combining perspectives from research drafts",
        details={
            "drafts_count": len(drafts),
            "stage": "draft_combination",
        },
    )

    _emit_progress(
        writer,
        "synthesis",
        "analyzing",
        "generating balanced analysis with LLM",
        details={
            "model": "structured output",
            "task": "synthesize from drafts",
        },
    )

    prompt = SYNTHESIS_FROM_DRAFTS_PROMPT.format(
        query=query,
        draft_count=len(drafts),
        drafts_summary=_format_drafts_summary(drafts),
        left_results=_format_results(left_results),
        right_results=_format_results(right_results),
    )

    try:
        structured_llm = llm.with_structured_output(SynthesisReport)
        result = await structured_llm.ainvoke(prompt)
        report = SynthesisReport.model_validate(result)
        citations = _extract_citations(report)

        logger.info(
            f"synthesis complete: {len(report.agreements)} agreements, "
            f"{len(report.disagreements)} disagreements, {len(citations)} citations, "
            f"{len(drafts)} drafts, {cycles_used} cycles"
        )

        _emit_progress(
            writer,
            "synthesis",
            "complete",
            f"report generated with {len(citations)} citations",
            details={
                "citation_count": len(citations),
                "agreements_found": len(report.agreements),
                "disagreements_found": len(report.disagreements),
                "uncertainties_noted": len(report.uncertainties),
                "cycles_used": cycles_used,
                "drafts_synthesized": len(drafts),
            },
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
            "metadata": {
                "cycles_used": cycles_used,
                "drafts_synthesized": len(drafts),
            },
        }

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
        _emit_progress(
            writer,
            "synthesis",
            "error",
            "Synthesis failed",
            details={"error": str(e), "query": query},
        )

        return {
            "error": str(e),
            "report": None,
            "current_agent": "synthesis",
        }
