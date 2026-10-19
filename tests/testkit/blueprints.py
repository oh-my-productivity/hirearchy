"""Blueprints (as dicts) that several test modules start from."""


def code_bp(tmp_path):
    ws = tmp_path / "proj"
    ws.mkdir(exist_ok=True)
    return {
        "mission": "Build a small CLI that converts CSV to markdown tables.",
        "needs": {
            "scope": "csv2md CLI only; no web UI",
            "deliverable": {"description": "A Python package csv2md with a CLI", "format": "python package"},
            "quality_bar": "tests pass from a clean checkout",
            "workspace": str(ws),
            "budget_runs": 30,
            "model_policy": "one model for all",
            "review": True,
            "approval": "approve plan first",
            "progress": "one line on request",
            "code": {"tests": "pytest, one per criterion", "packaging": "uv + pyproject", "commits": "local commits, never push"},
        },
        "agents": [{
            "name": "lead", "template": "manager",
            "children": [{"name": "dev", "template": "engineer"}, {"name": "qa", "template": "tester"},
                         {"name": "cr", "template": "code-reviewer"}],
        }],
        "task": {
            "title": "Build csv2md",
            "goal": "Implement the csv2md CLI in the workspace",
            "acceptance": ["`uv run pytest -q` passes with at least 5 tests", "`csv2md in.csv` prints a markdown table to stdout",
                           "the work is committed locally and nothing is pushed"],
        },
    }
