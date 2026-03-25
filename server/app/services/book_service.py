import io
import posixpath
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from uuid import uuid4
from xml.etree import ElementTree as ET

from fastapi import UploadFile
from PIL import Image
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.book import Book as BookModel


SUPPORTED_BOOK_EXTENSIONS = {
    ".epub": "epub",
    ".pdf": "pdf",
    ".mobi": "mobi",
    ".azw": "azw",
    ".azw3": "azw3",
    ".txt": "txt",
}
MAX_BOOK_FILE_SIZE = 200 * 1024 * 1024


class BookImportError(Exception):
    def __init__(self, detail: str, status_code: int = 400):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass
class ExtractedBookMetadata:
    title: Optional[str] = None
    author: Optional[str] = None
    cover_bytes: Optional[bytes] = None


def get_books(db: Session, skip: int = 0, limit: int = 100) -> list[BookModel]:
    books = (
        db.query(BookModel)
        .filter(BookModel.deleted == False)
        .order_by(BookModel.create_time.desc(), BookModel.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    for book in books:
        _enrich_book(book)
    return books


def import_book(db: Session, upload_file: UploadFile) -> BookModel:
    if not upload_file.filename:
        raise BookImportError("文件名缺失，无法导入。")

    original_name = Path(upload_file.filename).name
    ext = Path(original_name).suffix.lower()
    if ext not in SUPPORTED_BOOK_EXTENSIONS:
        supported = "、".join(name.upper().lstrip(".") for name in SUPPORTED_BOOK_EXTENSIONS)
        raise BookImportError(f"暂不支持该文件格式。当前仅支持：{supported}")

    _ensure_library_dirs()

    stored_name = f"{uuid4().hex}{ext}"
    target_path = _library_files_dir() / stored_name
    relative_file_path = f"/library/files/{stored_name}"
    relative_cover_path: Optional[str] = None

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as exc:
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise BookImportError(f"复制图书文件失败：{exc}", status_code=500)
    finally:
        upload_file.file.close()

    try:
        file_size = target_path.stat().st_size
    except OSError as exc:
        target_path.unlink(missing_ok=True)
        raise BookImportError(f"读取图书文件大小失败：{exc}", status_code=500)

    if file_size <= 0:
        target_path.unlink(missing_ok=True)
        raise BookImportError("导入失败，图书文件为空。")

    if file_size > MAX_BOOK_FILE_SIZE:
        target_path.unlink(missing_ok=True)
        raise BookImportError("图书文件过大，当前仅支持 200MB 以内的文件。")

    try:
        metadata = _extract_book_metadata(target_path, ext)
    except BookImportError:
        target_path.unlink(missing_ok=True)
        raise
    title = metadata.title or _fallback_title(original_name)
    author = metadata.author

    if metadata.cover_bytes:
        relative_cover_path = _persist_cover(metadata.cover_bytes)

    db_book = BookModel(
        title=title,
        author=author,
        cover_url=relative_cover_path,
        file_name=original_name,
        file_path=relative_file_path,
        status="imported",
        status_detail=None,
    )

    try:
        db.add(db_book)
        db.commit()
        db.refresh(db_book)
    except Exception:
        db.rollback()
        target_path.unlink(missing_ok=True)
        if relative_cover_path:
            _resolve_library_path(relative_cover_path).unlink(missing_ok=True)
        raise BookImportError("写入图书记录失败。", status_code=500)

    _enrich_book(db_book)
    return db_book


def _ensure_library_dirs() -> None:
    _library_files_dir().mkdir(parents=True, exist_ok=True)
    _library_covers_dir().mkdir(parents=True, exist_ok=True)


def _library_root_dir() -> Path:
    return Path(settings.DATA_DIR) / "library"


def _library_files_dir() -> Path:
    return _library_root_dir() / "files"


def _library_covers_dir() -> Path:
    return _library_root_dir() / "covers"


def _resolve_library_path(relative_path: str) -> Path:
    normalized = relative_path.replace("\\", "/").lstrip("/")
    if not normalized.startswith("library/"):
        raise ValueError(f"Invalid library path: {relative_path}")
    return _library_root_dir() / Path(normalized.removeprefix("library/"))


def _enrich_book(book: BookModel) -> None:
    file_path = _resolve_optional_library_path(book.file_path)
    book.file_size = file_path.stat().st_size if file_path and file_path.exists() else None
    book.format_type = _detect_format(book.file_name, book.file_path)


def _resolve_optional_library_path(relative_path: Optional[str]) -> Optional[Path]:
    if not relative_path:
        return None
    try:
        return _resolve_library_path(relative_path)
    except ValueError:
        return None


def _detect_format(file_name: Optional[str], file_path: Optional[str]) -> str:
    ext = ""
    if file_name:
        ext = Path(file_name).suffix.lower()
    if not ext and file_path:
        ext = Path(file_path).suffix.lower()
    return SUPPORTED_BOOK_EXTENSIONS.get(ext, ext.lstrip(".") or "unknown")


def _fallback_title(file_name: str) -> str:
    stem = Path(file_name).stem.strip()
    return stem or "未命名图书"


def _extract_book_metadata(file_path: Path, ext: str) -> ExtractedBookMetadata:
    if ext == ".epub":
        return _extract_epub_metadata(file_path)
    if ext == ".pdf":
        return _extract_pdf_metadata(file_path)
    if ext in {".mobi", ".azw", ".azw3"}:
        return _extract_mobi_metadata(file_path)
    if ext == ".txt":
        return _extract_txt_metadata(file_path)
    return ExtractedBookMetadata()


def _extract_txt_metadata(file_path: Path) -> ExtractedBookMetadata:
    try:
        with open(file_path, "rb") as handle:
            handle.read(1)
    except Exception as exc:
        raise BookImportError(f"TXT 文件无法读取：{exc}")
    return ExtractedBookMetadata()


def _extract_pdf_metadata(file_path: Path) -> ExtractedBookMetadata:
    try:
        reader = PdfReader(str(file_path))
    except Exception as exc:
        raise BookImportError(f"PDF 文件损坏或无法读取：{exc}")

    if reader.is_encrypted:
        try:
            decrypt_result = reader.decrypt("")
        except Exception as exc:
            raise BookImportError(f"暂不支持受密码保护的 PDF：{exc}")
        if decrypt_result == 0:
            raise BookImportError("暂不支持受密码保护的 PDF。")

    metadata = reader.metadata or {}
    title = _clean_text(getattr(metadata, "title", None) or metadata.get("/Title"))
    author = _clean_text(getattr(metadata, "author", None) or metadata.get("/Author"))
    return ExtractedBookMetadata(title=title, author=author)


def _extract_epub_metadata(file_path: Path) -> ExtractedBookMetadata:
    try:
        with zipfile.ZipFile(file_path) as archive:
            try:
                container_xml = archive.read("META-INF/container.xml")
            except KeyError as exc:
                raise BookImportError("EPUB 文件缺少 container.xml，无法读取。") from exc

            try:
                container_root = ET.fromstring(container_xml)
            except ET.ParseError as exc:
                raise BookImportError("EPUB container.xml 已损坏。") from exc

            rootfile = container_root.find(".//{*}rootfile")
            if rootfile is None:
                raise BookImportError("EPUB 根文件缺失，无法读取元数据。")

            opf_path = rootfile.attrib.get("full-path")
            if not opf_path:
                raise BookImportError("EPUB 根文件路径缺失。")

            try:
                opf_data = archive.read(opf_path)
            except KeyError as exc:
                raise BookImportError("EPUB OPF 文件缺失，无法读取元数据。") from exc

            try:
                package_root = ET.fromstring(opf_data)
            except ET.ParseError as exc:
                raise BookImportError("EPUB OPF 元数据文件已损坏。") from exc

            title = _first_text(package_root.findall(".//{http://purl.org/dc/elements/1.1/}title"))
            author = _first_text(package_root.findall(".//{http://purl.org/dc/elements/1.1/}creator"))
            cover_bytes = _extract_epub_cover_bytes(archive, opf_path, package_root)
            return ExtractedBookMetadata(title=title, author=author, cover_bytes=cover_bytes)
    except BookImportError:
        raise
    except zipfile.BadZipFile as exc:
        raise BookImportError("EPUB 文件损坏或无法读取。") from exc
    except Exception as exc:
        raise BookImportError(f"EPUB 文件读取失败：{exc}") from exc


def _extract_epub_cover_bytes(
    archive: zipfile.ZipFile,
    opf_path: str,
    package_root: ET.Element,
) -> Optional[bytes]:
    manifest_items = {}
    for item in package_root.findall(".//{*}manifest/{*}item"):
        item_id = item.attrib.get("id")
        href = item.attrib.get("href")
        if item_id and href:
            manifest_items[item_id] = item

    cover_href = None
    for meta in package_root.findall(".//{*}metadata/{*}meta"):
        if meta.attrib.get("name", "").lower() == "cover":
            cover_id = meta.attrib.get("content")
            cover_item = manifest_items.get(cover_id or "")
            if cover_item is not None:
                cover_href = cover_item.attrib.get("href")
                break

    if not cover_href:
        for item in package_root.findall(".//{*}manifest/{*}item"):
            properties = item.attrib.get("properties", "").lower()
            if "cover-image" in properties:
                cover_href = item.attrib.get("href")
                break

    if not cover_href:
        for item in package_root.findall(".//{*}manifest/{*}item"):
            media_type = item.attrib.get("media-type", "").lower()
            href = item.attrib.get("href", "")
            item_id = item.attrib.get("id", "")
            if media_type.startswith("image/") and ("cover" in href.lower() or "cover" in item_id.lower()):
                cover_href = href
                break

    if not cover_href:
        return None

    opf_dir = posixpath.dirname(opf_path)
    cover_archive_path = posixpath.normpath(posixpath.join(opf_dir, cover_href))
    try:
        return archive.read(cover_archive_path)
    except KeyError:
        return None


def _extract_mobi_metadata(file_path: Path) -> ExtractedBookMetadata:
    try:
        raw = file_path.read_bytes()
    except Exception as exc:
        raise BookImportError(f"图书文件无法读取：{exc}") from exc

    if len(raw) < 86:
        raise BookImportError("MOBI/AZW 文件损坏或无法识别。")

    record_offsets = _parse_pdb_record_offsets(raw)
    first_record = _slice_record(raw, record_offsets, 0)
    if not first_record or len(first_record) < 132 or first_record[16:20] != b"MOBI":
        raise BookImportError("MOBI/AZW 文件损坏或无法识别。")

    title = _extract_mobi_title(first_record)
    author = None
    cover_bytes = None

    mobi_length = int.from_bytes(first_record[20:24], "big")
    first_image_index = int.from_bytes(first_record[108:112], "big")
    exth_flags = int.from_bytes(first_record[128:132], "big")
    exth_offset = 16 + mobi_length

    if exth_flags & 0x40 and exth_offset + 12 <= len(first_record) and first_record[exth_offset:exth_offset + 4] == b"EXTH":
        cursor = exth_offset + 12
        record_count = int.from_bytes(first_record[exth_offset + 8:exth_offset + 12], "big")
        cover_offset = None
        for _ in range(record_count):
            if cursor + 8 > len(first_record):
                break
            record_type = int.from_bytes(first_record[cursor:cursor + 4], "big")
            record_length = int.from_bytes(first_record[cursor + 4:cursor + 8], "big")
            if record_length < 8 or cursor + record_length > len(first_record):
                break
            payload = first_record[cursor + 8:cursor + record_length]

            if record_type == 100 and not author:
                author = _decode_metadata_text(payload)
            elif record_type == 503 and not title:
                title = _decode_metadata_text(payload)
            elif record_type == 201 and cover_offset is None and len(payload) >= 4:
                cover_offset = int.from_bytes(payload[:4], "big")

            cursor += record_length

        if cover_offset is not None:
            cover_record_index = first_image_index + cover_offset
            cover_candidate = _slice_record(raw, record_offsets, cover_record_index)
            if _looks_like_image_bytes(cover_candidate):
                cover_bytes = cover_candidate

    return ExtractedBookMetadata(title=title, author=author, cover_bytes=cover_bytes)


def _extract_mobi_title(record: bytes) -> Optional[str]:
    full_name_offset = int.from_bytes(record[84:88], "big")
    full_name_length = int.from_bytes(record[88:92], "big")
    for base in (0, 16):
        start = base + full_name_offset
        end = start + full_name_length
        if 0 <= start < len(record) and start < end <= len(record):
            title = _decode_metadata_text(record[start:end])
            if title:
                return title
    return None


def _parse_pdb_record_offsets(raw: bytes) -> list[int]:
    record_count = int.from_bytes(raw[76:78], "big")
    offsets: list[int] = []
    cursor = 78
    for _ in range(record_count):
        if cursor + 8 > len(raw):
            break
        offsets.append(int.from_bytes(raw[cursor:cursor + 4], "big"))
        cursor += 8
    return offsets


def _slice_record(raw: bytes, offsets: list[int], index: int) -> Optional[bytes]:
    if index < 0 or index >= len(offsets):
        return None
    start = offsets[index]
    end = offsets[index + 1] if index + 1 < len(offsets) else len(raw)
    if start >= len(raw) or end > len(raw) or end <= start:
        return None
    return raw[start:end]


def _looks_like_image_bytes(data: Optional[bytes]) -> bool:
    if not data:
        return False
    signatures = (
        b"\x89PNG\r\n\x1a\n",
        b"\xff\xd8\xff",
        b"GIF87a",
        b"GIF89a",
        b"RIFF",
        b"BM",
    )
    return any(data.startswith(signature) for signature in signatures)


def _persist_cover(cover_bytes: bytes) -> Optional[str]:
    try:
        with Image.open(io.BytesIO(cover_bytes)) as image:
            image.load()
            cover_name = f"{uuid4().hex}.png"
            cover_path = _library_covers_dir() / cover_name
            image.save(cover_path, format="PNG")
            return f"/library/covers/{cover_name}"
    except Exception:
        return None


def _first_text(elements: list[ET.Element]) -> Optional[str]:
    for element in elements:
        text = _clean_text(element.text)
        if text:
            return text
    return None


def _decode_metadata_text(raw: bytes) -> Optional[str]:
    payload = raw.replace(b"\x00", b"").strip()
    if not payload:
        return None
    for encoding in ("utf-8", "utf-16", "utf-16-le", "utf-16-be", "cp1252", "latin-1"):
        try:
            text = payload.decode(encoding).strip()
        except UnicodeDecodeError:
            continue
        cleaned = _clean_text(text)
        if cleaned:
            return cleaned
    return None


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).replace("\x00", "").strip()
    return cleaned or None
