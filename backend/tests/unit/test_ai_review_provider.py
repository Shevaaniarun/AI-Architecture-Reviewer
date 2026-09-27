import json

from app.analyzer.llm.review_service import OpenAIReviewProvider


class FakeResponse:
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "{\"summary\":\"ok\"}"}}]}).encode()


def test_openai_provider_sends_prompt_and_parses_chat_completion(monkeypatch):
    import urllib.request

    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)
    provider = OpenAIReviewProvider("test-key", "test-model", timeout_seconds=7)
    content = provider.complete({"metrics": {"files": 1}})

    request = captured["request"]
    body = json.loads(request.data)
    assert request.full_url == OpenAIReviewProvider.endpoint
    assert request.get_header("Authorization") == "Bearer test-key"
    assert body["model"] == "test-model"
    assert body["response_format"] == {"type": "json_object"}
    assert '"files":1' in body["messages"][1]["content"]
    assert captured["timeout"] == 7
    assert content == '{"summary":"ok"}'


def test_openai_provider_rejects_non_text_message_content(monkeypatch):
    import urllib.request

    class InvalidContentResponse(FakeResponse):
        def read(self):
            return json.dumps({"choices": [{"message": {"content": None}}]}).encode()

    monkeypatch.setattr(urllib.request, "urlopen", lambda *_args, **_kwargs: InvalidContentResponse())

    try:
        OpenAIReviewProvider("test-key", "test-model").complete({})
    except RuntimeError as error:
        assert "unexpected response shape" in str(error)
    else:
        raise AssertionError("Non-text provider message should be rejected")
