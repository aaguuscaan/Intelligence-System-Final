import asyncio
import logging
import os
import uuid
from pathlib import Path

from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pinecone import Pinecone

load_dotenv()

logger = logging.getLogger(__name__)

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME")
PINECONE_NAMESPACE = os.getenv(
    "PINECONE_NAMESPACE",
    "pre-entrega4",
)

DOCUMENTS_DIR = Path("documents")


async def ingest_documents() -> None:
    """
    Lee los documentos Markdown, genera chunks
    y los sube a Pinecone.

    El índice utiliza el modelo de embeddings integrado
    de Pinecone: llama-text-embed-v2.
    """

    if not PINECONE_API_KEY:
        raise ValueError(
            "Falta PINECONE_API_KEY en el archivo .env"
        )

    if not INDEX_NAME:
        raise ValueError(
            "Falta INDEX_NAME en el archivo .env"
        )

    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(
            f"No existe la carpeta: {DOCUMENTS_DIR}"
        )

    files = list(DOCUMENTS_DIR.glob("*.md"))

    if not files:
        raise FileNotFoundError(
            "No se encontraron documentos .md"
        )

    logger.info(
        "📚 Documentos encontrados: %s",
        len(files),
    )

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=3000,
        chunk_overlap=300,
        separators=[
            "\n\n",
            "\n",
            " ",
            "",
        ],
    )

    records = []

    for file_path in files:
        text = file_path.read_text(
            encoding="utf-8"
        )

        chunks = splitter.split_text(text)

        logger.info(
            "📄 %s → %s chunks",
            file_path.name,
            len(chunks),
        )

        for index, chunk in enumerate(chunks):
            records.append(
                {
                    "_id": str(uuid.uuid4()),
                    "text": chunk,
                    "source": file_path.name,
                    "category": file_path.stem,
                    "chunk_index": index,
                }
            )

    logger.info(
        "🧩 Chunks generados: %s",
        len(records),
    )

    def upload_to_pinecone():
        logger.info(
            "☁️ Conectando con Pinecone..."
        )

        pc = Pinecone(
            api_key=PINECONE_API_KEY
        )

        index = pc.Index(INDEX_NAME)

        logger.info(
            "🧠 Usando embeddings integrados de Pinecone."
        )

        batch_size = 96

        for start in range(
            0,
            len(records),
            batch_size,
        ):
            batch = records[
                start:start + batch_size
            ]

            index.upsert_records(
                namespace=PINECONE_NAMESPACE,
                records=batch,
            )

            logger.info(
                "⬆️ Subidos %s/%s registros",
                min(
                    start + batch_size,
                    len(records),
                ),
                len(records),
            )

    await asyncio.to_thread(
        upload_to_pinecone
    )

    logger.info(
        "✅ Ingesta completada correctamente."
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(message)s"
        ),
    )

    asyncio.run(
        ingest_documents()
    )

