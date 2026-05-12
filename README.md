# Jarvis — Autonomous GitHub Issues Triage Agent

> Built this because I got tired of watching open issues pile up with no owner, no label, and no end in sight.

Jarvis is a LangGraph-powered agent that fully automates the GitHub issue lifecycle — from the moment an issue comes in to when it gets triaged, assigned, labeled, linked to related docs, and closed if it's gone stale. No manual intervention needed.

---

## Why I Built This

Most teams I've seen treat issue management as background noise — something someone gets to "eventually." Issues sit open for weeks, nobody knows who owns what, and engineers waste time context-switching just to figure out what's still relevant.

I wanted to see if I could automate that entire workflow as a proper agentic system. Jarvis is what came out of that.

---

## What It Does

The agent runs each GitHub issue through a multi-step LangGraph state machine:

```
extract_issue
     ↓
check_age_and_close        ← calculates actual business days (not calendar days)
     ↓
  [open?] ──── yes ──→ assign_issue  →  add_labels  →  find_related  →  summarize
     ↓
  [closed] ──────────────────────────────────────────────────────────→  summarize
```

**Step by step:**

1. **Extract** — Pulls issue metadata: title, body, state, assignee, comments, timestamps
2. **Age Check** — Calculates how many *business days* (Mon–Fri only) the issue has been open. If it's exceeded 5, the issue gets flagged and closed automatically
3. **Assign** — For open issues, picks an assignee from a team pool using a deterministic hash on the issue ID — so the same issue always maps to the same person, no randomness
4. **Label** — Scans title + body for keywords and tags accordingly: `bug`, `feature request`, `question`, `documentation`, `aws`, `gcp`, `ai service`, `support`
5. **Find Related** — Searches a local knowledge base for past issues or docs with overlapping content, and links them in a comment
6. **Summarize** — Generates a structured audit log: state, assignee, labels, timestamps, and all decisions made

Everything gets written to `triage_output.json` at the end.

---

## Tech Stack

| Layer | Tools |
|---|---|
| Agent Framework | LangGraph (StateGraph) |
| Language | Python 3.10+ |
| Data | JSON-based mock issues + knowledge base |
| Output | Structured JSON audit log |

---

## Project Structure

```
jarvis-triage-agent/
│
├── triage_agent.py          # Main agent — all nodes + graph definition
├── mock_issue_response.json # Sample GitHub issues (list or single dict)
├── mock_labels_response.json# Available label definitions
├── knowledge_base.json      # Past issues + docs for related-item matching
├── triage_output.json       # Auto-generated output after each run
└── README.md
```

---

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/YOUR_USERNAME/jarvis-triage-agent.git
cd jarvis-triage-agent
```

**2. Install dependencies**
```bash
pip install langgraph
```

**3. Set up your mock data**

Your `mock_issue_response.json` should look like this:
```json
[
  {
    "issue_code": "ISSUE-001",
    "title": "Bug: API returns 500 on empty payload",
    "body": "Getting a server error when the request body is empty.",
    "state": "open",
    "created_at": "2025-04-01T10:00:00Z",
    "assignee": null,
    "comments": []
  }
]
```

**4. Run the agent**
```bash
python triage_agent.py
```

**5. Check the output**
```bash
cat triage_output.json
```

---

## Sample Output

```json
{
  "issue_code": "ISSUE-001",
  "issue_state": "open",
  "assignee": "nithin",
  "created_at": "2025-04-01T10:00:00Z",
  "closed_at": null,
  "labels": ["bug"],
  "notes": [
    "Issue ISSUE-001 is 3 business days old.",
    "Issue ISSUE-001 is within 5 business days. No action taken.",
    "Issue ISSUE-001 assigned to @nithin.",
    "Added labels: ['bug']",
    "Added comment with related issues: ['ISSUE-003'] and docs: []"
  ],
  "processed_at": "2025-05-01T14:32:11.123456"
}
```

---

## Design Decisions Worth Mentioning

**Business days, not calendar days** — I made the age check skip weekends intentionally. An issue opened on Friday shouldn't be flagged stale by Monday morning. That felt like a product decision, not just a technical one.

**Deterministic assignment** — Using `hash(issue_code) % len(ASSIGNEES)` means the same issue always routes to the same person across reruns. This was a deliberate call to avoid ping-ponging ownership between runs.

**Conditional routing in LangGraph** — The graph branches at `check_age_and_close`: open issues go through the full assignment + labeling pipeline, closed ones skip straight to summarize. This keeps the graph clean and avoids unnecessary steps.

**Knowledge base matching is intentionally simple** — Word overlap with a threshold of 2 is basic but surprisingly effective for issue text. Didn't want to pull in embeddings for what's essentially a keyword problem at this scale.

---

## What's Next

A few things I'm thinking about adding:

- [ ] Swap mock JSON for live GitHub API calls via `PyGithub`
- [ ] Replace keyword labeling with an LLM classifier (GPT-4 or Gemma)
- [ ] Add embedding-based similarity for smarter related-issue matching
- [ ] Slack/email notification when an issue gets auto-closed
- [ ] GitHub Actions workflow to run Jarvis on a schedule

---

## Author

**Satya Sai Ganesh Yerramsetti**  
MS Computer Science — University of North Texas  
[LinkedIn](https://linkedin.com/in/satya-sai-ganesh-yerramsetti-2a204424b) · [GitHub](https://github.com/YOUR_USERNAME)  
satyasaiganeshyerramsetti@my.unt.edu
