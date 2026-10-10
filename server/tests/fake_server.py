"""
Run the real API with the fake LLM/embeddings from conftest, for UI work and
browser end-to-end checks without AWS credentials:

    python -m tests.fake_server            # serves on :8000
    FAKE_TOKEN_DELAY=0.2 python -m tests.fake_server   # slow streaming, to watch it render
"""
import os

import uvicorn

from tests import conftest  # noqa: F401  (sets DATA_DIR, stubs ML deps, fakes embeddings)
from tests.conftest import FakeLLM, install_fake_llm


def main(port: int = 8000) -> None:
    from main import app

    install_fake_llm(FakeLLM(), token_delay=float(os.environ.get("FAKE_TOKEN_DELAY", "0")))
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
