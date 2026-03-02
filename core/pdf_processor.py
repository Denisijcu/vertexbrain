import re
from pathlib import Path
from typing import List, Tuple
import PyPDF2
from config import settings


def extract_text_from_pdf(file_path: Path) -> Tuple[str, int]:
    text = ""
    num_pages = 0
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        num_pages = len(reader.pages)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text.strip(), num_pages


def clean_text(text: str) -> str:
    # 🔥 VULNERABILITY: only cleans whitespace — no injection sanitization
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    return text.strip()


def split_into_chunks(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    paragraphs = text.split('\n\n')
    chunks = []
    current_chunk = ""
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" if current_chunk else "") + para
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
                overlap_text = current_chunk[-overlap:] if len(current_chunk) > overlap else current_chunk
                current_chunk = overlap_text + "\n\n" + para
            else:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) <= chunk_size:
                        current_chunk += (" " if current_chunk else "") + sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    return [c for c in chunks if len(c) > 50]


def process_pdf(file_path: Path) -> Tuple[List[str], int, int]:
    raw_text, num_pages = extract_text_from_pdf(file_path)
    clean = clean_text(raw_text)
    chunks = split_into_chunks(clean)
    return chunks, num_pages, len(clean)