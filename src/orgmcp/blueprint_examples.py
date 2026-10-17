"""Ready-to-edit blueprint templates, served by the root tool ``blueprint_example(kind)``.

Each text is valid YAML (the schema summary is a comment header), so it can be passed to ``propose_org`` as is. Text
in <ANGLE BRACKETS> is a placeholder the assistant must replace with what the user said; paths start from ``base``
(the server's working directory) so they are absolute, as the validator requires.
"""

from __future__ import annotations

from pathlib import Path

from .core import OrgError

KINDS = ("research", "documents", "code")

SCHEMA = """\
# Blueprint schema in one paragraph. A blueprint is YAML with four top-level keys. `mission`: one paragraph on what the
# organization is for. `needs`: what the user asked for, in their terms: scope (the exact list of items, only what they
# gave you), deliverable {description, format, max_words, path}, quality_bar, sources, inputs (read-only folders with the
# user's files), workspace (the one folder agents may write in, for code), budget_runs (the user's cap in runs),
# models {cheap, strong} and model_policy, review (true/false), approval, progress, kind (research|writing|code), code
# {tests, packaging, commits}. `agents`: ONE top-level agent (usually template manager) with `children`; each agent has
# name, template (manager, researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer) or a custom
# `charter`, optional model (cheap|strong|id), tools, workspace, scale. `task`: the first task for the top agent: to,
# title, goal and `acceptance`, a list of exact, checkable criteria (numbers, sections, paths), never "good quality".
# Replace every <PLACEHOLDER>; delete what does not apply. Then call propose_org with the edited text.
"""

RESEARCH = """\
{schema}
# kind=research: the team gathers facts from the web (with a URL per claim), writes them up and has them fact-checked.
mission: >
  <One paragraph: what the organization produces and for whom, e.g. a sourced comparison of the items below.>
needs:
  kind: research
  scope: "<The exact items in scope, as the user listed them. Ask for the list; do not invent one.>"
  deliverable:
    description: <What the file contains, e.g. a comparison table plus a closing recommendation section>
    format: markdown               # what the user can open: markdown, plain text, csv, ...
    max_words: 1500                # length limit; also put it in an acceptance criterion
    path: {base}/deliverables/<name>.md   # where the user gets it; the assistant copies the checked file there
  quality_bar: Every factual claim has a primary-source URL; current facts come from the live source.
  sources: Web access to official sites and documentation; a source URL per claim.
  budget_runs: 25                  # the user's cap in runs (one run = one agent working session)
  models: {{cheap: claude-haiku-4.5, strong: claude-sonnet-4.6}}   # use model ids available to the user
  model_policy: cheap drafting, strong review   # or "one model for all" (then give no models)
  review: true                     # an independent fact-checker who did not write the text
  approval: Plan first; ask before any spend beyond the budget.
  progress: One line when I ask.
agents:
  - name: lead
    template: manager
    model: strong
    children:
      - {{name: researcher, template: researcher}}   # web_search + web_fetch
      - {{name: writer, template: writer}}
      - {{name: factcheck, template: fact-checker}}  # independent: re-checks the highest-impact claims on the web
task:
  to: lead
  title: <Short title of the work>
  goal: >
    <Research the scope, write the deliverable, have the claims independently fact-checked, apply every required
    change and report the final file.>
  acceptance:                      # exact and checkable; the assistant checks each one at the end
    - Covers exactly the items listed in the scope and no others.
    - At most 1500 words as counted by read.
    - Contains <the sections or table the user asked for, named exactly>.
    - Every factual claim has a source URL that the researcher or fact-checker fetched.
    - The fact-checker verified at least 6 high-impact claims and the writer applied every required change.
"""

DOCUMENTS = """\
{schema}
# kind=documents: the team reads the user's own local files (read-only, no web) and writes a new document from them.
mission: >
  <One paragraph: what document the organization writes from the user's files, and for whom.>
needs:
  kind: writing
  scope: "<What the document covers and what it leaves out, in the user's words.>"
  inputs:                          # read-only folders with the user's files; the team can read them, never change them
    - {base}/<folder-with-your-files>
  deliverable:
    description: <What the document is, e.g. an onboarding guide with one section per topic>
    format: markdown
    max_words: 1500
    path: {base}/deliverables/<name>.md   # a new folder in the user's current directory; stated plainly in the plan
  quality_bar: Every statement comes from the input files; where the files disagree or are silent, the document says so.
  sources: Only the files in needs.inputs; no web.
  budget_runs: 25
  models: {{cheap: claude-haiku-4.5, strong: claude-sonnet-4.6}}
  model_policy: cheap drafting, strong review
  review: true                     # a reviewer who did not write it checks it against the files
  approval: Plan first; ask before any spend beyond the budget.
  progress: One line when I ask.
agents:
  - name: lead
    template: manager
    model: strong
    children:
      - name: reader                # reads the input files and extracts what the document needs
        role: Reader of the user's files
        model: cheap
        tools: [read]
        charter: >
          Read the files in the input folders. Extract the facts the document needs, each with the file it came from.
          Note every place where files disagree or are silent. Never change the input files.
      - {{name: writer, template: writer}}
      - name: reviewer
        template: reviewer
        model: strong
        tools: [read]               # needs read access to check the text against the files
task:
  to: lead
  title: <Short title of the document>
  goal: >
    <Read the input files, write the document, have it checked against the files, apply every required change and
    report the final file.>
  acceptance:
    - Covers <the topics the user listed, named exactly> and nothing else.
    - At most 1500 words as counted by read.
    - Every statement is traceable to a named input file, and gaps or conflicts between files are listed in a final section titled "Open questions".
    - The reviewer checked at least 6 statements against the files and the writer applied every required change.
"""

CODE = """\
{schema}
# kind=code: engineers build software in one workspace folder (tests, local commits), testers and reviewers check it.
mission: >
  <One paragraph: what software the organization builds and for whom.>
needs:
  kind: code
  scope: "<What the software does and what it deliberately does not do, in the user's words.>"
  deliverable:
    description: <What is delivered, e.g. a Python package with a command-line tool>
    format: python package         # no path needed: the result is the workspace folder itself
  quality_bar: Tests pass from a clean checkout; no network use at runtime.
  workspace: {base}/<project-folder>   # the ONLY folder agents may write in or run commands in; created if missing
  budget_runs: 30
  models: {{cheap: claude-haiku-4.5, strong: claude-sonnet-4.6}}
  model_policy: cheap implementation, strong review
  review: true
  approval: Plan first; ask before any spend beyond the budget.
  progress: One line when I ask.
  code:
    tests: pytest, at least one test per acceptance criterion
    packaging: uv with a pyproject.toml
    commits: local commits per feature; never push
agents:
  - name: lead
    template: manager
    model: strong
    children:
      - {{name: dev, template: engineer}}          # write + shell, confined to the workspace
      - {{name: qa, template: tester}}             # independent: runs the software against the criteria
      - {{name: cr, template: code-reviewer}}      # read-only review of correctness and safety
task:
  to: lead
  title: <Short title of the software>
  goal: >
    <Implement the software in the workspace with tests, have it tested and reviewed independently, apply every
    required change and report.>
  acceptance:
    - "`uv run pytest -q` passes with at least 5 tests."
    - <The exact command or behavior that shows the main feature works, e.g. a command and its expected output.>
    - The tester ran the software against every criterion and the engineer applied every required change.
    - Work is committed locally in the workspace and nothing was pushed.
"""

TEMPLATES = {"research": RESEARCH, "documents": DOCUMENTS, "code": CODE}


def example(kind: str = "research", base: Path | str = ".") -> str:
    """The template text for ``kind`` with absolute paths under ``base``."""
    key = (kind or "research").strip().lower()
    if key not in TEMPLATES:
        raise OrgError(f"unknown kind '{kind}': use one of {', '.join(KINDS)} "
                       "(research = web sources, documents = write from the user's local files, code = repo workspace with tests)")
    return TEMPLATES[key].format(schema=SCHEMA, base=str(base).rstrip("/") or "/")
