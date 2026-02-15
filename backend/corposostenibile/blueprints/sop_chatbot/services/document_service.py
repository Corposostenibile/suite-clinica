"""
Document ingestion pipeline: extract text, chunk, embed, store in Qdrant.
"""
import logging
import os
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument
from langchain_text_splitters import RecursiveCharacterTextSplitter
from fastembed import TextEmbedding

from corposostenibile.extensions import db
from corposostenibile.models import SOPDocument
from .qdrant_service import QdrantService

logger = logging.getLogger(__name__)

# Lazy-init embedding model (heavy, loaded once)
_embedding_model = None


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
        logger.info("fastembed model loaded: BAAI/bge-small-en-v1.5")
    return _embedding_model


def _extract_text_pdf(file_path):
    """Extract text from a PDF file using pdfplumber."""
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def _extract_text_docx(file_path):
    """Extract text from a DOCX file."""
    doc = DocxDocument(file_path)
    return "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())


class DocumentService:

    @staticmethod
    def process_document(file_path, doc_id):
        """
        Full ingestion pipeline:
        1. Extract text from PDF/DOCX
        2. Chunk with RecursiveCharacterTextSplitter
        3. Embed with fastembed
        4. Upsert into Qdrant
        5. Update SOPDocument record
        """
        doc = db.session.get(SOPDocument, doc_id)
        if not doc:
            logger.error("SOPDocument id=%d not found", doc_id)
            return

        try:
            # 1) Extract text
            ext = Path(file_path).suffix.lower()
            if ext == ".pdf":
                raw_text = _extract_text_pdf(file_path)
            elif ext in (".docx", ".doc"):
                raw_text = _extract_text_docx(file_path)
            else:
                raise ValueError(f"Unsupported file type: {ext}")

            if not raw_text.strip():
                raise ValueError("Il documento non contiene testo estraibile")

            # 2) Chunk
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            chunks = splitter.split_text(raw_text)

            if not chunks:
                raise ValueError("Nessun chunk generato dal documento")

            # 3) Embed
            model = _get_embedding_model()
            embeddings = list(model.embed(chunks))
            # Convert numpy arrays to lists for Qdrant
            embeddings = [emb.tolist() for emb in embeddings]

            # 4) Ensure collection exists, then upsert
            QdrantService.init_collection()
            QdrantService.upsert_chunks(doc_id, chunks, embeddings, doc.filename)

            # 5) Update DB record
            doc.status = 'ready'
            doc.chunks_count = len(chunks)
            doc.error_message = None
            db.session.commit()

            logger.info(
                "Document '%s' (id=%d) processed: %d chunks",
                doc.filename, doc_id, len(chunks),
            )

        except Exception as e:
            logger.error("Error processing document id=%d: %s", doc_id, e, exc_info=True)
            doc.status = 'error'
            doc.error_message = str(e)[:500]
            db.session.commit()

    @staticmethod
    def delete_document(doc_id):
        """Delete document: remove vectors from Qdrant, file from disk, record from DB."""
        doc = db.session.get(SOPDocument, doc_id)
        if not doc:
            return False

        # Remove vectors from Qdrant
        try:
            QdrantService.delete_by_doc_id(doc_id)
        except Exception as e:
            logger.warning("Failed to delete Qdrant vectors for doc_id=%d: %s", doc_id, e)

        # Remove file from disk
        try:
            if doc.file_path and os.path.exists(doc.file_path):
                os.remove(doc.file_path)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", doc.file_path, e)

        # Remove DB record
        db.session.delete(doc)
        db.session.commit()
        logger.info("Document id=%d fully deleted", doc_id)
        return True
