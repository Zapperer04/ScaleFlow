# Document Intelligence Hardening — Validation Report
**Date:** 2026-05-27 14:31:09

## Summary
| Category | File | Parse Status | Parser Used | Duration | Chunks |
|---|---|---|---|---|---|
| A | category_A_simple.pdf | Error | N/A | 0s | 0 |
| B | category_B_academic.pdf | Error | N/A | 0s | 0 |
| C | category_C_large.pdf | Error | N/A | 0s | 0 |
| D | category_D_scanned.pdf | Error | N/A | 0s | 0 |
| E | category_E_malformed.pdf | Error | N/A | 0s | 0 |

### Category A: Simple Text PDF
- **Status**: ERROR
- **Exception**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### Category B: Academic PDF (equations/references)
- **Status**: ERROR
- **Exception**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### Category C: Large PDF (50+ pages)
- **Status**: ERROR
- **Exception**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### Category D: Scanned/Image PDF
- **Status**: ERROR
- **Exception**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))

### Category E: Malformed/Corrupted PDF
- **Status**: ERROR
- **Exception**: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))