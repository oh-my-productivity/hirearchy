# mypy: ignore-errors
"""The kit of the exit-check replays of phase 0b (``tests/testkit/org_replay.py`` and its manifest; design 19.1): it builds an organization from the
files a study kept, and a listed file that is missing, a message that does not parse or an id kept twice with different bytes fails the test that asks,
never skips it (a replay that quietly did not run proves nothing)."""

import re
from pathlib import Path

import pytest
from testkit import org_replay_manifest
from testkit.e4_replay import evidence
from testkit.org_replay import deliverable_folder, index_entries, log_block, materialize, md5_of, message_files, newest_version, utc_us
from testkit.org_replay_manifest import MANIFESTS, PREFIXES, VARIANTS

Failed = pytest.fail.Exception
CORPORA = ("E", "E2", "A5", "E3", "E4-s1r", "E4-s2r", "E4-s3")
WITH_DELIVERABLES = ("E4-s1r", "E4-s2r", "E4-s3")
WITH_SERVICE = tuple(c for c in CORPORA if c != "A5")


def message(msg_id: str, sender: str, to: str, body: str = "Do it.") -> str:
    return f"---\nid: {msg_id}\nfrom: {sender}\nto: {to}\ntype: task\ntitle: T\ncreated: '2026-10-18T02:16:44+00:00'\nhops: 0\n---\n{body}\n"


def mini(tmp_path: Path, folders: dict[str, dict[str, str]], **more) -> dict:
    """A manifest of a corpus of one directory (``tmp_path/ev``): ORG.md and the message folders given as ``{folder: {file name: text}}``; ``boxes`` lists
    each folder as the ``sent`` box of root unless ``more`` says otherwise."""
    evidence_dir = tmp_path / "ev"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "ORG.md").write_text("---\nmax_depth: 4\n---\n# Organization\n", encoding="utf-8")
    for folder, files in folders.items():
        (evidence_dir / folder).mkdir(parents=True, exist_ok=True)
        for name, text in files.items():
            (evidence_dir / folder / name).write_text(text, encoding="utf-8")
    entry = {
        "evidence": evidence_dir, "service": None, "owner": None, "boxes": tuple((folder, "root", "sent") for folder in folders),
        "received_from_sent": True, "contracts": (), "playbooks": (), "run_logs": (), "deliverables": (), "team_files": None, "charters": {},
        "org_md": "ORG.md",
    }
    return {**entry, **more}


# ------------------------------------------------------------------------------------------------- the manifest


def test_the_manifest_has_the_corpora_of_19_1_and_every_entry_has_the_same_keys():
    assert set(MANIFESTS) == set(CORPORA)
    assert all(tuple(sorted(entry)) == tuple(sorted(org_replay_manifest.ENTRY_KEYS)) for entry in MANIFESTS.values())


def test_prefixes_map_to_addresses():
    """E3 and E4 name an agent by a prefix of a folder (`lead-reviewer-read`): it is the address `lead/reviewer`; the empty prefix is root."""
    assert PREFIXES == {
        "": "root", "lead": "lead", "lead-reviewer": "lead/reviewer", "lead-writer": "lead/writer", "lead-checker": "lead/checker",
        "lead-reader": "lead/reader",
    }
    boxes = {folder: (address, box) for folder, address, box in MANIFESTS["E3"]["boxes"]}
    assert boxes["msgs/lead-reviewer-read"] == ("lead/reviewer", "read") and boxes["msgs/lead-writer-sent"] == ("lead/writer", "sent")
    assert boxes["msgs/read"] == ("root", "read") and boxes["msgs/lead-inbox"] == ("lead", "inbox")
    s1r = {folder: (address, box) for folder, address, box in MANIFESTS["E4-s1r"]["boxes"]}
    assert s1r["msgs/lead-checker-sent"] == ("lead/checker", "sent") and s1r["msgs/lead-reader-read"] == ("lead/reader", "read")


@pytest.mark.parametrize("corpus", CORPORA)
def test_every_kept_message_folder_is_listed_and_every_listed_one_exists(corpus):
    """A folder of messages the manifest forgets would be dropped quietly; one it lists and the study does not have fails the build."""
    entry = MANIFESTS[corpus]
    source = Path(entry["evidence"])
    listed = {folder for folder, _, _ in entry["boxes"]}
    kept = {f"msgs/{p.name}" for p in (source / "msgs").iterdir() if p.is_dir()}
    if corpus == "A5":
        assert kept == set() and listed == {"msgs/sent__*.md", "msgs/lead_sent__*.md"}
    else:
        assert kept == listed
    assert all(p.suffix == ".md" for folder in kept for p in (source / folder).iterdir())  # a folder of messages holds nothing else


@pytest.mark.parametrize("corpus", WITH_SERVICE)
def test_contract_and_playbook_versions_are_the_pinned_ones(corpus):
    entry = MANIFESTS[corpus]
    source = Path(entry["evidence"])
    for kind, key in (("contracts", "name"), ("playbooks", "service")):
        pinned = entry[kind]
        assert [v for _, v in pinned if v is not None] == list(range(1, len(pinned)))  # the history is v1, v2, ... then the current one
        for file, version in pinned:
            meta, _ = evidence(source / file)
            assert meta[key] == entry["service"]
            assert version is None or meta["version"] == version
        assert evidence(source / pinned[-1][0])[0]["version"] == len(pinned)  # the current one follows the history


@pytest.mark.parametrize("corpus", CORPORA)
def test_the_organization_holds_the_kept_files_of_the_corpus(corpus, tmp_path):
    entry = MANIFESTS[corpus]
    org = materialize(corpus, tmp_path)
    assert org == tmp_path.resolve() / "org"
    assert (org / "ORG.md").read_bytes() == (Path(entry["evidence"]) / entry["org_md"]).read_bytes()
    for address in entry["charters"]:
        assert (org / address / "AGENT.md").read_bytes() == (Path(entry["evidence"]) / entry["charters"][address]).read_bytes()
    kept = {p.name for folder, _, _ in entry["boxes"] for p in message_files(Path(entry["evidence"]), folder)}
    placed = {p.name for p in org.rglob("*.md") if re.match(r"\d{8}T\d{6}", p.name)}
    assert {n.split("__")[-1] for n in kept} <= placed  # every kept message is somewhere in the organization


# ------------------------------------------------------------------------------------------------- messages


def test_the_same_id_kept_twice_must_be_byte_identical(tmp_path):
    same = message("20261018T021644679563-root-b495", "root", "lead")
    ok = mini(tmp_path, {"a": {"20261018T021644679563-root-b495.md": same}, "b": {"20261018T021644679563-root-b495.md": same}})
    org = materialize("X", tmp_path / "ok", manifest=ok)
    assert (org / "sent" / "20261018T021644679563-root-b495.md").read_text(encoding="utf-8") == same
    other = tmp_path / "other"
    other.mkdir()
    differ = mini(other, {"a": {"20261018T021644679563-root-b495.md": same}, "b": {"20261018T021644679563-root-b495.md": same + "edited\n"}})
    with pytest.raises(Failed, match="kept twice with different bytes"):
        materialize("X", tmp_path / "differ", manifest=differ)


def test_a_message_goes_to_the_box_it_was_kept_in_and_a_sent_only_corpus_adds_the_recipients_copy(tmp_path):
    text = message("20261018T021658894998-lead-d702", "lead", "lead/writer")
    entry = mini(tmp_path, {"msgs": {"20261018T021658894998-lead-d702.md": text}}, boxes=(("msgs", "lead", "sent"),))
    org = materialize("X", tmp_path / "sentonly", manifest=entry)
    assert (org / "lead" / "sent" / "20261018T021658894998-lead-d702.md").read_text(encoding="utf-8") == text  # byte for byte, in its box
    assert (org / "lead" / "writer" / "read" / "20261018T021658894998-lead-d702.md").read_text(encoding="utf-8") == text  # the recipient's copy
    kept_both = materialize("X", tmp_path / "both", manifest={**entry, "received_from_sent": False})
    assert not (kept_both / "lead" / "writer" / "read").exists()  # a corpus that kept the received boxes gets only what was kept


def test_a_runtime_message_goes_to_its_recipient_only(tmp_path):
    """The runtime has no sent box: a note of the runtime kept in a `sent` folder (a sent-only corpus) is written to its recipient, not to a box of the
    runtime; kept in the recipient's `read` folder it is written there and nowhere else."""
    note = message("20261018T021658894998-runtime-0b01", "runtime", "lead")
    in_sent = mini(tmp_path, {"msgs": {"20261018T021658894998-runtime-0b01.md": note}}, boxes=(("msgs", "root", "sent"),))
    org = materialize("X", tmp_path / "a", manifest=in_sent)
    assert [p.name for p in org.rglob("*-runtime-*.md")] == ["20261018T021658894998-runtime-0b01.md"]
    assert (org / "lead" / "read" / "20261018T021658894998-runtime-0b01.md").is_file() and not (org / "sent").exists()
    other = tmp_path / "other"
    other.mkdir()
    received = mini(other, {"msgs": {"20261018T021658894998-runtime-0b01.md": note}}, boxes=(("msgs", "lead", "read"),), received_from_sent=True)
    org = materialize("X", tmp_path / "b", manifest=received)
    assert [str(p.relative_to(org)) for p in org.rglob("*-runtime-*.md")] == ["lead/read/20261018T021658894998-runtime-0b01.md"]


def test_a_message_that_does_not_parse_fails(tmp_path):
    for name, text, words in (
        ("20261018T021644679563-root-b495.md", "---\nid: [unclosed\n---\nbody\n", "does not parse"),
        ("20261018T021644679563-root-b495.md", "no frontmatter at all\n", "no id in its frontmatter"),
        ("20261018T021644679563-root-b495.md", message("20261018T021644679563-root-aaaa", "root", "lead"), "not named after its id"),
    ):
        folder = tmp_path / name[:4] / words[:4]
        folder.mkdir(parents=True)
        entry = mini(folder, {"msgs": {name: text}})
        with pytest.raises(Failed, match=words):
            materialize("X", folder / "out", manifest=entry)


def test_a_missing_listed_file_fails(tmp_path):
    """Every kind of listed file: a folder, a contract, a charter, a run-log folder, a delivered file, the ORG.md."""
    base = MANIFESTS["E4-s2r"]
    for key, broken in (
        ("boxes", (("msgs/no-such-folder", "root", "sent"),)),
        ("contracts", (("service/history--SERVICE.v1.md", 1), ("service/NOPE.md", None))),
        ("playbooks", (("playbook/NOPE.md", None),)),
        ("charters", {"lead": "org-files/NOPE.md"}),
        ("run_logs", (("run-logs/no-such-agent", "lead"),)),
        ("deliverables", (MANIFESTS["E4-s2r"]["deliverables"][0] | {"file": "memos/NOPE.md"},)),
        ("org_md", "org-files/NOPE.md"),
        ("team_files", "memos/versions/NOPE.txt"),
    ):
        with pytest.raises(Failed, match=r"no evidence (file|directory)|matches"):
            materialize("E4-s2r", tmp_path / key, manifest={**base, key: broken})
    nothing = mini(tmp_path, {}, boxes=(("msgs/sent__*.md", "root", "sent"),))
    with pytest.raises(Failed, match="no evidence file matches"):
        materialize("X", tmp_path / "glob", manifest=nothing)


# ------------------------------------------------------------------------------------------------- charters


def test_root_and_runtime_get_no_charter(tmp_path):
    """An address the messages name that has no kept charter gets a minimal one (`name` only), with its ancestors; root and the runtime get none."""
    entry = mini(tmp_path, {"msgs": {
        "20261018T021658894998-lead-d702.md": message("20261018T021658894998-lead-d702", "lead/writer", "root"),
        "20261018T021658894999-runtime-0b01.md": message("20261018T021658894999-runtime-0b01", "runtime", "lead/writer"),
    }})
    org = materialize("X", tmp_path / "out", manifest=entry)
    agents = sorted(str(p.parent.relative_to(org)) for p in org.rglob("AGENT.md"))
    assert agents == ["lead", "lead/writer"]
    assert (org / "lead" / "writer" / "AGENT.md").read_text(encoding="utf-8") == "---\nname: writer\n---\n"
    assert not (org / "AGENT.md").exists() and not (org / "runtime").exists() and not (org / "root").exists()


@pytest.mark.parametrize("corpus", CORPORA)
def test_the_real_corpora_get_no_charter_for_root_or_the_runtime(corpus, tmp_path):
    org = materialize(corpus, tmp_path)
    assert not (org / "AGENT.md").exists() and not (org / "runtime").exists() and not (org / "root").exists()
    assert (org / "lead" / "AGENT.md").is_file()


# ------------------------------------------------------------------------------------------------- the contract, the times, the deliverables


def contract_with_path(path: str) -> str:
    return f"---\nname: weekly-memo\nacceptance:\n- It is short.\ndeliverable:\n  description: A memo.\n  path: {path}\nbudget: 5\nversion: 1\n---\n"


def test_the_deliverable_path_is_rewritten_and_only_that(tmp_path):
    text = contract_with_path("/tmp/orgmcp-e-1/deliverables")
    entry = mini(
        tmp_path, {"msgs": {"20261018T021644679563-root-b495.md": message("20261018T021644679563-root-b495", "root", "lead")}},
        service="weekly-memo", owner="lead", contracts=(("c.md", None),),
    )
    (Path(entry["evidence"]) / "c.md").write_text(text, encoding="utf-8")
    org = materialize("X", tmp_path / "out", manifest=entry)
    made = (org / "lead" / "services" / "weekly-memo" / "SERVICE.md").read_text(encoding="utf-8")
    old, new = text.splitlines(), made.splitlines()
    assert len(old) == len(new)
    changed = [(a, b) for a, b in zip(old, new, strict=True) if a != b]
    assert changed == [("  path: /tmp/orgmcp-e-1/deliverables", f"  path: {(tmp_path / 'out').resolve() / 'no-deliverables'}")]
    assert made.endswith("budget: 5\nversion: 1\n---\n")
    assert not (tmp_path / "out" / "no-deliverables").exists()  # a corpus without deliverables: the folder is missing, never created
    no_path = mini(tmp_path / "np", {}, service="weekly-memo", owner="lead", contracts=(("c.md", None),))
    (Path(no_path["evidence"]) / "c.md").write_text("---\nname: x\n---\n", encoding="utf-8")
    with pytest.raises(Failed, match="no single `  path:` line"):
        materialize("X", tmp_path / "np-out", manifest=no_path)


@pytest.mark.parametrize("corpus", WITH_SERVICE)
def test_every_kept_contract_changes_in_its_path_line_alone(corpus, tmp_path):
    entry = MANIFESTS[corpus]
    source = Path(entry["evidence"])
    org = materialize(corpus, tmp_path)
    folder = deliverable_folder(tmp_path.resolve(), corpus)
    assert folder.name == ("deliverables" if corpus in WITH_DELIVERABLES else "no-deliverables")
    assert folder.is_dir() == (corpus in WITH_DELIVERABLES)
    place = org / "lead" / "services" / entry["service"]
    for file, version in entry["contracts"]:
        made = (place / ("SERVICE.md" if version is None else f"history/SERVICE.v{version}.md")).read_text(encoding="utf-8").splitlines()
        kept = (source / file).read_text(encoding="utf-8").splitlines()
        assert len(made) == len(kept)
        assert [(a, b) for a, b in zip(kept, made, strict=True) if a != b] == [(next(a for a in kept if a.startswith("  path: ")), f"  path: {folder}")]
    for file, version in entry["playbooks"]:  # a playbook is byte-identical
        target = place / ("PLAYBOOK.md" if version is None else f"history/PLAYBOOK.v{version}.md")
        assert target.read_bytes() == (source / file).read_bytes()


def test_times_are_utc_microseconds():
    """Message ids are UTC already; INDEX.txt and the git log are +01:00 and the deliverables log is Z: all become UTC microseconds."""
    assert utc_us("2026-10-22T19:12:45.031Z") == 1792696365031000
    assert utc_us("2026-10-22T19:36:41+01:00") == 1792694201000000  # 18:36:41 UTC
    assert utc_us("2026-10-22T18:36:41+00:00") == utc_us("2026-10-22T19:36:41+01:00")
    assert utc_us("2026-10-22T19:12:45.000001Z") - utc_us("2026-10-22T19:12:45Z") == 1
    with pytest.raises(Failed, match="has no offset or Z"):
        utc_us("2026-10-22T19:12:45")


@pytest.mark.parametrize("corpus", WITH_DELIVERABLES)
def test_each_pinned_deliverable_time_is_its_log_line(corpus, tmp_path):
    """The manifest pins each delivered file's last write: the line of the log exists, starts `[<time>] call #<n>`, and the command names the file; the
    replay's file carries that time as its modification time."""
    entry = MANIFESTS[corpus]
    source = Path(entry["evidence"])
    org = materialize(corpus, tmp_path)
    assert entry["deliverables"]
    for item in entry["deliverables"]:
        time, block = log_block(source / item["log"], item["line"])
        assert time == item["mtime"]
        first = block.splitlines()[0]
        assert first.startswith(f"[{item['mtime']}] call #{item['call']} ")
        assert Path(item["file"]).name in block  # the command writes this file
        made = deliverable_folder(tmp_path.resolve(), corpus) / Path(item["file"]).name
        assert made.stat().st_mtime_ns == utc_us(item["mtime"]) * 1000
        assert made.read_bytes() == (source / item["file"]).read_bytes()
    assert not (org / "deliverables").exists()  # the folder is beside the organization, not in it


def test_a_log_line_that_is_not_a_command_fails(tmp_path):
    log = tmp_path / "log.txt"
    log.write_text("# log\n\n[2026-10-22T19:12:45.031Z] call #31 turn 7 execute_bash\nCOMMAND: cp a b\n", encoding="utf-8")
    assert log_block(log, 3) == ("2026-10-22T19:12:45.031Z", "[2026-10-22T19:12:45.031Z] call #31 turn 7 execute_bash\nCOMMAND: cp a b")
    for line, words in ((1, "is not the start of a logged command"), (9, "has no line 9")):
        with pytest.raises(Failed, match=words):
            log_block(log, line)


@pytest.mark.parametrize("corpus", WITH_DELIVERABLES)
def test_team_files_are_the_newest_listed_versions(corpus, tmp_path):
    """The org path of each memo holds the newest version INDEX.txt lists (by UTC time), which is also the working tree's file."""
    entry = MANIFESTS[corpus]
    index = Path(entry["evidence"]) / entry["team_files"]
    org = materialize(corpus, tmp_path)
    working = dict(re.findall(r"^(\S+) working tree md5 ([0-9a-f]{32})", index.read_text(encoding="utf-8"), re.MULTILINE))
    assert set(working) == set(index_entries(index))
    for path in index_entries(index):
        version_file, listed = newest_version(index, path)
        assert md5_of(version_file) == listed == working[path]
        assert (org / path).read_bytes() == version_file.read_bytes()


# ------------------------------------------------------------------------------------------------- run logs, variants


def test_run_logs_are_empty_files_named_like_the_kept_ones(tmp_path):
    org = materialize("E3", tmp_path)
    for folder, address in MANIFESTS["E3"]["run_logs"]:
        kept = sorted(p.name for p in (Path(MANIFESTS["E3"]["evidence"]) / folder).glob("*.log"))
        made = sorted((org / address / "runs").glob("*.log"))
        assert [p.name for p in made] == kept and kept and all(p.stat().st_size == 0 for p in made)


def test_the_variant_r2_links_r1_adds_one_human_link_to_root_and_lead(tmp_path):
    base = materialize("E3", tmp_path / "base")
    org = materialize("E3", tmp_path / "v", "r2-links-r1")
    new_id = "20261021T154600000000-root-0b01"
    link, source = (org / "sent" / f"{new_id}.md").read_text(encoding="utf-8"), (org / "sent" / "20261021T154557001479-root-8ca0.md").read_text(encoding="utf-8")
    assert (org / "lead" / "read" / f"{new_id}.md").read_text(encoding="utf-8") == link
    changed = [(a, b) for a, b in zip(source.splitlines(), link.splitlines(), strict=True) if a != b]
    assert changed == [
        ("id: 20261021T154557001479-root-8ca0", f"id: {new_id}"),
        ("title: 'criterion link on \"Memo for the meeting of 2026-10-19\": C11'", "title: 'criterion link on \"Memo for the meeting of 2026-10-19\": R1'"),
        ("created: '2026-10-21T15:45:57+00:00'", "created: '2026-10-21T15:46:00+00:00'"),
        ("criterion: C11", "criterion: R1"),
    ]
    assert "reply_to: 20261021T154215089638-root-5c11" in link and "source: human" in link
    assert sorted(p.name for p in org.rglob("*.md")) == sorted([*(p.name for p in base.rglob("*.md")), f"{new_id}.md", f"{new_id}.md"])


@pytest.mark.parametrize("count", [12, 11])
def test_the_constructed_variant_r3_overspend_adds_n_empty_run_logs_inside_the_window_of_ab46(count, tmp_path):
    """A constructed variant, not an observation (design 19.3 E3-9): N empty run logs of `lead`, 21-character stamps between 15:38:09.201054 and the last
    result of case ab46 at 15:43:42.518435. The manifest, the kit's docstring and this test all say so."""
    base = {p.name for p in (materialize("E3", tmp_path / "base") / "lead" / "runs").glob("*.log")}
    org = materialize("E3", tmp_path / "v", f"r3-overspend-{count}")
    added = sorted(p.name for p in (org / "lead" / "runs").glob("*.log") if p.name not in base)
    assert len(added) == count and added[0] == "20261021T154300000001.log" and added[-1] == f"20261021T1543000000{count:02d}.log"
    assert all(len(n) == len("20261021T154300000001.log") and "20261021T153809201054" < n[:21] < "20261021T154342518435" for n in added)
    assert all((org / "lead" / "runs" / n).stat().st_size == 0 for n in added)
    assert "constructed variant, not an observation" in VARIANTS["r3-overspend-<N>"]["what"]
    assert "constructed variant, not an observation" in (Path(org_replay_manifest.__file__).with_name("org_replay.py")).read_text(encoding="utf-8")


def test_a_variant_is_for_e3_only_and_must_be_known(tmp_path):
    with pytest.raises(Failed, match="for E3 only"):
        materialize("E", tmp_path / "e", "r2-links-r1")
    with pytest.raises(Failed, match="unknown variant"):
        materialize("E3", tmp_path / "e3", "r4-nothing")
    with pytest.raises(Failed, match="N is 1 to 99"):
        materialize("E3", tmp_path / "e3-0", "r3-overspend-0")
