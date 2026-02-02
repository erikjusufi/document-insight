from collections.abc import Callable, Iterable
from pathlib import Path

import fitz
from sqlalchemy.orm import Session

from app.core.settings import get_settings
from app.db.models import Document, DocumentChunk, DocumentPage
from app.db.repos.documents import DocumentRepository
from app.services.ocr_service import OCRService
from app.services.language_service import LanguageService


class ExtractionService:
    def __init__(self, repo: DocumentRepository, ocr_service: OCRService | None = None) -> None:
        self.repo = repo
        self._ocr_service = ocr_service

    def _get_ocr_service(self) -> OCRService:
        if self._ocr_service is None:
            self._ocr_service = OCRService()
        return self._ocr_service

    def extract_from_document(
        self,
        session: Session,
        document: Document,
        progress: Callable[[int, int], None] | None = None,
    ) -> tuple[int, int]:
        doc_path = Path(document.file_path)
        pages: list[DocumentPage] = []
        chunks: list[DocumentChunk] = []

        if document.content_type.startswith("image/"):
            text = self._get_ocr_service().extract_text_from_image(doc_path)
            pages.append(
                DocumentPage(
                    document_id=document.id,
                    page_number=1,
                    text=text,
                )
            )
            for chunk_index, (start, end) in enumerate(chunk_ranges(text)):
                chunks.append(
                    DocumentChunk(
                        document_id=document.id,
                        page_number=1,
                        chunk_index=chunk_index,
                        start_offset=start,
                        end_offset=end,
                    )
                )
            self.repo.replace_pages_and_chunks(session, document.id, pages, chunks)
            self._update_language_if_missing(session, document, pages)
            if progress:
                progress(1, 1)
            return len(pages), len(chunks)

        with fitz.open(doc_path) as pdf:
            total_pages = max(pdf.page_count, 1)
            for page_index in range(pdf.page_count):
                page = pdf.load_page(page_index)
                text = page.get_text("text")
                min_len = get_settings().ocr_min_text_length
                if not text or len(text.strip()) < min_len:
                    pix = page.get_pixmap()
                    image_path = doc_path.parent / f"{doc_path.stem}_page_{page_index + 1}.png"
                    pix.save(str(image_path))
                    text = self._get_ocr_service().extract_text_from_image(image_path)
                    image_path.unlink(missing_ok=True)
                pages.append(
                    DocumentPage(
                        document_id=document.id,
                        page_number=page_index + 1,
                        text=text,
                    )
                )
                for chunk_index, (start, end) in enumerate(chunk_ranges(text)):
                    chunks.append(
                        DocumentChunk(
                            document_id=document.id,
                            page_number=page_index + 1,
                            chunk_index=chunk_index,
                            start_offset=start,
                            end_offset=end,
                        )
                    )
                if progress:
                    progress(page_index + 1, total_pages)

        self.repo.replace_pages_and_chunks(session, document.id, pages, chunks)
        self._update_language_if_missing(session, document, pages)
        return len(pages), len(chunks)

    def _update_language_if_missing(
        self,
        session: Session,
        document: Document,
        pages: list[DocumentPage],
    ) -> None:
        if document.language:
            return
        combined = "\n".join(page.text for page in pages)
        language = LanguageService().detect_language(combined)
        if language:
            self.repo.update_language(session, document, language)


def chunk_ranges(text: str, size: int = 500, overlap: int = 50) -> Iterable[tuple[int, int]]:
    if size <= 0:
        return []
    if overlap >= size:
        overlap = 0
    start = 0
    text_length = len(text)
    while start < text_length:
        end = min(start + size, text_length)
        if end > start:
            yield start, end
        if end == text_length:
            break
        start = end - overlap
