from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Task:
    action: str
    argument: str | None = None


def load_tasks(path: Path) -> list[Task]:
    tasks: list[Task] = []
    if not path.exists():
        return [Task(action="collect_metrics")]

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            action, argument = line.split(":", 1)
            tasks.append(Task(action=action.strip(), argument=argument.strip()))
        else:
            tasks.append(Task(action=line))

    return tasks or [Task(action="collect_metrics")]
