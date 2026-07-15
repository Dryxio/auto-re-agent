# Getting Started

## Installation

```bash
# Standard installation with the Ghidra query bridge
python3 -m pip install --upgrade "auto-re-agent[ghidra-bridge]>=0.2.0"

# Or include PyGhidra for headless exports
python3 -m pip install --upgrade "auto-re-agent[headless]>=0.2.0"
```

## Quick Start

1. Initialize configuration:
```bash
re-agent init
```

2. Edit `re-agent.yaml` with your LLM API key and Ghidra bridge path.

3. Reverse a single function:
```bash
re-agent reverse --address 0x6F86A0 --class CTrain
```

4. Reverse a full class:
```bash
re-agent reverse --class CTrain --max-functions 5
```

5. Run parity checks:
```bash
re-agent parity --limit 50
```

6. Check progress:
```bash
re-agent status
```
