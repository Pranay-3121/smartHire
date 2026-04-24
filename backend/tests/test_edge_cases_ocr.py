import pytest
from unittest.mock import patch, MagicMock
from backend.tools.ocr_fallback import is_scanned_pdf


class TestOCRFallback:
    def test_is_scanned_pdf_true_when_no_text(self):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "   "
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))
        mock_doc.__len__ = MagicMock(return_value=1)

        with patch("fitz.open", return_value=mock_doc):
            result = is_scanned_pdf("/fake/path.pdf")
        assert result is True

    def test_is_scanned_pdf_false_when_has_text(self):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a real text resume with lots of content here."
        mock_doc = MagicMock()
        mock_doc.__iter__ = MagicMock(return_value=iter([mock_page]))

        with patch("fitz.open", return_value=mock_doc):
            result = is_scanned_pdf("/fake/path.pdf")
        assert result is False

    def test_is_scanned_pdf_returns_false_on_exception(self):
        with patch("fitz.open", side_effect=Exception("file error")):
            result = is_scanned_pdf("/fake/path.pdf")
        assert result is False

    def test_extract_text_via_ocr_file_not_found(self):
        from backend.tools.ocr_fallback import extract_text_via_ocr
        with pytest.raises(FileNotFoundError):
            extract_text_via_ocr("/nonexistent/path/resume.pdf")

    def test_extract_text_via_ocr_pdf(self):
        from backend.tools.ocr_fallback import extract_text_via_ocr
        import tempfile, os

        mock_page = MagicMock()
        mock_pix = MagicMock()
        mock_pix.tobytes.return_value = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
        mock_page.get_pixmap.return_value = mock_pix
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=1)
        mock_doc.__getitem__ = MagicMock(return_value=mock_page)

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"%PDF-1.4 fake content")
            tmp_path = f.name

        try:
            with patch("fitz.open", return_value=mock_doc):
                with patch("PIL.Image.open") as mock_img_open:
                    with patch("pytesseract.image_to_string", return_value="Extracted OCR text"):
                        mock_img_open.return_value = MagicMock()
                        result = extract_text_via_ocr(tmp_path)
            assert "Extracted OCR text" in result
        finally:
            os.unlink(tmp_path)
