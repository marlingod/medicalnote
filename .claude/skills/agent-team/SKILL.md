---
name: agent-team
description: >
  Orchestrates a team of specialized AI agents (Researcher, Writer, Reviewer, Adversarial Critic,
  Test Engineer, Implementation Architect) that collaborate through structured adversarial debate
  to produce high-quality software architecture documents, PRDs, implementation plans, and code.
  Agents challenge each other's claims using evidence-weighted consensus — only claims backed by
  real evidence survive. Use this skill whenever the user wants: multi-perspective technical analysis,
  adversarial review of architecture decisions, a full research-to-implementation pipeline with
  built-in quality gates, a "red team / blue team" analysis of any technical approach, a PRD or
  design doc that has been stress-tested by simulated experts, or any task where they say things
  like "have agents debate this", "research and implement", "I want multiple perspectives",
  "challenge this design", "write a PRD with review", or "red team this architecture".
---

# Agent Team: Adversarial Research-to-Implementation Pipeline

## Overview

This skill orchestrates 6 specialized AI agents in a structured adversarial debate protocol.
Unlike simple chain-of-thought or sequential agent pipelines, this system models real scientific
discourse: agents make claims, back them with evidence, and other agents actively try to disprove
those claims. Only evidence-weighted consensus survives into the final deliverables.

**Why this matters:** A single-pass LLM response has no internal adversarial pressure. It confirms
its own biases. This system forces every architectural claim through a gauntlet of specialized
skeptics before it reaches the final document.

## Agent Roster

Six agents, each with a distinct epistemic role:

| Agent | Role | Temperature | Purpose |
|-------|------|-------------|---------|
| **Researcher** | Blue Team | 0.3 | Gathers evidence, identifies patterns, proposes initial architecture |
| **Writer** | Blue Team | 0.4 | Synthesizes findings into structured documents (PRD, design docs) |
| **Reviewer** | Neutral | 0.5 | Checks completeness, consistency, alignment with requirements |
| **Adversarial Critic** | Red Team | 0.8 | Actively tries to disprove claims, finds logical gaps, proposes failure modes |
| **Test Engineer** | Red Team | 0.6 | Designs tests that would falsify claims, identifies untestable assertions |
| **Implementation Architect** | Blue Team | 0.3 | Translates surviving claims into concrete code, identifies practical blockers |

The temperature gradient is intentional: Red Team agents run hotter to generate more creative
attacks, while Blue Team agents run cooler for precision. This mimics real scientific debate
where skeptics think laterally while researchers think precisely.

## When to Use This Skill

Read `references/agent-roles.md` for detailed agent system prompts before starting.

Trigger this skill when the user wants any of:
- Multi-agent research and analysis on a technical topic
- Architecture design with adversarial review
- Full PRD-to-implementation pipeline with quality gates
- Red team / blue team analysis of a technical decision
- Stress-tested design documents
- Any task requiring multiple expert perspectives with debate

## Execution Protocol

### Phase 0: Setup

1. Create a workspace directory: `agent-team-workspace/<topic-slug>/`
2. Initialize the findings document from `assets/findings-template.md`
3. Read `references/agent-roles.md` for the full agent system prompts
4. Confirm the research question / architecture challenge with the user

### Phase 1: Research & Initial Proposal (Blue Team)

Run the **Researcher** agent first. The orchestrator script handles this:

```bash
cd /path/to/agent-team
python scripts/orchestrator.py \
  --phase research \
  --topic "<user's topic>" \
  --workspace "agent-team-workspace/<topic-slug>" \
  --max-rounds 3
```

The Researcher produces a structured proposal with tagged claims:

```
[CLAIM-001] {evidence: "high" | "medium" | "low" | "none"}
<claim text>
[EVIDENCE] <supporting evidence with source>
[CONFIDENCE] <0.0-1.0>
```

Every claim MUST have an evidence tag. Claims with evidence:"none" are flagged as hypotheses.

### Phase 2: Documentation (Writer)

The **Writer** takes the Researcher's output and produces:
- A structured findings document
- A draft PRD (if implementation is requested)
- Architecture decision records (ADRs)

```bash
python scripts/orchestrator.py \
  --phase write \
  --workspace "agent-team-workspace/<topic-slug>"
```

### Phase 3: Adversarial Debate (Red Team vs Blue Team)

This is the core innovation. Run the debate loop:

```bash
python scripts/orchestrator.py \
  --phase debate \
  --workspace "agent-team-workspace/<topic-slug>" \
  --max-rounds 3 \
  --consensus-threshold 0.7
```

The debate follows this protocol for each round:

1. **Critic attacks** — The Adversarial Critic reads all claims and attempts to:
   - Find logical contradictions between claims
   - Identify missing failure modes
   - Propose alternative explanations for evidence
   - Challenge assumptions that aren't backed by evidence
   
2. **Test Engineer challenges** — Designs specific tests that would falsify claims:
   - "If CLAIM-003 is true, then X should also be true. Is X verified?"
   - "CLAIM-007 is unfalsifiable as stated — rephrase or remove"
   - Proposes concrete test cases and benchmarks

3. **Researcher defends** — Responds to attacks with:
   - Additional evidence
   - Refined claims with caveats
   - Acknowledged gaps (honest uncertainty)
   - Concessions where attacks are valid

4. **Reviewer judges** — Evaluates each claim-attack-defense triple:
   - Assigns evidence weight (0.0-1.0)
   - Flags unresolved disputes
   - Updates consensus status

5. **Consensus check** — Claims are scored:
   - Evidence weight × Defender confidence × (1 - Successful attack strength)
   - Claims above threshold survive
   - Claims below threshold are either revised or removed
   - Unresolved disputes are flagged for human review

### Phase 4: Implementation (Blue Team)

After consensus, the **Implementation Architect** takes surviving claims and:
- Writes concrete implementation code
- Maps each code section to the claims it implements
- Identifies practical blockers not caught in debate
- Proposes a phased implementation plan

```bash
python scripts/orchestrator.py \
  --phase implement \
  --workspace "agent-team-workspace/<topic-slug>"
```

### Phase 5: Final Review & Synthesis

One final pass where ALL agents review the complete package:

```bash
python scripts/orchestrator.py \
  --phase synthesize \
  --workspace "agent-team-workspace/<topic-slug>"
```

This produces the final deliverables:
- `findings.md` — Consensus findings with full provenance trail
- `prd.md` — Product Requirements Document (if applicable)
- `implementation-plan.md` — Phased implementation with code
- `debate-log.md` — Full transcript of adversarial debate
- `evidence-registry.json` — Machine-readable evidence chain
- `test-plan.md` — Test cases derived from debate challenges

## Evidence-Weighted Consensus Engine

The consensus mechanism is the heart of this system. Read `references/debate-protocol.md`
for the full algorithm, but the key principle is:

**Claims don't survive by authority — they survive by evidence.**

Each claim carries:
- `evidence_sources`: List of concrete references (docs, benchmarks, examples)
- `confidence`: The proposer's confidence (0.0-1.0)
- `attack_strength`: Strongest successful attack (0.0-1.0)  
- `defense_strength`: Strength of defense against attacks (0.0-1.0)
- `consensus_score`: Computed as `evidence_weight * confidence * defense_strength * (1 - attack_strength)`

Claims with `consensus_score >= threshold` enter the final document as "Established."
Claims between 0.4 and threshold enter as "Provisional — needs further evidence."
Claims below 0.4 are removed with a note in the debate log explaining why.

## Running the Full Pipeline

For a complete research-to-implementation run:

```bash
python scripts/orchestrator.py \
  --phase all \
  --topic "<user's research question or architecture challenge>" \
  --workspace "agent-team-workspace/<topic-slug>" \
  --max-rounds 3 \
  --consensus-threshold 0.7 \
  --output-format markdown
```

## Tips for Effective Use

- **Be specific with the topic**: "Design a distributed cache for our microservices" works
  better than "design something for caching"
- **Set round limits**: 3 debate rounds is usually sufficient; more rounds have diminishing
  returns and increasing token cost
- **Review the debate log**: The most valuable output is often not the final document but
  the attacks that were raised and how they were addressed
- **Human-in-the-loop**: After Phase 3, review flagged disputes before Phase 4. The system
  explicitly marks claims it couldn't resolve.
- **Adjust consensus threshold**: 0.7 is strict (scientific paper quality). Use 0.5 for
  exploratory work, 0.8+ for production architecture decisions.

## Output Structure

```
agent-team-workspace/<topic-slug>/
├── findings.md                  # Living findings document (updated each round)
├── prd.md                       # Product Requirements Document
├── implementation-plan.md       # Phased implementation with code
├── test-plan.md                 # Test cases from debate challenges
├── debate-log.md                # Full adversarial debate transcript
├── evidence-registry.json       # Machine-readable evidence chain
└── rounds/
    ├── round-1/
    │   ├── researcher-proposal.md
    │   ├── critic-attacks.md
    │   ├── test-engineer-challenges.md
    │   ├── researcher-defense.md
    │   ├── reviewer-judgment.md
    │   └── consensus-snapshot.json
    ├── round-2/
    │   └── ...
    └── round-3/
        └── ...
```
