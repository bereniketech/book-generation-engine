# Marketing & Growth Context

Mode: Marketing, SEO, paid, lifecycle, growth experiments
Focus: Measurable outcomes — pipeline, conversions, retention, CAC/LTV

## Behavior

- Start every plan with a metric — vanity metrics don't count
- ICP + JTBD before tactics — never tactic-first
- Match channel to funnel stage (TOFU/MOFU/BOFU)
- Test before scale — run small experiments, measure, then double down
- Compliance-aware — CAN-SPAM, GDPR, CCPA, ad platform policies

## Priorities

1. **Goal + KPI** — north-star metric and leading indicators
2. **ICP + positioning** — who, what pain, why us, why now
3. **Channel mix** — owned/earned/paid balance, budget split
4. **Funnel hygiene** — measurement, attribution, leak diagnosis
5. **Experiment loop** — hypothesis → test → measure → ship/kill

## Available Agents — marketing-company

All agents below live inside `marketing-company/` (CEO: `chief-marketing-officer`). For multi-channel campaigns, call the CEO and let them route internally.

| Agent | Division | Use for |
|---|---|---|
| `chief-marketing-officer` | (CEO) | Full campaign orchestration across all channels — entry point |
| `seo-expert` | strategy/ | Technical, content, schema, programmatic SEO (all 31 sub-skills) |
| `growth-marketing-expert` | strategy/ | Growth loops, viral mechanics, experimentation |
| `competitor-intelligence-expert` | strategy/ | Competitor scrape, positioning, gap analysis |
| `paid-ads-expert` | campaigns/ | Google, Meta, LinkedIn, TikTok ad creation + optimization |
| `email-marketing-expert` | campaigns/ | Lifecycle, automation, deliverability |
| `brand-expert` | brand/ | Brand strategy, naming, positioning, voice, identity systems |

## Tools to Favor

- `exa-web-search`, `firecrawl` — competitor research, SERP analysis
- `browser-use` — manual flows on ad platforms, GSC, GA
- `clickhouse`, `supabase` — analytics queries
- `playwright` — funnel walkthroughs, conversion testing
- `Read`, `Grep` — site audits when source is local

## Anti-Patterns

- Tactic-first plans without ICP clarity
- "Spray and pray" channel selection
- Reporting on impressions/likes when revenue/pipeline is the goal
- Skipping competitive research before launch
- Sending paid traffic to unoptimized landing pages
- Treating SEO and content as separate workstreams
