---
name: deep-research
description: Conduct autonomous multi-step research using web search, Exa, and Firecrawl. Covers market analysis, competitive landscaping, technology evaluation, and structured research reports.
---

# Deep Research

Conduct systematic, multi-source research and synthesize findings into actionable reports.

---

## 1. Research Protocol

```
Step 1: Define the research question precisely
  Bad:  "Research AI tools"
  Good: "Which AI code generation tools are used by enterprise teams >500 engineers, 
         their pricing, integration complexity, and reported ROI?"

Step 2: Identify source types
  Primary: surveys, interviews, first-party data
  Secondary: industry reports, academic papers, analyst research
  Tertiary: news, blog posts, social discussion

Step 3: Execute search strategy (§2)
Step 4: Synthesize findings (§3)
Step 5: Validate key claims (§4)
Step 6: Produce report (§5)
```

---

## 2. Search Strategy

### Web search (use Exa for semantic, Google for broad)

```
For each research question, search 3–5 angles:
- "[Topic] market size 2025"
- "[Topic] industry report"
- "[Competitor] pricing OR revenue"
- "best [topic] [year]" — for current state
- site:reddit.com "[topic]" — for honest user opinions
- "[Topic] vs [competitor] comparison"
```

### Exa (semantic search — better for research)
```
# Semantic search finds related concepts, not just keyword matches
exa_search(query="enterprise AI developer tools adoption rate ROI", type="neural")

# Domain-filtered search
exa_search(query="AI code review tools", include_domains=["github.com", "arxiv.org"])

# Find similar pages
exa_find_similar(url="https://relevant-report.com/article")
```

### Firecrawl (extract structured data from websites)
```
# Scrape a single page
firecrawl_scrape(url="https://competitor.com/pricing")

# Crawl entire site section
firecrawl_crawl(url="https://competitor.com/blog", max_pages=20)

# Extract structured data
firecrawl_extract(url="https://g2.com/products/tool/reviews", 
                  prompt="Extract: reviewer company size, rating, pros, cons")
```

---

## 3. Synthesis Framework

After collecting sources, organize findings into:

```markdown
## Finding 1: [Key claim]
**Confidence**: High/Medium/Low
**Evidence**:
- [Source 1]: [Specific data point] [URL]
- [Source 2]: [Supporting evidence] [URL]
**Contradicting evidence**: [If any]

## Finding 2: ...
```

**Synthesis rules:**
- Mark confidence level for every claim
- Prefer primary sources (original data) over secondary
- When sources contradict: present both, note the conflict, explain likely reason
- Distinguish: fact vs interpretation vs prediction
- Quantify when possible: "$4.2B market" not "large market"

---

## 4. Market Research Template

```markdown
# Market Research: [Topic]
Date: [Date] | Researcher: Claude

## Executive Summary (3 bullets max)
- [Most important finding]
- [Second most important]
- [Key implication for action]

## Market Size
- TAM: $[X]B (source: [X], methodology: [Y])
- SAM: $[X]B (our addressable portion)
- SOM: $[X]M (realistically capturable in 3 years)
- Growth rate: [X]% CAGR through [year]

## Key Players
| Company | Market share | Positioning | Key strength |
|---|---|---|---|
| [A] | ~X% | [segment] | [advantage] |

## Customer Segments
| Segment | Size | Pain points | Willingness to pay |
|---|---|---|---|
| [Enterprise] | ~[N]k companies | [pain] | $[X]/month |

## Technology Trends
- [Trend 1]: [impact on market]
- [Trend 2]: [impact on market]

## Regulatory Landscape
- [Regulation]: [applies to whom], [timeline]

## Opportunities
1. [Opportunity with evidence]
2. [Opportunity with evidence]

## Sources
[Full citation list]
```

---

## 5. Competitive Analysis Report

```markdown
# Competitive Landscape: [Your Category]
Date: [Date]

## Overview
[2-sentence summary of competitive dynamics]

## Direct Competitors
[Per competitor: product, pricing, go-to-market, funding, team size, weaknesses]

## Indirect Competitors
[Who else competes for this budget/attention?]

## Positioning Map
[2x2 matrix: axes relevant to your market]

## Gaps & Opportunities
[Where is the white space? What do all competitors fail to do well?]

## Recommended Positioning
[Based on gaps: how should you position?]
```

---

## 6. Research Quality Checklist

- [ ] Research question is specific and answerable
- [ ] At least 5 independent sources consulted
- [ ] Primary sources used where available
- [ ] Conflicting information noted and reconciled
- [ ] All statistics include source and date
- [ ] Confidence level marked on major claims
- [ ] Report includes limitations ("we couldn't find data on X")
- [ ] Conclusions follow from evidence (no speculation presented as fact)
