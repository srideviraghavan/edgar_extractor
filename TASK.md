# AI Engineer Take-Home Assignment

## The task

Build a pipeline that extracts structured financial data from SEC EDGAR press-release filings (8-K) into a consistent JSON schema. Target facts include revenue, net income, EPS, segment breakdowns, and forward guidance.

EDGAR filings are messy. They exceed typical LLM context windows. Financial data lives in HTML tables and in narrative prose, sometimes reported at different scales, some filings omit guidance entirely. Your pipeline needs to handle all this and more.

Your submission should show us how you have thought through the problem before starting your solution.

## Acceptance Criteria

The pipeline must:

1. Handle documents that exceed context windows of 200K
2. Extract data from HTML tables (examples include income statements, balance sheets, segment breakdowns)
3. Extract data and management quotes from narrative prose (forward guidance, risk factors)
4. Maintain data lineage for auditing by having an exact XPath or equivalent direct source reference
5. Assign a confidence score to each extracted value
6. Output results into a JSON schema you define that uniquely identifies company data across filings
7. Track token usage and dollar cost per filing

## What we give you

The repo contains a `data/` directory with 20 HTML EDGAR filings. Some have clean tables and standard formatting; others have scale changes, missing guidance sections, merged table cells, unusual HTML, etc. We will evaluate your agent against our own golden set that is not in the provided filings to evaluate its real-world performance versus our own production extraction system.

You will receive a Portkey API endpoint along with 2 API keys, one is to be used with your coding agent of choice, the second by the pipeline service during development. **All LLM calls to the Portkey endpoint will be logged and there's some usage-restrictions applied**.

## Logistics

We expect roughly 4-6 hours of actual work. Any language is fine, though we prefer Typescript. Submit as a GitHub repository (public, or private with reviewer access) OR as a self-contained zip including the `.git` folder.

## AI tool use

We require you to use an AI coding tool to complete the task. You can use whatever AI coding tools you want: Cursor, Claude Code, Copilot, Codex, anything else. However you must configure them to use the Portkey API key and API token provided.

Part of this test is an evaluation of how well you can leverage coding agents, how you decompose the problem before prompting, your prompts themselves, and if you catch the agent's mistakes and how you correct them.

## Submission Requirements

1. You must use the provided Portkey API & keys with your coding tool, any submission without it or partially omitting it will not be accepted.

2. Commit incrementally so your git history shows how you worked, not just the final result.

3. If you used a spec, plan, or research notes to guide your coding agent, those files must be included in the repo.

4. Maintain a dev log in the repository, notes about what went wrong or what approaches you tried is more useful to us than a polished-looking final product. This does not need to be written incrementally but it must be human-written.

## After you submit

You'll walk through your solution with two of our engineers for about 45-60 minutes.

We'll ask you to explain your architecture, your prompts and library choices, and your evaluation results. We'll ask what you did in the first 30 minutes. We'll want to know how this would scale to hundreds of filings in parallel. We'll ask you to show us places where the AI got something wrong and what you did about it. We'll quiz you about certain interactions with the coding agent.

## Questions

Email your recruiting contact with clarifying questions before you start. Asking questions about the scope, the target facts, or how to handle ambiguous cases is encouraged but entirely optional.
