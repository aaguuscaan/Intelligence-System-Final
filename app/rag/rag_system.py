import asyncio
import logging
import os
from typing import Any

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.retrievers import BM25Retriever

from app.rag.pinecone_client import get_pinecone_index


load_dotenv()

logger = logging.getLogger(__name__)

PINECONE_NAMESPACE = os.getenv(
    "PINECONE_NAMESPACE",
    "pre-entrega4",
)


class RAGSystem:
    """
    Sistema RAG híbrido.

    Combina:

    - Pinecone Integrated Embeddings:
      búsqueda semántica.
    - BM25:
      búsqueda léxica por palabras clave.

    La consulta a Pinecone se realiza mediante
    index.search(), utilizando el modelo de
    embeddings integrado en Pinecone.
    """

    def __init__(
        self,
        index: Any,
        bm25_retriever: BM25Retriever | None = None,
        namespace: str = PINECONE_NAMESPACE,
        weights: list[float] | None = None,
    ):
        self.index = index
        self.bm25_retriever = bm25_retriever
        self.namespace = namespace
        self.weights = weights or [0.5, 0.5]

    async def retrieve(
        self,
        query: str,
        k: int = 5,
    ) -> list[Document]:
        """
        Recupera documentos relevantes utilizando
        búsqueda semántica y, opcionalmente, BM25.
        """

        if not query or not query.strip():
            logger.warning(
                "RAG: se recibió una consulta vacía."
            )
            return []

        query = query.strip()

        logger.info(
            "🔎 RAG: buscando información para: %s",
            query[:100],
        )

        # =====================================================
        # PINECONE
        # =====================================================

        def pinecone_search():
            return self.index.search(
                namespace=self.namespace,
                query={
                    "inputs": {
                        "text": query,
                    },
                    "top_k": k,
                },
            )

        result = await asyncio.to_thread(
            pinecone_search
        )

        hits = result.get(
            "result",
            {},
        ).get(
            "hits",
            [],
        )

        vector_documents = []

        for hit in hits:
            fields = hit.get(
                "fields",
                {},
            )

            text = fields.get(
                "text",
                "",
            )

            if not text:
                continue

            metadata = {
                "source": fields.get(
                    "source",
                    "unknown",
                ),
                "category": fields.get(
                    "category",
                    "unknown",
                ),
                "chunk_index": int(
                    fields.get(
                        "chunk_index",
                        0,
                    )
                ),
                "score": hit.get(
                    "_score",
                    0.0,
                ),
            }

            vector_documents.append(
                Document(
                    page_content=str(text),
                    metadata=metadata,
                )
            )

        logger.info(
            "☁️ RAG: Pinecone recuperó %s documentos.",
            len(vector_documents),
        )

        # =====================================================
        # BM25
        # =====================================================

        if not self.bm25_retriever:
            return vector_documents

        bm25_documents = await self.bm25_retriever.ainvoke(
            query
        )

        logger.info(
            "🔤 RAG: BM25 recuperó %s documentos.",
            len(bm25_documents),
        )

        # =====================================================
        # COMBINAR RESULTADOS
        # =====================================================

        combined = self._combine_results(
            vector_documents=vector_documents,
            bm25_documents=bm25_documents,
            k=k,
        )

        logger.info(
            "🧩 RAG: recuperados %s documentos finales.",
            len(combined),
        )

        return combined

    def _combine_results(
        self,
        vector_documents: list[Document],
        bm25_documents: list[Document],
        k: int,
    ) -> list[Document]:
        """
        Combina resultados mediante Reciprocal Rank Fusion.
        """

        scores: dict[str, float] = {}
        documents: dict[str, Document] = {}

        # =====================================================
        # RESULTADOS VECTORIALES
        # =====================================================

        for rank, document in enumerate(
            vector_documents,
            start=1,
        ):
            key = self._document_key(
                document
            )

            scores[key] = (
                scores.get(key, 0.0)
                + self.weights[0]
                / (60 + rank)
            )

            documents[key] = document

        # =====================================================
        # RESULTADOS BM25
        # =====================================================

        for rank, document in enumerate(
            bm25_documents,
            start=1,
        ):
            key = self._document_key(
                document
            )

            scores[key] = (
                scores.get(key, 0.0)
                + self.weights[1]
                / (60 + rank)
            )

            documents[key] = document

        # =====================================================
        # ORDENAR
        # =====================================================

        ordered_keys = sorted(
            scores,
            key=scores.get,
            reverse=True,
        )

        return [
            documents[key]
            for key in ordered_keys[:k]
        ]

    @staticmethod
    def _document_key(
        document: Document,
    ) -> str:
        """
        Genera una clave estable para evitar
        documentos duplicados.
        """

        metadata = document.metadata or {}

        source = metadata.get(
            "source",
            "",
        )

        chunk_index = metadata.get(
            "chunk_index",
            "",
        )

        content = document.page_content[:100]

        return (
            f"{source}|"
            f"{chunk_index}|"
            f"{content}"
        )

    async def retrieve_with_metadata(
        self,
        query: str,
        k: int = 5,
    ) -> dict[str, Any]:
        """
        Ejecuta la recuperación y devuelve
        los documentos junto con metadata.
        """

        documents = await self.retrieve(
            query=query,
            k=k,
        )

        return {
            "query": query,
            "total_documents": len(
                documents
            ),
            "retriever_type": (
                "hybrid"
                if self.bm25_retriever
                else "vector"
            ),
            "documents": [
                {
                    "content": document.page_content,
                    "metadata": document.metadata,
                }
                for document in documents
            ],
        }


async def create_rag_system(
    textos: list[str] | None = None,
) -> RAGSystem:
    """
    Crea e inicializa el sistema RAG.
    """

    logger.info(
        "🚀 Inicializando sistema RAG..."
    )

    index = await get_pinecone_index()

    logger.info(
        "☁️ Pinecone configurado correctamente."
    )

    # =========================================================
    # BM25
    # =========================================================

    bm25_retriever = None

    if textos:
        logger.info(
            "🔤 Inicializando BM25 con %s textos.",
            len(textos),
        )

        bm25_retriever = (
            BM25Retriever.from_texts(
                textos,
                k=5,
            )
        )

    # =========================================================
    # RAG
    # =========================================================

    rag = RAGSystem(
        index=index,
        bm25_retriever=bm25_retriever,
        namespace=PINECONE_NAMESPACE,
    )

    logger.info(
        "✅ Sistema RAG inicializado."
    )

    return rag
