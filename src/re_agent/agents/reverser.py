"""Reverser agent — gathers context and asks LLM to produce reversed C++ code."""
from __future__ import annotations

import re
from pathlib import Path

from re_agent.agents.source_context import SourceContextBuilder
from re_agent.backend.protocol import REBackend
from re_agent.config.schema import ProjectProfile
from re_agent.core.models import FunctionTarget
from re_agent.core.session import Session
from re_agent.llm.protocol import LLMProvider, Message
from re_agent.parity.source_indexer import SourceIndexer
from re_agent.utils.templates import render_template

PROMPTS_DIR = Path(__file__).parent / "prompts"
CODE_BLOCK_RE = re.compile(r"```(?:cpp|c\+\+)?\s*\n(.*?)```", re.S)
REVERSED_TAG_RE = re.compile(r"REVERSED_FUNCTION:\s*(.+)")


class ReverserAgent:
    """Gathers decompile context and asks the LLM to reverse a function."""

    def __init__(
        self,
        llm: LLMProvider,
        backend: REBackend,
        source_root: Path | None = None,
        project_profile: ProjectProfile | None = None,
        indexer: SourceIndexer | None = None,
        session: Session | None = None,
        report_dir: Path | None = None,
    ) -> None:
        self.llm = llm
        self.backend = backend
        self._source_context_builder: SourceContextBuilder | None = None
        if source_root is not None and project_profile is not None and source_root.exists():
            self._source_context_builder = SourceContextBuilder(
                source_root=source_root,
                profile=project_profile,
                indexer=indexer,
                session=session,
                report_dir=report_dir,
            )
        self._conversation_id: str | None = None
        self.last_prompt: str = ""
        self.last_response: str = ""

    def reverse(self, target: FunctionTarget) -> tuple[str, str]:
        """Reverse a function. Returns (code, reversed_function_tag)."""
        # Gather context
        decompile_result = self.backend.decompile(target.address)
        decompiled = decompile_result.raw_output

        caps = self.backend.capabilities

        xrefs_text = ""
        if caps.has_xrefs:
            try:
                xrefs = self.backend.xrefs_from(target.address)
                xrefs_text = "\n".join(f"- {x.name} ({x.address}) [{x.ref_type}]" for x in xrefs) or "None found"
            except Exception:
                xrefs_text = "Unavailable"

        structs_text = ""
        if caps.has_structs and target.class_name:
            try:
                struct = self.backend.get_struct(target.class_name)
                if struct:
                    structs_text = f"{struct.name} (size: {struct.size})\n"
                    structs_text += "\n".join(
                        f"  +0x{f.offset:X} {f.type_str} {f.name} (size: {f.size})"
                        for f in struct.fields
                    )
            except Exception:
                structs_text = "Unavailable"

        system_prompt = render_template(PROMPTS_DIR / "reverser_system.md")
        source_context = ""
        if self._source_context_builder is not None:
            source_context = self._source_context_builder.build(target)
        task_prompt = render_template(
            PROMPTS_DIR / "reverser_task.md",
            class_name=target.class_name,
            function_name=target.function_name,
            address=target.address,
            decompiled=decompiled,
            xrefs=xrefs_text or "None",
            structs=structs_text or "None",
            source_context=source_context or "None",
        )

        if self._conversation_id is None and self.llm.supports_conversations:
            self._conversation_id = self.llm.new_conversation(system_prompt)

        self.last_prompt = task_prompt

        if self._conversation_id:
            response = self.llm.resume(self._conversation_id, task_prompt)
        else:
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=task_prompt),
            ]
            response = self.llm.send(messages)

        self.last_response = response
        code = self._extract_code(response)
        tag = self._extract_tag(response)
        return code, tag

    def fix(
        self,
        checker_report: str,
        issues: list[str],
        fix_instructions: list[str],
        target: FunctionTarget,
        objective_findings: list[str] | None = None,
    ) -> tuple[str, str]:
        """Ask the reverser to fix code based on checker feedback."""
        all_issues = list(issues)
        all_fix_instructions = list(fix_instructions)
        if objective_findings:
            all_issues.extend(f"objective verifier: {finding}" for finding in objective_findings)
            all_fix_instructions.extend(
                "Resolve objective mismatch: " + finding for finding in objective_findings
            )
        fix_prompt = render_template(
            PROMPTS_DIR / "fix_instructions.md",
            checker_report=checker_report,
            issues="\n".join(f"- {i}" for i in all_issues),
            fix_instructions="\n".join(f"- {i}" for i in all_fix_instructions),
            class_name=target.class_name,
            function_name=target.function_name,
            address=target.address,
        )

        self.last_prompt = fix_prompt

        if self._conversation_id:
            response = self.llm.resume(self._conversation_id, fix_prompt)
        else:
            messages = [Message(role="user", content=fix_prompt)]
            response = self.llm.send(messages)

        self.last_response = response
        code = self._extract_code(response)
        tag = self._extract_tag(response)
        return code, tag

    @staticmethod
    def _extract_code(response: str) -> str:
        m = CODE_BLOCK_RE.search(response)
        return m.group(1).strip() if m else response.strip()

    @staticmethod
    def _extract_tag(response: str) -> str:
        m = REVERSED_TAG_RE.search(response)
        return m.group(1).strip() if m else ""
