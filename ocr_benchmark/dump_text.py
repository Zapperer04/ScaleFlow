from pathlib import Path
for eng in ['Tesseract', 'EasyOCR', 'DocTR']:
    for cat in ['B', 'C', 'E', 'G']:
        p = Path(f'ocr_benchmark/extracted/{eng}_{cat}.txt')
        text = p.read_text('utf-8') if p.exists() else 'N/A'
        print(f'\n--- {eng} {cat} ---')
        print(text[:250].replace('\n', ' '))
