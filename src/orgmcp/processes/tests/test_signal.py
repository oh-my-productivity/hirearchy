# mypy: ignore-errors
# A test moved from tests/ by tools/relocate_tests.py: untyped until it is converted. Delete the first line when this file is typed.

from orgmcp.processes._spawn import PopenHandle


def test_signalling_a_finished_run_is_harmless():
    import subprocess

    proc = subprocess.Popen(["true"], start_new_session=True)
    proc.wait()
    PopenHandle(proc).signal_group(9)
