<div align="center">

# Triage Agent

**An autonomous GitHub issue management system built on LangGraph**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-FF6B35?style=flat-square)](https://github.com/langchain-ai/langgraph)
[![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)]()

</div>

---

> Built this because I got tired of watching open issues pile up with no owner, no label, and no end in sight. There had to be a better way.

Triage Agent is a LangGraph-powered autonomous system that handles the full GitHub issue lifecycle — from the moment an issue comes in to when it gets triaged, assigned, labeled, linked to related docs, and closed if it's gone stale. No manual intervention needed.

---


## The Problem It Solves

Most engineering teams treat issue management as background noise. Issues sit open for weeks, nobody knows who owns what, engineers waste time context-switching just to figure out what's still relevant, and important bugs get buried under a pile of stale feature requests.

I wanted to see if I could build a proper agentic system that handles all of that automatically. This is what came out of that experiment.

---

## How It Works

The agent processes each GitHub issue through a multi-step LangGraph state machine. Here's the flow:

```
┌─────────────────┐
│  extract_issue  │  ← Pull issue metadata (title, body, state, timestamps)
└────────┬────────┘
         │
┌────────▼────────────┐
│ check_age_and_close │  ← Calculate business days open (Mon–Fri only)
└────────┬────────────┘
         │
    ┌────▼────┐
    │  open?  │
    └────┬────┘
   yes   │    no
   ┌─────▼──────────────────────────────────────────────┐
   │  assign_issue → add_labels → find_related           │
   └─────────────────────────────────────┬──────────────┘
                                         │
                               ┌─────────▼─────────┐
                               │     summarize      │  ← Audit log to JSON
                               └───────────────────┘
```

**What each step does:**

**1. Extract** — Pulls the issue metadata: title, body, current state, assignee, comments, and timestamps. Normalises the data so everything downstream works with a consistent shape.

**2. Age Check** — Calculates how many *business days* the issue has been open (weekends excluded — an issue opened Friday shouldn't be flagged stale by Monday). If it's been open more than 5 business days with no resolution, it gets auto-closed.

**3. Assign** — For open issues, picks an assignee from the team pool using a deterministic hash on the issue ID. The same issue always routes to the same person across reruns — no ping-ponging ownership.

**4. Label** — Scans the title and body for relevant keywords and applies labels automatically: `bug`, `feature request`, `question`, `documentation`, `aws`, `gcp`, `ai service`, `support`.

**5. Find Related** — Searches a local knowledge base for past issues or documentation with overlapping content, then links them in a comment. Currently uses word-overlap matching — simple but effective at this scale.

**6. Summarize** — Generates a structured audit log capturing every decision the agent made: final state, assignee, labels applied, timestamps, and a full notes trail.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent Framework | LangGraph (StateGraph) |
| Language | Python 3.10+ |
| Data Input | JSON-based mock issues + knowledge base |
| Output | Structured JSON audit log |

---

## Project Structure

```
triage-agent/
│
├── triage_agent.py            # Core agent — all nodes + graph definition
├── mock_issue_response.json   # Sample GitHub issues for testing
├── mock_labels_response.json  # Available label definitions
├── knowledge_base.json        # Past issues + docs for related-item matching
├── requirements.txt           # Python dependencies
└── README.md
```

---

## Getting Started

**1. Clone the repo**
```bash
git clone https://github.com/SSG-YERRAMSETTI/triage-agent.git
cd triage-agent
```

**2. Create a virtual environment**
```bash
python -m venv venv
source venv/bin/activate      # Mac / Linux
venv\Scripts\activate         # Windows
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure your issues**

The agent reads from `mock_issue_response.json`. You can add your own issues in this format:

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

**5. Run the agent**
```bash
python triage_agent.py
```

**6. Check the output**
```bash
cat triage_output.json
```

---

## Sample Output

After running, `triage_output.json` captures a full audit trail for each processed issue:

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

## Design Decisions

A few choices I made deliberately that are worth explaining:

**Business days, not calendar days**
The age check skips weekends. An issue opened on Friday shouldn't be flagged stale by Monday morning — that would close things before anyone even had a chance to look at them. It felt more like a product decision than a technical one.

**Deterministic assignment**
Using `hash(issue_code) % len(ASSIGNEES)` means the same issue always routes to the same person across reruns. This avoids a situation where an issue gets re-assigned every time the agent runs, which would be confusing and noisy for the team.

**Conditional routing in LangGraph**
The graph branches at `check_age_and_close`: open issues go through the full assignment and labeling pipeline, closed ones skip straight to summarize. Keeps the graph clean and avoids running unnecessary steps on already-resolved issues.

**Knowledge base matching is intentionally simple**
Word overlap with a threshold of 2 is basic, but it works well for issue text at this scale. Pulling in embeddings and a vector database for what's essentially a keyword problem felt like over-engineering — YAGNI applies here. That said, it's on the roadmap.

---

## What's Next

- [ ] Replace mock JSON with live GitHub API calls via `PyGithub`
- [ ] Swap keyword labeling with an LLM classifier (GPT-4o or Gemma)
- [ ] Add embedding-based similarity search for smarter related-issue matching
- [ ] Slack and email notifications when issues get auto-closed
- [ ] GitHub Actions workflow to run the agent on a schedule
- [ ] Configurable SLA thresholds (not hardcoded to 5 days)
- [ ] Support for multiple assignee pools per label/team

---

## Author

**Satya Sai Ganesh Yerramsetti**
MS Computer Science — University of North Texas

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0077B5?style=flat-square&logo=linkedin)](https://linkedin.com/in/satya-sai-ganesh-yerramsetti-2a204424b)
[![GitHub](https://img.shields.io/badge/GitHub-SSG--YERRAMSETTI-181717?style=flat-square&logo=github)](https://github.com/SSG-YERRAMSETTI)
[![Email](https://img.shields.io/badge/Email-Contact-D14836?style=flat-square&logo=gmail)](mailto:ganeshyss0916@gmail.com)

---

<div align="center">
  <sub>If this was useful, a ⭐ on the repo goes a long way.</sub>
</div>
