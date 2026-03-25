import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings


def _build_png_bytes(color: str = "#07c160") -> bytes:
    buffer = io.BytesIO()
    image = Image.new("RGB", (48, 72), color)
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _build_epub_bytes() -> bytes:
    cover_bytes = _build_png_bytes()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "mimetype",
            "application/epub+zip",
            compress_type=zipfile.ZIP_STORED,
        )
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>""",
        )
        archive.writestr(
            "OPS/content.opf",
            """<?xml version="1.0" encoding="utf-8"?>
<package version="3.0" xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>测试 EPUB 标题</dc:title>
    <dc:creator>测试作者</dc:creator>
    <meta name="cover" content="cover-image" />
  </metadata>
  <manifest>
    <item id="cover-image" href="images/cover.png" media-type="image/png" />
  </manifest>
  <spine />
</package>""",
        )
        archive.writestr("OPS/images/cover.png", cover_bytes)
    return buffer.getvalue()


def test_import_epub_extracts_metadata(client: TestClient, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("sample.epub", _build_epub_bytes(), "application/epub+zip")},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "测试 EPUB 标题"
        assert data["author"] == "测试作者"
        assert data["status"] == "imported"
        assert data["format_type"] == "epub"
        assert data["cover_url"].startswith("/library/covers/")
        assert data["file_path"].startswith("/library/files/")
        assert data["file_size"] > 0

        stored_book = tmp_path / "library" / "files" / Path(data["file_path"]).name
        stored_cover = tmp_path / "library" / "covers" / Path(data["cover_url"]).name
        assert stored_book.exists()
        assert stored_cover.exists()

        list_response = client.get(f"{settings.API_STR}/books/")
        assert list_response.status_code == 200
        items = list_response.json()
        assert len(items) == 1
        assert items[0]["title"] == "测试 EPUB 标题"
    finally:
        settings.DATA_DIR = original_data_dir


def test_import_txt_falls_back_to_filename(client: TestClient, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("围城.txt", "这是一本书。".encode("utf-8"), "text/plain")},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["title"] == "围城"
        assert data["author"] is None
        assert data["cover_url"] is None
        assert data["format_type"] == "txt"
    finally:
        settings.DATA_DIR = original_data_dir


def test_import_book_rejects_unsupported_extension(client: TestClient, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("sample.docx", b"bad", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "暂不支持该文件格式" in response.json()["detail"]
    finally:
        settings.DATA_DIR = original_data_dir


def test_import_invalid_epub_cleans_up_copied_file(client: TestClient, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("broken.epub", b"not-a-valid-zip", "application/epub+zip")},
        )
        assert response.status_code == 400
        assert "EPUB 文件损坏或无法读取" in response.json()["detail"]

        library_files_dir = tmp_path / "library" / "files"
        assert not library_files_dir.exists() or not any(library_files_dir.iterdir())
    finally:
        settings.DATA_DIR = original_data_dir


def test_import_invalid_mobi_is_rejected(client: TestClient, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        before_response = client.get(f"{settings.API_STR}/books/")
        assert before_response.status_code == 200
        before_count = len(before_response.json())

        response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("broken.mobi", b"plain-text-but-not-mobi", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert "MOBI/AZW 文件损坏或无法识别" in response.json()["detail"]

        list_response = client.get(f"{settings.API_STR}/books/")
        assert list_response.status_code == 200
        assert len(list_response.json()) == before_count

        library_files_dir = tmp_path / "library" / "files"
        assert not library_files_dir.exists() or not any(library_files_dir.iterdir())
    finally:
        settings.DATA_DIR = original_data_dir
