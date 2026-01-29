import pytest


pytestmark = pytest.mark.unit


class DummyOpenaiForTest:
    """Minimal harness to unit-test Wikipedia sufficiency parsing logic."""

    def __init__(self, openai_backend):
        self._backend = openai_backend


class TestWikipediaSufficiencyCheck:
    def test_extract_first_json_object_basic(self, mock_console):
        from app.backends.openai import Openai

        cfg = {
            "openai": {
                "api_url": "http://localhost",
                "model": "test-model",
                "tools_enabled": False,
            },
            "llm": {"system_prompt": ""},
        }

        backend = Openai(console=mock_console, parent=None, config=cfg)

        assert backend._extract_first_json_object(
            '{"answered": true, "answer": "x", "missing": ""}'
        ) == {
            "answered": True,
            "answer": "x",
            "missing": "",
        }

    def test_extract_first_json_object_fenced(self, mock_console):
        from app.backends.openai import Openai

        cfg = {
            "openai": {
                "api_url": "http://localhost",
                "model": "test-model",
                "tools_enabled": False,
            },
            "llm": {"system_prompt": ""},
        }

        backend = Openai(console=mock_console, parent=None, config=cfg)

        text = """```json
{"answered": false, "answer": "no", "missing": "date"}
```"""
        assert backend._extract_first_json_object(text) == {
            "answered": False,
            "answer": "no",
            "missing": "date",
        }

    def test_wikipedia_sufficiency_answered_true_returns_answer(
        self, mock_console, monkeypatch
    ):
        from app.backends.openai import Openai

        cfg = {
            "openai": {
                "api_url": "http://localhost",
                "model": "test-model",
                "tools_enabled": False,
            },
            "llm": {"system_prompt": ""},
        }

        backend = Openai(console=mock_console, parent=None, config=cfg)

        def fake_chat(messages, temperature=None, tools=None, format=None):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"answered": true, "answer": "Ada Lovelace was a mathematician.", "missing": ""}'
                        }
                    }
                ]
            }

        monkeypatch.setattr(backend, "chat", fake_chat)

        out = backend._wikipedia_answer_sufficiency_inference(
            question="Who was Ada Lovelace?",
            wikipedia_extract="Ada Lovelace was an English mathematician.",
        )
        assert out == "Ada Lovelace was a mathematician."

    def test_wikipedia_sufficiency_answered_false_returns_missing(
        self, mock_console, monkeypatch
    ):
        from app.backends.openai import Openai

        cfg = {
            "openai": {
                "api_url": "http://localhost",
                "model": "test-model",
                "tools_enabled": False,
            },
            "llm": {"system_prompt": ""},
        }

        backend = Openai(console=mock_console, parent=None, config=cfg)

        def fake_chat(messages, temperature=None, tools=None, format=None):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"answered": false, "answer": "The extract doesn\u2019t say.", "missing": "birth date"}'
                        }
                    }
                ]
            }

        monkeypatch.setattr(backend, "chat", fake_chat)

        out = backend._wikipedia_answer_sufficiency_inference(
            question="What is Ada Lovelace\u2019s birth date?",
            wikipedia_extract="Ada Lovelace was an English mathematician.",
        )
        assert out == "The extract doesn\u2019t say.\n\nMissing: birth date"
