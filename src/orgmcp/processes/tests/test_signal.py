# mypy: ignore-errors
# A test moved from tests/ by refactor step E1: not type-checked strictly (production code is). Delete the first line when this file is typed.

from orgmcp.processes._spawn import PopenHandle


def test_signalling_a_finished_run_is_harmless():
    import subprocess

    proc = subprocess.Popen(["true"], start_new_session=True)
    proc.wait()
    PopenHandle(proc).signal_group(9)
