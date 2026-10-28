"""The text of the ready-to-edit blueprint templates (package-private; moved verbatim from the flat ``blueprint_examples``).

Each text is valid YAML (the schema summary is a comment header). Text in <ANGLE BRACKETS> is a placeholder the assistant must replace with what the
user said; paths start from ``{base}``. With the service templates the work is offered as a standing service (``services:``)."""

from __future__ import annotations

SCHEMA = """\
# Blueprint schema in one paragraph. A blueprint is YAML with four top-level keys. `mission`: one paragraph on what the
# organization is for. `needs`: what the user asked for, in their terms: scope (the exact list of items, only what they
# gave you), deliverable {description, format, max_words, path}, quality_bar, sources, inputs (read-only folders with the
# user's files), workspace (the one folder agents may write in, for code), budget_runs (the user's cap in runs),
# models {cheap, strong} and model_policy, review (true/false), approval, progress, kind (research|writing|code|analysis), code
# {tests, packaging, commits}. `agents`: ONE top-level agent (usually template manager) with `children`; each agent has
# name, template (manager, researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer, analyst,
# data-checker) or a custom
# `charter`, optional model (cheap|strong|id), tools, workspace, scale. `task`: the first task for the top agent: to,
# title, goal and `acceptance`, a list of exact, checkable criteria (numbers, sections, paths), never "good quality".
# Replace every <PLACEHOLDER>; delete what does not apply. Then call propose_org with the edited text.
"""

RESEARCH = """\
{schema}
# kind=research: the team gathers facts from the web (with a URL per claim), writes them up and has every claim fact-checked.
mission: >
  <One paragraph: what the organization produces and for whom, e.g. a sourced comparison of the items below.>
needs:
  kind: research
  scope: "<The exact items in scope, as the user listed them. Ask for the list; do not invent one.>"
  elicitation: <THE USER'S ANSWERS, VERBATIM>   # what the user said, verbatim; every `from:` below is a quote of it
  deliverable:
    description: <What the file contains, e.g. a comparison table plus a closing recommendation section labelled as our assessment>
    format: markdown               # what the user can open: markdown, plain text, csv, ...
    max_words: 1500                # length limit; also put it in an acceptance criterion
    path: {base}/deliverables/<name>.md   # where the user gets it; the assistant copies the checked file there
  quality_bar: Every factual claim cites the page that states it; opinions are labelled as judgement, without citations; current facts come from the live source.
  sources: Web access to official sites and documentation; a source URL per claim.
  budget_runs: 25                  # the user's cap in runs (one run = one agent working session)
  models: {{cheap: claude-sonnet-5.5, strong: claude-sonnet-5.5}}   # same model for both tiers: the floor is claude-sonnet-5.5, nothing below it is available
  model_policy: one model for all   # claude-sonnet-5.5 at high effort for every agent; nothing below it is available
  review: true                     # an independent fact-checker who did not write the text
  approval: Plan first; ask before any spend beyond the budget.
  progress: One line when I ask.
agents:
  - name: lead
    template: manager
    model: strong                  # the lead stays strong: it decides how every other run is spent
    children:
      - {{name: researcher, template: researcher}}   # web_search + web_fetch
      - {{name: writer, template: writer}}
      - {{name: factcheck, template: fact-checker}}  # independent: quotes the source for EVERY factual claim (ledger of facts and judgement)
task:
  to: lead
  title: <Short title of the work>
  goal: >
    <Research the scope, write the deliverable, have the claims independently fact-checked, apply every required
    change and report the final file.>
  acceptance:                      # exact and checkable; the assistant checks each one at the end
    # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
    - text: Covers exactly the items listed in the scope and no others.
      default: true
    - text: At most 1500 words as counted by read.
      default: true
    - text: Contains <the sections or table the user asked for, named exactly>, and the closing recommendation section is marked as our assessment (judgement).
      from: <THE USER'S EXACT WORDS>
    - text: Every sentence with a number, name, version, license, price, date or "no/only/all" is a factual claim and cites the URL of the page that states it; the fact-checker fetched that page and quoted the sentence.
      default: true
    - text: The recommendation section is judgement. It has no citations or new facts and rests only on claims verified elsewhere in the document.
      default: true
    - text: "The fact-checker's final coverage line reads 'n of m factual claims verified' with n = m (none wrong, unsupported or not-checkable) and 'each resting on verified facts: yes' for its judgement statements, and the writer applied every required change."
      default: true
    - text: The final report pastes that coverage line verbatim, with the path of the fact-checker's ledger.
      default: true
"""

DOCUMENTS = """\
{schema}
# kind=documents: the team reads the user's own local files (read-only, no web) and writes a new document from them.
mission: >
  <One paragraph: what document the organization writes from the user's files, and for whom.>
needs:
  kind: writing
  scope: "<What the document covers and what it leaves out, in the user's words.>"
  elicitation: <THE USER'S ANSWERS, VERBATIM>   # what the user said, verbatim; every `from:` below is a quote of it
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
  models: {{cheap: claude-sonnet-5.5, strong: claude-sonnet-5.5}}
  model_policy: one model for all   # claude-sonnet-5.5 at high effort for every agent; nothing below it is available
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
    # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
    - text: Covers <the topics the user listed, named exactly> and nothing else.
      from: <THE USER'S EXACT WORDS>
    - text: At most 1500 words as counted by read.
      default: true
    - text: Every statement is traceable to a named input file, and gaps or conflicts between files are listed in a final section titled "Open questions".
      default: true
    - text: "Every statement is checked against its named input file in the reviewer's report, and the writer applied every required change."
      default: true
"""

CODE = """\
{schema}
# kind=code: engineers build software in one workspace folder (tests, local commits), testers and reviewers check it.
mission: >
  <One paragraph: what software the organization builds and for whom.>
needs:
  kind: code
  scope: "<What the software does and what it deliberately does not do, in the user's words.>"
  elicitation: <THE USER'S ANSWERS, VERBATIM>   # what the user said, verbatim; every `from:` below is a quote of it
  deliverable:
    description: <What is delivered, e.g. a Python package with a command-line tool>
    format: python package         # no path needed: the result is the workspace folder itself
  quality_bar: Tests pass from a clean checkout; no network use at runtime.
  workspace: {base}/<project-folder>   # the ONLY folder agents may write in or run commands in; created if missing
  budget_runs: 30
  models: {{cheap: claude-sonnet-5.5, strong: claude-sonnet-5.5}}
  model_policy: one model for all   # claude-sonnet-5.5 at high effort for every agent; nothing below it is available
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
    # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
    - text: "`uv run pytest -q` passes with at least 5 tests."
      default: true
    - text: <The exact command or behavior that shows the main feature works, e.g. a command and its expected output.>
      from: <THE USER'S EXACT WORDS>
    - text: The tester ran the software against every criterion and the engineer applied every required change.
      default: true
    - text: Work is committed locally in the workspace and nothing was pushed.
      default: true
"""

ANALYSIS = """\
{schema}
# kind=analysis: the team analyses the user's data files (read-only) with a script, has the key figures recomputed independently and writes the findings.
mission: >
  <One paragraph: which question the organization answers from the user's data, and for whom.>
needs:
  kind: analysis
  scope: "<The question and the outcome to explain, e.g. what drives product returns; which file(s) and period.>"
  elicitation: <THE USER'S ANSWERS, VERBATIM>   # what the user said, verbatim; every `from:` below is a quote of it
  inputs:                          # read-only folders with the user's data; the team can read them, never change them
    - {base}/<folder-with-your-data>
  workspace: {base}/analysis-work  # a scratch folder OUTSIDE the data folder: scripts and outputs live here
  deliverable:
    description: <What the report contains, e.g. the strongest effects with counts, then recommendations labelled as our assessment>
    format: markdown
    max_words: 1000
    path: {base}/deliverables/<name>.md
  quality_bar: Every number is reproducible from one script and appears with its label in the script's output; no conclusion from a slice under 30 rows.
  sources: Only the files in needs.inputs; no web.
  budget_runs: 25
  models: {{cheap: claude-sonnet-5.5, strong: claude-sonnet-5.5}}
  model_policy: one model for all   # claude-sonnet-5.5 at high effort for every agent; nothing below it is available
  review: true                     # a checker who did not do the analysis recomputes the figures with its own script
  approval: Plan first; ask before any spend beyond the budget.
  progress: One line when I ask.
agents:
  - name: lead
    template: manager
    model: strong
    children:
      - {{name: analyst, template: analyst, model: strong}}   # read + shell in the workspace; one script, labelled output
      - {{name: checker, template: data-checker, model: strong}}  # independent: its own script, label-bound figure check
      - {{name: writer, template: writer, tools: [read]}}   # reads the analyst's output (read-only); writes the report
task:
  to: lead
  title: <Short title of the analysis>
  goal: >
    <Analyse the data for the question, explore the outcome against every dimension and pair, have the key figures
    recomputed independently, write the report from the labelled output, apply every required change and report the final file.>
  acceptance:
    # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
    - text: Uses only <the data file(s)> in the data folder, and the checker confirmed the data files are unchanged (same checksums before and after).
      from: <THE USER'S EXACT WORDS>
    - text: One script in the workspace regenerates every figure in the report; running it twice from a clean state gives identical output.
      default: true
    - text: The script explores <the outcome> against every available column and against every pair of the strongest dimensions (for example reason x region); the report lists the strongest effects with their counts (n and share).
      from: <THE USER'S EXACT WORDS>
    - text: Each number in the report appears together with its label in the script output; the checker verified every label and number pair, not only that the number occurs.
      default: true
    - text: No conclusion is drawn from a slice with fewer than 30 rows; such slices are marked "too small".
      default: true
    - text: At most 1000 words as counted by read; the recommendations are in a section labelled as our assessment (judgement), without figures that are not in the script output.
      default: true
    - text: "The checker's line reads 'Figures checked: n of m match' with n = m, and also 'dimensions covered: k of d' with k = d, strongest pairs scanned: yes, reproducible: yes, data unchanged: yes; the writer applied every required change."
      default: true
"""

TEMPLATES = {"research": RESEARCH, "documents": DOCUMENTS, "code": CODE, "analysis": ANALYSIS}

# ------------------------------------------------------------------------------------------------ services

SERVICE_SCHEMA = """\
# Blueprint schema in one paragraph. A blueprint is YAML with these top-level keys. `mission`: one paragraph on what the
# organization is for. `needs`: what the user asked for, in their terms: scope (the exact list of items, only what they
# gave you), quality_bar, sources, inputs (read-only folders with the user's files), workspace (the one folder agents may
# write in, for code), budget_runs (the user's cap in runs for ONE request), models {cheap, strong} and model_policy,
# review (true/false), approval, progress, kind (research|writing|code|analysis), code {tests, packaging, commits}.
# `agents`: ONE top-level agent (usually template manager) with `children`; each agent has name, template (manager,
# researcher, writer, reviewer, fact-checker, engineer, tester, code-reviewer, analyst, data-checker) or a custom
# `charter`, optional model (cheap|strong|id), tools, workspace, scale. `services`: what the top agent offers again and
# again, each with name, description, inputs (what changes per request), acceptance (exact, checkable criteria: the
# contract, which only the user can change), deliverable {description, format, max_words, path}, budget (runs per request),
# optional playbook (the workflow; left out, one is generated) and locked. After every request the lead records lessons and
# may improve the playbook, never the checks. `task` is optional: leave it out to build the team now and request later, or
# make it a first request {service, inputs, title}. Replace every <PLACEHOLDER>; delete what does not apply. Then call
# propose_org with the edited text.
"""

SERVICE_HEAD = """\
services:                          # work the lead offers again and again; each request becomes one task built from this contract
  - name: <service-name>           # lowercase-dashed, e.g. weekly-brief; requests name the service only
    owner: lead                    # optional: the top-level agent (the only owner allowed for now)
    description: <One line saying what one request delivers>
    inputs:                        # what changes with each request; everything else is fixed by this contract
      - name: <input-name>         # lowercase letters, digits, underscores, e.g. topic
        description: <What the requester gives>
        required: true             # false = optional
"""

SERVICE_TAIL = """\
    budget: {budget}                     # runs handed down with each request; within needs.budget_runs (the cap for ONE request); leave out for the plan's number (the estimate + 25%, or + one round of client questions when more)
    locked: false                  # true: the lead may not improve the playbook (default false: it may, but never lower the checks above)
    # playbook: |                  # optional first workflow (steps, budget plan, pitfalls); leave out and one is generated from the team
# task:                            # OPTIONAL first request, started on approval. Leave it out to build the team now and request later
#   service: <service-name>        # (nothing runs until then); uncomment it to start with one request.
#   inputs:
#     <input-name>: <value>
#   title: <Short title of this request>
"""

SERVICE_BODIES = {
    "research": """\
    acceptance:                    # the contract: exact and checkable; only the user can change it, the lead can never lower it
      # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
      - text: At most 600 words as counted by read.
        default: true
      - text: Contains <the sections or table the user asked for, named exactly>.
        from: <THE USER'S EXACT WORDS>
      - text: Every sentence with a number, name, version, license, price, date or "no/only/all" is a factual claim and cites the URL of the page that states it; the fact-checker fetched that page and quoted the sentence.
        default: true
      - text: Judgement is in a section labelled as our assessment, with no citations or new facts, and rests only on claims verified elsewhere in the document.
        default: true
      - text: "The fact-checker's final coverage line reads 'n of m factual claims verified' with n = m, and the lead's report pastes it verbatim."
        default: true
    deliverable:
      description: <What one request produces, e.g. one markdown file with the brief>
      format: markdown
      max_words: 600               # also put it in an acceptance criterion
      path: {base}/deliverables/<name>   # a FOLDER: the assistant copies each checked result into it
""",
    "documents": """\
    acceptance:                    # the contract: exact and checkable; only the user can change it, the lead can never lower it
      # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
      - text: Covers <the topic of the request> and nothing else.
        from: <THE USER'S EXACT WORDS>
      - text: At most 1500 words as counted by read.
        default: true
      - text: Every statement is traceable to a named input file, and gaps or conflicts between files are listed in a final section titled "Open questions".
        default: true
      - text: "Every statement is checked against its named input file in the reviewer's report, and the writer applied every required change."
        default: true
    deliverable:
      description: <What one request produces, e.g. one markdown section for the topic>
      format: markdown
      max_words: 1500              # also put it in an acceptance criterion
      path: {base}/deliverables/<name>   # a FOLDER: the assistant copies each checked result into it
""",
    "code": """\
    acceptance:                    # the contract: exact and checkable; only the user can change it, the lead can never lower it
      # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
      - text: "`uv run pytest -q` passes, including at least one new test for the requested change."
        default: true
      - text: <The exact command or behavior that shows the requested change works, e.g. a command and its expected output.>
        from: <THE USER'S EXACT WORDS>
      - text: The tester ran the software against every criterion and the engineer applied every required change.
        default: true
      - text: The change is committed locally in the workspace and nothing was pushed.
        default: true
    deliverable:
      description: <What one request produces, e.g. the requested change, tested and committed in the workspace>
      format: code and tests in the workspace   # no path needed: the result is the workspace folder itself
""",
    "analysis": """\
    acceptance:                    # the contract: exact and checkable; only the user can change it, the lead can never lower it
      # each criterion: text, and from: <the user's exact words> (asked: <your question>) or default: true (your proposal); put their answers, verbatim, in needs.elicitation
      - text: Uses only the data files in the data folder, and the checker confirmed they are unchanged (same checksums before and after).
        default: true
      - text: One script in the workspace regenerates every figure in the report; running it twice from a clean state gives identical output.
        default: true
      - text: Each number in the report appears together with its label in the script output; the checker verified every label and number pair.
        default: true
      - text: No conclusion is drawn from a slice with fewer than 30 rows; such slices are marked "too small".
        default: true
      - text: At most 1000 words as counted by read; recommendations are in a section labelled as our assessment (judgement).
        default: true
      - text: "The checker's line reads 'Figures checked: n of m match' with n = m, and the writer applied every required change."
        default: true
    deliverable:
      description: <What one request produces, e.g. a report on the question of the request>
      format: markdown
      max_words: 1000              # also put it in an acceptance criterion
      path: {base}/deliverables/<name>   # a FOLDER: the assistant copies each checked result into it
""",
}
SERVICE_BUDGETS = {"research": 24, "documents": 22, "code": 25, "analysis": 25}
