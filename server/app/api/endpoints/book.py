from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
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
