---
name: research-information-retreival
description: Search, retrieve, and synthesize information from the web, documentation, or codebases. Use when the user wants to research a topic, find documentation, compare technologies, or answer knowledge-intensive questions.
---

# Research & Information Retrieval Skill

Execute research tasks that produce accurate, well-structured, properly attributed findings by searching intelligently, cross-referencing multiple sources, and synthesizing into clear outputs.

---

## 1. Clarifying Research Scope Before Starting

Assess whether the request is sufficiently defined before beginning any non-trivial task.

**Ask for clarification when:**
- The topic is ambiguous (e.g., "research Python" — which aspect?)
- The desired depth is unclear (quick overview vs. comprehensive deep-dive)
- The target audience is unknown (beginner vs. expert, technical vs. business)
- The time horizon matters (current state vs. historical vs. future trends)

**Do not ask when:**
- The request is a clear, specific question with an obvious answer type
- The user provides enough context to infer intent
- A quick search can resolve the ambiguity faster than asking

When in doubt, state your assumption explicitly and proceed: *"I'll interpret this as a comparison of managed vs. self-hosted options — let me know if you meant something otherwise."*

---

## 2. Query Formulation and Search Strategy

**Principles:**
- Be specific: prefer `"React Server Components performance tradeoffs 2024"` over `"React performance"`.
- Use domain-specific vocabulary matching the target domain.
- Decompose complex questions into individual sub-queries.
- Anticipate source types: official docs, papers, benchmarks, community discussions.
- Iterate on failure — never repeat the same query expecting different results.

**Query progression pattern:**
1. Start with a broad orienting query to map the landscape
2. Follow with targeted queries on specific sub-topics
3. Use a verification query to cross-check key claims

**For deep research tasks:** Break the topic into 3-5 research sub-questions before searching. For broad topics, launch parallel research agents — one per cluster of sub-questions — then synthesize findings in the main session.

---

## 3. Tool Selection

| Situation | Preferred Tool |
|---|---|
| Current events, recent releases, live documentation | `WebSearch` + `WebFetch` |
| General knowledge that doesn't change frequently | Internal knowledge first, then `WebSearch` to verify |
| Project-specific code, configs, or internal docs | `Glob`, `Grep`, `Read` on local files |
| Official documentation for a library/framework | `WebFetch` the docs URL directly |
| Comparing multiple technologies | `WebSearch` for each, then synthesize |
| Understanding a codebase's architecture | `Glob` to map structure, `Grep` for patterns, `Read` for key files |
| Neural/semantic search (companies, code, people) | Exa MCP: `web_search_exa`, `get_code_context_exa` |
| Full content scraping + crawling | Firecrawl MCP: `firecrawl_search`, `firecrawl_scrape` |

**Rules:**
- Always check local files first for project-specific questions.
- Use `WebSearch` when information could have changed in the past 12 months.
- Avoid redundant searches: if two searches return similar results, synthesize rather than searching again.
- Prefer Exa for code examples, company research, and people lookups; prefer Firecrawl for full-page content extraction.

---

## 4. Multi-Source Research and Cross-Referencing

Reliable research never relies on a single source.

**Multi-source protocol:**
1. Identify source types needed: official docs, academic papers, practitioner blogs, community discussions, benchmarks.
2. Gather at least 2-3 independent sources for any factual claim that influences a decision.
3. Priority: official documentation > peer-reviewed research > reputable publications > practitioner blogs > community discussions.
4. Run parallel searches when sub-queries are independent — do not search sequentially.
5. Cross-reference key facts: if Source A says X and Source B says Y, investigate further.

**Aim for 15-30 unique sources on deep research tasks.** Deep-read 3-5 key sources in full — do not rely only on snippets.

**For codebase research:**
- Use `Grep` to find all occurrences of a concept, not just the first match.
- Use `Glob` to understand the full file structure before diving into specific files.
- Check both implementation files and their associated tests.

---

## 5. Iterative Retrieval for Codebase Context

When searching a codebase and initial queries return poor results, use the iterative retrieval pattern:

1. **Dispatch**: broad keyword search across candidate file patterns
2. **Evaluate**: score each file's relevance (high / medium / low / none)
3. **Refine**: add terminology discovered in high-relevance files; exclude confirmed irrelevant paths; target identified gaps
4. **Loop**: repeat with refined criteria, max 3 cycles

**Stop condition**: 3+ high-relevance files with no critical gaps remaining. Use the smallest set of high-relevance files rather than accumulating mediocre ones.

This solves the "context problem" where subagents don't know what context they need until they start working.

---

## 6. Evaluating and Verifying Sources

**Source quality indicators:**
- **Authority**: Is this the official source? Is the author a recognized expert?
- **Recency**: For fast-moving domains (AI, cloud, frameworks), anything over 18 months old may be outdated.
- **Specificity**: Does the source address the exact question?
- **Corroboration**: Is this claim supported by other independent sources?
- **Motivation**: Does the source have a commercial incentive to present biased information?

**Verification steps for critical claims:**
1. Find a second independent source making the same claim
2. Check whether the claim has been contradicted in more recent sources
3. For technical claims, look for working examples or benchmark data
4. For statistics, trace to the original study or data provider

**When you cannot verify:** State clearly that a claim is unverified or single-sourced. Never present uncertain information with false confidence.

---

## 7. Handling Conflicting and Outdated Information

**Conflicting sources:** Do not silently pick one. Identify whether it is a factual contradiction, difference of opinion, or context-dependent advice. Present both positions and explain conditions under which each applies.

> "Sources disagree on this point. [Source A] recommends X, citing [reason]. [Source B] recommends Y, citing [reason]. The difference appears to stem from [context]. For your use case, [recommendation]."

**Outdated information signals:**
- Publication date more than 12-18 months ago in a fast-moving domain
- References to deprecated APIs or discontinued products
- More recent sources contradict the older source's claims

Flag outdated information explicitly rather than silently using it. Search for "[topic] [current year]" to surface updates.

---

## 8. Depth vs. Breadth

**Choose breadth (survey) when:** The user is exploring an unfamiliar domain, asking for a comparison, or requesting a summary.

**Choose depth (deep-dive) when:** The user has a specific narrow problem, the topic involves nuanced non-obvious answers, or a high-stakes decision is being made.

**Adaptive strategy:**
1. Begin with a breadth pass (1-2 searches) to map the landscape
2. Identify the 1-3 sub-topics most relevant to the actual need
3. Conduct targeted deep dives on those sub-topics only
4. Resist researching everything — surface area is not quality

---

## 9. Citation and Source Attribution

Every factual claim from a source must be attributed. Citation is not optional.

**Citation rules:**
- Cite the source immediately after the sentence it supports — not in a bulk references section at the end.
- For web sources, include the URL or source name inline.
- For local files, cite the file path and relevant line numbers or function names.
- Cite up to three sources per claim; choose the most authoritative.
- Never reproduce copyrighted content verbatim; paraphrase and cite.
- Never fabricate citations or invent URLs.

**Formats:**
- Web: `According to the React documentation (react.dev/reference/hooks), ...`
- Local file: `The configuration is set in \`/src/config/database.ts\` (lines 42-58).`
- Multiple: `This behavior is confirmed by both the MDN documentation and the WHATWG spec.`

---

## 10. Synthesizing and Presenting Research

**Synthesis process:** Aggregate → Deduplicate → Reconcile conflicts → Abstract underlying patterns → Contextualize to user's situation → Prioritize most important findings first.

**Avoid:** list dumping without connecting points; false balance between fringe and mainstream; over-hedging every statement.

**Report structure (standard):**
1. Executive summary (2-3 sentences): direct answer to the core question
2. Main sections (`##` headers): one major aspect each
3. Comparison tables: when evaluating multiple options
4. Code snippets: for technical implementations
5. Caveats and limitations
6. Closing synthesis

**Format by query type:**
- Comparison (A vs. B): always use a markdown table as primary format
- "How does X work": structured explanation with `##` sections and inline examples
- "What are the options for X": unordered list with brief descriptions
- "Should I use X or Y": brief recommendation upfront, then supporting analysis
- Academic/deep research: long-form prose with headings and citations throughout

**Universal rules:**
- Begin with a 2-3 sentence overview that answers the core question before diving into detail
- Never start the response with a header — begin with prose
- Use Level 2 headers (`##`) for major sections
- Prefer flat lists over nested; use tables for comparisons

---

## 11. Research Completeness Check

Before delivering findings:
- [ ] Does the response directly answer the original question?
- [ ] Have all parts of a multi-part question been addressed?
- [ ] Are key claims cited to sources?
- [ ] Is conflicting information surfaced and resolved (or flagged)?
- [ ] Is potentially outdated information flagged?
- [ ] Is depth appropriate — neither too shallow nor exhaustive?
- [ ] Does the response begin with a summary, not a header?
- [ ] Are comparisons in table format?
- [ ] Are unverified claims explicitly flagged?

---

## 12. Codebase Research Specifics

When researching a local codebase rather than the web:

1. **Map before diving**: use `Glob` to understand project structure before reading individual files
2. **Search for concepts, not just strings**: use `Grep` with pattern matching to find all files related to a concept
3. **Cite precisely**: reference exact file paths and line numbers for every code claim
4. **Distinguish implementation from intent**: read tests and comments alongside implementation — they often reveal intended behavior
5. **Use technical names exactly**: refer to function names, class names, and file paths using exact spelling in backticks
6. **Note gaps**: if the codebase doesn't contain enough information, say so explicitly — do not speculate or fabricate
7. **Add a Notes section**: after the main answer, include adjacent code or concepts that have surface similarity but were not the primary answer

Codebase research does not replace web research when the question involves general best practices or external library behavior.
