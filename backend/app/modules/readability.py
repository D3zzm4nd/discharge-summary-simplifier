"""FR-11: Flesch-Kincaid Grade Level and Flesch Reading Ease."""
import textstat

class ReadabilityEvaluator:
    @staticmethod
    def score(text):
        if not text.strip(): return {"fk_grade": None, "reading_ease": None}
        return {"fk_grade": round(textstat.flesch_kincaid_grade(text), 1),
                "reading_ease": round(textstat.flesch_reading_ease(text), 1)}
