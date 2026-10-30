"""The rules that find things worth changing, and rank what they find.

Phase 1 of the client's brief: recommendations, shown and not applied. Nothing
in this package writes to Google, and nothing writes the action log -- the log
records a decision, and the decision is the guardrails' to make.

- `catalogue` -- the rules as versioned data, including the three the client
  has not specified and which are therefore not implemented.
- `library` -- R1 and R4, the two that are.
- `recommend` -- what a rule found, and how it ranks.
- `engine` -- the daily pass, the ten-a-week cap, and the refusal to run at all
  on figures nobody should act on.
"""
