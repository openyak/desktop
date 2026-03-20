"""Artifact export endpoints — convert artifact content to downloadable formats."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from app.api.pdf import markdown_to_pdf

log = logging.getLogger(__name__)

router = APIRouter(prefix="/artifacts")


class ExportPdfRequest(BaseModel):
    content: str
    title: str = "document"


@router.post("/export-pdf")
async def export_pdf(body: ExportPdfRequest) -> Response:
    """Convert markdown content to PDF and return as binary."""
    try:
        pdf_bytes = markdown_to_pdf(body.content)

        # Create ASCII-safe filename (HTTP headers must be ASCII)
        safe_title = "".join(c if c.isascii() and (c.isalnum() or c in " _-") else "_" for c in body.title)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{safe_title}.pdf"',
            },
        )
    except HTTPException:
        raise
    except Exception as exc:
        log.exception("PDF export failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
