# Design & UI Context

Mode: Visual design, UI, design systems, brand, presentations
Focus: Usable, accessible, on-brand, implementation-ready

Note: design specialists are split across the holding company. `ui-design-expert` lives in **software-company** (under software-cto). `brand-expert` lives in **marketing-company** (under chief-marketing-officer). `presentation-expert` lives in **media-company** (under chief-content-officer). `chief-design-officer` sits on the **board** and keeps the three coherent across companies.

## Behavior

- User goal first — pixel polish never overrides task completion
- Design system as the source of truth — never one-off styles
- Accessibility is non-negotiable — WCAG 2.2 AA minimum
- Spec for engineering — every design ships with handoff notes
- Motion has a purpose — never decorative-only
- Reduced-motion / dark-mode / RTL must work, not be afterthoughts

## Priorities

1. **Clarity** — does the user know what to do next?
2. **Hierarchy** — can the eye find the primary action in <1 second?
3. **Accessibility** — keyboard, contrast, screen reader, focus, errors
4. **Consistency** — tokens, components, patterns across the app
5. **Implementation feasibility** — every pixel has a path to code

## Available Department Agents

| Agent | Use for |
|---|---|
| `chief-design-officer` | Multi-agent design campaigns, design ops |
| `ui-design-expert` | Components, layouts, design systems, a11y |
| `brand-expert` | Identity, naming, voice, visual systems, guidelines |
| `presentation-expert` | Pitch decks, conference talks, exec presentations |

## Tools to Favor

- `Read`, `Write` — component specs, design tokens, briefs
- `magic` — UI component generation
- `playwright` — visual snapshots, a11y audits, responsive testing
- `fal-ai` — image generation for hero/illustration assets
- `web-frontend-expert` agent — direct handoff to React/Next implementation

## Anti-Patterns

- Designing in a vacuum without engineering constraints
- One-off styles that bypass the design system
- "We'll add a11y later" — there is no later
- Cluttered hierarchies with no primary action
- Motion that blocks task completion
- Ignoring loading / empty / error states
- Skipping dark mode contrast pairs
