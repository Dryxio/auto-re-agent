# Getting Started

The `0.2.0` packages are not yet published on PyPI. Install the current source
versions from GitHub:

```bash
python3 -m pip install --upgrade \
  "ghidra-ai-bridge[headless] @ git+https://github.com/Dryxio/ghidra-ai-bridge.git@main" \
  "auto-re-agent @ git+https://github.com/Dryxio/auto-re-agent.git@main"
```

## Prepare Ghidra

```bash
ghidra-bridge init
# Edit ghidra-bridge.yaml with the local Ghidra project and program.
ghidra-bridge export all
ghidra-bridge build-map # optional when source/hook patterns are configured
ghidra-bridge info
```

## Configure the agent

```bash
re-agent init --profile generic-cpp
```

Edit `re-agent.yaml` to configure:

- an authenticated LLM provider;
- `backend.cli_path: ghidra-bridge`;
- the project source paths and patterns;
- trusted build/test commands for candidate validation.

Validation is strict by default. With no configured commands it returns
`UNKNOWN`, which `require_verified: true` rejects. Configure meaningful project
gates and set `trust_configured_commands: true`, or explicitly disable
validation for an unverified exploratory run.

## Run

```bash
# Start with one function
re-agent reverse --address 0x401000

# Then run a bounded class batch
re-agent reverse --class CTrain --max-functions 5

# Analyze existing source-tree parity
re-agent parity --address 0x401000 --strict-exit

# Inspect recorded progress
re-agent status
```

See the repository [README](../README.md) for providers, validation semantics,
profiles, outputs, safety notes, and the complete CLI overview.
