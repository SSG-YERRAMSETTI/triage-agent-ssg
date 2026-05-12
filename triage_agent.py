import json
from datetime import datetime, timedelta
from pathlib import Path
from langgraph.graph import StateGraph

# -------------------------
# Paths
# -------------------------
BASE_PATH = Path(__file__).parent
MOCK_RESPONSE_PATH = BASE_PATH / "mock_issue_response.json"
MOCK_LABELS_PATH = BASE_PATH / "mock_labels_response.json"
KNOWLEDGE_PATH = BASE_PATH / "knowledge_base.json"
TRIAGE_OUTPUT_PATH = BASE_PATH / "triage_output.json"

# -------------------------
# Assignment Config
# -------------------------
ASSIGNEES = ["urooj", "nithin"]

# -------------------------
# Load Issues
# -------------------------
def load_issues():
    if not MOCK_RESPONSE_PATH.exists():
        raise FileNotFoundError(
            f"Mock issues file not found at {MOCK_RESPONSE_PATH}. "
            "Make sure 'mock_issue_response.json' exists in the project root."
        )

    with MOCK_RESPONSE_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        return [payload]

    raise ValueError("Expected a list or dict of issues")

# -------------------------
# Extract Issue
# -------------------------
def extract_issue(state):
    issue_payload = state.get("issue") or state.get("issue_data")
    if not issue_payload:
        raise ValueError("No issue payload provided")

    issue_code = (
        state.get("issue_code")
        or issue_payload.get("issue_code")
        or issue_payload.get("id", "")
    )

    state["issue_code"] = str(issue_code).strip()
    state["issue_data"] = issue_payload
    state["labels"] = []
    state["related_docs"] = []
    state["notes"] = []

    return state


def sync_comment_authors_with_assignee(state: dict):
    assignee = state["issue_data"].get("assignee")
    comments = state["issue_data"].get("comments", [])

    if not assignee:
        return state

    for comment in comments:
        if not comment.get("author"):
            comment["author"] = assignee

    return state


# -------------------------
# Business Day Logic
# -------------------------
def business_days_between(start, end) -> int:
    """Calculate number of business days between two dates."""
    day_count = 0
    current = start
    while current.date() < end.date():
        if current.weekday() < 5:  # Monday=0, Friday=4
            day_count += 1
        current += timedelta(days=1)
    return day_count


# -------------------------
# Check Age + Close
# -------------------------
def check_age_and_close(state):
    issue_data = state["issue_data"]
    issue_code = state["issue_code"]

    if issue_data.get("state") == "closed":
        state["notes"].append(
            f"Issue {issue_code} already closed. Skipping close."
        )
        return state

    created_at_str = issue_data.get("created_at", "")

    try:
        created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
        now = datetime.now(created_at.tzinfo)

        business_days = business_days_between(created_at, now)
        state["notes"].append(
            f"Issue {issue_code} is {business_days} business days old."
        )

        if business_days > 5:
            state["notes"].append(
                f"Issue {issue_code} exceeded 5 business days. Closing issue."
            )
            # FIX: update issue_data state so after_check routing works correctly
            state["issue_data"] = {
                **issue_data,
                "state": "closed",
                "closed_at": now.isoformat(),
            }
        else:
            state["notes"].append(
                f"Issue {issue_code} is within 5 business days. No action taken."
            )

    except ValueError:
        state["notes"].append(f"Invalid created_at for issue {issue_code}")

    return state


# -------------------------
# Assign Issue
# -------------------------
def assign_issue(state):
    issue_data = state["issue_data"]
    issue_code = state["issue_code"]

    if issue_data.get("state") == "closed":
        state["notes"].append(
            f"Issue {issue_code} is closed. Skipping assignment."
        )
        return state

    assignee = ASSIGNEES[hash(issue_code) % len(ASSIGNEES)]

    print(f"Simulating API call to assign issue {issue_code} to @{assignee}...")
    state["issue_data"] = {
        **issue_data,
        "assignee": assignee,
    }

    state["notes"].append(
        f"Issue {issue_code} assigned to @{assignee}."
    )

    return state


# -------------------------
# Routing Logic
# -------------------------
def after_check(state):
    if state["issue_data"].get("state") == "open":
        return "assign_issue"
    return "summarize"


# -------------------------
# Add Labels
# -------------------------
def add_labels(state):
    all_labels = []
    if MOCK_LABELS_PATH.exists():
        with MOCK_LABELS_PATH.open("r", encoding="utf-8") as handle:
            try:
                all_labels = json.load(handle)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {MOCK_LABELS_PATH}, continuing without label hints.")
    else:
        print(f"Warning: Labels file not found at {MOCK_LABELS_PATH}. Continuing without label hints.")

    issue_data = state["issue_data"]
    text = f"{issue_data.get('title', '')} {issue_data.get('body', '')}".lower()

    labels = []

    if "bug" in text or "error" in text or "fix" in text:
        labels.append("bug")
    if "new" in text and "feature" in text:
        labels.append("new feature request")
    if "question" in text or "help" in text:
        labels.append("question")
    if "documentation" in text or "docs" in text:
        labels.append("documentation")
    if "aws" in text:
        labels.append("aws")
    if "gcp" in text:
        labels.append("gcp")
    if "ai service" in text:
        labels.append("ai service")
    if "mlc" in text:
        labels.append("mlc")
    if "support" in text:
        labels.append("support")

    labels = list(set(labels))
    state["labels"] = labels
    state["notes"].append(f"Added labels: {labels}")

    return state


# -------------------------
# Find Related Issues / Docs
# -------------------------
def find_related(state):
    knowledge_base = []

    if KNOWLEDGE_PATH.exists():
        with KNOWLEDGE_PATH.open("r", encoding="utf-8") as handle:
            try:
                knowledge_base = json.load(handle)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse {KNOWLEDGE_PATH}. No related docs will be found.")
    else:
        print(f"Warning: Knowledge base not found at {KNOWLEDGE_PATH}. No related docs will be found.")

    current_text = (
        f"{state['issue_data'].get('title', '')} "
        f"{state['issue_data'].get('body', '')}"
    ).lower()

    related_issues = []
    related_docs = []

    for item in knowledge_base:
        if item.get("issue_code") == state["issue_code"]:
            continue

        item_text = f"{item.get('title', '')} {item.get('body', '')}".lower()
        overlap = set(current_text.split()) & set(item_text.split())

        if len(overlap) >= 2:
            if "documentation" in item.get("labels", []):
                related_docs.append(item["issue_code"])
            else:
                related_issues.append(item["issue_code"])

        if len(related_issues) >= 3 and len(related_docs) >= 2:
            break

    print(f"Simulating API call to add comment to issue {state['issue_code']}...")
    state["notes"].append(
        f"Added comment with related issues: {related_issues[:3]} "
        f"and docs: {related_docs[:2]}"
    )

    return state


# -------------------------
# Summarize
# -------------------------
def summarize(state):
    issue_data = state["issue_data"]

    state["summary"] = {
        "issue_code": state["issue_code"],
        "issue_state": issue_data.get("state"),
        "assignee": issue_data.get("assignee"),
        "created_at": issue_data.get("created_at"),
        "closed_at": issue_data.get("closed_at"),
        "labels": state.get("labels", []),
        "notes": state.get("notes", []),
    }

    return state


# -------------------------
# Graph Definition
# FIX: removed business_days_between as a node — it's a utility function,
# not a state-compatible graph node. extract_issue now connects directly
# to check_age_and_close, which calls business_days_between internally.
# -------------------------
graph = StateGraph(dict)

graph.add_node("extract_issue", extract_issue)
graph.add_node("check_age_and_close", check_age_and_close)
graph.add_node("assign_issue", assign_issue)
graph.add_node("add_labels", add_labels)
graph.add_node("find_related", find_related)
graph.add_node("summarize", summarize)

graph.set_entry_point("extract_issue")
graph.add_edge("extract_issue", "check_age_and_close")   # FIX: direct connection
graph.add_conditional_edges("check_age_and_close", after_check)
graph.add_edge("assign_issue", "add_labels")
graph.add_edge("add_labels", "find_related")
graph.add_edge("find_related", "summarize")

app = graph.compile()

# -------------------------
# Run
# -------------------------
issues_list = load_issues()
triage_results = []

print("Processing issues...")
for issue_input in issues_list:
    issue_code = issue_input.get("issue_code") or issue_input.get("id", "UNKNOWN")
    print(f"\n--- Processing {issue_code} ---")

    result = app.invoke({"issue": issue_input})
    print(result["summary"])

    triage_results.append({
        **result["summary"],
        "processed_at": datetime.now().isoformat()
    })

    print(f"--- Completed {issue_code} ---\n")

print(f"Saving triage results to {TRIAGE_OUTPUT_PATH}...")
with TRIAGE_OUTPUT_PATH.open("w", encoding="utf-8") as handle:
    json.dump(triage_results, handle, indent=2)

print(f"Successfully saved {len(triage_results)} triaged issues")
