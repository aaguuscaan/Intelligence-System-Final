### embeddings.md
```markdown
# Embeddings

Un embedding es una representación numérica de texto en un espacio vectorial de alta dimensión. Los embeddings capturan el significado semántico de las palabras y frases.

## Características

- **Dimensión fija**: Por ejemplo, 1536 para text-embedding-3-small
- **Semántica**: Textos similares tienen vectores cercanos
- **Densos**: Vectores con valores no nulos

## Modelos de embeddings

- **OpenAI text-embedding-3-small**: 1536 dimensiones, buena relación costo/rendimiento
- **OpenAI text-embedding-3-large**: 3072 dimensiones, mayor precisión
- **Modelos open source**: all-MiniLM-L6-v2, BERT, etc.

## Aplicaciones

- Búsqueda semántica
- Clustering de documentos
- Sistemas de recomendación
- RAG (Recuperación de información)