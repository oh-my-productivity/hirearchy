"""The number of collected tests never drops (ARCHITECTURE.md section 7: moves keep every test, nothing is deleted or skipped away).

``baseline_test_count.txt`` is the count of the commit this scaffold was built on. A step that adds tests may raise it (a diff of
that file is a review item); lowering it is forbidden. The relocation manifest of 7.3 (``test_relocation_count``) belongs to step E0.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import REPO

pytestmark = pytest.mark.architecture

BASELINE = Path(__file__).with_name("baseline_test_count.txt")


def test_the_collected_count_is_at_least_the_baseline():
    baseline = int(BASELINE.read_text(encoding="utf-8").split()[0])
    result = subprocess.run([sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"], capture_output=True,
                            text=True, cwd=REPO, timeout=600)
    match = re.search(r"(\d+) tests? collected", result.stdout)
    assert match, result.stdout[-500:] + result.stderr[-500:]
    assert int(match.group(1)) >= baseline, f"{match.group(1)} collected < baseline {baseline}: a test was deleted or lost"
