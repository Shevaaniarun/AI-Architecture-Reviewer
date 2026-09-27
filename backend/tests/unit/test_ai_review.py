import json

from app.analyzer.llm.review_service import build_review_evidence, generate_ai_review
from app.core.config import Settings


def make_analysis():
    return {
        "analysis_id": "ANL-test",
        "repository": {"name": "sample", "python_files": 1},
        "metrics": {
            "files": 1,
            "lines_of_code": 20,
            "classes": 1,
            "functions": 2,
            "methods": 1,
            "imports": 3,
            "function_metrics": [],
            "file_metrics": [],
        },
        "dependency_graph": {"dependency_count": 1, "cycles": []},
        "architecture": {
            "status": "INFERRED",
            "components": [{"name": "services"}],
            "relationships": [],
        },
        "findings": [
            {
                "id": "finding-1",
                "type": "Long Method",
                "severity": "high",
                "status": "detected",
                "file": "service.py",
                "line": 4,
                "message": "Function exceeds line threshold.",
                "evidence": {"lines": 80},
                "source_snippet": {"text": "def work():\\n    pass"},
            }
        ],
    }


def test_ai_is_reported_unconfigured_without_network_request():
    analysis = make_analysis()
    result = generate_ai_review(analysis, Settings(_env_file=None))

    assert result["status"] == "not_configured"
    assert result["findings"] == []
    assert analysis["findings"][0]["type"] == "Long Method"


def test_evidence_builder_sends_compact_project_and_selected_finding_data():
    evidence = build_review_evidence(make_analysis())

    assert evidence["project"] == {"name": "sample", "python_files": 1}
    assert evidence["metrics"]["lines_of_code"] == 20
    assert evidence["findings"][0]["finding_id"] == "finding-1"
    assert "function_metrics" not in evidence["metrics"]
    assert evidence["findings"][0]["source_snippet"]


def test_ai_review_keeps_only_supported_finding_ids(monkeypatch):
    from app.analyzer.llm import review_service

    replies = iter(
        [
            "not json",
            json.dumps(
                {
                    "summary": "A small service project.",
                    "findings": [
                        {
                            "finding_id": "finding-1",
                            "explanation": "The function combines several operations.",
                            "architectural_impact": "Maintenance may be harder.",
                            "recommendation": "Split responsibilities into smaller functions.",
                        },
                        {
                            "finding_id": "invented-id",
                            "explanation": "Unsupported claim.",
                            "architectural_impact": "Unknown.",
                            "recommendation": "Unknown.",
                        },
                    ],
                    "architecture_summary": "One inferred service component.",
                    "overall_recommendations": ["Add focused unit tests."],
                }
            ),
        ]
    )
    calls = []

    def fake_complete(self, evidence):
        calls.append(evidence)
        return next(replies)

    monkeypatch.setattr(review_service.OpenAIReviewProvider, "complete", fake_complete)
    result = generate_ai_review(
        make_analysis(),
        Settings(_env_file=None, llm_provider="openai", llm_api_key="test-key", llm_model="test-model"),
    )

    assert len(calls) == 2
    assert calls[1]["format_retry"]
    assert result["status"] == "complete"
    assert [item["finding_id"] for item in result["findings"]] == ["finding-1"]
    assert result["overall_recommendations"] == ["Add focused unit tests."]


def test_ai_review_returns_raw_text_after_two_malformed_responses(monkeypatch):
    from app.analyzer.llm import review_service

    replies = iter(["not json one", "not json two"])
    calls = []

    def fake_complete(self, evidence):
        calls.append(evidence)
        return next(replies)

    monkeypatch.setattr(review_service.OpenAIReviewProvider, "complete", fake_complete)
    result = generate_ai_review(
        make_analysis(),
        Settings(_env_file=None, llm_provider="openai", llm_api_key="test-key", llm_model="test-model"),
    )

    assert len(calls) == 2
    assert result["status"] == "malformed"
    assert result["raw_text"] == "not json two"
    assert result["findings"] == []


def test_ai_provider_error_returns_unavailable_without_modifying_analysis(monkeypatch):
    from app.analyzer.llm import review_service

    def fail_provider(self, evidence):
        raise RuntimeError("provider unavailable")

    analysis = make_analysis()
    monkeypatch.setattr(review_service.OpenAIReviewProvider, "complete", fail_provider)
    result = generate_ai_review(
        analysis,
        Settings(_env_file=None, llm_provider="openai", llm_api_key="test-key", llm_model="test-model"),
    )

    assert result["status"] == "unavailable"
    assert analysis["findings"][0]["id"] == "finding-1"
