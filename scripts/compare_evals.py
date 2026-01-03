#!/usr/bin/env python3
import json
import sys

def load_results(path: str) -> list[dict]:
    with open(path) as f:
        return json.load(f)


def get_query_scores(results: list[dict]) -> dict[str, dict]:
    scores = {}
    for result in results:
        query = result.get("query")
        if not query:
            continue

        if "error" in result:
            scores[query] = {"error": result["error"]}
        elif "scores" in result:
            scores[query] = {
                "balance": result["scores"]["balance"]["score"],
                "groundedness": result["scores"]["groundedness"]["score"],
                "citation": result["scores"]["citation"]["score"],
                "average": result["scores"]["average"],
            }
    return scores


def compare_results(file1: str, file2: str):
    results1 = load_results(file1)
    results2 = load_results(file2)

    scores1 = get_query_scores(results1)
    scores2 = get_query_scores(results2)

    all_queries = sorted(set(scores1.keys()) | set(scores2.keys()))

    print(f"\n{'Query':<60} {'File 1':<25} {'File 2':<25} {'Diff':<10}")
    print("=" * 120)

    total_diff = 0
    count = 0

    for query in all_queries:
        s1 = scores1.get(query)
        s2 = scores2.get(query)

        if not s1 or not s2:
            status1 = "missing" if not s1 else "error" if "error" in s1 else "ok"
            status2 = "missing" if not s2 else "error" if "error" in s2 else "ok"
            print(f"{query[:58]:<60} {status1:<25} {status2:<25} {'N/A':<10}")
            continue

        if "error" in s1 or "error" in s2:
            e1 = s1.get("error", "ok")
            e2 = s2.get("error", "ok")
            print(f"{query[:58]:<60} {e1:<25} {e2:<25} {'N/A':<10}")
            continue

        avg1 = s1["average"]
        avg2 = s2["average"]
        diff = avg2 - avg1
        total_diff += diff
        count += 1

        diff_str = f"{diff:+.3f}"
        print(
            f"{query[:58]:<60} {avg1:.3f} (b:{s1['balance']:.2f} g:{s1['groundedness']:.2f} c:{s1['citation']:.2f})"
            f" {avg2:.3f} (b:{s2['balance']:.2f} g:{s2['groundedness']:.2f} c:{s2['citation']:.2f}) {diff_str:<10}"
        )

    print("=" * 120)
    if count > 0:
        avg_diff = total_diff / count
        print(f"\nAverage difference: {avg_diff:+.3f} (positive = file 2 better)")
        print(f"Queries compared: {count}")
    else:
        print("\nNo comparable queries found")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python compare_evals.py <file1.json> <file2.json>")
        sys.exit(1)

    compare_results(sys.argv[1], sys.argv[2])
