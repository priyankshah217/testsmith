Below is the complete product context for the feature under test.

────────────────────────────────────────
PRODUCT CONTEXT
────────────────────────────────────────

{context}

────────────────────────────────────────

Follow all system prompt rules. Execute Phase 1 (rule extraction),
Phase 2 (test design), and Phase 3 (validation) internally.

Title rules:
- Describe the scenario or behavior ONLY
- No type prefixes ("UI -", "E2E -", "Negative -")
- No priority labels ("P0:", "P1:")

Example of ONE test case (format reference only — do not copy content):
{
  "ID": "TC-001",
  "Title": "First-time user sees onboarding screen",
  "Preconditions": "User has no previous sessions.",
  "Steps": "1. Open the app for the first time",
  "Expected Result": "The onboarding screen is displayed with setup instructions.",
  "Priority": "P1",
  "Type": "Functional"
}

Return ONLY the final JSON — no prose, no markdown, no explanations.
