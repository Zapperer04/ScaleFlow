# Phase 5 — Recovery Rate, WER/CER, and Table Recovery Report

## Recovery Rate by Engine and Category

| Engine | Cat | Chars | Recovery | Keyword Hits |
| :--- | :--- | :--- | :--- | :--- |
| Tesseract | B | 142 | 100.0% | throughput, ledger, distributed |
| Tesseract | C | 142 | 100.0% | replication, nodes, reliability |
| Tesseract | D | 78 | 50.0% | test |
| Tesseract | E | 411 | 0.0% | none |
| Tesseract | F | 350 | 0.0% | none |
| Tesseract | G | 114 | 100.0% | john, handwriting |
| Tesseract | H | 49 | 50.0% | handwritten |
| PaddleOCR | B | 0 | 0.0% | none |
| PaddleOCR | C | 0 | 0.0% | none |
| PaddleOCR | D | 0 | 0.0% | none |
| PaddleOCR | E | 0 | 0.0% | none |
| PaddleOCR | F | 0 | 0.0% | none |
| PaddleOCR | G | 0 | 0.0% | none |
| PaddleOCR | H | 0 | 0.0% | none |
| EasyOCR | B | 133 | 100.0% | throughput, ledger, distributed |
| EasyOCR | C | 136 | 66.7% | nodes, reliability |
| EasyOCR | D | 130 | 100.0% | document, test |
| EasyOCR | E | 389 | 0.0% | none |
| EasyOCR | F | 345 | 0.0% | none |
| EasyOCR | G | 110 | 50.0% | john |
| EasyOCR | H | 48 | 0.0% | none |
| DocTR | B | 143 | 100.0% | throughput, ledger, distributed |
| DocTR | C | 113 | 100.0% | replication, nodes, reliability |
| DocTR | D | 130 | 100.0% | document, test |
| DocTR | E | 405 | 0.0% | none |
| DocTR | F | 346 | 0.0% | none |
| DocTR | G | 110 | 100.0% | john, handwriting |
| DocTR | H | 47 | 50.0% | handwritten |
| Surya | B | 67 | 0.0% | none |
| Surya | C | 67 | 0.0% | none |
| Surya | D | 67 | 0.0% | none |
| Surya | E | 67 | 0.0% | none |
| Surya | F | 67 | 0.0% | none |
| Surya | G | 67 | 0.0% | none |
| Surya | H | 67 | 0.0% | none |

## WER / CER by Engine and Category

> WER = Word Error Rate (substitution+deletion+insertion / reference words)
> CER = Character Error Rate (same formula at character level)
> Lower is better. N/A = ground truth empty or extraction empty.

| Engine | Cat | WER | CER | GT chars | Extracted chars |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Tesseract | B | N/A | N/A | 0 | 142 |
| Tesseract | C | N/A | N/A | 0 | 142 |
| Tesseract | D | N/A | N/A | 0 | 78 |
| Tesseract | E | N/A | N/A | 0 | 411 |
| Tesseract | F | 0.9996 | 0.9996 | 814991 | 350 |
| Tesseract | G | N/A | N/A | 0 | 114 |
| Tesseract | H | N/A | N/A | 0 | 49 |
| PaddleOCR | B | N/A | N/A | 0 | 0 |
| PaddleOCR | C | N/A | N/A | 0 | 0 |
| PaddleOCR | D | N/A | N/A | 0 | 0 |
| PaddleOCR | E | N/A | N/A | 0 | 0 |
| PaddleOCR | F | N/A | N/A | 814991 | 0 |
| PaddleOCR | G | N/A | N/A | 0 | 0 |
| PaddleOCR | H | N/A | N/A | 0 | 0 |
| EasyOCR | B | N/A | N/A | 0 | 133 |
| EasyOCR | C | N/A | N/A | 0 | 136 |
| EasyOCR | D | N/A | N/A | 0 | 130 |
| EasyOCR | E | N/A | N/A | 0 | 389 |
| EasyOCR | F | 0.9996 | 0.9996 | 814991 | 345 |
| EasyOCR | G | N/A | N/A | 0 | 110 |
| EasyOCR | H | N/A | N/A | 0 | 48 |
| DocTR | B | N/A | N/A | 0 | 143 |
| DocTR | C | N/A | N/A | 0 | 113 |
| DocTR | D | N/A | N/A | 0 | 130 |
| DocTR | E | N/A | N/A | 0 | 405 |
| DocTR | F | 0.9996 | 0.9996 | 814991 | 346 |
| DocTR | G | N/A | N/A | 0 | 110 |
| DocTR | H | N/A | N/A | 0 | 47 |
| Surya | B | N/A | N/A | 0 | 67 |
| Surya | C | N/A | N/A | 0 | 67 |
| Surya | D | N/A | N/A | 0 | 67 |
| Surya | E | N/A | N/A | 0 | 67 |
| Surya | F | 1.0000 | 0.9999 | 814991 | 67 |
| Surya | G | N/A | N/A | 0 | 67 |
| Surya | H | N/A | N/A | 0 | 67 |

## Table Recovery (Category F Only)

Expected table cells: `name, date, amount, total, authorization, description`

| Engine | Table Cell Recovery | Score |
| :--- | :--- | :--- |
| Tesseract |            | 0.0% |
| PaddleOCR |            | 0.0% |
| EasyOCR |            | 0.0% |
| DocTR |            | 0.0% |
| Surya |            | 0.0% |