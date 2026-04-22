# Space Browser Plugin for Agent Zero

Browser automation via Space Agent - a fast, browser-native alternative to browser_agent.

## Overview

Space Browser wraps [Space Agent](https://github.com/nicholasgriffintn/space-agent) to provide browser automation
capabilities without Playwright. It uses a server-side agent loop that calls OpenRouter LLMs
and executes JavaScript code blocks in a sandboxed environment.

## Features

- **No Playwright dependency** - Uses Space Agent's lightweight Node.js server instead
- **Auto-start** - Space Agent server starts automatically with Agent Zero
- **OpenRouter integration** - Uses your OpenRouter API key for LLM calls
- **Plug-and-play** - Enable in Agent Zero settings and start using the `space_browser` tool

## Requirements

- OpenRouter API key (get one at https://openrouter.ai)
- Node.js 18+ installed
- Space Agent installed (or provide path to custom installation)

## Configuration

Access plugin settings in Agent Zero's web UI:

| Setting | Description | Default |
|---------|-------------|--------|
| OpenRouter API Key | Your OpenRouter API key | (empty) |
| Default Model | LLM model to use | anthropic/claude-sonnet-4 |
| Space Agent URL | URL of running Space Agent server | http://localhost:3000 |
| Max Steps | Maximum agent loop iterations | 15 |
| Timeout | Request timeout in seconds | 300 |
| Auto Start | Start Space Agent server automatically | true |
| Space Agent Path | Custom path to Space Agent installation | (empty) |

## Usage

The plugin exposes the `space_browser` tool with these arguments:

- `message` (required): The task to perform
- `reset` (optional): Set to "true" to start a fresh session

Example tool call:
```json
{
  "tool_name": "space_browser",
  "tool_args": {
    "message": "Navigate to example.com and extract the page title",
    "reset": false
  }
}
```

## Architecture

1. Agent Zero calls the `space_browser` tool
2. Plugin ensures Space Agent server is running (auto-start if configured)
3. Tool sends task to Space Agent's `/api/task_run` endpoint
4. Space Agent runs server-side agent loop: LLM call -> execute JS -> loop -> return result
5. Result is returned to Agent Zero

## API Endpoint: POST /api/task_run

The Space Agent fork adds a new endpoint that accepts:

```json
{
  "task": "string - the task to perform",
  "api_key": "string - OpenRouter API key",
  "model": "string - optional, defaults to anthropic/claude-sonnet-4",
  "max_steps": 10
}
```

Returns:
```json
{
  "success": true,
  "result": "final text response",
  "steps": 3,
  "code_blocks_executed": 2
}
```

## License

MIT License - see LICENSE file for details.
