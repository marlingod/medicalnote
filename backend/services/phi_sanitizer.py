import re


class PHISanitizer:
    """Strip identifiable information before sending text to LLM providers."""

    SSN_PATTERN = re.compile(r"\b\d{3}-?\d{2}-?\d{4}\b")
    PHONE_PATTERN = re.compile(r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    DOB_PATTERN = re.compile(r"\b(?:0[1-9]|1[0-2])[/\-](?:0[1-9]|[12]\d|3[01])[/\-](?:19|20)\d{2}\b")

    @classmethod
    def sanitize_for_llm(cls, text: str, patient_name: str = "", dob: str = "") -> str:
        """Replace known PHI with placeholders. Clinical observations are preserved."""
        if not text:
            return text

        # Replace patient name if provided
        if patient_name:
            for name_part in patient_name.split():
                if len(name_part) > 1:  # Skip single characters
                    text = re.sub(re.escape(name_part), "[PATIENT]", text, flags=re.IGNORECASE)

        # Replace date of birth if provided
        if dob:
            text = text.replace(dob, "[DOB]")

        # Replace SSN
        text = cls.SSN_PATTERN.sub("[SSN]", text)
        # Replace phone numbers
        text = cls.PHONE_PATTERN.sub("[PHONE]", text)
        # Replace emails
        text = cls.EMAIL_PATTERN.sub("[EMAIL]", text)
        # Replace date patterns that look like DOBs
        text = cls.DOB_PATTERN.sub("[DOB]", text)

        return text
