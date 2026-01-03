"""test script for parallel sub-query execution"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.graph import build_research_graph
from src.utils.logger import logger


async def test_parallel_execution():
    """test that sub-queries execute in parallel within a single cycle"""
    print("\n=== Testing Parallel Sub-Query Execution ===\n")

    graph = build_research_graph()

    test_query = "What are perspectives on universal healthcare?"

    print(f"Query: {test_query}\n")
    print("Starting research...\n")

    config = {"configurable": {"thread_id": "test-parallel-execution"}}

    try:
        result = await graph.ainvoke(
            {
                "query": test_query,
                "thread_id": "test-parallel-execution",
                "clarification_response": "I'm asking about federal universal healthcare proposals in the US",
            },
            config,
        )

        cycles_used = result.get("supervisor_cycle", 0)
        drafts = result.get("drafts", [])
        sub_queries = result.get("sub_queries", [])

        print("\n=== Results ===\n")
        print(f"Supervisor cycles used: {cycles_used}")
        print(f"Total sub-queries generated: {len(sub_queries)}")
        print(f"Total drafts collected: {len(drafts)}")

        print("\n=== Sub-Queries ===")
        for sq in sub_queries:
            print(f"  - [{sq['angle']}] {sq['query']}")

        print("\n=== Drafts ===")
        for draft in drafts:
            print(f"  - {draft['sub_query_id']}: {draft['summary'][:80]}...")
            print(f"    Findings: {len(draft['key_findings'])}")
            print(f"    Sources: {draft['sources_count']}")

        report = result.get("report")
        if report:
            print("\n=== Report Generated ===")
            print(f"Summary: {report.get('summary', '')[:150]}...")
            print(
                f"Metadata: {report.get('metadata', {}).get('cycles_used', 0)} cycles, "
                f"{report.get('metadata', {}).get('drafts_synthesized', 0)} drafts"
            )

        print("\n=== Test Validation ===")
        if len(sub_queries) > 1 and cycles_used <= 3:
            print(
                f"✓ PASS: Generated {len(sub_queries)} sub-queries and completed in {cycles_used} cycles"
            )
        else:
            print(
                f"✗ FAIL: Expected multiple sub-queries and ≤3 cycles, got {len(sub_queries)} queries, {cycles_used} cycles"
            )

        if len(drafts) == len(sub_queries):
            print(f"✓ PASS: All {len(sub_queries)} sub-queries produced drafts")
        else:
            print(
                f"✗ FAIL: Expected {len(sub_queries)} drafts, got {len(drafts)} drafts"
            )

    except Exception as e:
        logger.error(f"test failed: {e}", exc_info=True)
        print(f"\n✗ FAIL: {e}")
        return False

    return True


if __name__ == "__main__":
    success = asyncio.run(test_parallel_execution())
    sys.exit(0 if success else 1)
