import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

# Default rules definitions
DEFAULT_RULES = [
    {
        "rule_code": "COMP_SUBJ",
        "name": "Subjective section present",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_OBJ",
        "name": "Objective section present",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_ASSESS",
        "name": "Assessment section present",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_PLAN",
        "name": "Plan section present",
        "category": "completeness",
        "severity": "error",
        "points": 15,
    },
    {
        "rule_code": "COMP_HPI",
        "name": "HPI elements documented",
        "category": "completeness",
        "severity": "warning",
        "points": 10,
        "description": "HPI should include location, quality, severity, timing, context, modifying factors, and associated signs/symptoms",
    },
    {
        "rule_code": "COMP_ROS",
        "name": "Review of Systems documented",
        "category": "completeness",
        "severity": "warning",
        "points": 5,
    },
    {
        "rule_code": "BILL_ICD10",
        "name": "ICD-10 codes present",
        "category": "billing",
        "severity": "warning",
        "points": 10,
    },
    {
        "rule_code": "BILL_CPT",
        "name": "CPT codes present",
        "category": "billing",
        "severity": "warning",
        "points": 5,
    },
    {
        "rule_code": "BILL_EM_MATCH",
        "name": "E/M level matches documentation",
        "category": "billing",
        "severity": "info",
        "points": 5,
    },
    {
        "rule_code": "CMS_MDM",
        "name": "Medical Decision Making documented",
        "category": "compliance",
        "severity": "warning",
        "points": 10,
    },
]

# HPI elements keywords
HPI_KEYWORDS = {
    "location": ["location", "where", "area", "site", "region"],
    "quality": ["quality", "sharp", "dull", "burning", "aching", "throbbing"],
    "severity": ["severity", "scale", "rate", "mild", "moderate", "severe", "10"],
    "timing": ["timing", "onset", "duration", "started", "began", "ago", "since"],
    "context": ["context", "after", "when", "during", "while", "activity"],
    "modifying": ["better", "worse", "improves", "worsens", "relieves", "aggravates"],
    "associated": ["associated", "also", "along with", "accompanied", "nausea", "vomiting"],
}

# ROS system keywords
ROS_SYSTEMS = [
    "constitutional", "eyes", "ent", "cardiovascular", "respiratory",
    "gi", "gastrointestinal", "gu", "genitourinary", "musculoskeletal",
    "skin", "neurological", "psychiatric", "endocrine", "hematologic",
    "allergic", "immunologic",
]


class QualityRulesEngine:
    """Rules engine for evaluating clinical note quality."""

    def evaluate_note(self, note) -> dict[str, Any]:
        """Evaluate a clinical note against all quality rules."""
        findings = []
        total_points = 0
        deducted_points = 0
        completeness_total = 0
        completeness_deducted = 0
        billing_total = 0
        billing_deducted = 0
        compliance_total = 0
        compliance_deducted = 0

        for rule_def in DEFAULT_RULES:
            rule_code = rule_def["rule_code"]
            points = rule_def["points"]
            category = rule_def["category"]

            total_points += points
            if category == "completeness":
                completeness_total += points
            elif category == "billing":
                billing_total += points
            elif category == "compliance":
                compliance_total += points

            passed, message = self._evaluate_rule(rule_code, note)
            findings.append({
                "rule_code": rule_code,
                "passed": passed,
                "message": message,
                "severity": rule_def["severity"],
                "category": category,
                "points": points,
            })

            if not passed:
                deducted_points += points
                if category == "completeness":
                    completeness_deducted += points
                elif category == "billing":
                    billing_deducted += points
                elif category == "compliance":
                    compliance_deducted += points

        overall = max(0, round(100 * (1 - deducted_points / max(total_points, 1))))
        completeness = max(0, round(100 * (1 - completeness_deducted / max(completeness_total, 1))))
        billing = max(0, round(100 * (1 - billing_deducted / max(billing_total, 1))))
        compliance = max(0, round(100 * (1 - compliance_deducted / max(compliance_total, 1))))

        suggested_em = self._suggest_em_level(note, findings)

        return {
            "overall_score": overall,
            "completeness_score": completeness,
            "billing_score": billing,
            "compliance_score": compliance,
            "suggested_em_level": suggested_em,
            "findings": findings,
        }

    def _evaluate_rule(self, rule_code: str, note) -> tuple[bool, str]:
        """Evaluate a single rule against a note."""
        if rule_code == "COMP_SUBJ":
            text = getattr(note, "subjective", "") or ""
            if len(text.strip()) < 10:
                return False, "Subjective section is missing or too brief."
            return True, "Subjective section present."

        elif rule_code == "COMP_OBJ":
            text = getattr(note, "objective", "") or ""
            if len(text.strip()) < 10:
                return False, "Objective section is missing or too brief."
            return True, "Objective section present."

        elif rule_code == "COMP_ASSESS":
            text = getattr(note, "assessment", "") or ""
            if len(text.strip()) < 5:
                return False, "Assessment section is missing or too brief."
            return True, "Assessment section present."

        elif rule_code == "COMP_PLAN":
            text = getattr(note, "plan", "") or ""
            if len(text.strip()) < 5:
                return False, "Plan section is missing or too brief."
            return True, "Plan section present."

        elif rule_code == "COMP_HPI":
            subjective = (getattr(note, "subjective", "") or "").lower()
            found = 0
            for element, keywords in HPI_KEYWORDS.items():
                if any(kw in subjective for kw in keywords):
                    found += 1
            if found < 3:
                return False, f"HPI has {found}/7 elements. Consider adding more detail."
            return True, f"HPI documents {found}/7 elements."

        elif rule_code == "COMP_ROS":
            text = (getattr(note, "subjective", "") or "").lower()
            text += " " + (getattr(note, "objective", "") or "").lower()
            systems_found = sum(1 for sys in ROS_SYSTEMS if sys in text)
            if systems_found < 2:
                return False, "Review of Systems not adequately documented."
            return True, f"ROS covers {systems_found} systems."

        elif rule_code == "BILL_ICD10":
            codes = getattr(note, "icd10_codes", []) or []
            if not codes:
                return False, "No ICD-10 codes present."
            return True, f"{len(codes)} ICD-10 code(s) present."

        elif rule_code == "BILL_CPT":
            codes = getattr(note, "cpt_codes", []) or []
            if not codes:
                return False, "No CPT codes present."
            return True, f"{len(codes)} CPT code(s) present."

        elif rule_code == "BILL_EM_MATCH":
            # Info-level: just note the current codes
            codes = getattr(note, "cpt_codes", []) or []
            em_codes = [c for c in codes if re.match(r"^992\d{2}$", c)]
            if not em_codes:
                return True, "No E/M code to validate."
            return True, f"E/M code: {em_codes[0]}"

        elif rule_code == "CMS_MDM":
            assessment = (getattr(note, "assessment", "") or "").lower()
            plan = (getattr(note, "plan", "") or "").lower()
            combined = assessment + " " + plan
            has_diagnosis = len(assessment.strip()) > 20
            has_plan = len(plan.strip()) > 20
            if not (has_diagnosis and has_plan):
                return False, "Medical decision making not adequately documented."
            return True, "MDM documented in assessment and plan."

        return True, "Rule not implemented."

    def _suggest_em_level(self, note, findings: list) -> str:
        """Suggest E/M level based on documentation completeness."""
        failed = [f for f in findings if not f["passed"]]
        error_count = sum(1 for f in failed if f["severity"] == "error")
        warning_count = sum(1 for f in failed if f["severity"] == "warning")

        if error_count >= 2:
            return "99212"
        elif error_count == 1:
            return "99213"
        elif warning_count >= 2:
            return "99213"
        elif warning_count == 1:
            return "99214"
        else:
            return "99214"
