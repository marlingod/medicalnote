#!/usr/bin/env python3
"""
Agent Team Orchestrator
=======================
Orchestrates a team of specialized AI agents through adversarial debate rounds
to produce evidence-weighted consensus on software architecture decisions.

Usage:
    python orchestrator.py --phase all --topic "Design a distributed cache" --workspace ./workspace
    python orchestrator.py --phase debate --workspace ./workspace --max-rounds 3
"""

import argparse
import json
import os
import sys
import time
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

AGENT_CONFIGS = {
    "researcher": {
        "role": "Blue Team — Evidence Gatherer & Initial Architect",
        "temperature": 0.3,
        "team": "blue",
    },
    "writer": {
        "role": "Blue Team — Document Synthesizer",
        "temperature": 0.4,
        "team": "blue",
    },
    "reviewer": {
        "role": "Neutral — Quality & Consistency Checker",
        "temperature": 0.5,
        "team": "neutral",
    },
    "critic": {
        "role": "Red Team — Claim Destroyer",
        "temperature": 0.8,
        "team": "red",
    },
    "test_engineer": {
        "role": "Red Team — Falsification Designer",
        "temperature": 0.6,
        "team": "red",
    },
    "implementer": {
        "role": "Blue Team — Code Realizer",
        "temperature": 0.3,
        "team": "blue",
    },
}

EVIDENCE_WEIGHTS = {
    "high": 0.9,
    "medium": 0.6,
    "low": 0.3,
    "none": 0.1,
}

# ---------------------------------------------------------------------------
# Agent System Prompts (loaded from references/agent-roles.md or inline)
# ---------------------------------------------------------------------------

def load_agent_prompts(skill_dir: str) -> dict:
    """Load agent system prompts from the references directory."""
    roles_path = os.path.join(skill_dir, "references", "agent-roles.md")
    prompts = {}

    if os.path.exists(roles_path):
        with open(roles_path, "r") as f:
            content = f.read()
        # Parse system prompts from markdown code blocks
        import re
        sections = re.split(r"## \d+\.\s+", content)
        agent_map = {
            "Researcher Agent": "researcher",
            "Writer Agent": "writer",
            "Reviewer Agent": "reviewer",
            "Adversarial Critic Agent": "critic",
            "Test Engineer Agent": "test_engineer",
            "Implementation Architect Agent": "implementer",
        }
        for section in sections:
            for title, key in agent_map.items():
                if title in section:
                    # Extract content between ``` markers under System Prompt
                    match = re.search(
                        r"### System Prompt\s*```(.*?)```",
                        section,
                        re.DOTALL,
                    )
                    if match:
                        prompts[key] = match.group(1).strip()
    return prompts


# ---------------------------------------------------------------------------
# Claude API Interaction
# ---------------------------------------------------------------------------

def call_claude(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.5,
    max_tokens: int = 4096,
) -> str:
    """
    Call Claude via the Anthropic API using subprocess + curl.
    Works in environments where the anthropic Python SDK may not be installed.
    Falls back to `claude -p` CLI if available.
    """
    # Try using the `claude` CLI tool (preferred in Claude Code environments)
    claude_cli = _find_claude_cli()
    if claude_cli:
        return _call_via_cli(claude_cli, system_prompt, user_message)

    # Fallback: use the Anthropic Python SDK
    try:
        import anthropic
        client = anthropic.Anthropic()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text
    except ImportError:
        pass

    # Fallback: raw curl
    return _call_via_curl(system_prompt, user_message, temperature, max_tokens)


def _find_claude_cli() -> Optional[str]:
    """Check if the `claude` CLI is available."""
    try:
        result = subprocess.run(
            ["which", "claude"], capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _call_via_cli(cli_path: str, system_prompt: str, user_message: str) -> str:
    """Call Claude via the CLI tool."""
    combined = f"SYSTEM CONTEXT:\n{system_prompt}\n\nTASK:\n{user_message}"
    result = subprocess.run(
        [cli_path, "-p", combined],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Claude CLI error: {result.stderr}")
    return result.stdout


def _call_via_curl(
    system_prompt: str,
    user_message: str,
    temperature: float,
    max_tokens: int,
) -> str:
    """Call Claude via curl (requires ANTHROPIC_API_KEY env var)."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError(
            "No Claude CLI found and ANTHROPIC_API_KEY not set. "
            "Install the `claude` CLI or set your API key."
        )
    payload = json.dumps({
        "model": "claude-sonnet-4-20250514",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": system_prompt,
        "messages": [{"role": "user", "content": user_message}],
    })
    result = subprocess.run(
        [
            "curl", "-s", "https://api.anthropic.com/v1/messages",
            "-H", "Content-Type: application/json",
            "-H", f"x-api-key: {api_key}",
            "-H", "anthropic-version: 2023-06-01",
            "-d", payload,
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    resp = json.loads(result.stdout)
    if "content" in resp:
        return resp["content"][0]["text"]
    raise RuntimeError(f"API error: {json.dumps(resp, indent=2)}")


# ---------------------------------------------------------------------------
# Evidence Registry
# ---------------------------------------------------------------------------

class EvidenceRegistry:
    """Tracks all claims, attacks, defenses, and consensus scores."""

    def __init__(self, workspace: str, threshold: float = 0.7):
        self.workspace = workspace
        self.threshold = threshold
        self.registry_path = os.path.join(workspace, "evidence-registry.json")
        self.claims = {}
        self.metadata = {
            "topic": "",
            "total_rounds": 0,
            "threshold": threshold,
            "timestamp": datetime.now().isoformat(),
        }
        self._load()

    def _load(self):
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r") as f:
                data = json.load(f)
            self.claims = data.get("claims", {})
            self.metadata = data.get("metadata", self.metadata)

    def save(self):
        os.makedirs(os.path.dirname(self.registry_path), exist_ok=True)
        with open(self.registry_path, "w") as f:
            json.dump(
                {"claims": self.claims, "metadata": self.metadata},
                f,
                indent=2,
            )

    def register_claim(
        self,
        claim_id: str,
        text: str,
        evidence_level: str,
        evidence_sources: list,
        confidence: float,
    ):
        self.claims[claim_id] = {
            "text": text,
            "evidence_level": evidence_level,
            "evidence_sources": evidence_sources,
            "initial_confidence": confidence,
            "current_confidence": confidence,
            "rounds": [],
            "final_status": "PROPOSED",
            "final_score": 0.0,
        }

    def record_round(
        self,
        claim_id: str,
        round_num: int,
        attacks: list,
        defenses: list,
        challenges: list,
        judgment: dict,
    ):
        if claim_id not in self.claims:
            return
        self.claims[claim_id]["rounds"].append({
            "round": round_num,
            "attacks": attacks,
            "defenses": defenses,
            "challenges": challenges,
            "judgment": judgment,
        })
        # Update status based on consensus score
        score = judgment.get("consensus_score", 0.0)
        self.claims[claim_id]["final_score"] = score
        if score >= self.threshold:
            self.claims[claim_id]["final_status"] = "ESTABLISHED"
        elif score >= 0.4:
            self.claims[claim_id]["final_status"] = "PROVISIONAL"
        else:
            self.claims[claim_id]["final_status"] = "REMOVED"

    def compute_consensus_score(
        self,
        evidence_level: str,
        confidence: float,
        attack_strength: float,
        defense_strength: float,
    ) -> float:
        ew = EVIDENCE_WEIGHTS.get(evidence_level, 0.3)
        score = ew * confidence * defense_strength * (1 - attack_strength)
        return round(score, 4)

    def get_established_claims(self) -> dict:
        return {
            k: v for k, v in self.claims.items()
            if v["final_status"] == "ESTABLISHED"
        }

    def get_provisional_claims(self) -> dict:
        return {
            k: v for k, v in self.claims.items()
            if v["final_status"] == "PROVISIONAL"
        }

    def get_removed_claims(self) -> dict:
        return {
            k: v for k, v in self.claims.items()
            if v["final_status"] == "REMOVED"
        }

    def summary(self) -> str:
        total = len(self.claims)
        established = len(self.get_established_claims())
        provisional = len(self.get_provisional_claims())
        removed = len(self.get_removed_claims())
        proposed = total - established - provisional - removed
        return (
            f"Claims: {total} total | "
            f"{established} established | "
            f"{provisional} provisional | "
            f"{removed} removed | "
            f"{proposed} pending"
        )


# ---------------------------------------------------------------------------
# Phase Executors
# ---------------------------------------------------------------------------

def phase_research(topic: str, workspace: str, prompts: dict) -> str:
    """Phase 1: Research agent investigates the topic."""
    print(f"\n{'='*60}")
    print("PHASE 1: RESEARCH")
    print(f"{'='*60}")
    print(f"Topic: {topic}\n")

    system_prompt = prompts.get("researcher", "You are a senior technical researcher.")
    user_msg = (
        f"Research the following topic and produce structured claims with evidence:\n\n"
        f"TOPIC: {topic}\n\n"
        f"Produce numbered claims [CLAIM-001] through [CLAIM-NNN] with evidence levels, "
        f"sources, and confidence scores. Also identify alternative approaches and known gaps."
    )

    print("  [Researcher] Investigating...")
    result = call_claude(system_prompt, user_msg, temperature=0.3)

    # Save output
    round_dir = os.path.join(workspace, "rounds", "round-0-research")
    os.makedirs(round_dir, exist_ok=True)
    with open(os.path.join(round_dir, "researcher-proposal.md"), "w") as f:
        f.write(result)

    print(f"  [Researcher] Done — saved to {round_dir}/researcher-proposal.md")
    return result


def phase_write(workspace: str, research_output: str, prompts: dict) -> str:
    """Phase 2: Writer synthesizes research into documents."""
    print(f"\n{'='*60}")
    print("PHASE 2: DOCUMENTATION")
    print(f"{'='*60}\n")

    system_prompt = prompts.get("writer", "You are a senior technical writer.")
    user_msg = (
        f"Transform the following research findings into a structured findings document "
        f"and a draft PRD. Preserve all claim IDs and evidence citations.\n\n"
        f"RESEARCH FINDINGS:\n{research_output}"
    )

    print("  [Writer] Drafting documents...")
    result = call_claude(system_prompt, user_msg, temperature=0.4)

    with open(os.path.join(workspace, "findings.md"), "w") as f:
        f.write(result)
    with open(os.path.join(workspace, "prd.md"), "w") as f:
        f.write(result)  # Writer should separate these; orchestrator can split later

    print("  [Writer] Done — saved findings.md and prd.md")
    return result


def phase_debate(
    workspace: str,
    findings: str,
    prompts: dict,
    registry: EvidenceRegistry,
    max_rounds: int = 3,
) -> str:
    """Phase 3: Adversarial debate between agents."""
    print(f"\n{'='*60}")
    print("PHASE 3: ADVERSARIAL DEBATE")
    print(f"{'='*60}\n")

    debate_log = []
    current_doc = findings

    for round_num in range(1, max_rounds + 1):
        print(f"\n--- ROUND {round_num} of {max_rounds} ---\n")
        round_dir = os.path.join(workspace, "rounds", f"round-{round_num}")
        os.makedirs(round_dir, exist_ok=True)

        # Step 1: Critic attacks
        print("  [Critic] Launching attacks...")
        critic_prompt = prompts.get("critic", "You are an adversarial critic.")
        critic_msg = (
            f"Analyze the following document and attack its claims. "
            f"Focus on the STRONGEST claims first.\n\n"
            f"DOCUMENT:\n{current_doc}"
        )
        attacks = call_claude(critic_prompt, critic_msg, temperature=0.8)
        with open(os.path.join(round_dir, "critic-attacks.md"), "w") as f:
            f.write(attacks)
        print("  [Critic] Attacks filed.")

        # Step 2: Test Engineer challenges
        print("  [Test Engineer] Designing falsification tests...")
        test_prompt = prompts.get("test_engineer", "You are a test engineer.")
        test_msg = (
            f"Review the following document AND the critic's attacks. "
            f"Design tests that would falsify each claim.\n\n"
            f"DOCUMENT:\n{current_doc}\n\n"
            f"CRITIC ATTACKS:\n{attacks}"
        )
        challenges = call_claude(test_prompt, test_msg, temperature=0.6)
        with open(os.path.join(round_dir, "test-engineer-challenges.md"), "w") as f:
            f.write(challenges)
        print("  [Test Engineer] Challenges submitted.")

        # Step 3: Researcher defends
        print("  [Researcher] Mounting defense...")
        researcher_prompt = prompts.get("researcher", "You are a technical researcher.")
        defense_msg = (
            f"Your research findings are under attack. Defend your claims, "
            f"concede where attacks are valid, and provide additional evidence "
            f"where possible.\n\n"
            f"YOUR ORIGINAL DOCUMENT:\n{current_doc}\n\n"
            f"ATTACKS:\n{attacks}\n\n"
            f"TEST CHALLENGES:\n{challenges}"
        )
        defenses = call_claude(researcher_prompt, defense_msg, temperature=0.3)
        with open(os.path.join(round_dir, "researcher-defense.md"), "w") as f:
            f.write(defenses)
        print("  [Researcher] Defense complete.")

        # Step 4: Reviewer judges
        print("  [Reviewer] Evaluating debate...")
        reviewer_prompt = prompts.get("reviewer", "You are a principal engineer reviewer.")
        review_msg = (
            f"You are judging a debate round. Evaluate each claim-attack-defense "
            f"triple and assign consensus scores.\n\n"
            f"Use this formula:\n"
            f"  consensus_score = evidence_weight × confidence × defense_strength × (1 - attack_strength)\n\n"
            f"Evidence weights: high=0.9, medium=0.6, low=0.3, none=0.1\n"
            f"Threshold for ESTABLISHED: {registry.threshold}\n\n"
            f"ORIGINAL DOCUMENT:\n{current_doc}\n\n"
            f"ATTACKS:\n{attacks}\n\n"
            f"CHALLENGES:\n{challenges}\n\n"
            f"DEFENSES:\n{defenses}\n\n"
            f"For each claim, output:\n"
            f"  CLAIM-NNN: evidence_weight=X, confidence=X, attack_strength=X, "
            f"defense_strength=X, consensus_score=X, verdict=ESTABLISHED|PROVISIONAL|REMOVED\n\n"
            f"Then produce an UPDATED version of the findings document reflecting "
            f"the debate outcomes. Remove claims that are REMOVED, add caveats to "
            f"PROVISIONAL claims, and strengthen ESTABLISHED claims."
        )
        judgment = call_claude(reviewer_prompt, review_msg, temperature=0.5)
        with open(os.path.join(round_dir, "reviewer-judgment.md"), "w") as f:
            f.write(judgment)
        print("  [Reviewer] Judgment rendered.")

        # Update the living document
        current_doc = judgment  # The reviewer's updated doc becomes input for next round

        # Log the round
        debate_log.append({
            "round": round_num,
            "attacks_file": f"rounds/round-{round_num}/critic-attacks.md",
            "challenges_file": f"rounds/round-{round_num}/test-engineer-challenges.md",
            "defenses_file": f"rounds/round-{round_num}/researcher-defense.md",
            "judgment_file": f"rounds/round-{round_num}/reviewer-judgment.md",
        })

        # Save consensus snapshot
        with open(os.path.join(round_dir, "consensus-snapshot.json"), "w") as f:
            json.dump({"round": round_num, "summary": registry.summary()}, f, indent=2)

        print(f"\n  Round {round_num} complete. {registry.summary()}")

    # Save full debate log
    debate_log_path = os.path.join(workspace, "debate-log.md")
    with open(debate_log_path, "w") as f:
        f.write(f"# Debate Log\n\n")
        f.write(f"Total rounds: {max_rounds}\n")
        f.write(f"Consensus threshold: {registry.threshold}\n\n")
        for entry in debate_log:
            f.write(f"## Round {entry['round']}\n")
            for key, val in entry.items():
                if key != "round":
                    f.write(f"- {key}: `{val}`\n")
            f.write("\n")

    # Update findings with final consensus doc
    with open(os.path.join(workspace, "findings.md"), "w") as f:
        f.write(current_doc)

    print(f"\n  Debate complete. Final document saved to findings.md")
    return current_doc


def phase_implement(workspace: str, consensus_doc: str, prompts: dict) -> str:
    """Phase 4: Implementation Architect writes code."""
    print(f"\n{'='*60}")
    print("PHASE 4: IMPLEMENTATION")
    print(f"{'='*60}\n")

    system_prompt = prompts.get("implementer", "You are a staff software engineer.")
    user_msg = (
        f"The following architecture document has been through adversarial debate "
        f"and represents evidence-weighted consensus. Implement it.\n\n"
        f"Produce:\n"
        f"1. A phased implementation plan\n"
        f"2. Production-quality code for Phase 1 (MVP)\n"
        f"3. Any NEW practical blockers you discover\n"
        f"4. A dependency manifest\n\n"
        f"CONSENSUS DOCUMENT:\n{consensus_doc}"
    )

    print("  [Implementer] Writing code...")
    result = call_claude(system_prompt, user_msg, temperature=0.3)

    with open(os.path.join(workspace, "implementation-plan.md"), "w") as f:
        f.write(result)

    print("  [Implementer] Done — saved implementation-plan.md")
    return result


def phase_synthesize(
    workspace: str,
    consensus_doc: str,
    implementation: str,
    prompts: dict,
) -> str:
    """Phase 5: Final review by all agents."""
    print(f"\n{'='*60}")
    print("PHASE 5: FINAL SYNTHESIS")
    print(f"{'='*60}\n")

    system_prompt = prompts.get("reviewer", "You are a principal engineer reviewer.")
    user_msg = (
        f"Conduct a FINAL review of the complete package:\n\n"
        f"CONSENSUS FINDINGS:\n{consensus_doc}\n\n"
        f"IMPLEMENTATION PLAN:\n{implementation}\n\n"
        f"Check:\n"
        f"1. Does the implementation faithfully represent the consensus?\n"
        f"2. Are there any remaining inconsistencies?\n"
        f"3. Produce a final executive summary\n"
        f"4. List all open items that require human decision\n"
        f"5. Generate a test plan based on the debate challenges"
    )

    print("  [Reviewer] Final synthesis...")
    result = call_claude(system_prompt, user_msg, temperature=0.5)

    with open(os.path.join(workspace, "final-review.md"), "w") as f:
        f.write(result)

    # Also produce test plan from Test Engineer
    test_prompt = prompts.get("test_engineer", "You are a test engineer.")
    test_msg = (
        f"Based on the following consensus document and implementation plan, "
        f"produce a comprehensive test plan.\n\n"
        f"CONSENSUS:\n{consensus_doc}\n\n"
        f"IMPLEMENTATION:\n{implementation}"
    )

    print("  [Test Engineer] Writing test plan...")
    test_plan = call_claude(test_prompt, test_msg, temperature=0.6)

    with open(os.path.join(workspace, "test-plan.md"), "w") as f:
        f.write(test_plan)

    print("  [Test Engineer] Done — saved test-plan.md")
    print(f"\n  Synthesis complete.")
    return result


# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

def run_pipeline(
    topic: str,
    workspace: str,
    skill_dir: str,
    max_rounds: int = 3,
    consensus_threshold: float = 0.7,
    phase: str = "all",
):
    """Run the full or partial agent team pipeline."""
    os.makedirs(workspace, exist_ok=True)

    # Load agent prompts
    prompts = load_agent_prompts(skill_dir)

    # Initialize evidence registry
    registry = EvidenceRegistry(workspace, threshold=consensus_threshold)
    registry.metadata["topic"] = topic

    print(f"\n{'#'*60}")
    print(f"  AGENT TEAM ORCHESTRATOR")
    print(f"  Topic: {topic}")
    print(f"  Workspace: {workspace}")
    print(f"  Max debate rounds: {max_rounds}")
    print(f"  Consensus threshold: {consensus_threshold}")
    print(f"  Phase: {phase}")
    print(f"{'#'*60}")

    research_output = ""
    written_doc = ""
    consensus_doc = ""
    implementation = ""

    if phase in ("all", "research"):
        research_output = phase_research(topic, workspace, prompts)
        if phase == "research":
            registry.save()
            return

    if phase in ("all", "write"):
        if not research_output:
            # Load from previous phase
            rpath = os.path.join(workspace, "rounds", "round-0-research", "researcher-proposal.md")
            if os.path.exists(rpath):
                with open(rpath) as f:
                    research_output = f.read()
        written_doc = phase_write(workspace, research_output, prompts)
        if phase == "write":
            registry.save()
            return

    if phase in ("all", "debate"):
        if not written_doc:
            fpath = os.path.join(workspace, "findings.md")
            if os.path.exists(fpath):
                with open(fpath) as f:
                    written_doc = f.read()
        consensus_doc = phase_debate(
            workspace, written_doc, prompts, registry, max_rounds
        )
        if phase == "debate":
            registry.save()
            return

    if phase in ("all", "implement"):
        if not consensus_doc:
            fpath = os.path.join(workspace, "findings.md")
            if os.path.exists(fpath):
                with open(fpath) as f:
                    consensus_doc = f.read()
        implementation = phase_implement(workspace, consensus_doc, prompts)
        if phase == "implement":
            registry.save()
            return

    if phase in ("all", "synthesize"):
        if not consensus_doc:
            fpath = os.path.join(workspace, "findings.md")
            if os.path.exists(fpath):
                with open(fpath) as f:
                    consensus_doc = f.read()
        if not implementation:
            ipath = os.path.join(workspace, "implementation-plan.md")
            if os.path.exists(ipath):
                with open(ipath) as f:
                    implementation = f.read()
        phase_synthesize(workspace, consensus_doc, implementation, prompts)

    registry.save()

    print(f"\n{'#'*60}")
    print(f"  PIPELINE COMPLETE")
    print(f"  {registry.summary()}")
    print(f"  Outputs in: {workspace}/")
    print(f"{'#'*60}\n")

    # List final outputs
    print("Final deliverables:")
    for fname in [
        "findings.md", "prd.md", "implementation-plan.md",
        "test-plan.md", "debate-log.md", "evidence-registry.json",
        "final-review.md",
    ]:
        fpath = os.path.join(workspace, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"  ✓ {fname} ({size:,} bytes)")
        else:
            print(f"  ✗ {fname} (not generated)")


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Agent Team Orchestrator — Adversarial Research Pipeline"
    )
    parser.add_argument(
        "--phase",
        choices=["all", "research", "write", "debate", "implement", "synthesize"],
        default="all",
        help="Which phase to run (default: all)",
    )
    parser.add_argument(
        "--topic",
        type=str,
        required=True,
        help="The research question or architecture challenge",
    )
    parser.add_argument(
        "--workspace",
        type=str,
        default="./agent-team-workspace",
        help="Directory for outputs (default: ./agent-team-workspace)",
    )
    parser.add_argument(
        "--skill-dir",
        type=str,
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Path to the agent-team skill directory",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=3,
        help="Maximum debate rounds (default: 3)",
    )
    parser.add_argument(
        "--consensus-threshold",
        type=float,
        default=0.7,
        help="Consensus score threshold for ESTABLISHED (default: 0.7)",
    )

    args = parser.parse_args()

    run_pipeline(
        topic=args.topic,
        workspace=args.workspace,
        skill_dir=args.skill_dir,
        max_rounds=args.max_rounds,
        consensus_threshold=args.consensus_threshold,
        phase=args.phase,
    )


if __name__ == "__main__":
    main()
