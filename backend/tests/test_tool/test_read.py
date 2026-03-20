"""Read tool tests."""

import asyncio
from pathlib import Path

import pytest

from app.schemas.agent import AgentInfo
from app.tool.builtin.read import ReadTool
from app.tool.context import ToolContext


def _make_ctx() -> ToolContext:
    return ToolContext(
        session_id="test-session",
        message_id="test-msg",
        agent=AgentInfo(name="test", description="", mode="primary"),
        call_id="test-call",
    )


class TestReadTool:
    @pytest.fixture
    def tool(self):
        return ReadTool()

    @pytest.mark.asyncio
    async def test_read_file(self, tool: ReadTool, tmp_path: Path):
        f = tmp_path / "hello.txt"
        f.write_text("line1\nline2\nline3\n")

        result = await tool.execute({"file_path": str(f)}, _make_ctx())
        assert result.success
        assert "line1" in result.output
        assert "line2" in result.output
        assert "line3" in result.output

    @pytest.mark.asyncio
    async def test_read_with_offset_limit(self, tool: ReadTool, tmp_path: Path):
        f = tmp_path / "lines.txt"
        f.write_text("\n".join(f"line{i}" for i in range(1, 11)))

        result = await tool.execute({"file_path": str(f), "offset": 3, "limit": 2}, _make_ctx())
        assert result.success
        assert "line3" in result.output
        assert "line4" in result.output
        assert "line1" not in result.output

    @pytest.mark.asyncio
    async def test_read_nonexistent(self, tool: ReadTool):
        result = await tool.execute({"file_path": "/nonexistent/file.txt"}, _make_ctx())
        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_read_directory(self, tool: ReadTool, tmp_path: Path):
        (tmp_path / "a.txt").touch()
        (tmp_path / "b.txt").touch()

        result = await tool.execute({"file_path": str(tmp_path)}, _make_ctx())
        assert result.success
        assert "a.txt" in result.output
        assert "b.txt" in result.output

    @pytest.mark.asyncio
    async def test_line_numbers_format(self, tool: ReadTool, tmp_path: Path):
        f = tmp_path / "num.txt"
        f.write_text("hello\nworld\n")

        result = await tool.execute({"file_path": str(f)}, _make_ctx())
        assert result.success
        # Should have line number prefixes
        assert "\t" in result.output  # tab separator between number and content


class TestReadOfficeFormats:
    """Test reading binary office document formats via ReadTool."""

    @pytest.fixture
    def tool(self):
        return ReadTool()

    @pytest.mark.asyncio
    async def test_read_pdf(self, tool: ReadTool, tmp_path: Path):
        pytest.importorskip("pypdf")
        rc = pytest.importorskip("reportlab.pdfgen.canvas")

        pdf_path = tmp_path / "test.pdf"
        c = rc.Canvas(str(pdf_path))
        c.drawString(72, 700, "Hello PDF")
        c.save()

        result = await tool.execute({"file_path": str(pdf_path)}, _make_ctx())
        assert result.success
        assert "Hello PDF" in result.output

    @pytest.mark.asyncio
    async def test_read_docx(self, tool: ReadTool, tmp_path: Path):
        docx_mod = pytest.importorskip("docx")

        docx_path = tmp_path / "test.docx"
        doc = docx_mod.Document()
        doc.add_paragraph("Hello DOCX")
        doc.save(str(docx_path))

        result = await tool.execute({"file_path": str(docx_path)}, _make_ctx())
        assert result.success
        assert "Hello DOCX" in result.output

    @pytest.mark.asyncio
    async def test_read_xlsx(self, tool: ReadTool, tmp_path: Path):
        openpyxl = pytest.importorskip("openpyxl")

        xlsx_path = tmp_path / "test.xlsx"
        wb = openpyxl.Workbook()
        ws = wb.active
        ws["A1"] = "Hello XLSX"
        wb.save(str(xlsx_path))

        result = await tool.execute({"file_path": str(xlsx_path)}, _make_ctx())
        assert result.success
        assert "Hello XLSX" in result.output

    @pytest.mark.asyncio
    async def test_read_pptx(self, tool: ReadTool, tmp_path: Path):
        pptx_mod = pytest.importorskip("pptx")

        pptx_path = tmp_path / "test.pptx"
        prs = pptx_mod.Presentation()
        slide = prs.slides.add_slide(prs.slide_layouts[0])
        slide.shapes.title.text = "Hello PPTX"
        prs.save(str(pptx_path))

        result = await tool.execute({"file_path": str(pptx_path)}, _make_ctx())
        assert result.success
        assert "Hello PPTX" in result.output

    @pytest.mark.asyncio
    async def test_read_pdf_with_offset_limit(self, tool: ReadTool, tmp_path: Path):
        pytest.importorskip("pypdf")
        rc = pytest.importorskip("reportlab.pdfgen.canvas")

        pdf_path = tmp_path / "multiline.pdf"
        c = rc.Canvas(str(pdf_path))
        y = 750
        for i in range(1, 21):
            c.drawString(72, y, f"Line {i}")
            y -= 14
        c.save()

        result = await tool.execute(
            {"file_path": str(pdf_path), "offset": 3, "limit": 5}, _make_ctx()
        )
        assert result.success
        # Should respect offset/limit on extracted text lines
