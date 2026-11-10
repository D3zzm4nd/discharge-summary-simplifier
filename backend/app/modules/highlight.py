"""FR-10: flag critical self-care and medication instructions for visual highlighting."""
import re

PATTERNS = [re.compile(p, re.I) for p in [
    r"\b(take|taking|use|apply|inject)\b.*\b(daily|times|morning|night|evening|hours?|days?|weeks?|every|before|after|with)\b",
    r"\b(do not|don't|never|avoid|stop|must|should not)\b",
    r"\b(return|come back|go to|call|seek)\b.*\b(hospital|emergency|clinic|doctor|immediately|urgent|help)\b",
    r"\b(follow[- ]?up|appointment|review)\b",
    r"\b\d+(?:\.\d+)?\s?(mg|mcg|g|ml|iu|units?|tablets?|capsules?|drops?)\b",
    r"\b(finish|complete)\b.*\b(course|medicine|antibiotic|tablets)\b",
    r"\b(fever|bleeding|chest pain|difficulty breathing|severe|emergency|warning)\b"]]

class CriticalInstructionDetector:
    @staticmethod
    def is_critical(sentence): return any(p.search(sentence) for p in PATTERNS)
