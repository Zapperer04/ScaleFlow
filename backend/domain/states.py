from enum import Enum
from typing import Set, Dict
from backend.domain.exceptions.exceptions import InvalidTransition

class PipelineState(str, Enum):
    Uploaded = "Uploaded"
    Processing = "Processing"
    Preprocessed = "Preprocessed"
    Parsed = "Parsed"
    Chunked = "Chunked"
    Embedded = "Embedded"
    Indexed = "Indexed"
    Ready = "Ready"
    Failed = "Failed"
    Cancelled = "Cancelled"

# Define allowable transitions
VALID_TRANSITIONS: Dict[PipelineState, Set[PipelineState]] = {
    PipelineState.Uploaded: {
        PipelineState.Processing,
        PipelineState.Preprocessed,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Processing: {
        PipelineState.Preprocessed,
        PipelineState.Parsed,
        PipelineState.Chunked,
        PipelineState.Embedded,
        PipelineState.Indexed,
        PipelineState.Ready,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Preprocessed: {
        PipelineState.Processing,
        PipelineState.Parsed,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Parsed: {
        PipelineState.Processing,
        PipelineState.Chunked,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Chunked: {
        PipelineState.Processing,
        PipelineState.Embedded,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Embedded: {
        PipelineState.Processing,
        PipelineState.Indexed,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Indexed: {
        PipelineState.Processing,
        PipelineState.Ready,
        PipelineState.Failed,
        PipelineState.Cancelled,
    },
    PipelineState.Ready: set(),  # Terminal
    PipelineState.Failed: set(),  # Terminal
    PipelineState.Cancelled: set(),  # Terminal
}

def validate_transition(current: PipelineState, target: PipelineState) -> None:
    if current == target:
        return
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransition(f"Illegal transition from {current.value} to {target.value}")
