import pytest
from backend.domain.value_objects.document_id import DocumentId
from backend.domain.value_objects.page_number import PageNumber
from backend.domain.entities.page import Page
from backend.domain.aggregates.pipeline import Pipeline
from backend.domain.states import PipelineState, validate_transition
from backend.domain.exceptions.exceptions import ValidationError, InvalidTransition

def test_value_object_validation():
    with pytest.raises(ValidationError):
        DocumentId(0)
    with pytest.raises(ValidationError):
        DocumentId(-5)
    with pytest.raises(ValidationError):
        PageNumber(-1)

    doc_id = DocumentId(10)
    assert doc_id.value == 10
    assert doc_id.to_dict() == 10

def test_entity_serialization():
    page = Page(page_number=PageNumber(1), text="Hello World", metadata={"font": "Arial"})
    data = page.to_dict()
    assert data["page_number"] == 1
    assert data["text"] == "Hello World"
    assert data["metadata"] == {"font": "Arial"}

    page2 = Page.from_dict(data)
    assert page == page2

def test_invalid_state_transition():
    with pytest.raises(InvalidTransition):
        validate_transition(PipelineState.Ready, PipelineState.Processing)
    
    # Valid transition should not raise
    validate_transition(PipelineState.Uploaded, PipelineState.Processing)
