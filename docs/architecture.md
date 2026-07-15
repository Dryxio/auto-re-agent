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

- **CLI**: argparse entry points (init, reverse, parity, status)
- **Config**: YAML + env + CLI overlay, project profiles
- **Orchestrator**: Single function or class-level auto-advance
- **Agents**: independently configurable Reverser + Checker with fix loop
- **LLM**: Protocol-based providers (Claude, Codex)
- **Backend**: RE tool abstraction with context, vtable, global, string,
  normalized P-code, and CFG capability flags
- **Parity**: 11-signal verification engine with scoring
- **Validation**: safe candidate overlay plus configurable build/test commands
- **Knowledge graph**: persistent calls, strings, and global relationships
- **Reports**: JSON/markdown output, session tracking
