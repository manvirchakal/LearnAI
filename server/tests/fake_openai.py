"""
A minimal OpenAI-compatible server standing in for vLLM in tests:
/v1/models, /v1/chat/completions (incl. streaming), /v1/embeddings and
/v1/audio/transcriptions. Chat replies come from a FakeLLM-style responder.
"""
import hashlib
import json
import re
import socket
import threading
import time
from typing import Callable, List

import uvicorn
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import StreamingResponse

TOC_JSON = json.dumps({"chapters": [
    {"number": "Chapter 1", "title": "Scanned One", "page": 1, "sections": [{"title": "1.1 First", "page": 2}]},
    {"number": "Chapter 2", "title": "Scanned Two", "page": 4, "sections": []},
]})


class FakeOpenAIServer:
    def __init__(self, responder: Callable[[str], str], models: List[str]):
        self.responder = responder
        self.models = models
        self.requests: List[dict] = []
        self.app = self._build()
        self.port = _free_port()
        self.base_url = f"http://127.0.0.1:{self.port}/v1"
        self._server = uvicorn.Server(uvicorn.Config(self.app, port=self.port, log_level="warning"))
        self._thread = threading.Thread(target=self._server.run, daemon=True)

    def __enter__(self):
        self._thread.start()
        deadline = time.time() + 10
        while not self._server.started:
            if time.time() > deadline:
                raise RuntimeError("fake OpenAI server did not start")
            time.sleep(0.02)
        return self

    def __exit__(self, *exc):
        self._server.should_exit = True
        self._thread.join(timeout=5)

    def _reply(self, messages: list) -> str:
        content = messages[-1]["content"]
        if isinstance(content, list):
            if any(part.get("type") == "image_url" for part in content):
                return TOC_JSON
            content = " ".join(part.get("text", "") for part in content)
        return self.responder(content)

    def _build(self) -> FastAPI:
        app = FastAPI()

        @app.get("/v1/models")
        def models():
            return {"object": "list", "data": [{"id": m, "object": "model"} for m in self.models]}

        @app.post("/v1/chat/completions")
        async def chat(request: Request):
            body = await request.json()
            self.requests.append({"path": "chat", **body})
            text = self._reply(body["messages"])
            base = {"id": "chatcmpl-fake", "created": int(time.time()), "model": body["model"]}
            if not body.get("stream"):
                return {**base, "object": "chat.completion", "choices": [
                    {"index": 0, "message": {"role": "assistant", "content": text}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}}

            def events():
                for token in re.findall(r"\S+\s*", text):
                    chunk = {**base, "object": "chat.completion.chunk",
                             "choices": [{"index": 0, "delta": {"content": token}, "finish_reason": None}]}
                    yield f"data: {json.dumps(chunk)}\n\n"
                done = {**base, "object": "chat.completion.chunk",
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]}
                yield f"data: {json.dumps(done)}\n\ndata: [DONE]\n\n"

            return StreamingResponse(events(), media_type="text/event-stream")

        @app.post("/v1/embeddings")
        async def embeddings(request: Request):
            body = await request.json()
            inputs = body["input"] if isinstance(body["input"], list) else [body["input"]]
            self.requests.append({"path": "embeddings", "model": body["model"], "count": len(inputs)})
            data = [{"object": "embedding", "index": i,
                     "embedding": [b / 255 for b in hashlib.sha256(t.encode()).digest()[:8]]}
                    for i, t in enumerate(inputs)]
            return {"object": "list", "data": data, "model": body["model"],
                    "usage": {"prompt_tokens": 1, "total_tokens": 1}}

        @app.post("/v1/audio/transcriptions")
        async def transcriptions(file: UploadFile = File(...), model: str = Form(...)):
            size = len(await file.read())
            self.requests.append({"path": "transcriptions", "model": model, "filename": file.filename, "size": size})
            return {"text": f"transcribed {file.filename}"}

        return app


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
