# Interface Inventory

- **Parser Interface**: Implemented via functional mapping in `pdf_parser.py`.
  - *Stable?*: No. | *ISP Violation?*: Yes. | *Split?*: Yes, separate parser into explicit digital vs OCR classes.
- **Embedding Interface**: Defined in `embedding_service.py`.
  - *Stable?*: Yes. | *ISP Violation?*: No.
- **Vector Store Interface**: Defined in `vector_store.py`.
  - *Stable?*: Yes. | *ISP Violation?*: No.\n