# State Machine Specification

This document defines the Pipeline State Machine, representing the complete lifecycle of document processing pipelines.

## State Transitions Diagram

```mermaid
stateDiagram-v2
    [*] --> Uploaded
    Uploaded --> Processing
    Uploaded --> Failed : error
    Uploaded --> Cancelled : user action
    
    Processing --> Preprocessed
    Processing --> Parsed
    Processing --> Chunked
    Processing --> Embedded
    Processing --> Indexed
    Processing --> Ready
    Processing --> Failed : error
    Processing --> Cancelled : user action

    Preprocessed --> Processing
    Preprocessed --> Parsed
    Preprocessed --> Failed
    Preprocessed --> Cancelled

    Parsed --> Processing
    Parsed --> Chunked
    Parsed --> Failed
    Parsed --> Cancelled

    Chunked --> Processing
    Chunked --> Embedded
    Chunked --> Failed
    Chunked --> Cancelled

    Embedded --> Processing
    Embedded --> Indexed
    Embedded --> Failed
    Embedded --> Cancelled

    Indexed --> Processing
    Indexed --> Ready
    Indexed --> Failed
    Indexed --> Cancelled

    Ready --> [*]
    Failed --> [*]
    Cancelled --> [*]
```

## Transition Validation

- State transitions are validated by `backend/domain/states.py`.
- Attempting illegal state transitions raises `InvalidTransition` (inherits from `DomainException`).
