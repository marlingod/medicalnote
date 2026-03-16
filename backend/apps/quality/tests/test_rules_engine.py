from django.test import TestCase
from apps.quality.rules_engine import CMSRulesEngine


class CMSRulesEngineTest(TestCase):
    def setUp(self):
        self.engine = CMSRulesEngine()

    def test_score_note_with_complete_soap(self):
        """A well-documented note should score >= 80%."""
        subjective = (
            "Patient presents with headache in the temporal region (location), "
            "described as throbbing (quality), moderate severity (7/10 on pain scale), "
            "with duration of 3 days since onset. The pain is constant (timing), "
            "triggered during stress (context). Ibuprofen makes it better (modifying factors), "
            "with associated nausea and photophobia. "
            "Review of Systems: Constitutional - negative for fever. HEENT - positive for headache. "
            "Cardiovascular - negative. Respiratory - negative. Gastrointestinal - nausea present. "
            "Genitourinary - negative. Musculoskeletal - negative. Integumentary - negative. "
            "Neurological - photophobia noted. Psychiatric - reports stress. Endocrine - negative. "
            "Hematologic - negative. Allergic - negative. "
            "Past medical history: hypertension. Family history: mother with migraines. "
            "Social history: works as accountant, no tobacco, occasional alcohol. "
            "Medications: lisinopril 10mg daily. Allergies: NKDA."
        )
        objective = (
            "Vital signs: BP 130/82, heart rate 78, temperature 98.6, respiratory rate 16, SpO2 99%, weight 175 lbs. "
            "Head: normocephalic, atraumatic. Eyes: pupils equal, reactive. "
            "Neck: supple, no lymphadenopathy. "
            "Heart: regular rate and rhythm, no murmur. S1/S2 normal. "
            "Lungs: clear to auscultation, normal breath sounds. "
            "Abdomen: soft, non-tender, normal bowel sounds. "
            "Extremities: no edema, full range of motion. "
            "Neurological: cranial nerves intact, normal motor and sensory exam, reflexes 2+. "
            "Skin: no rash or lesion noted. "
            "Psychiatric: mood anxious, affect congruent, oriented x3."
        )
        assessment = (
            "1. Tension-type headache, likely stress-related. "
            "Consider migraine as differential diagnosis. Rule out secondary causes. "
            "Patient has risk factors including family history."
        )
        plan = (
            "1. Prescribe sumatriptan 50mg PRN for acute episodes. "
            "2. Continue ibuprofen 400mg as needed. "
            "3. Refer to neurology if no improvement in 2 weeks. "
            "4. Lab work: CBC, BMP to rule out metabolic causes. "
            "5. Follow-up in 2 weeks. "
            "6. Return precautions: emergency if worst headache of life."
        )

        result = self.engine.score_note(
            subjective=subjective,
            objective=objective,
            assessment=assessment,
            plan=plan,
            icd10_codes=["R51.9", "G43.909"],
            cpt_codes=["99214"],
        )

        assert result["overall_score"] >= 80
        assert result["score_level"] in ("excellent", "good")
        assert result["em_level_suggested"] in ("99214", "99215")
        assert result["rules_version"] == "1.0.0"

    def test_score_note_with_minimal_content(self):
        """A minimal note should score < 50%."""
        result = self.engine.score_note(
            subjective="Headache.",
            objective="Looks okay.",
            assessment="Headache.",
            plan="Tylenol.",
        )
        assert result["overall_score"] < 50
        assert result["score_level"] == "needs_improvement"
        assert len(result["suggestions"]) > 0

    def test_hpi_elements_detection(self):
        subjective = "Pain in the left shoulder (location), sharp quality, severe 8/10, for 2 weeks duration."
        result = self.engine.score_note(
            subjective=subjective, objective="", assessment="", plan=""
        )
        history = result["category_scores"]["history"]
        assert "location" in history["items_found"]
        assert "quality" in history["items_found"]
        assert "severity" in history["items_found"]
        assert "duration" in history["items_found"]

    def test_ros_detection(self):
        subjective = (
            "Constitutional: no fever. HEENT: no vision changes. Cardiovascular: no chest pain. "
            "Respiratory: no SOB. Gastrointestinal: no nausea. Genitourinary: normal. "
            "Musculoskeletal: no joint pain. Integumentary: no rash. Neurological: no numbness. "
            "Psychiatric: no depression. Endocrine: no polydipsia. "
            "Hematologic: no bruising. Allergic: NKDA."
        )
        result = self.engine.score_note(
            subjective=subjective, objective="", assessment="", plan=""
        )
        history = result["category_scores"]["history"]
        assert "complete_ros" in history["items_found"]

    def test_exam_systems_detection(self):
        objective = (
            "BP 120/80, heart rate 72. Head normocephalic. Eyes PERRLA. "
            "Neck supple. Heart regular rhythm. Lungs clear breath sounds. "
            "Abdomen soft non-tender. Extremities full range of motion. "
            "Cranial nerves intact. Skin clear."
        )
        result = self.engine.score_note(
            subjective="", objective=objective, assessment="", plan=""
        )
        exam = result["category_scores"]["examination"]
        assert len(exam["items_found"]) >= 7

    def test_mdm_scoring(self):
        assessment = (
            "Differential diagnosis includes tension headache versus migraine. "
            "Consider rule out intracranial pathology given risk factors."
        )
        plan = (
            "Prescribe medication for headache. Refer to neurology. "
            "Follow-up in 2 weeks. Lab testing ordered. "
            "Risk of progression is low with current management."
        )
        result = self.engine.score_note(
            subjective="", objective="", assessment=assessment, plan=plan,
            icd10_codes=["R51.9"],
        )
        mdm = result["category_scores"]["medical_decision_making"]
        assert "diagnoses_documented" in mdm["items_found"]
        assert "differential" in mdm["items_found"]
        assert "treatment_plan" in mdm["items_found"]
        assert "risk_assessment" in mdm["items_found"]
        assert "icd10_codes" in mdm["items_found"]

    def test_coding_accuracy_scoring(self):
        result = self.engine.score_note(
            subjective="", objective="",
            assessment="Tension headache with clinical evidence",
            plan="",
            icd10_codes=["R51.9"],
            cpt_codes=["99214"],
        )
        coding = result["category_scores"]["coding_accuracy"]
        assert "icd10_format_valid" in coding["items_found"]
        assert "cpt_codes" in coding["items_found"]
        assert "code_alignment" in coding["items_found"]

    def test_coding_accuracy_invalid_icd10(self):
        result = self.engine.score_note(
            subjective="", objective="",
            assessment="Assessment documented here",
            plan="",
            icd10_codes=["R51.9", "INVALID"],
        )
        coding = result["category_scores"]["coding_accuracy"]
        assert "icd10_partial_valid" in coding["items_found"]

    def test_em_level_determination(self):
        # High MDM -> 99215
        result = self.engine.score_note(
            subjective="", objective="",
            assessment="Detailed assessment with differential diagnosis and rule out considerations",
            plan="Prescribe medication. Follow-up in 1 week. Risk assessment low.",
            icd10_codes=["R51.9"],
        )
        assert result["em_level_suggested"] in ("99214", "99215")

    def test_suggestions_generated_for_missing_elements(self):
        result = self.engine.score_note(
            subjective="Headache.",
            objective="Normal exam.",
            assessment="Headache.",
            plan="Tylenol.",
        )
        assert len(result["suggestions"]) > 0
        # Should suggest adding missing elements
        suggestion_text = " ".join(result["suggestions"]).lower()
        assert "ros" in suggestion_text or "review" in suggestion_text or "hpi" in suggestion_text
