"""HTTP client for Space Agent task_run API."""

import asyncio
import requests
from functools import partial


def _run_task_sync(
    space_agent_url: str,
    task: str,
    api_key: str,
    api_url: str = "https://api.z.ai/api/coding/paas/v4/chat/completions",
    model: str = "glm-5.1",
    max_steps: int = 15,
    timeout: float = 300.0,
) -> dict:
    """Synchronous task execution using requests."""
    url = f"{space_agent_url.rstrip('/')}/api/task_run"
    payload = {
        "task": task,
        "api_key": api_key,
        "api_url": api_url,
        "model": model,
        "max_steps": max_steps,
    }
    resp = requests.post(url, json=payload, timeout=timeout)
    if resp.status_code != 200:
        raise RuntimeError(
            f"Space Agent task_run failed (HTTP {resp.status_code}): {resp.text}"
        )
    return resp.json()


async def run_task(
    space_agent_url: str,
    task: str,
    api_key: str,
    api_url: str = "https://api.z.ai/api/coding/paas/v4/chat/completions",
    model: str = "glm-5.1",
    max_steps: int = 15,
    timeout: float = 300.0,
) -> dict:
    """Send a task to Space Agent and return the result (async wrapper).

    Args:
        space_agent_url: Base URL of the Space Agent server.
        task: Natural language task description.
        api_key: Z.AI (or OpenRouter) API key.
        api_url: LLM API endpoint URL.
        model: LLM model identifier.
        max_steps: Maximum agent loop iterations.
        timeout: HTTP request timeout in seconds.

    Returns:
        dict with keys: success, result, steps, code_blocks_executed
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None,
        partial(
            _run_task_sync,
            space_agent_url=space_agent_url,
            task=task,
            api_key=api_key,
            api_url=api_url,
            model=model,
            max_steps=max_steps,
            timeout=timeout,
        ),
    )
