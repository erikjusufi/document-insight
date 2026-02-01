from langdetect import DetectorFactory, LangDetectException, detect

DetectorFactory.seed = 0


class LanguageService:
    def detect_language(self, text: str) -> str | None:
        cleaned = text.strip()
        if len(cleaned) < 20:
            return None
        try:
            return detect(cleaned)
        except LangDetectException:
            return None
