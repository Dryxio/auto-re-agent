# Architecture

re-agent is structured as a layered pipeline:

```
CLI -> Config -> Orchestrator -> Agent Loop -> LLM Providers
                      |              |
                      v              v
              Function Picker    RE Backend (Ghidra)
                      |
                      v
               Parity Engine
```

## Layers

- **CLI**: argparse entry points (init, reverse, parity, status)
- **Config**: YAML + env + CLI overlay, project profiles
- **Orchestrator**: Single function or class-level auto-advance
- **Agents**: Reverser + Checker with fix loop
- **LLM**: Protocol-based providers (Claude, Codex)
- **Backend**: RE tool abstraction with capability flags
- **Parity**: 11-signal verification engine with scoring
- **Reports**: JSON/markdown output, session tracking
