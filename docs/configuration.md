# Configuration

re-agent is configured primarily through `re-agent.yaml`, plus the supported
environment variables and runtime CLI flags documented below.

## Priority Order

Supported CLI overrides > supported environment variables > YAML config > defaults

## Environment Variables

| Variable | Maps to |
|----------|---------|
| `RE_AGENT_LLM_PROVIDER` | `llm.provider` |
| `RE_AGENT_LLM_API_KEY` | `llm.api_key` |
| `RE_AGENT_LLM_MODEL` | `llm.model` |
| `RE_AGENT_LLM_BASE_URL` | `llm.base_url` |
| `RE_AGENT_BACKEND_CLI_PATH` | `backend.cli_path` |
| `RE_AGENT_BACKEND_TIMEOUT` | `backend.timeout_s` |

## LLM Config

```yaml
llm:
  provider: "claude"        # claude | claude-cli | openai | openai-compat | codex
  model: "claude-sonnet-4-5-20250929"
  api_key: null
  base_url: null
  max_tokens: 4096
  temperature: 0.0
  timeout_s: 1800
  input_cost_per_million: 0.0
  output_cost_per_million: 0.0
```

Notes:

- `claude` uses the Anthropic SDK and typically reads `ANTHROPIC_API_KEY`
- `openai` and `openai-compat` use the OpenAI-compatible chat completions provider and typically read `OPENAI_API_KEY`
- `codex` uses the local `codex` CLI and ChatGPT login credentials instead of an API key
- `claude-cli` uses the local Claude Code CLI login. `cli_path`,
  `max_budget_usd`, and `effort` are optional.

Independent role overrides inherit the top-level `llm` block only when the
role is omitted:

```yaml
agents:
  reverser:
    provider: claude-cli
    model: sonnet
    max_budget_usd: 1.0
    effort: high
  checker:
    provider: codex
    model: gpt-5.4
```

A present role block is a complete `LLMConfig`; its individual fields are not
merged with the top-level block.

## Backend Config

```yaml
backend:
  type: ghidra-bridge
  cli_path: ghidra-bridge
  timeout_s: 45
```

The `ghidra-ai-bridge` package installs the `ghidra-bridge` executable. Prepare
its exports separately before running reversal commands.

## Project Profile

The `project_profile` section makes re-agent work across different RE projects.
This example is specifically for GTA-reversed-style source:

```yaml
project_profile:
  hook_patterns:
    - 'RH_ScopedInstall\s*\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+)'
  stub_markers: ["NOTSA_UNREACHABLE"]
  stub_call_prefix: "plugin::Call"
  source_root: "./source/game_sa"
  source_extensions: [".cpp", ".h", ".hpp"]
```

## Parity Config

```yaml
parity:
  enabled: true
  call_count_warn_diff: 3
  inline_wrapper_autoskip: false
```

## Orchestrator Config

```yaml
orchestrator:
  max_review_rounds: 4
  max_functions_per_class: 10
  objective_verifier_enabled: true
  objective_call_count_tolerance: 3
  objective_control_flow_tolerance: 2
  investigation_enabled: true
  max_investigations: 8
  selection_strategy: dependency-order # dependency-order | easiest-first | high-impact
  max_attempts_per_function: 3
```

## Candidate Validation

Generated code is written to a safe overlay. Commands can use both format
placeholders and environment variables.

```yaml
validation:
  enabled: true
  # true copies the project to a temporary isolated directory before commands
  copy_project: false
  project_root: .
  build_commands:
    - 'clang++ -fsyntax-only "{candidate_file}"'
  test_commands: []
  runtime_commands: [] # optional differential/record-replay harness
  require_build: true
  require_tests: false
  require_runtime: false
  require_verified: true # UNKNOWN validation results block acceptance
  trust_configured_commands: false # explicit attestation for project-owned shell gates
  parity_fail_on_red: true
  parity_fail_on_yellow: false
  command_timeout_s: 900
  working_directory: .
  keep_project_copy: false # delete isolated full-project copies after validation
```

With `copy_project: true`, the default working directory becomes the isolated
project copy and the source candidate replaces the real relative source file.
Configure the project inside that copy (for example `cmake -S . -B build`)
before building because generated `build/` directories are intentionally not copied.
With it disabled, build commands must consume `{candidate_file}` or
`RE_AGENT_CANDIDATE_FILE` explicitly.

Shell commands are user-defined and cannot be proven meaningful merely by
inspecting their text. They therefore produce `UNKNOWN` until
`trust_configured_commands: true` explicitly attests that the configured
project commands compile/test the candidate. The non-isolated placeholder
check is an additional mistake detector, not a semantic proof.
