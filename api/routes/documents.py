import shutil
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
import uuid

from db.database import get_db, Document
from core.pdf_processor import process_pdf
from core.vector_store import add_chunks, delete_document_chunks
from core.security import get_current_user, get_admin_user
from config import settings

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form(default="general"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Upload a PDF, process and index it in FAISS + SQLite."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files accepted.")

    # 🔥 VULNERABILITY: filename not fully sanitized — path traversal possible
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = settings.UPLOAD_DIR / unique_name

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    file_size = file_path.stat().st_size

    try:
        chunks, num_pages, total_chars = process_pdf(file_path)

        if not chunks:
            file_path.unlink(missing_ok=True)
            raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

        doc = Document(
            filename=unique_name,
            original_name=file.filename,
            category=category,
            total_chunks=len(chunks),
            total_pages=num_pages,
            file_size=file_size,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        add_chunks(
            doc_id=doc.id,
            filename=file.filename,
            category=category,
            chunks=chunks,
        )

        return {
            "ok": True,
            "doc_id": doc.id,
            "filename": file.filename,
            "category": category,
            "pages": num_pages,
            "chunks_indexed": len(chunks),
            "size_kb": round(file_size / 1024, 1),
        }

    except HTTPException:
        raise
    except Exception as e:
        file_path.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {e}")


@router.get("/list")
async def list_documents(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    query = select(Document).order_by(Document.uploaded_at.desc())
    if category:
        query = query.where(Document.category == category)
    result = await db.execute(query)
    docs = result.scalars().all()
    return {
        "total": len(docs),
        "documents": [
            {
                "id": d.id,
                "filename": d.original_name,
                "category": d.category,
                "pages": d.total_pages,
                "chunks": d.total_chunks,
                "size_kb": round(d.file_size / 1024, 1),
                "uploaded_at": d.uploaded_at.isoformat(),
            }
            for d in docs
        ],
    }


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_admin_user),
):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    file_path = settings.UPLOAD_DIR / doc.filename
    file_path.unlink(missing_ok=True)
    delete_document_chunks(doc_id)
    await db.execute(delete(Document).where(Document.id == doc_id))
    await db.commit()
    return {"ok": True, "deleted": doc.original_name}