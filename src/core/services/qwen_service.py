"""
Qwen Code error analysis service.
Runs `echo <prompt> | qwen` as async subprocess, parses structured response.
"""

from __future__ import annotations

import asyncio
import logging
import shlex
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class QwenAnalysisResult:
    root_cause: str
    suggested_fix: str
    affected_files: list[str]
    severity: str  # critical / high / medium / low
    raw_response: str


async def analyze_error(
    title: str,
    culprit: str,
    traceback: str,
    project: str,
) -> QwenAnalysisResult:
    """Run Qwen Code analysis on an error and return structured result."""
    prompt = (
        f"You are a senior Python developer analyzing a production error.\n\n"
        f"Project: {project}\n"
        f"Error: {title}\n"
        f"Culprit: {culprit}\n\n"
        f"Traceback:\n"
        f"{traceback}\n\n"
        f"Respond ONLY in this exact format (no markdown, no extra text):\n"
        f"ROOT_CAUSE: <one sentence>\n"
        f"SEVERITY: <critical|high|medium|low>\n"
        f"AFFECTED_FILES: <comma-separated file paths, or 'unknown'>\n"
        f"FIX: <concrete fix description, max 3 sentences>"
    )

    try:
        proc = await asyncio.create_subprocess_shell(
            f"echo {shlex.quote(prompt)} | qwen",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        raw = stdout.decode().strip()

        if proc.returncode != 0:
            stderr_text = stderr.decode().strip()
            logger.error("Qwen exited with %d: %s", proc.returncode, stderr_text)
            return QwenAnalysisResult(
                root_cause=f"Qwen failed (code {proc.returncode}): {stderr_text[:200]}",
                suggested_fix="Check logs manually",
                affected_files=[],
                severity="unknown",
                raw_response="",
            )

        return _parse_response(raw)

    except TimeoutError:
        logger.error("Qwen analysis timed out after 120s")
        return QwenAnalysisResult(
            root_cause="Analysis timed out",
            suggested_fix="Run manually",
            affected_files=[],
            severity="unknown",
            raw_response="",
        )
    except Exception as exc:  # noqa: BLE001 — catch-all for subprocess errors
        logger.exception("Qwen analysis failed: %s", exc)
        return QwenAnalysisResult(
            root_cause=f"Analysis failed: {exc}",
            suggested_fix="Check logs",
            affected_files=[],
            severity="unknown",
            raw_response="",
        )


def _parse_response(raw: str) -> QwenAnalysisResult:
    """Parse Qwen response into structured fields."""
    lines: dict[str, str] = {}
    for line in raw.splitlines():
        if ": " in line:
            key, _, value = line.partition(": ")
            lines[key.strip().upper()] = value.strip()

    affected = lines.get("AFFECTED_FILES", "")
    affected_files = [
        f.strip() for f in affected.split(",") if f.strip() and f.strip().lower() != "unknown"
    ]

    return QwenAnalysisResult(
        root_cause=lines.get("ROOT_CAUSE", "Unknown"),
        suggested_fix=lines.get("FIX", "Unknown"),
        affected_files=affected_files,
        severity=lines.get("SEVERITY", "unknown").lower(),
        raw_response=raw,
    )
