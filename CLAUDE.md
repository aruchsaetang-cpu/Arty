## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- When graphify-out/graph.json exists, run `graphify query "<question>"` before your first grep, search or source-file read for a codebase question, and put this rule in every subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. When the answer is under a Markdown heading, `graphify section "<heading>"` prints that section's text, so the .md need not be opened. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- A committed graphify-out/graph.json is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild or its hooks.

## Model routing (user request)
- Main session model is chosen by the user (`/model`); Claude cannot switch it.
- Subagents: pass `model` on the Agent tool. `haiku` = file search, logs, docs, renames. `sonnet` = default coding (Three.js, camera, lighting,
  render scripts, tests). `opus` = hard physics/biomechanics, fight choreography, pipeline architecture, bugs sonnet failed on.
- Use the cheapest model that is reliable. Escalate only after a real failure. No extra agents without clear benefit.
- Give each agent only the files it needs. Never run two full film renders at once (RAM). Report: task, model used, files, tests, open issues.
- Reply style: caveman (short words, short sentences), see HANDOFF.md section 9.

## Brainstorm first (user request)
- Before starting a new project, or before fixing something the user says is wrong, use the `superpowers:brainstorming` skill first.
- Find out what is wrong and what they want, then fix. Skip it only for tiny, fully clear requests.
