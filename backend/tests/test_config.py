import pytest

from app.core.config import Settings


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("http://localhost:5173", ["http://localhost:5173"]),
        ("http://a.com, http://b.com ,", ["http://a.com", "http://b.com"]),
        ('["http://a.com","http://b.com"]', ["http://a.com", "http://b.com"]),
    ],
)
def test_cors_origins_accepts_env_formats(monkeypatch, raw, expected):
    monkeypatch.setenv("CORS_ORIGINS", raw)
    assert Settings(_env_file=None).cors_origins == expected


def test_cors_origins_from_dotenv_file(tmp_path):
    # Regression: the shipped .env.example used a plain comma-separated value that crashed startup.
    env = tmp_path / ".env"
    env.write_text("CORS_ORIGINS=http://localhost:5173\nPOSTGRES_USER=ignored\n")
    assert Settings(_env_file=env).cors_origins == ["http://localhost:5173"]


def test_shipped_env_example_is_loadable():
    from pathlib import Path

    # Process env vars outrank the file, so assert on a value the test env doesn't set.
    example = Path(__file__).resolve().parents[2] / ".env.example"
    s = Settings(_env_file=example)  # must not raise
    assert s.cors_origins == ["http://localhost:5173"]
    assert s.llm_model == "groq:llama-3.3-70b-versatile"
