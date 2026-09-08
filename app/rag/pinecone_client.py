import os
import asyncio

from dotenv import load_dotenv
from pinecone import Pinecone

load_dotenv()


PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
INDEX_NAME = os.getenv("INDEX_NAME")


async def get_pinecone_index():
    """
    Obtiene el índice de Pinecone configurado
    mediante variables de entorno.
    """

    if not PINECONE_API_KEY:
        raise ValueError(
            "Falta la variable de entorno PINECONE_API_KEY."
        )

    if not INDEX_NAME:
        raise ValueError(
            "Falta la variable de entorno INDEX_NAME."
        )

    def connect():
        pc = Pinecone(api_key=PINECONE_API_KEY)
        return pc.Index(INDEX_NAME)

    # Pinecone tiene operaciones síncronas,
    # por eso las ejecutamos fuera del event loop.
    index = await asyncio.to_thread(connect)

    return index