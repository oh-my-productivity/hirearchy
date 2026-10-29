"""Scratch patches of the P2 harness for the labelled sensitivity (reported, NOT adopted). Applied only to copies under
/tmp/hirearchy-p2-score/h-*/; the frozen harness under EV/harness/ is never written. Each patch is one exact replacement."""
import sys
from pathlib import Path

ROOT = Path("/tmp/hirearchy-p2-score")
PATCHES = {
    # 5(a): finish_stream.sh:68 writes "total: session-store empty-argument failed calls: 23 (...)"; gate_p1.py:339 read only "^total: (\d+)"
    "5a": ("gate_p1.py",
           'm = re.findall(r"^total: (\\d+)", ec, re.M)',
           'm = re.findall(r"^total: (?:session-store empty-argument failed calls: )?(\\d+)", ec, re.M)'),
    # 6.2: watch_views.sh runs run_stream on each service's view, which loaded the stream's most frequent service; name the view's own service
    "62": ("rederive_watch.py",
           "    w = load_world(stream)\n    der = Derivation(w)",
           "    w = load_world(stream, stream.name.split(\"--\", 1)[1] if \"--\" in stream.name else None)\n    der = Derivation(w)"),
    # 6.3: Org.view linked msgs/ (and service/, playbook/) to a relative self.ev, so a relative EV left dangling links; resolve it
    "63": ("rederive_p2.py",
           '        (d / "msgs").symlink_to(self.ev / "msgs")\n        src = self.ev / "services-all" / svc_dir',
           '        (d / "msgs").symlink_to(self.ev.resolve() / "msgs")\n        src = self.ev.resolve() / "services-all" / svc_dir'),
}
TARGETS = {"h-5a": ["5a"], "h-62": ["62"], "h-63": ["63"], "h-all": ["5a", "62", "63"]}

for d, keys in TARGETS.items():
    for k in keys:
        f, old, new = PATCHES[k]
        p = ROOT / d / f
        t = p.read_text()
        n = t.count(old)
        if n != 1:
            sys.exit(f"{d}/{f}: patch {k} matched {n} times")
        p.write_text(t.replace(old, new))
        print(f"patched {d}/{f} ({k})")
