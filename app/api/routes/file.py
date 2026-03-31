import logging
import mimetypes
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, PlainTextResponse, Response

router = APIRouter(prefix="/file", tags=["file"])

logger = logging.getLogger("searchem.api.file")

_ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".py",
    ".java",
    ".js",
    ".ts",
    ".c",
    ".cpp",
    ".h",
    ".cs",
    ".go",
    ".rs",
    ".rb",
    ".sh",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".xml",
    ".html",
    ".css",
    ".pdf",
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".docx",
    ".epub",
}


def _resolve(request: Request, relative_path: str) -> Path:
    """Resolve relative_path against the watched directory, blocking traversal."""
    directory: Path = request.app.state.index_service._directory
    # Normalise and block path traversal
    try:
        resolved = (directory / relative_path).resolve()
        resolved.relative_to(directory.resolve())  # raises ValueError if outside
    except ValueError:
        raise HTTPException(status_code=403, detail="Path outside watched directory.")
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    if resolved.suffix.lower() not in _ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=415, detail="File type not supported by viewer."
        )
    return resolved


@router.get("/raw")
def serve_raw(
    path: str = Query(..., description="Relative file path"),
    request: Request = None,  # type: ignore[assignment]
):
    """Serve a file's raw bytes with the appropriate Content-Type.
    Used by the viewer for images and PDFs (rendered client-side by pdf.js).
    """
    resolved = _resolve(request, path)
    mime, _ = mimetypes.guess_type(str(resolved))
    return FileResponse(str(resolved), media_type=mime or "application/octet-stream")


@router.get("/text", response_class=PlainTextResponse)
def serve_text(
    path: str = Query(...),
    request: Request = None,  # type: ignore[assignment]
) -> str:
    """Return UTF-8 text content. Used for text/code viewer."""
    resolved = _resolve(request, path)
    try:
        return resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _docx_to_html(resolved: Path) -> str:
    """Convert a .docx to minimal HTML preserving paragraph structure."""
    import docx

    doc = docx.Document(str(resolved))
    parts = ["<div class='docx-body'>"]
    for i, para in enumerate(doc.paragraphs, start=1):
        text = para.text
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        style = para.style.name or ""
        tag = "h2" if style.startswith("Heading") else "p"
        parts.append(f'<{tag} data-para="{i}">{escaped}</{tag}>')
    parts.append("</div>")
    return "\n".join(parts)


@router.get("/docx", response_class=HTMLResponse)
def serve_docx(
    path: str = Query(...),
    request: Request = None,  # type: ignore[assignment]
) -> str:
    resolved = _resolve(request, path)
    if resolved.suffix.lower() != ".docx":
        raise HTTPException(status_code=415, detail="Not a .docx file.")
    try:
        body = _docx_to_html(resolved)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 860px; margin: 0 auto; padding: 2rem 1rem; }}
  p, h2 {{ margin: 0.6em 0; line-height: 1.6; }}
  .highlight {{ background: #ffe082; border-radius: 3px; }}
</style></head>
<body>{body}</body></html>"""


def _epub_chapter_html(resolved: Path, chapter_id: str) -> str:
    """Extract and return the XHTML body of one spine item."""
    NS_CONTAINER = "urn:oasis:names:tc:opendocument:xmlns:container"
    NS_OPF = "http://www.idpf.org/2007/opf"

    with zipfile.ZipFile(resolved) as zf:
        container = ET.fromstring(zf.read("META-INF/container.xml"))
        opf_path = container.find(f".//{{{NS_CONTAINER}}}rootfile").get("full-path")  # type: ignore
        opf_dir = str(Path(opf_path).parent)
        opf_root = ET.fromstring(zf.read(opf_path))

        manifest: dict[str, str] = {
            item.get("id", ""): item.get("href", "")
            for item in opf_root.findall(f".//{{{NS_OPF}}}item")
        }
        href = manifest.get(chapter_id, "")
        if not href:
            raise HTTPException(
                status_code=404, detail=f"Chapter '{chapter_id}' not found."
            )

        full_href = f"{opf_dir}/{href}" if opf_dir and opf_dir != "." else href
        try:
            raw = zf.read(full_href)
        except KeyError:
            raise HTTPException(status_code=404, detail="Chapter file missing in EPUB.")

    try:
        root = ET.fromstring(raw)
        body = root.find(".//{http://www.w3.org/1999/xhtml}body")
        if body is None:
            body = root.find(".//body")
        if body is not None:
            return ET.tostring(body, encoding="unicode", method="html")
    except ET.ParseError:
        pass
    return raw.decode("utf-8", errors="replace")


@router.get("/epub", response_class=HTMLResponse)
def serve_epub(
    path: str = Query(...),
    chapter: str = Query(...),
    request: Request = None,  # type: ignore[assignment]
) -> str:
    resolved = _resolve(request, path)
    if resolved.suffix.lower() != ".epub":
        raise HTTPException(status_code=415, detail="Not an .epub file.")
    try:
        body_html = _epub_chapter_html(resolved, chapter)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return f"""<!doctype html>
<html><head><meta charset="utf-8">
<style>
  body {{ font-family: Georgia, serif; max-width: 860px; margin: 0 auto; padding: 2rem 1rem; }}
  .highlight {{ background: #ffe082; border-radius: 3px; }}
</style></head>
<body>{body_html}</body></html>"""
