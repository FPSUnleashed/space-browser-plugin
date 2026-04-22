"""Space Browser tool - browser automation via Space Agent."""

from helpers.tool import Tool, Response


class SpaceBrowser(Tool):
    """
    Browser automation tool powered by Space Agent.
    Sends tasks to the Space Agent server-side agent loop for execution.
    """

    async def execute(self, message: str = "", reset: bool = False, **kwargs) -> Response:
        """Execute a browser task via Space Agent.

        Args:
            message: Natural language task description for the browser agent.
            reset: Start a fresh browser session (true/false).
        """
        task = message or self.args.get("message", "")
        if not task:
            return Response(
                message="Error: No task provided. Use 'message' argument.",
                break_loop=False,
            )

        # Load plugin config using proper Agent Zero API
        try:
            from helpers.plugins import get_plugin_config
            config = get_plugin_config("space_browser", agent=self.agent) or {}
        except Exception:
            try:
                config = self.agent.config.get("plugins", {}).get("space_browser", {})
            except Exception:
                config = {}

        space_agent_url = config.get("space_agent_url", "http://localhost:3000")
        api_url = config.get(
            "api_url",
            "https://api.z.ai/api/coding/paas/v4/chat/completions"
        )
        api_key = config.get("api_key", "")
        model = config.get("default_model", "glm-5.1")
        max_steps = int(config.get("max_steps", 15))
        timeout = float(config.get("timeout", 300))
        auto_start = config.get("auto_start", True)
        space_agent_path = config.get("space_agent_path", "")

        if not api_key:
            return Response(
                message=(
                    "Error: API key not configured. "
                    "Set it in Space Browser plugin settings."
                ),
                break_loop=False,
            )

        # Import helpers - proper Agent Zero import path
        try:
            from usr.plugins.space_browser.helpers.space_server import ensure_server_running
            from usr.plugins.space_browser.helpers.space_client import run_task
        except ImportError:
            try:
                import sys
                sys.path.insert(0, '/a0/usr')
                from plugins.space_browser.helpers.space_server import ensure_server_running
                from plugins.space_browser.helpers.space_client import run_task
            except ImportError as e:
                return Response(
                    message=f"Error: Failed to import Space Browser helpers: {e}",
                    break_loop=False,
                )

        # Auto-start server if needed
        if auto_start:
            try:
                await self.set_progress("Starting Space Agent server...")
                port = (
                    int(space_agent_url.split(":")[-1].split("/")[0])
                    if ":" in space_agent_url
                    else 3000
                )
                space_agent_url = await ensure_server_running(
                    space_agent_path=space_agent_path,
                    port=port,
                )
            except Exception as e:
                return Response(
                    message=f"Error starting Space Agent server: {e}",
                    break_loop=False,
                )

        # Send task
        try:
            await self.set_progress(f"Executing task via Space Agent: {task[:100]}...")
            result = await run_task(
                space_agent_url=space_agent_url,
                task=task,
                api_key=api_key,
                api_url=api_url,
                model=model,
                max_steps=max_steps,
                timeout=timeout,
            )

            if result.get("success"):
                output = result.get("result", "Task completed.")
                steps = result.get("steps", 0)
                code_blocks = result.get("code_blocks_executed", 0)
                step_log = result.get("step_log", [])

                # Build detailed response with step history
                msg_parts = [output]

                if step_log:
                    msg_parts.append("")
                    msg_parts.append("### Steps")
                    for entry in step_log:
                        step_num = entry.get("step", "?")
                        entry_type = entry.get("type", "")

                        if entry_type == "thinking":
                            reasoning = entry.get("reasoning", "")
                            if reasoning:
                                msg_parts.append(f"**Step {step_num} — Thinking:** {reasoning[:500]}")
                        elif entry_type == "code":
                            block_num = entry.get("block", "?")
                            code = entry.get("code", "")
                            parts = [f"**Step {step_num} — Code Block {block_num}:**"]
                            if code:
                                parts.append(f"```javascript\n{code[:1000]}\n```")
                            if entry.get("output"):
                                parts.append(f"Output: `{entry['output'][:500]}`")
                            if entry.get("result"):
                                parts.append(f"Result: `{entry['result'][:500]}`")
                            if entry.get("error"):
                                parts.append(f"Error: `{entry['error'][:500]}`")
                            msg_parts.append("\n".join(parts))

                msg_parts.append("")
                msg_parts.append(f"[Space Agent: {steps} steps, {code_blocks} code blocks executed]")

                return Response(message="\n".join(msg_parts), break_loop=False)
            else:
                # Task failed or crashed - show partial results if available
                step_log = result.get("step_log", [])
                steps = result.get("steps", 0)
                error = result.get("error", "Unknown error")
                is_partial = result.get("partial", False)

                msg_parts = []
                if is_partial:
                    msg_parts.append(f"⚠️ **Space Agent crashed at step {steps}:** {error}")
                    msg_parts.append("")
                    msg_parts.append("### Partial Steps (before crash)")
                else:
                    msg_parts.append(f"**Space Agent task failed:** {error}")
                    if step_log:
                        msg_parts.append("")
                        msg_parts.append("### Steps")

                if step_log:
                    for entry in step_log:
                        step_num = entry.get("step", "?")
                        entry_type = entry.get("type", "")

                        if entry_type == "thinking":
                            reasoning = entry.get("reasoning", "")
                            if reasoning:
                                msg_parts.append(f"**Step {step_num} — Thinking:** {reasoning[:500]}")
                        elif entry_type == "code":
                            block_num = entry.get("block", "?")
                            code = entry.get("code", "")
                            parts = [f"**Step {step_num} — Code Block {block_num}:**"]
                            if code:
                                parts.append(f"```javascript\n{code[:1000]}\n```")
                            if entry.get("output"):
                                parts.append(f"Output: `{entry['output'][:500]}`")
                            if entry.get("result"):
                                parts.append(f"Result: `{entry['result'][:500]}`")
                            if entry.get("error"):
                                parts.append(f"Error: `{entry['error'][:500]}`")
                            msg_parts.append("\n".join(parts))

                return Response(message="\n".join(msg_parts), break_loop=False)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            return Response(
                message=f"Error executing Space Agent task: {type(e).__name__}: {e}\n\nTraceback:\n{tb[-500:]}",
                break_loop=False,
            )
