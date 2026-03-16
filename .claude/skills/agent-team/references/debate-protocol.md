# Adversarial Debate Protocol & Evidence-Weighted Consensus

## Core Principle

Claims survive not by who proposed them, but by how well they withstand attack
and how strong their evidence is. This is modeled on scientific peer review,
not majority vote.

## Consensus Score Formula

```
consensus_score = evidence_weight × confidence × defense_strength × (1 - attack_strength)
```

Where:
- `evidence_weight` (0.0-1.0): Based on evidence level tag
  - "high" → 0.9
  - "medium" → 0.6
  - "low" → 0.3
  - "none" → 0.1
- `confidence` (0.0-1.0): Researcher's stated confidence
- `defense_strength` (0.0-1.0): How well the defense addressed attacks (rated by Reviewer)
- `attack_strength` (0.0-1.0): Max attack confidence that wasn't fully defended

## Claim Lifecycle

```
PROPOSED → CHALLENGED → DEFENDED → JUDGED → {ESTABLISHED | PROVISIONAL | REMOVED}
```

### State Transitions

1. **PROPOSED** — Researcher introduces claim with evidence tag
2. **CHALLENGED** — Critic or Test Engineer attacks the claim
3. **DEFENDED** — Researcher responds with defense or concession
4. **JUDGED** — Reviewer computes consensus score
5. **Terminal states:**
   - `consensus_score >= threshold` → **ESTABLISHED** (enters final document as fact)
   - `0.4 <= consensus_score < threshold` → **PROVISIONAL** (enters with caveat)
   - `consensus_score < 0.4` → **REMOVED** (logged in debate transcript only)

## Round Structure

Each round follows a fixed sequence to ensure fairness:

```
Round N:
  1. Critic reads all current claims → produces attacks
  2. Test Engineer reads claims + attacks → produces test challenges
  3. Researcher reads attacks + challenges → produces defenses
  4. Reviewer reads everything → produces judgments + updated scores
  5. Orchestrator updates findings document with new consensus state
```

### Round Termination Conditions

Stop iterating when ANY of:
- All claims are ESTABLISHED or REMOVED (no PROVISIONAL remains)
- Max rounds reached (default: 3)
- No new attacks were raised (convergence)
- Score changes from previous round are all < 0.05 (stability)

## Evidence Registry Schema

The orchestrator maintains a JSON registry tracking every claim's lifecycle:

```json
{
  "claims": {
    "CLAIM-001": {
      "text": "The system should use event sourcing for audit trail",
      "evidence_level": "high",
      "evidence_sources": [
        "Martin Fowler's Event Sourcing pattern (2005)",
        "Microsoft CQRS/ES documentation"
      ],
      "initial_confidence": 0.85,
      "rounds": [
        {
          "round": 1,
          "attacks": [
            {
              "id": "ATTACK-003",
              "agent": "critic",
              "type": "SCALE_FAILURE",
              "text": "Event sourcing creates unbounded event stores...",
              "confidence": 0.6
            }
          ],
          "defenses": [
            {
              "text": "Snapshots + compaction address unbounded growth...",
              "additional_evidence": ["Kafka log compaction docs"],
              "revised_claim": null
            }
          ],
          "challenges": [
            {
              "id": "TEST-002",
              "agent": "test_engineer",
              "text": "Run load test: 10M events over 30 days...",
              "falsified_if": "Query latency exceeds 200ms p99"
            }
          ],
          "judgment": {
            "evidence_weight": 0.9,
            "confidence": 0.85,
            "attack_strength": 0.6,
            "defense_strength": 0.8,
            "consensus_score": 0.245,
            "verdict": "PROVISIONAL",
            "notes": "Defense addressed growth concern but needs benchmark data"
          }
        }
      ],
      "final_status": "PROVISIONAL",
      "final_score": 0.245
    }
  },
  "metadata": {
    "topic": "...",
    "total_rounds": 3,
    "threshold": 0.7,
    "timestamp": "2026-03-14T..."
  }
}
```

## Debate Integrity Rules

1. **No agent can see another agent's system prompt.** Each agent only sees outputs.
2. **The Critic MUST attack the strongest claims first.** Easy attacks on weak claims waste rounds.
3. **The Researcher MUST concede when an attack is valid.** Stubbornness is penalized by the Reviewer.
4. **The Reviewer MUST be calibrated.** If the Reviewer gives all claims 0.9, something is wrong.
5. **The Test Engineer provides the ultimate tiebreaker.** If a claim is untestable, it cannot be ESTABLISHED — only PROVISIONAL at best.

## Deadlock Resolution

If a claim oscillates between PROVISIONAL and CHALLENGED for 2+ rounds:

1. The orchestrator flags it as DISPUTED
2. Both sides submit their strongest single piece of evidence
3. The Reviewer makes a final ruling
4. If the Reviewer cannot decide, the claim enters the final document as:
   ```
   ⚠️ DISPUTED: [Claim text]
   For: [Best evidence supporting]
   Against: [Best evidence opposing]
   Recommended: Human review required
   ```

## Anti-Patterns to Avoid

- **Rubber-stamp reviews**: Reviewer approving everything → increase Critic temperature
- **Nihilistic criticism**: Critic attacking everything at 1.0 confidence → discount uniform attacks
- **Evidence inflation**: Researcher citing "common knowledge" as "high" evidence → audit rigorously
- **Scope creep**: Agents introducing claims outside the original topic → orchestrator filters
- **Circular defense**: "This is true because the document says so" → Reviewer rejects immediately
