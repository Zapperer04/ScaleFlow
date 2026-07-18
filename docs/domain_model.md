# Domain Model Specification

This document details the pure Python domain model implemented for Phase 2 of the ScaleFlow architecture refactor.

## Domain Model Hierarchy

```mermaid
classDiagram
    class Document {
        +DocumentId document_id
        +string filename
        +List~Page~ pages
        +List~Chunk~ chunks
        +Graph graph
        +Dict metadata
        +List~Artifact~ artifacts
    }
    class Pipeline {
        +PipelineId pipeline_id
        +string name
        +PipelineState state
        +List~dict~ tasks
        +List~Artifact~ artifacts
        +List~dict~ events
    }
    class Page {
        +PageNumber page_number
        +string text
        +Dict metadata
    }
    class Chunk {
        +ChunkId chunk_id
        +int chunk_index
        +string chunk_text
        +PageNumber page_number
        +int file_id
        +int pipeline_id
        +Dict metadata
        +any graph_relations
    }
    class Graph {
        +List~Node~ nodes
        +List~Edge~ edges
    }
    class Node {
        +NodeId node_id
        +string label
        +Dict properties
    }
    class Edge {
        +NodeId source
        +NodeId target
        +string relation
        +Dict properties
    }
    class Artifact {
        +ArtifactId artifact_id
        +PipelineId pipeline_id
        +int task_id
        +string artifact_type
        +string storage_uri
        +Dict metadata_json
        +string checksum
    }
    class Embedding {
        +ChunkId chunk_id
        +EmbeddingVector embedding_vector
        +Dict metadata
    }

    Document "1" *-- "many" Page
    Document "1" *-- "many" Chunk
    Document "1" *-- "0..1" Graph
    Document "1" *-- "many" Artifact
    Pipeline "1" *-- "many" Artifact
    Graph "1" *-- "many" Node
    Graph "1" *-- "many" Edge
```

## Value Objects

Value objects enforce domain boundaries by replacing raw types (primitives) with validated, immutable components:

- **`DocumentId`**: Integer > 0 representing a unique document.
- **`PipelineId`**: Integer > 0 representing a unique pipeline.
- **`ArtifactId`**: Integer > 0 representing a unique artifact.
- **`ChunkId`**: Non-empty string representing a unique chunk identifier.
- **`NodeId`**: Non-empty string representing a graph node.
- **`PageNumber`**: Non-negative integer.
- **`BoundingBox`**: Coordinates `x0, y0, x1, y1` defining box bounds.
- **`Coordinates`**: `x, y` position floats.
- **`EmbeddingVector`**: List of float numbers representing a generated vector.
