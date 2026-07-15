"""Resumable evaluation run storage.

scripts/run_evaluation.py calls a real LLM once per query; if the OpenAI
account hits a rate limit or exhausts its quota partway through a run (a
real risk with a 38-query dataset), the run should not have to start over
from query 1. `RunCheckpoint` persists each case's result to disk as soon
as it's computed, so a re-run skips whatever's already done and only
processes the remaining cases -- the resumed run is a continuation of the
same run, not a new one, until every case has a result.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

RESULTS_DIR = Path("evaluation/results")
CHECKPOINT_PATH = RESULTS_DIR / "checkpoint.json"
LATEST_PATH = RESULTS_DIR / "latest.json"


class RunCheckpoint:
    """Tracks per-case results for one (possibly interrupted-and-resumed)
    evaluation run, keyed by case name.
    """

    def __init__(self, path: Path = CHECKPOINT_PATH):
        self.path = path
        self.results: Dict[str, Dict] = self._load()

    def _load(self) -> Dict[str, Dict]:
        if not self.path.exists():
            return {}
        with open(self.path) as f:
            data = json.load(f)
        return data.get("results", {})

    def __contains__(self, name: str) -> bool:
        return name in self.results

    def __len__(self) -> int:
        return len(self.results)

    def record(self, name: str, result: Dict) -> None:
        """Save one case's result immediately -- called right after each
        LLM call succeeds, so a failure on case N+1 never loses cases
        1..N.
        """
        self.results[name] = result
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "results": self.results,
        }
        tmp_path = self.path.with_suffix(".json.tmp")
        with open(tmp_path, "w") as f:
            json.dump(payload, f, indent=2)
        tmp_path.replace(self.path)  # atomic rename on POSIX filesystems

    def discard(self) -> None:
        """Wipe this checkpoint (used by --fresh) without touching any
        already-archived completed runs.
        """
        self.results = {}
        if self.path.exists():
            self.path.unlink()

    def archive_and_clear(self, report: Dict) -> Path:
        """Called once every case in the dataset has a result. Writes a
        timestamped, permanent record of the completed run (so
        .claude/skills/evaluate.md's "regressions compared to previous
        runs, if a baseline exists" has something to actually compare
        against), refreshes `latest.json`, and clears the in-progress
        checkpoint since there is nothing left to resume.
        """
        self.path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_path = self.path.parent / f"run_{timestamp}.json"
        payload = {
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "report": report,
            "results": self.results,
        }
        with open(archive_path, "w") as f:
            json.dump(payload, f, indent=2)
        with open(LATEST_PATH, "w") as f:
            json.dump(payload, f, indent=2)
        if self.path.exists():
            self.path.unlink()
        return archive_path
