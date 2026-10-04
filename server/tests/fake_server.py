"""
Run the real API with the fake LLM/embeddings from conftest, for UI work and
browser end-to-end checks without AWS credentials:

    python -m tests.fake_server            # serves on :8000
"""
import uvicorn

from tests import conftest  # noqa: F401  (sets DATA_DIR, stubs ML deps, fakes embeddings)
from tests.conftest import FakeLLM


def main(port: int = 8000) -> None:
    import agents.chat_agent as chat
    import agents.content_agent as content
    import services.profile_service as profile
    from main import app

    fake = FakeLLM()
    content.invoke_llm = fake
    profile.invoke_llm = fake
    chat.invoke_llm_with_history = lambda prompt, history, **kw: f"(fake tutor) You asked: {prompt.splitlines()[-3][:120]}"
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
