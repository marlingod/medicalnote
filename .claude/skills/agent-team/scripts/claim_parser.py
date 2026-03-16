#!/usr/bin/env python3
"""
Claim Parser
=============
Extracts structured claims from agent outputs.
Parses [CLAIM-NNN] blocks, [ATTACK-NNN] blocks, [TEST-NNN] blocks,
and reviewer judgments into machine-readable structures.
"""

import re
import json
from typing import Optional


def parse_claims(text: str) -> list[dict]:
    """
    Extract claims from researcher output.

    Expected format:
        [CLAIM-001] {evidence: "high"}
        Some claim text here
        [EVIDENCE] Supporting evidence
        [CONFIDENCE] 0.85
    """
    claims = []
    # Match claim blocks
    pattern = re.compile(
        r'\[CLAIM-(\d+)\]\s*\{evidence:\s*["\']?(high|medium|low|none)["\']?\}\s*'
        r'(.*?)'
        r'(?=\[CLAIM-\d+\]|\[EVIDENCE\]|$)',
        re.DOTALL | re.IGNORECASE,
    )
    evidence_pattern = re.compile(
        r'\[EVIDENCE\]\s*(.*?)(?=\[CONFIDENCE\]|\[CLAIM-\d+\]|$)',
        re.DOTALL,
    )
    confidence_pattern = re.compile(
        r'\[CONFIDENCE\]\s*([\d.]+)',
    )

    # Split by claim markers for simpler parsing
    sections = re.split(r'(?=\[CLAIM-\d+\])', text)

    for section in sections:
        claim_match = re.match(
            r'\[CLAIM-(\d+)\]\s*\{evidence:\s*["\']?(high|medium|low|none)["\']?\}\s*(.*)',
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if not claim_match:
            continue

        claim_id = f"CLAIM-{claim_match.group(1).zfill(3)}"
        evidence_level = claim_match.group(2).lower()
        remaining = claim_match.group(3)

        # Extract claim text (before [EVIDENCE])
        text_match = re.match(r'(.*?)(?=\[EVIDENCE\]|\[CONFIDENCE\]|$)', remaining, re.DOTALL)
        claim_text = text_match.group(1).strip() if text_match else remaining.strip()

        # Extract evidence
        ev_match = evidence_pattern.search(remaining)
        evidence_text = ev_match.group(1).strip() if ev_match else ""

        # Extract confidence
        conf_match = confidence_pattern.search(remaining)
        confidence = float(conf_match.group(1)) if conf_match else 0.5

        claims.append({
            "id": claim_id,
            "text": claim_text,
            "evidence_level": evidence_level,
            "evidence_text": evidence_text,
            "confidence": min(max(confidence, 0.0), 1.0),
        })

    return claims


def parse_attacks(text: str) -> list[dict]:
    """
    Extract attacks from critic output.

    Expected format:
        [ATTACK-001] Targets: [CLAIM-003]
          Type: LOGICAL_CONTRADICTION
          Attack: ...
          Evidence: ...
          Confidence: 0.7
          Constructive Alternative: ...
    """
    attacks = []
    sections = re.split(r'(?=\[ATTACK-\d+\])', text)

    for section in sections:
        attack_match = re.match(
            r'\[ATTACK-(\d+)\]\s*(?:Targets?:\s*\[?(CLAIM-\d+)\]?)?\s*(.*)',
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if not attack_match:
            continue

        attack_id = f"ATTACK-{attack_match.group(1).zfill(3)}"
        target = attack_match.group(2) or "UNKNOWN"
        remaining = attack_match.group(3)

        # Extract fields
        attack_type = _extract_field(remaining, "Type")
        attack_text = _extract_field(remaining, "Attack")
        evidence = _extract_field(remaining, "Evidence")
        confidence = _extract_float(remaining, "Confidence", 0.5)
        alternative = _extract_field(remaining, "Constructive Alternative")

        attacks.append({
            "id": attack_id,
            "targets": target,
            "type": attack_type,
            "text": attack_text,
            "evidence": evidence,
            "confidence": confidence,
            "constructive_alternative": alternative,
        })

    return attacks


def parse_tests(text: str) -> list[dict]:
    """
    Extract test challenges from test engineer output.

    Expected format:
        [TEST-001] Falsifies: [CLAIM-003]
          GIVEN: ...
          WHEN: ...
          THEN: ...
          FALSIFIED IF: ...
          EFFORT: ...
          PRIORITY: P0
    """
    tests = []
    sections = re.split(r'(?=\[TEST-\d+\])', text)

    for section in sections:
        test_match = re.match(
            r'\[TEST-(\d+)\]\s*(?:Falsifies?:\s*\[?(CLAIM-\d+)\]?)?\s*(.*)',
            section,
            re.DOTALL | re.IGNORECASE,
        )
        if not test_match:
            continue

        test_id = f"TEST-{test_match.group(1).zfill(3)}"
        target = test_match.group(2) or "UNKNOWN"
        remaining = test_match.group(3)

        tests.append({
            "id": test_id,
            "targets": target,
            "given": _extract_field(remaining, "GIVEN"),
            "when": _extract_field(remaining, "WHEN"),
            "then": _extract_field(remaining, "THEN"),
            "falsified_if": _extract_field(remaining, "FALSIFIED IF"),
            "effort": _extract_field(remaining, "EFFORT"),
            "priority": _extract_field(remaining, "PRIORITY"),
        })

    return tests


def parse_judgments(text: str) -> list[dict]:
    """
    Extract reviewer judgments.

    Expected format:
        CLAIM-001: evidence_weight=0.9, confidence=0.85, attack_strength=0.6,
        defense_strength=0.8, consensus_score=0.245, verdict=PROVISIONAL
    """
    judgments = []
    pattern = re.compile(
        r'(CLAIM-\d+):\s*'
        r'evidence_weight=([\d.]+).*?'
        r'confidence=([\d.]+).*?'
        r'attack_strength=([\d.]+).*?'
        r'defense_strength=([\d.]+).*?'
        r'consensus_score=([\d.]+).*?'
        r'verdict=(\w+)',
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        judgments.append({
            "claim_id": match.group(1),
            "evidence_weight": float(match.group(2)),
            "confidence": float(match.group(3)),
            "attack_strength": float(match.group(4)),
            "defense_strength": float(match.group(5)),
            "consensus_score": float(match.group(6)),
            "verdict": match.group(7).upper(),
        })
    return judgments


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_field(text: str, field_name: str) -> str:
    """Extract a labeled field from text."""
    pattern = re.compile(
        rf'{field_name}\s*:\s*(.*?)(?=\n\s*\w+\s*:|$)',
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _extract_float(text: str, field_name: str, default: float = 0.5) -> float:
    """Extract a float-valued labeled field."""
    pattern = re.compile(rf'{field_name}\s*:\s*([\d.]+)', re.IGNORECASE)
    match = pattern.search(text)
    if match:
        try:
            return min(max(float(match.group(1)), 0.0), 1.0)
        except ValueError:
            return default
    return default


# ---------------------------------------------------------------------------
# CLI: quick test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python claim_parser.py <file.md> [claims|attacks|tests|judgments]")
        sys.exit(1)

    filepath = sys.argv[1]
    parse_type = sys.argv[2] if len(sys.argv) > 2 else "claims"

    with open(filepath) as f:
        content = f.read()

    parsers = {
        "claims": parse_claims,
        "attacks": parse_attacks,
        "tests": parse_tests,
        "judgments": parse_judgments,
    }

    parser = parsers.get(parse_type, parse_claims)
    results = parser(content)
    print(json.dumps(results, indent=2))
