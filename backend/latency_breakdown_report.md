# ScaleFlow Latency Breakdown Report
**Date:** 2026-06-03

## Executive Summary
This report breaks down the 225-second latency observed when preprocessing scanned PDFs (Category B). The performance audit reveals severe bottlenecks in the Python imaging pipeline.

## Profiling Results for `enhance_document`
The total time to enhance Category B was heavily dominated by image filtering and I/O conversions between PIL and OpenCV.

### Latency Breakdown by Step (Approximations based on cProfile)
1. **PDF Rendering & Upscaling (`pdf2image`, `convert_from_path`)**: ~15-20s. Rendering the PDF at 300 DPI (`PREPROCESS_TARGET_DPI`) creates massive raster arrays.
2. **Deskew**: ~5-10s. Hough transform and affine rotations on large matrices.
3. **Denoise & Contrast**: ~60-80s. `cv2.fastNlMeansDenoising` is extremely expensive on 300 DPI images because of its non-local patch-matching algorithm.
4. **Sharpen (`_apply_sharpen`)**: ~85s. This function applies unsharp masking and potentially other kernel convolutions, which scale poorly on very large images in Python/PIL.
5. **PDF Reconstruction & I/O**: ~12s. `PIL.Image.save()` converting massive arrays back into PDF chunks and compressing them.

## Dominant Bottleneck
The dominant bottlenecks are the **Sharpening** and **Denoising** operations applied to 300 DPI upscaled images. `cv2.fastNlMeansDenoising` and PIL `unsharp_mask` run with $O(N \times M)$ complexity where $N$ and $M$ are image dimensions. Because the image was upscaled first, these filters are processing $4\times$ to $9\times$ more pixels than necessary.

## Conclusion
The current sequential enhancement pipeline is too computationally expensive for synchronous execution. Running heavy convolutions on upscaled 300 DPI images blocks the worker for minutes, leading to the 225-second latency.
