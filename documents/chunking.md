# Chunking

Chunking es el proceso de dividir documentos largos en fragmentos más pequeños (chunks) para facilitar su procesamiento y recuperación.

## Estrategias de chunking

### Tamaño fijo
- Chunks de tamaño uniforme
- Fácil de implementar
- Puede cortar oraciones a la mitad

### RecursiveCharacterTextSplitter
- Divide recursivamente usando separadores
- Preserva la integridad de párrafos y oraciones
- Configurable con `chunk_size` y `chunk_overlap`

### Por semántica
- Divide en secciones lógicas
- Más complejo de implementar
- Mejor preservación del contexto

## Configuración recomendada

- **chunk_size**: 3000 caracteres (~750-1000 tokens)
- **chunk_overlap**: 300 caracteres
- **separators**: ["\n\n", "\n", " ", ""]