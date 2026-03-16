"""
CMS E/M Documentation Quality Rules Engine

Evaluates clinical notes against CMS Evaluation and Management (E/M) documentation
requirements based on the 2021+ guidelines (medical decision making or time-based).

Scoring categories:
1. History (HPI elements, ROS, PFSH)
2. Examination (body systems, organ systems examined)
3. Medical Decision Making (diagnoses, data, risk)
4. Coding Accuracy (ICD-10/CPT appropriateness)
"""

import re
from dataclasses import dataclass, field


@dataclass
class RuleFinding:
    category: str
    element: str
    status: str  # "present", "missing", "insufficient"
    detail: str = ""
    suggestion: str = ""
    weight: float = 1.0  # Scoring weight


@dataclass
class CategoryScore:
    score: float
    max_score: float
    items_found: list = field(default_factory=list)
    items_missing: list = field(default_factory=list)


class CMSRulesEngine:
    """Evaluates clinical notes against CMS E/M documentation requirements."""

    VERSION = "1.0.0"

    # HPI elements per CMS guidelines
    HPI_ELEMENTS = [
        ("location", ["location", "site", "area", "region"]),
        ("quality", ["quality", "sharp", "dull", "aching", "burning", "throbbing"]),
        ("severity", ["severity", "scale", "mild", "moderate", "severe", "/10"]),
        ("duration", ["duration", "days", "weeks", "months", "years", "since", "onset"]),
        ("timing", ["timing", "constant", "intermittent", "frequent", "occasional"]),
        ("context", ["context", "after", "when", "during", "triggered"]),
        ("modifying_factors", ["better", "worse", "relieved", "aggravated", "alleviating"]),
        ("associated_signs", ["associated", "accompanied", "also", "with", "without"]),
    ]

    # Review of Systems categories
    ROS_SYSTEMS = [
        "constitutional", "heent", "cardiovascular", "respiratory",
        "gastrointestinal", "genitourinary", "musculoskeletal",
        "integumentary", "neurological", "psychiatric", "endocrine",
        "hematologic", "allergic",
    ]

    # Physical exam body areas
    EXAM_SYSTEMS = [
        ("vitals", ["bp", "blood pressure", "heart rate", "pulse", "temperature",
                     "respiratory rate", "spo2", "oxygen", "weight", "bmi"]),
        ("heent", ["head", "eyes", "ears", "nose", "throat", "pupils", "conjunctiva"]),
        ("neck", ["neck", "thyroid", "lymph", "jugular"]),
        ("cardiovascular", ["heart", "cardiac", "murmur", "rhythm", "s1", "s2"]),
        ("respiratory", ["lungs", "breath sounds", "wheezing", "rales", "rhonchi"]),
        ("abdomen", ["abdomen", "bowel sounds", "tender", "distension", "hepatomegaly"]),
        ("musculoskeletal", ["extremities", "range of motion", "joint", "muscle", "gait"]),
        ("neurological", ["cranial nerves", "motor", "sensory", "reflexes", "coordination"]),
        ("skin", ["skin", "rash", "lesion", "wound", "erythema"]),
        ("psychiatric", ["mood", "affect", "orientation", "judgment", "insight"]),
    ]

    def score_note(self, subjective: str, objective: str, assessment: str, plan: str,
                   icd10_codes: list = None, cpt_codes: list = None) -> dict:
        """Score a clinical note and return detailed results."""
        icd10_codes = icd10_codes or []
        cpt_codes = cpt_codes or []

        findings = []

        # Score each category
        history_score = self._score_history(subjective, findings)
        exam_score = self._score_examination(objective, findings)
        mdm_score = self._score_medical_decision_making(assessment, plan, icd10_codes, findings)
        coding_score = self._score_coding(icd10_codes, cpt_codes, assessment, findings)

        # Calculate overall score
        category_scores = {
            "history": {
                "score": history_score.score,
                "max_score": history_score.max_score,
                "items_found": history_score.items_found,
                "items_missing": history_score.items_missing,
            },
            "examination": {
                "score": exam_score.score,
                "max_score": exam_score.max_score,
                "items_found": exam_score.items_found,
                "items_missing": exam_score.items_missing,
            },
            "medical_decision_making": {
                "score": mdm_score.score,
                "max_score": mdm_score.max_score,
                "items_found": mdm_score.items_found,
                "items_missing": mdm_score.items_missing,
            },
            "coding_accuracy": {
                "score": coding_score.score,
                "max_score": coding_score.max_score,
                "items_found": coding_score.items_found,
                "items_missing": coding_score.items_missing,
            },
        }

        total_score = sum(cs["score"] for cs in category_scores.values())
        total_max = sum(cs["max_score"] for cs in category_scores.values())
        overall_pct = round((total_score / total_max * 100) if total_max > 0 else 0, 1)

        # Determine score level
        if overall_pct >= 90:
            score_level = "excellent"
        elif overall_pct >= 75:
            score_level = "good"
        elif overall_pct >= 50:
            score_level = "fair"
        else:
            score_level = "needs_improvement"

        # Generate suggestions from findings
        suggestions = [f.suggestion for f in findings if f.status in ("missing", "insufficient") and f.suggestion]

        # Determine E/M level
        em_level = self._determine_em_level(history_score, exam_score, mdm_score)

        return {
            "overall_score": overall_pct,
            "score_level": score_level,
            "category_scores": category_scores,
            "findings": [
                {"category": f.category, "element": f.element, "status": f.status,
                 "detail": f.detail, "suggestion": f.suggestion}
                for f in findings
            ],
            "suggestions": suggestions,
            "em_level_suggested": em_level,
            "rules_version": self.VERSION,
        }

    def _score_history(self, subjective: str, findings: list) -> CategoryScore:
        text_lower = subjective.lower()
        found = []
        missing = []
        score = 0
        max_score = len(self.HPI_ELEMENTS) + 2  # +2 for ROS and PFSH

        # Check HPI elements
        for element_name, keywords in self.HPI_ELEMENTS:
            if any(kw in text_lower for kw in keywords):
                found.append(element_name)
                score += 1
                findings.append(RuleFinding("history", element_name, "present",
                                            f"HPI element '{element_name}' documented"))
            else:
                missing.append(element_name)
                findings.append(RuleFinding("history", element_name, "missing",
                                            f"HPI element '{element_name}' not found",
                                            f"Consider documenting {element_name} in HPI"))

        # Check for ROS
        ros_count = sum(1 for sys in self.ROS_SYSTEMS if sys in text_lower or sys[:4] in text_lower)
        if ros_count >= 10:
            found.append("complete_ros")
            score += 1
            findings.append(RuleFinding("history", "ROS", "present",
                                        f"Complete ROS documented ({ros_count} systems)"))
        elif ros_count >= 2:
            found.append("partial_ros")
            score += 0.5
            findings.append(RuleFinding("history", "ROS", "insufficient",
                                        f"Partial ROS ({ros_count} systems)",
                                        "Document at least 10 systems for complete ROS"))
        else:
            missing.append("ros")
            findings.append(RuleFinding("history", "ROS", "missing",
                                        "Review of Systems not documented",
                                        "Add Review of Systems to subjective section"))

        # Check for PFSH (Past/Family/Social History)
        pfsh_keywords = ["past medical", "pmh", "family history", "social history",
                         "surgical history", "medications", "allergies"]
        pfsh_count = sum(1 for kw in pfsh_keywords if kw in text_lower)
        if pfsh_count >= 3:
            found.append("pfsh")
            score += 1
            findings.append(RuleFinding("history", "PFSH", "present", "PFSH documented"))
        elif pfsh_count >= 1:
            found.append("partial_pfsh")
            score += 0.5
            findings.append(RuleFinding("history", "PFSH", "insufficient",
                                        "Partial PFSH documented",
                                        "Include past medical, family, and social history"))
        else:
            missing.append("pfsh")
            findings.append(RuleFinding("history", "PFSH", "missing",
                                        "Past/Family/Social History not documented",
                                        "Add PFSH to subjective section"))

        return CategoryScore(score, max_score, found, missing)

    def _score_examination(self, objective: str, findings: list) -> CategoryScore:
        text_lower = objective.lower()
        found = []
        missing = []
        score = 0
        max_score = len(self.EXAM_SYSTEMS)

        for system_name, keywords in self.EXAM_SYSTEMS:
            if any(kw in text_lower for kw in keywords):
                found.append(system_name)
                score += 1
                findings.append(RuleFinding("examination", system_name, "present",
                                            f"Exam system '{system_name}' documented"))
            else:
                missing.append(system_name)
                findings.append(RuleFinding("examination", system_name, "missing",
                                            f"Exam system '{system_name}' not documented",
                                            f"Consider documenting {system_name} examination"))

        return CategoryScore(score, max_score, found, missing)

    def _score_medical_decision_making(self, assessment: str, plan: str,
                                       icd10_codes: list, findings: list) -> CategoryScore:
        text_lower = (assessment + " " + plan).lower()
        found = []
        missing = []
        score = 0
        max_score = 5

        # Check for documented diagnoses
        if len(assessment.strip()) > 20:
            found.append("diagnoses_documented")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "diagnoses", "present",
                                        "Diagnoses/assessment documented"))
        else:
            missing.append("diagnoses")
            findings.append(RuleFinding("medical_decision_making", "diagnoses", "missing",
                                        "Assessment section is too brief",
                                        "Expand assessment with clinical reasoning and diagnoses"))

        # Check for differential diagnosis
        diff_keywords = ["differential", "rule out", "r/o", "consider", "versus", "vs"]
        if any(kw in text_lower for kw in diff_keywords):
            found.append("differential")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "differential", "present",
                                        "Differential diagnosis considered"))
        else:
            missing.append("differential")
            findings.append(RuleFinding("medical_decision_making", "differential", "missing",
                                        "No differential diagnosis documented",
                                        "Include differential diagnoses in assessment"))

        # Check for treatment plan
        plan_keywords = ["prescribe", "medication", "refer", "follow-up", "follow up",
                         "return", "lab", "test", "imaging", "treatment"]
        if any(kw in text_lower for kw in plan_keywords):
            found.append("treatment_plan")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "treatment_plan", "present",
                                        "Treatment plan documented"))
        else:
            missing.append("treatment_plan")
            findings.append(RuleFinding("medical_decision_making", "treatment_plan", "missing",
                                        "Treatment plan not clearly documented",
                                        "Document specific treatment plan, medications, or referrals"))

        # Check for risk assessment
        risk_keywords = ["risk", "prognosis", "monitoring", "precaution", "emergency",
                         "hospitalization", "complication"]
        if any(kw in text_lower for kw in risk_keywords):
            found.append("risk_assessment")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "risk_assessment", "present",
                                        "Risk level documented"))
        else:
            missing.append("risk_assessment")
            findings.append(RuleFinding("medical_decision_making", "risk_assessment", "missing",
                                        "Risk assessment not documented",
                                        "Consider documenting risk level and management considerations"))

        # Check ICD-10 codes
        if len(icd10_codes) > 0:
            found.append("icd10_codes")
            score += 1
            findings.append(RuleFinding("medical_decision_making", "icd10_codes", "present",
                                        f"{len(icd10_codes)} ICD-10 code(s) documented"))
        else:
            missing.append("icd10_codes")
            findings.append(RuleFinding("medical_decision_making", "icd10_codes", "missing",
                                        "No ICD-10 codes documented",
                                        "Add appropriate ICD-10 codes for diagnoses"))

        return CategoryScore(score, max_score, found, missing)

    def _score_coding(self, icd10_codes: list, cpt_codes: list,
                      assessment: str, findings: list) -> CategoryScore:
        found = []
        missing = []
        score = 0
        max_score = 3

        # ICD-10 format validation
        icd10_pattern = re.compile(r'^[A-Z]\d{2}(\.\d{1,4})?$')
        if icd10_codes:
            valid_codes = [c for c in icd10_codes if icd10_pattern.match(c)]
            if len(valid_codes) == len(icd10_codes):
                found.append("icd10_format_valid")
                score += 1
                findings.append(RuleFinding("coding_accuracy", "icd10_format", "present",
                                            "ICD-10 codes are properly formatted"))
            else:
                found.append("icd10_partial_valid")
                score += 0.5
                findings.append(RuleFinding("coding_accuracy", "icd10_format", "insufficient",
                                            f"{len(valid_codes)}/{len(icd10_codes)} ICD-10 codes valid",
                                            "Review ICD-10 code formatting (e.g., R51.9)"))
        else:
            missing.append("icd10_codes")
            findings.append(RuleFinding("coding_accuracy", "icd10_codes", "missing",
                                        "No ICD-10 codes", "Add ICD-10 codes for documented diagnoses"))

        # CPT code presence
        if cpt_codes:
            found.append("cpt_codes")
            score += 1
            findings.append(RuleFinding("coding_accuracy", "cpt_codes", "present",
                                        f"{len(cpt_codes)} CPT code(s) documented"))
        else:
            missing.append("cpt_codes")
            findings.append(RuleFinding("coding_accuracy", "cpt_codes", "missing",
                                        "No CPT codes documented",
                                        "Add appropriate CPT/E&M codes"))

        # Code-assessment alignment (basic check)
        if icd10_codes and len(assessment.strip()) > 10:
            found.append("code_alignment")
            score += 1
            findings.append(RuleFinding("coding_accuracy", "code_alignment", "present",
                                        "Codes appear aligned with assessment"))
        elif icd10_codes:
            missing.append("code_alignment")
            findings.append(RuleFinding("coding_accuracy", "code_alignment", "insufficient",
                                        "Assessment may not fully support codes",
                                        "Ensure documented assessment supports all coded diagnoses"))

        return CategoryScore(score, max_score, found, missing)

    def _determine_em_level(self, history: CategoryScore, exam: CategoryScore,
                            mdm: CategoryScore) -> str:
        """Determine suggested E/M level based on MDM complexity (2021+ guidelines)."""
        mdm_pct = (mdm.score / mdm.max_score * 100) if mdm.max_score > 0 else 0

        if mdm_pct >= 80:
            return "99215"  # High complexity
        elif mdm_pct >= 60:
            return "99214"  # Moderate complexity
        elif mdm_pct >= 40:
            return "99213"  # Low complexity
        elif mdm_pct >= 20:
            return "99212"  # Straightforward
        else:
            return "99211"  # Minimal
