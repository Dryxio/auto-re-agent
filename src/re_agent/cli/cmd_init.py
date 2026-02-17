"""re-agent init command — generates config file."""
from __future__ import annotations

import argparse
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from re_agent.config.defaults import DEFAULT_CONFIG_YAML, EXAMPLE_PROFILE_TEMPLATES


def cmd_init(args: argparse.Namespace) -> int:
    config_path = Path(args.config)

    if config_path.exists():
        print(f"Config already exists: {config_path}")
        print("Delete it first if you want to regenerate.")
        return 1

    content = DEFAULT_CONFIG_YAML

    if args.profile and args.profile in EXAMPLE_PROFILE_TEMPLATES:
        print(f"Using profile template: {args.profile}")
        # Parse the default YAML, overlay the profile, and re-serialize
        data = yaml.safe_load(content)
        profile_overrides = EXAMPLE_PROFILE_TEMPLATES[args.profile]
        if "project_profile" not in data:
            data["project_profile"] = {}
        for key, value in profile_overrides.items():
            data["project_profile"][key] = value
        content = "# re-agent configuration\n"
        content += f"# Profile: {args.profile}\n\n"
        content += yaml.dump(data, default_flow_style=False, sort_keys=False)
    elif args.profile:
        available = ", ".join(EXAMPLE_PROFILE_TEMPLATES)
        print(f"Unknown profile: {args.profile}")
        print(f"Available profiles: {available}")
        return 1

    config_path.write_text(content, encoding="utf-8")
    print(f"Created {config_path}")
    print("Edit it to configure your LLM provider, backend, and project profile.")
    return 0
