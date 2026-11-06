"""The campaign builder: Search only, as the client's brief says for the MVP.

- `validate` -- the six checks every line of ad text passes, in the brief's order.
- `keywords` -- the keywords gate: only a phrase Keyword Planner confirms.
- `draft` -- fifteen headlines and four descriptions per theme, kept if they pass.
- `build` -- a whole campaign written for review: searches, then text, then checks.
- `campaign` -- the plan as data, and the one request that creates it in Google.
- `launch` -- checked here, checked by Google, then created whole.
- `models` -- the draft between "start writing" and "launch", and its record.

Since 6 November it builds and launches whole campaigns, at the owner's request,
from the designs (Figma 87:10926 and 17:2048). Still waiting on the client: the
per-industry prohibited-claim lists and the category fallback templates. The
validator reads whatever lists it is given and passes everything when given
none, which is the only honest behaviour for a stage nobody has described yet.
"""
