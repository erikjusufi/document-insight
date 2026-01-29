from pathlib import Path

import easyocr

from app.core.settings import get_settings


class OCRService:
    def __init__(self) -> None:
        settings = get_settings()
        self.reader = easyocr.Reader(settings.ocr_languages, gpu=False)

    def extract_text_from_image(self, image_path: Path) -> str:
        results = self.reader.readtext(str(image_path))
        return " ".join(result[1] for result in results)
