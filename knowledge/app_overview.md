# How this app works

## What it does

This is an AI-powered donor analytics tool built for the Institute for Advanced Studies in Culture (IASC). It lets the development team ask natural language questions about their donor database and receive data-grounded, actionable answers — without writing SQL or navigating a reporting interface.

Example questions it can answer:
- "Which lapsed donors in Virginia gave more than $5,000?"
- "Plan a fundraising trip to NYC: who should we meet?"
- "Which subscribers have high wealth scores but have never donated?"
- "What does our donor pipeline look like by state?"

## Architecture

```
User question (chat input)
        │
        ▼
LLM (Claude or GPT, selectable in the sidebar)
        │
        ├── Decides which data to retrieve
        │   (tool use / function calling)
        │
        ├── Calls Python query functions
        │   that run parameterized SQL against
        │   a SQLite database of donor records
        │
        └── Optionally uses a fundraising
            knowledge base injected into
            the system prompt
        │
        ▼
LLM synthesizes results into a natural-language
response with data citations and recommendations
        │
        ▼
Displayed in the Streamlit chat UI
(with token usage and cost per response)
```

## Available tools (what the LLM can query)

The LLM has access to eight query functions:

| Tool | Purpose |
|---|---|
| `search_donors` | Filter contacts by location, status, giving history, subscription, wealth score, email engagement |
| `get_donor_detail` | Full profile for a single contact including gift history and interactions |
| `get_summary_statistics` | Aggregate totals and averages grouped by state, status, subscription type, or giving vehicle |
| `get_geographic_distribution` | Donor counts and giving totals by state — useful for trip planning |
| `get_lapsed_donors` | Contacts who have not given recently but have a giving history |
| `get_prospects_by_potential` | Non-donors ranked by engagement signals and wealth indicators |
| `plan_fundraising_trip` | Best contacts to meet in a target city, ranked by a composite score |
| `get_app_usage_stats` | Cumulative token usage and cost across all sessions |

## Data

The database contains ~5,000 synthetic donor records with fields drawn from three real IASC data sources:

- **Salesforce:** contact info, gift dates and amounts, donor status, giving vehicle
- **MailChimp:** subscription type/status, email open rate, last click date
- **WealthEngine:** wealth score (1–10)

All data is **entirely synthetic** — procedurally generated to resemble real fundraising data but containing no actual IASC donor information. No real names, contact details, or giving histories are stored.

## Model options

Select the model in the sidebar under Settings:

| Model | Speed | Cost | Best for |
|---|---|---|---|
| **GPT-5.4 mini** (default) | Fast | Cheapest | Most queries |
| GPT-5.4 | Fast | Moderate | Complex analysis |
| Claude Sonnet | Moderate | Moderate | Alternative for complex queries |
| Claude Haiku | Fast | Cheap | Development and testing |

GPT models require an `OPENAI_API_KEY`; Claude models require an `ANTHROPIC_API_KEY`.

## Knowledge base

In addition to live data queries, the app can draw on two reference documents injected into the system prompt:

- **Fundraising best practices** — general principles for donor cultivation, re-engagement, moves management, and major gift strategy
- **IASC organizational context** — IASC-specific notes on their donor base, fundraising approach, and Hedgehog Review subscriber relationships

These are only loaded when the question signals it needs them (keyword matching), saving tokens on pure data queries.

## Token tracking

Every response shows an inline usage line: model, number of API calls, input/output tokens, estimated cost, and latency. The sidebar accumulates totals for the current session. Costs are also logged persistently across sessions and can be queried: "How much have we spent on API calls this week?"

## Limitations

- **Synthetic data only.** Real Salesforce, MailChimp, and WealthEngine integration is out of scope for this prototype.
- **No authentication.** Do not deploy this app publicly with real donor data.
- **No data export.** Results appear in the chat; there is no CSV download.
- **No persistent conversation history.** Closing the browser tab starts a fresh session.
- **Wealth and engagement scores are estimates.** Mock scores simulate real data but do not reflect actual donor capacity or behavior.
