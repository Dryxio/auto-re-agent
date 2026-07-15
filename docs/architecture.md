# Architecture

re-agent is structured as a layered pipeline:

```
CLI -> Config -> Orchestrator -> Evidence Loop -> LLM Providers
                      |              |
                      v              v
              Function Picker    RE Backend Protocol
                      |
                      v
       Candidate Overlay -> Build/Test -> Parity/IR Gate
```

## Layers

- **CLI**: argparse entry points (init, reverse, parity, status, estimate)
- **Config**: YAML + supported environment/CLI overrides, project profiles
- **Orchestrator**: Single function or class-level auto-advance
- **Agents**: independently configurable Reverser + Checker with fix loop
- **LLM**: Protocol-based providers (Claude API/CLI, OpenAI-compatible, Codex CLI)
- **Backend**: RE tool abstraction with context, vtable, global, string,
  normalized P-code, and CFG capability flags
- **Parity**: 11-signal verification engine with scoring
- **Validation**: safe candidate overlay plus configurable build/test/runtime commands
- **Knowledge graph**: persistent calls, strings, and global relationships
- **Reports**: JSON/markdown output, session tracking
