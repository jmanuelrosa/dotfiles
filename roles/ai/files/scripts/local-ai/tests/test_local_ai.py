"""Static and pure-function checks for the local model manager.

Downloads, Ollama imports, launchd, and benchmark agent runs stay out of this suite.
Those are deliberately explicit `local-ai` operations; the unit tests cover the
catalog and serialization mistakes that would make those costly operations unsafe.
"""

import importlib.machinery
import importlib.util
import json

from dotkit.testing import AI_SCRIPTS_DIR

TOOL_DIR = AI_SCRIPTS_DIR / "local-ai"
SCRIPT = TOOL_DIR / "local-ai"


def load_tool():
    loader = importlib.machinery.SourceFileLoader("local_ai_tool", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


def test_catalog_pins_immutable_verified_artifacts():
    parsed = json.loads((TOOL_DIR / "models.json").read_text())
    assert parsed["schema"] == 1
    assert set(parsed["candidates"]) == {"qwen36", "glm47", "devstral2"}
    for key, model in parsed["candidates"].items():
        assert len(model["revision"]) == (64 if key == "devstral2" else 40)
        assert len(model["sha256"]) == 64
        assert model["file"].endswith(".gguf") or model["file"].startswith("sha256-")
        assert 15_000_000_000 < model["bytes"] < 18_000_000_000


def test_modelfile_has_distinct_context_and_model_parameters(tmp_path):
    tool = load_tool()
    model = tool.catalog()["candidates"]["glm47"]
    text = tool.modelfile(model, tmp_path / "model.gguf", 65536)
    assert text.startswith(f"FROM {tmp_path / 'model.gguf'}\n")
    assert "PARAMETER num_ctx 65536\n" in text
    assert "PARAMETER min_p 0.01\n" in text
    assert "PARAMETER repeat_penalty 1.0\n" in text


def test_event_parser_counts_agent_tools_and_tokens():
    tool = load_tool()
    output = "\n".join(
        [
            json.dumps({"type": "tool_execution_start", "toolName": "read"}),
            json.dumps(
                {"type": "tool_execution_end", "toolName": "read", "isError": False}
            ),
            json.dumps({"type": "message_end", "message": {"usage": {"output": 42}}}),
            json.dumps({"type": "agent_end"}),
        ]
    )
    parsed = tool.parse_events(output)
    assert parsed == {
        "tool_calls": 1,
        "tool_names": ["read"],
        "tool_errors": 0,
        "output_tokens": 42,
        "api_errors": 0,
        "agent_end": True,
    }


def test_event_parser_detects_api_errors():
    tool = load_tool()
    parsed = tool.parse_events(
        json.dumps(
            {
                "type": "message_end",
                "message": {"stopReason": "error", "errorMessage": "out of memory"},
            }
        )
    )
    assert parsed["api_errors"] == 1


def test_pi_config_exposes_only_stable_aliases_for_model_cycling():
    settings = json.loads((TOOL_DIR.parents[1] / "pi" / "settings.json").read_text())
    assert settings["defaultProvider"] == "local"
    assert settings["defaultModel"] == "local-code-quality:32k"
    assert settings["enabledModels"] == [
        "local/local-code-quality:32k",
        "local/local-code-fast:32k",
        "local/local-code-quality:64k",
        "local/local-code-fast:64k",
    ]


def test_pi_models_have_matching_32k_and_64k_stable_profiles():
    models = json.loads((TOOL_DIR.parents[1] / "pi" / "models.json").read_text())
    entries = {row["id"]: row for row in models["providers"]["local"]["models"]}
    for profile in ("quality", "fast"):
        assert entries[f"local-code-{profile}:32k"]["contextWindow"] == 32768
        assert entries[f"local-code-{profile}:64k"]["contextWindow"] == 65536
        assert entries[f"local-code-{profile}:32k"]["reasoning"] is False
        assert entries[f"local-code-{profile}:64k"]["reasoning"] is False


def test_server_policy_disables_cloud():
    policy = json.loads((TOOL_DIR.parents[1] / "ollama" / "server.json").read_text())
    assert policy == {"disable_ollama_cloud": True}
