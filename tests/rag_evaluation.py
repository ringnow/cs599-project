"""RAGAS evaluation: measure RAG answer quality.

Run with:
    pytest tests/rag_evaluation.py -v --no-header 2>&1 | head -80

Requires:
    pip install ragas langchain-google-vertexai

This test suite evaluates the RAG system's answer quality using RAGAS
metrics: faithfulness, answer_relevancy, context_precision, context_recall.

Test cases are based on the actual documents in the knowledge base.
If the knowledge base is empty, tests will be skipped gracefully.
"""
import os
import json
import pytest
from typing import Dict, List, Optional

# ── Ragas compatibility shim ──────────────────────────────────────────
# ragas 0.4.3 imports langchain_community.chat_models.vertexai which no
# longer exists in newer langchain-community. Provide a dummy module.
try:
    import langchain_community.chat_models.vertexai  # noqa: F401
except ImportError:
    import sys
    from unittest.mock import MagicMock
    sys.modules['langchain_community.chat_models.vertexai'] = MagicMock()
    if hasattr(MagicMock, 'ChatVertexAI'):
        pass

# ── Test Data ──────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "question": "感知模块测试中算法2的PSNR目标值是多少？",
        "expected_topics": ["PSNR", "感知模块", "算法2"],
        "min_sources": 1,
    },
    {
        "question": "自动驾驶感知模块有哪些主要组件？",
        "expected_topics": ["感知", "传感器", "融合"],
        "min_sources": 1,
    },
    {
        "question": "SSIM指标在算法评估中的作用是什么？",
        "expected_topics": ["SSIM", "评估", "指标"],
        "min_sources": 1,
    },
    {
        "question": "点云去噪通常使用哪些方法？",
        "expected_topics": ["点云", "去噪", "滤波"],
        "min_sources": 1,
    },
    {
        "question": "知识库中是否包含有关transformer架构的信息？",
        "expected_topics": [],
        "min_sources": 0,  # May not be in the KB
    },
    {
        "question": "请详细介绍卡尔曼滤波在障碍物跟踪中的应用",
        "expected_topics": ["卡尔曼滤波", "障碍物跟踪"],
        "min_sources": 1,
    },
    {
        "question": "这篇文章的测试周期是多久？",
        "expected_topics": ["测试", "周期", "日期"],
        "min_sources": 1,
    },
]


# ── Fixtures ──────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def kb_stats() -> Dict:
    """Check if the knowledge base has documents."""
    try:
        import requests
        resp = requests.get("http://localhost:8000/api/knowledge/stats", timeout=5)
        if resp.ok:
            return resp.json()
        return {"enabled": False, "total_documents": 0}
    except Exception:
        return {"enabled": False, "total_documents": 0}


# ── Helpers ──────────────────────────────────────────────────────────

def ask_rag(question: str) -> Optional[Dict]:
    """Call the RAG QA endpoint and return the response."""
    import requests
    try:
        resp = requests.post(
            "http://localhost:8000/api/knowledge/ask",
            json={"question": question, "top_k": 5},
            timeout=60,
        )
        if resp.ok:
            return resp.json()
        return None
    except Exception:
        return None


def compute_ragas_score(question: str, answer: str, contexts: List[str]) -> Dict:
    """Compute RAGAS metrics for a single Q-A pair.

    Requires ragas to be installed and a working LLM provider configured.
    """
    try:
        from ragas import evaluate
        from ragas.metrics.collections import (
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        )
        from datasets import Dataset

        data = Dataset.from_dict({
            "question": [question],
            "answer": [answer],
            "contexts": [contexts],
        })

        result = evaluate(
            dataset=data,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        )

        # Convert to plain dict
        scores = {}
        for metric_name, value in result.items():
            if hasattr(value, '__iter__') and not isinstance(value, str):
                scores[metric_name] = float(list(value)[0])
            else:
                scores[metric_name] = float(value)
        return scores
    except ImportError:
        return {"error": "ragas not installed. Run: pip install ragas"}
    except Exception as e:
        return {"error": str(e)}


# ── Test Cases ────────────────────────────────────────────────────────

@pytest.mark.skipif(
    os.getenv("SKIP_RAGAS_EVAL", "") == "1",
    reason="Set SKIP_RAGAS_EVAL=1 to skip RAGAS evaluation (requires running server)",
)
class TestRAGEvaluation:

    def test_kb_available(self, kb_stats):
        """Knowledge base must have documents for meaningful evaluation."""
        if not kb_stats.get("enabled") or kb_stats.get("total_documents", 0) == 0:
            pytest.skip("Knowledge base is empty — upload documents first")

    @pytest.mark.parametrize("case", TEST_CASES, ids=[c["question"][:30] for c in TEST_CASES])
    def test_rag_qa(self, case: Dict, kb_stats):
        """Test RAG QA endpoint returns answers with proper sources."""
        if not kb_stats.get("enabled") or kb_stats.get("total_documents", 0) == 0:
            pytest.skip("Knowledge base is empty")

        result = ask_rag(case["question"])
        assert result is not None, f"RAG QA returned None for: {case['question']}"

        # Check answer exists
        assert "answer" in result, "Response missing 'answer'"
        assert len(result["answer"]) > 20, f"Answer too short: {result['answer'][:50]}"

        # Check sources
        sources = result.get("sources", [])
        if case["min_sources"] > 0:
            assert len(sources) >= case["min_sources"], (
                f"Expected >= {case['min_sources']} sources, got {len(sources)}"
            )

        # Check expected topics appear in answer (if any)
        if case["expected_topics"]:
            for topic in case["expected_topics"]:
                assert topic in result["answer"], (
                    f"Expected topic '{topic}' in answer: {result['answer'][:100]}"
                )

    def test_ragas_faithfulness(self, kb_stats):
        """Compute RAGAS faithfulness score on a subset of test cases."""
        if not kb_stats.get("enabled") or kb_stats.get("total_documents", 0) == 0:
            pytest.skip("Knowledge base is empty")

        scores_list = []
        for case in TEST_CASES[:3]:  # Use first 3 for speed
            result = ask_rag(case["question"])
            if not result:
                continue

            answer = result.get("answer", "")
            sources = result.get("sources", [])
            contexts = [s.get("text", "") for s in sources if s.get("text")]

            if not contexts:
                continue

            scores = compute_ragas_score(case["question"], answer, contexts)
            if "error" not in scores:
                scores_list.append(scores)

        if not scores_list:
            pytest.skip("Could not compute RAGAS scores (no responses with contexts)")

        # Aggregate
        avg_scores = {}
        for key in scores_list[0]:
            vals = [s[key] for s in scores_list if key in s]
            avg_scores[f"avg_{key}"] = sum(vals) / len(vals)

        print(f"\n📊 RAGAS Scores ({len(scores_list)} samples):")
        for k, v in avg_scores.items():
            print(f"  {k}: {v:.4f}")

        # Assert minimum thresholds
        min_faithfulness = float(os.getenv("RAGAS_MIN_FAITHFULNESS", "0.7"))
        if "avg_faithfulness" in avg_scores:
            assert avg_scores["avg_faithfulness"] >= min_faithfulness, (
                f"Faithfulness {avg_scores['avg_faithfulness']:.4f} < threshold {min_faithfulness}"
            )


# ── CLI Runner ────────────────────────────────────────────────────────

if __name__ == "__main__":
    """Run evaluation and print a report."""
    print("=" * 60)
    print("  RAG Evaluation Report")
    print("=" * 60)

    import requests
    stats_resp = requests.get("http://localhost:8000/api/knowledge/stats", timeout=5)
    stats = stats_resp.json() if stats_resp.ok else {"enabled": False}
    print(f"  KB enabled: {stats.get('enabled')}")
    print(f"  Documents:  {stats.get('total_documents', 0)}")
    print(f"  Chunks:     {stats.get('total_chunks', 0)}")
    print()

    if not stats.get("enabled") or stats.get("total_documents", 0) == 0:
        print("  ⚠️  Knowledge base is empty. Upload documents first.")
        exit(0)

    all_scores = []
    for i, case in enumerate(TEST_CASES):
        print(f"  [{i+1}/{len(TEST_CASES)}] {case['question'][:60]}...")
        result = ask_rag(case["question"])
        if not result:
            print(f"        ❌ No response")
            continue

        answer = result.get("answer", "")
        sources = result.get("sources", [])
        contexts = [s.get("text", "") for s in sources if s.get("text")]

        print(f"        Answer: {len(answer)} chars, {len(sources)} sources")

        if contexts:
            scores = compute_ragas_score(case["question"], answer, contexts)
            if "error" not in scores:
                all_scores.append(scores)
                print(f"        RAGAS: faith={scores.get('faithfulness', 0):.3f}, "
                      f"relev={scores.get('answer_relevancy', 0):.3f}, "
                      f"prec={scores.get('context_precision', 0):.3f}")
            else:
                print(f"        RAGAS error: {scores['error'][:60]}")
        print()

    if all_scores:
        print("=" * 60)
        print("  Summary")
        print("=" * 60)
        for key in all_scores[0]:
            vals = [s[key] for s in all_scores if key in s]
            avg = sum(vals) / len(vals)
            print(f"  avg_{key}: {avg:.4f}")
    else:
        print("  No RAGAS scores computed.")
