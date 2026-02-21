# Science Behind BriefBot

This document explains how BriefBot works, what scientific ideas it applies, and the evidence behind those ideas.

## System Overview

BriefBot is a research workflow, not a single model. It combines:

- Intent and complexity classification to decide how to search.
- Optional query decomposition to turn complex questions into focused sub-questions.
- A two-stage web search (light pass, then targeted deep pass).
- Epistemic routing that changes retrieval and ranking weights based on what kind of truth is needed.
- Evidence-weighted synthesis that preserves disagreements.
- A corrective self-reflection gate for follow-up questions.

## Techniques Applied and Evidence

### 1) Complexity Classification + Optional Query Decomposition

**What we do**
- Classify a query as `BROAD_EXPLORATORY` or `COMPLEX_ANALYTICAL`.
- If complex, optionally decompose into 3-5 sub-questions before deeper retrieval.

**Why it helps**
- Decomposition reduces reasoning load and improves coverage on multi-hop questions.

**Evidence**
- Plan-and-Solve prompting shows that explicit decomposition improves zero-shot reasoning for complex tasks (Wang et al., 2023).
- Chain-of-Thought prompting demonstrates that structured intermediate reasoning improves performance on multi-step problems (Wei et al., 2022).

### 2) Epistemic Routing + Dynamic Weighting

**What we do**
- Classify the epistemic stance of the question (opinion, factual, trending, how-to, or balanced).
- Adjust ranking weights across sources (e.g., Reddit/X higher for sentiment, Web higher for technical facts, YouTube higher for how-to).

**Why it helps**
- Different questions require different evidence types. A single fixed ranking can underweight the most relevant source class.

**Evidence**
- Mixture-of-Experts routing shows that task-conditional routing improves outcomes over fixed, uniform treatment of all inputs.
- Information Retrieval theory supports weighting sources based on the type of truth required (epistemic alignment).

### 3) Two-Stage Web Search (Light Pass -> Targeted Deep Pass)

**What we do**
- Run a light web search first to discover terms, entities, and signal sources.
- Use those signals to run targeted deep searches and refine retrieval.

**Why it helps**
- Early reconnaissance reduces query drift and improves precision in later retrieval.

**Evidence**
- Iterative retrieval is a common IR strategy for narrowing scope and improving relevance.

### 4) Corrective Retrieval-Augmented Generation (CRAG) Gate

**What we do**
- For follow-up questions, run a self-reflection gate.
- If confidence that existing context contains the answer is below 0.8, trigger a small targeted re-search.

**Why it helps**
- Prevents hallucinations and stale answers when context is insufficient.

**Evidence**
- CRAG shows that self-reflection with corrective retrieval improves factual reliability and reduces error propagation (Yan et al., 2024).

### 5) Dialectical Synthesis (Conflict Preservation)

**What we do**
- Explicitly preserve and present disagreements between sources.
- Avoid averaging away contradictions.

**Why it helps**
- Conflicts often carry the most actionable information (e.g., official claims vs on-the-ground sentiment).

**Evidence**
- Multi-perspective RAG and dialectical prompting emphasize exposing disagreement to improve decision quality.

## How These Ideas Fit Together

1. **Classify** the question (complexity + epistemic stance).
2. **Decompose** only when complex.
3. **Probe lightly**, then **retrieve deeply** with better targets.
4. **Rank dynamically** based on the stance.
5. **Synthesize dialectically** and preserve conflicts.
6. **Reflect** on follow-ups and re-search only when confidence is low.

The result is a research pipeline that adapts the retrieval strategy to the user's epistemic goal, while reducing reasoning errors and preserving real-world disagreement.
