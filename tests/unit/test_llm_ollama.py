from grapheinstein.core.parsers.llm_ollama import (
    OllamaError,
    check_ready,
    model_available,
)


def test_model_available_exact_and_prefix():
    tags = ["qwen3.5-2b-mlx:fp16-8gbGPU", "llama3.2:latest"]
    assert model_available("qwen3.5-2b-mlx:fp16-8gbGPU", tags=tags)
    assert model_available("llama3.2", tags=tags)
    assert not model_available("missing-model", tags=tags)


def test_check_ready_missing_model():
    ok, msg = check_ready(
        model="nope",
        base_url="http://localhost:11434",
        list_models_fn=lambda _url: ["other:latest"],
    )
    assert ok is False
    assert "skipped" in msg.lower() or "not found" in msg.lower()


def test_check_ready_unreachable():
    def boom(_url):
        raise OllamaError("down")

    ok, msg = check_ready(
        model="x",
        base_url="http://localhost:9",
        list_models_fn=boom,
    )
    assert ok is False
    assert "skipped" in msg.lower() or "unreachable" in msg.lower()


def test_check_ready_ok():
    ok, msg = check_ready(
        model="m:latest",
        list_models_fn=lambda _url: ["m:latest"],
    )
    assert ok is True
    assert "Using Ollama" in msg
