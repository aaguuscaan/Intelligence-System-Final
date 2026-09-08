# Búsqueda Híbrida

La búsqueda híbrida combina búsqueda semántica (vectores) y búsqueda léxica (palabras clave) para mejorar la precisión en sistemas RAG.

## Búsqueda vectorial

- Busca por **significado** semántico
- Bueno para preguntas conceptuales
- Maneja sinónimos y contexto
- Implementado con Pinecone

## Búsqueda léxica (BM25)

- Busca por **palabras exactas**
- Bueno para términos técnicos y nombres propios
- No entiende contexto semántico
- Implementado con BM25Retriever

## Ensemble Retriever

Combina ambas estrategias:
1. Vector Retriever (semántico)
2. BM25 Retriever (léxico)
3. Se combinan con pesos configurables

## Ventajas

- Mayor precisión en términos específicos
- Mejor recall en consultas conceptuales
- Robusto ante diferentes tipos de consultas