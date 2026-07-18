# API Endpoints Inventory

| Endpoint | Method | Input Payload | Output Payload | DB Touched | Redis Touched |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/files/upload` | POST | Form data (Multipart File) | File metadata json | Yes | No |
| `/pipelines` | POST | Pipeline parameters | Created pipeline metadata | Yes | Yes (Task queues) |
| `/search` | POST | `{query, top_k}` | Reranked result array | Yes | No |
| `/tasks/poll` | POST | Worker status/capabilities | Task payload or empty | Yes | Yes |
| `/tasks/<id>/claim` | POST | `{worker_id}` | Claim confirmation | Yes | No |
| `/tasks/<id>/renew-lease` | POST | `{lease_token, extend_by_seconds}` | Renewal status | Yes | No |
| `/metrics/system` | GET | None | Memory and CPU metrics | Yes | Yes |\n