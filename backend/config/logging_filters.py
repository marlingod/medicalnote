import logging
import re


class PHISanitizationFilter(logging.Filter):
    """Redact potential PHI from log messages (HIPAA §164.530(c))."""

    PATTERNS = [
        (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[SSN-REDACTED]"),           # SSN
        (re.compile(r"\b\d{9}\b"), "[SSN-REDACTED]"),                         # SSN no dashes
        (re.compile(r"\b\(\d{3}\)\s*\d{3}-\d{4}\b"), "[PHONE-REDACTED]"),   # Phone (xxx) xxx-xxxx
        (re.compile(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b"), "[PHONE-REDACTED]"), # Phone xxx-xxx-xxxx
        (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[EMAIL-REDACTED]"),
        (re.compile(r"\b(?:0[1-9]|1[0-2])/(?:0[1-9]|[12]\d|3[01])/(?:19|20)\d{2}\b"), "[DOB-REDACTED]"),
    ]

    def filter(self, record):
        if isinstance(record.msg, str):
            for pattern, replacement in self.PATTERNS:
                record.msg = pattern.sub(replacement, record.msg)
        if record.args:
            sanitized = []
            for arg in record.args if isinstance(record.args, tuple) else [record.args]:
                if isinstance(arg, str):
                    for pattern, replacement in self.PATTERNS:
                        arg = pattern.sub(replacement, arg)
                sanitized.append(arg)
            record.args = tuple(sanitized) if isinstance(record.args, tuple) else sanitized[0]
        return True
