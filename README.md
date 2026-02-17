# re-agent

Autonomous reverse engineering agent — orchestrates LLMs + Ghidra for scalable binary analysis.

## Overview

re-agent automates the reverse engineering workflow by coordinating LLM agents (reverser + checker) with Ghidra decompilation through [ghidra-ai-bridge](https://github.com/dryxio/ghidra-ai-bridge). It implements a verify-then-fix loop with configurable quality gates powered by an 11-signal parity engine.

```
re-agent reverse --class CTrain
    │
    ├── Config (re-agent.yaml + env + CLI)
    │   └── project_profile (stub_markers, hook_patterns, source_layout)
    │
    ├── Orchestrator (single / class runner)
    │   ├── Function Picker (ranks by caller count, filters completed)
    │   ├── Context Gatherer (decompile + xrefs + structs)
    │   │
    │   ├── Agent Loop (reverser → checker → fix, max N rounds)
    │   │   ├── LLM Providers: Claude (Anthropic SDK) | Codex (OpenAI SDK)
    │   │   └── Prompt Templates (customizable .md files)
    │   │
    │   ├── Parity Engine (GREEN/YELLOW/RED verification gate)
    │   │   ├── Source Indexer (C++ body parser)
    │   │   ├── 11 Heuristic Signals (all configurable/toggleable)
    │   │   └── Semantic Rules + Manual Approvals
    │   │
    │   └── Session State (JSON progress file)
    │
    └── RE Backend: ghidra-ai-bridge
        └── Capability flags → graceful degradation
```

## Installation

```bash
pip install re-agent
```

For Ghidra integration:
```bash
pip install "re-agent[ghidra-bridge]"
```

## Quick Start

```bash
# 1. Initialize project config
re-agent init

# 2. Edit re-agent.yaml with your project settings

# 3. Reverse a single function
re-agent reverse --address 0x6F86A0

# 4. Reverse all functions in a class
re-agent reverse --class CTrain --max-functions 10

# 5. Run parity checks
re-agent parity --address 0x6F86A0

# 6. Check progress
re-agent status
```

## Configuration

re-agent uses a layered configuration system (highest priority first): CLI flags > environment variables (`RE_AGENT_*`) > `re-agent.yaml` > defaults.

```yaml
llm:
  provider: claude           # claude | openai
  model: claude-sonnet-4-5-20250929
  # api_key: set via RE_AGENT_LLM_API_KEY env var

backend:
  type: ghidra-bridge
  cli_path: ~/ghidra-tools/ghidra

orchestrator:
  max_review_rounds: 4
  max_functions_per_class: 10

project_profile:
  source_root: ./source/game_sa
  hook_patterns:
    - 'RH_ScopedInstall\s*\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+)'
  stub_markers: ["NOTSA_UNREACHABLE"]
  stub_call_prefix: "plugin::Call"
```

See [docs/configuration.md](docs/configuration.md) for all options.

## CLI Reference

| Command | Description |
|---------|-------------|
| `re-agent init` | Generate `re-agent.yaml` config file |
| `re-agent reverse --address ADDR` | Reverse a single function |
| `re-agent reverse --class CLASS` | Reverse all functions in a class |
| `re-agent reverse --dry-run` | Show what would be reversed |
| `re-agent parity --address ADDR` | Run parity checks on a function |
| `re-agent parity --filter REGEX` | Run parity checks matching pattern |
| `re-agent status` | Show reversal progress |
| `re-agent status --class CLASS` | Show progress for a specific class |

## LLM Providers

- **Claude** (Anthropic SDK) — set `ANTHROPIC_API_KEY`
- **Codex** (OpenAI SDK) — set `OPENAI_API_KEY`

## Parity Engine

The parity engine runs 11 configurable heuristic signals to verify reversed code matches the original binary:

| Signal | Level | Description |
|--------|-------|-------------|
| Missing source | RED | No source body found for hooked function |
| Stub markers | RED | Source contains stub markers (e.g., NOTSA_UNREACHABLE) |
| Trivial stub | RED | Plugin-call heavy with tiny body and no control flow |
| Large ASM tiny source | RED | ASM >= 80 instructions but source <= 12 lines |
| Plugin-call heavy | YELLOW | Plugin calls dominate the function body |
| Short body | YELLOW | Body has fewer than 6 lines |
| Low call count | YELLOW | Decompile shows many callees but source has few |
| FP sensitivity | YELLOW | ASM has floating-point ops but source doesn't |
| Call count mismatch | YELLOW | Source call count differs significantly from ASM |
| NaN logic | YELLOW | Decompile has NaN handling but source doesn't |
| Inline wrapper | INFO | Function is a thin inline wrapper |

## Safety

- **No auto-commit**: re-agent writes code but never commits or pushes
- **Bounded retries**: Hard cap on fix loop iterations (default: 4)
- **Deterministic logs**: Every LLM call logged with timestamps
- **No destructive ops**: Never deletes files, modifies git, or runs builds
- **Session isolation**: Progress appended, never overwritten

## Development

```bash
git clone https://github.com/dryxio/auto-re-agent.git
cd auto-re-agent
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

pytest tests/
ruff check src/
mypy src/re_agent/
```

## License

MIT
