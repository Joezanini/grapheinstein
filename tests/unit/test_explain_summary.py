from pathlib import Path

from grapheinstein.core.explain import explain_concept, summarize_neighborhood
from grapheinstein.core.graph import load_artifact

FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "explain_graphs" / "auth_neighborhood.json"
)


def test_summarize_ok_with_injectable_chat():
    artifact = load_artifact(FIXTURE)
    artifact["graph"]["explain_match_ids"] = ["concept::auth"]

    def fake_chat(**_kwargs):
        return "Auth is implemented by check_auth in this project."

    status, text, detail = summarize_neighborhood(
        concept="auth",
        artifact=artifact,
        model="fake-model",
        base_url="http://localhost:9",
        chat_fn=fake_chat,
        list_models_fn=lambda _url: ["fake-model"],
    )
    assert status == "ok"
    assert text and "check_auth" in text
    assert detail is None


def test_summarize_skipped_when_model_missing():
    artifact = load_artifact(FIXTURE)
    status, text, detail = summarize_neighborhood(
        concept="auth",
        artifact=artifact,
        model="missing-model",
        base_url="http://localhost:9",
        list_models_fn=lambda _url: [],
    )
    assert status == "skipped"
    assert text is None
    assert detail and "skipped" in detail.lower()


def test_explain_concept_summary_injectable(tmp_path: Path):
    out = tmp_path / "sub.json"

    def fake_chat(**_kwargs):
        return "Neighborhood summary about Auth."

    result = explain_concept(
        "auth",
        FIXTURE,
        out,
        want_summary=True,
        use_embeddings=False,
        chat_fn=fake_chat,
        list_models_fn=lambda _url: ["qwen3.5-2b-mlx:fp16-8gbGPU"],
    )
    assert out.exists()
    assert result.summary_status == "ok"
    assert result.summary_text and "Auth" in result.summary_text
    assert "explained_concept" in load_artifact(out)["graph"]
