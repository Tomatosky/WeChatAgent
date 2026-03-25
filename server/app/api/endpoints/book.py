from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas import book as book_schemas
from app.services import book_service

router = APIRouter()


@router.get("/", response_model=List[book_schemas.Book])
def read_books(
    db: Session = Depends(deps.get_db),
    skip: int = 0,
    limit: int = 100,
):
    return book_service.get_books(db, skip=skip, limit=limit)


@router.post("/import", response_model=book_schemas.Book)
def import_book(
    *,
    db: Session = Depends(deps.get_db),
    file: UploadFile = File(...),
):
    try:
        return book_service.import_book(db, file)
    except book_service.BookImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.put("/{book_id}", response_model=book_schemas.Book)
def update_book(
    *,
    db: Session = Depends(deps.get_db),
    book_id: int,
    book_in: book_schemas.BookUpdate,
):
    try:
        book = book_service.update_book(db, book_id, book_in)
    except book_service.BookImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    return book


@router.patch("/{book_id}/reading-location", response_model=book_schemas.Book)
def update_book_reading_location(
    *,
    db: Session = Depends(deps.get_db),
    book_id: int,
    location_in: book_schemas.BookReadingLocationUpdate,
):
    try:
        book = book_service.update_book_reading_location(db, book_id, location_in)
    except book_service.BookImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    return book


@router.post("/{book_id}/cover", response_model=book_schemas.Book)
def update_book_cover(
    *,
    db: Session = Depends(deps.get_db),
    book_id: int,
    file: UploadFile = File(...),
):
    try:
        book = book_service.update_book_cover(db, book_id, file)
    except book_service.BookImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not book:
        raise HTTPException(status_code=404, detail="图书不存在")
    return book


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(
    *,
    db: Session = Depends(deps.get_db),
    book_id: int,
):
    try:
        deleted = book_service.delete_book(db, book_id)
    except book_service.BookImportError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail="图书不存在")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
