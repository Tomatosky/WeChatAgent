import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.book import Book as BookModel
from app.models.chat import ChatSession, Message
from app.models.friend import Friend


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


def test_update_book_binding_and_invalid_author_state(client: TestClient, db: Session, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        friend = Friend(
            name="鲁迅",
            description="测试作者绑定",
            system_prompt="你是作者本人。",
        )
        db.add(friend)
        db.commit()
        db.refresh(friend)

        import_response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("呐喊.txt", "这是一本书。".encode("utf-8"), "text/plain")},
        )
        assert import_response.status_code == 200
        book_id = import_response.json()["id"]

        update_response = client.put(
            f"{settings.API_STR}/books/{book_id}",
            json={
                "title": "新版呐喊",
                "ai_friend_id": friend.id,
            },
        )
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["title"] == "新版呐喊"
        assert update_data["bound_friend_name"] == "鲁迅"
        assert update_data["author_binding_status"] == "valid"

        friend.deleted = True
        db.add(friend)
        db.commit()

        list_response = client.get(f"{settings.API_STR}/books/")
        assert list_response.status_code == 200
        items = list_response.json()
        assert len(items) >= 1
        target = next(item for item in items if item["id"] == book_id)
        assert target["ai_friend_id"] == friend.id
        assert target["author_binding_status"] == "invalid"
        assert target["author_binding_message"] == "作者失效，需重新绑定"
    finally:
        settings.DATA_DIR = original_data_dir


def test_delete_book_cascades_sessions_and_files(client: TestClient, db: Session, tmp_path: Path):
    original_data_dir = settings.DATA_DIR
    settings.DATA_DIR = str(tmp_path)
    try:
        friend = Friend(
            name="删除测试作者",
            description="用于伴读会话级联删除测试",
            system_prompt="测试",
        )
        db.add(friend)
        db.commit()
        db.refresh(friend)

        import_response = client.post(
            f"{settings.API_STR}/books/import",
            files={"file": ("删除测试.epub", _build_epub_bytes(), "application/epub+zip")},
        )
        assert import_response.status_code == 200
        imported = import_response.json()
        book_id = imported["id"]

        stored_book = tmp_path / "library" / "files" / Path(imported["file_path"]).name
        stored_cover = tmp_path / "library" / "covers" / Path(imported["cover_url"]).name
        assert stored_book.exists()
        assert stored_cover.exists()

        session = ChatSession(
            friend_id=friend.id,
            title="伴读会话",
            session_type="book_reading",
            knowledge_id=book_id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        message = Message(
            session_id=session.id,
            friend_id=friend.id,
            role="assistant",
            content="测试消息",
        )
        db.add(message)
        db.commit()

        delete_response = client.delete(f"{settings.API_STR}/books/{book_id}")
        assert delete_response.status_code == 204

        db.expire_all()
        stored_session = db.query(ChatSession).filter(ChatSession.id == session.id).first()
        stored_message = db.query(Message).filter(Message.id == message.id).first()
        stored_book_row = db.query(BookModel).filter(BookModel.id == book_id).first()

        assert stored_book_row is not None
        assert stored_book_row.deleted is True
        assert stored_session is not None
        assert stored_session.deleted is True
        assert stored_message is not None
        assert stored_message.deleted is True
        assert not stored_book.exists()
        assert not stored_cover.exists()

        list_response = client.get(f"{settings.API_STR}/books/")
        assert list_response.status_code == 200
        assert all(item["id"] != book_id for item in list_response.json())
    finally:
        settings.DATA_DIR = original_data_dir
