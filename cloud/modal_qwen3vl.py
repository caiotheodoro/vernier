"""Serves `Qwen/Qwen3-VL-8B-Instruct-FP8` via vLLM's OpenAI-compatible server, on Modal.

`docs/DECISIONS.md` D042: the sole judge in the panel after `gemini-2.5-flash` was found
deprecated for new API keys and Anthropic was ruled out. Modal is the deployment target while
Modal credits last; AWS is the fallback once they run out (Caio's own instruction). Nothing in
`src/vernier/judges/qwen3vl.py`'s `_call_qwen3vl` seam names Modal -- it is a plain `openai`
client pointed at `QWEN3VL_BASE_URL`, so redeploying this exact vLLM server on an AWS EC2/ECS
L4 instance instead is a deployment change, not a code change on either side.

Structure verified live against Modal's own current example
(`modal-labs/modal-examples/06_gpu_and_ml/llm-serving/vllm_inference.py`, fetched directly, not
assumed from older training knowledge -- Modal's serving API changed at least once this year,
per the 1.0 `keep_warm`->`min_containers` rename): `@app.server` wraps a class whose
`@modal.enter()` starts vLLM as a subprocess and whose `@modal.exit()` terminates it. This is
Modal's dedicated decorator for a persistent, internet-facing server process, not the older
`@app.cls` + `@modal.web_server`/`@modal.asgi_app()` pattern.

L4 compute capability (8.9, Ada Lovelace) meets vLLM's FP8 W8A8 requirement (`>= 8.9`, verified
against vLLM's own current docs -- an earlier paraphrase said "> 8.9" strictly, which would have
excluded L4; the real wording is "or equal") -- no fallback to the unquantized bf16 checkpoint
is needed.

Deploy: `modal deploy cloud/modal_qwen3vl.py`
Smoke test: `modal run cloud/modal_qwen3vl.py`
"""

from __future__ import annotations

import json
from typing import Any

import aiohttp
import modal

# Pinned to the real HF revision, not `main` -- sourced from a live HfApi().model_info() call,
# matching this project's own revision-pinning discipline (sampling/revisions.py,
# docs/upstream/PROVENANCE.json) rather than trusting a mutable ref.
MODEL_NAME = "Qwen/Qwen3-VL-8B-Instruct-FP8"
MODEL_REVISION = "9cdc6310a8cb770ce18efaf4e9935334512aee45"

VLLM_VERSION = "0.21.0"  # matches Modal's own current example's pin at time of writing
VLLM_PORT = 8000
N_GPU = 1
MINUTES = 60  # seconds

vllm_image = (
    modal.Image.from_registry("nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12")
    .entrypoint([])
    .uv_pip_install(f"vllm=={VLLM_VERSION}")
    .env({"HF_XET_HIGH_PERFORMANCE": "1"})
)

hf_cache_vol = modal.Volume.from_name("vernier-huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vernier-vllm-cache", create_if_missing=True)

app = modal.App("vernier-qwen3vl-judge")


@app.server(
    image=vllm_image,
    gpu=f"L4:{N_GPU}",
    # Scale-to-zero for now (min_containers=0, the default): an unattended always-warm
    # container bills continuously (~$0.80/hr) with no request in flight, which is the wrong
    # default before the first real deploy has even been smoke-tested. Cold start for an 8B
    # model is real (likely 1-2 minutes) but bounded and one-time per idle period -- switch to
    # min_containers=1 once a real judging run's request volume justifies paying to avoid it.
    min_containers=0,
    scaledown_window=15 * MINUTES,
    startup_timeout=10 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
        "/root/.cache/vllm": vllm_cache_vol,
    },
    port=VLLM_PORT,
    # No HF secret: Qwen/Qwen3-VL-8B-Instruct-FP8 is confirmed not gated (live HfApi() check),
    # so there is nothing an HF_TOKEN would unblock here -- adding one would be a credential
    # dependency for a scenario that can't happen with this model.
    unauthenticated=False,  # judge calls carry no reason to be publicly reachable
    target_concurrency=4,  # a single-judge audit run, not a public-traffic service
)
class Server:
    @modal.enter()
    def start(self) -> None:
        import subprocess

        cmd = [
            "vllm",
            "serve",
            MODEL_NAME,
            "--revision",
            MODEL_REVISION,
            "--served-model-name",
            MODEL_NAME,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
            "--uvicorn-log-level=info",
            "--tensor-parallel-size",
            str(N_GPU),
            # Exactly one image per prompt -- vernier's judge_frame sends one frame at a time,
            # never a multi-image batch in a single request.
            "--limit-mm-per-prompt",
            json.dumps({"image": 1, "video": 0, "audio": 0}),
        ]
        print(*cmd)
        self.process = subprocess.Popen(cmd)

    @modal.exit()
    def stop(self) -> None:
        self.process.terminate()


@app.local_entrypoint()
async def test(test_timeout: int = 10 * MINUTES) -> None:
    """`modal run cloud/modal_qwen3vl.py` -- health-check the deployed server, then send one
    real text-only completion (no image) to confirm the endpoint answers at all, before
    `judges/qwen3vl.py` ever sends it a real frame."""
    import asyncio
    import time

    # get_url is attached by @app.server at decoration time -- confirmed present at runtime
    # (hasattr(Server, "get_url") is True) even though modal's type stubs don't expose it on
    # the decorated class statically.
    url = await Server.get_url.aio()  # type: ignore[attr-defined]

    async with aiohttp.ClientSession(base_url=url) as session:
        print(f"Running health check for server at {url}")
        deadline = time.time() + test_timeout - 1 * MINUTES
        while time.time() < deadline:
            async with session.get("/health", timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    break
                if resp.status == 503:
                    await asyncio.sleep(1)
                    continue
                raise RuntimeError(f"health check failed for {url}: HTTP {resp.status}")
        else:
            raise RuntimeError(f"health check never passed for {url}")
        print(f"Successful health check for server at {url}")

        payload: dict[str, Any] = {
            "model": MODEL_NAME,
            "messages": [{"role": "user", "content": "Reply with exactly one word: OK"}],
            "max_tokens": 16,
        }
        async with session.post(
            "/v1/chat/completions", json=payload, headers={"Content-Type": "application/json"}
        ) as resp:
            resp.raise_for_status()
            body = await resp.json()
            print("response:", body["choices"][0]["message"]["content"])
