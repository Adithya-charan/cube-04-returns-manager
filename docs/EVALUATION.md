# Evaluation Methodology

## Current Status

Evaluation has **not been measured**. No held-out 50-unit dataset, human labels, computed accuracy, error rates, agreement scores, or latency summary is present in this repository. The earlier failure-mode and latency claims in prior reports are unsupported and must not be treated as results.

`evaluation/evaluate.py` currently prints this status only; it does not execute an evaluation pipeline.

## Command
Run the status check with:
```bash
python evaluation/evaluate.py
```

To report results, first collect the held-out cases and two independent labels, record the inference outputs and timing, then calculate per-check accuracy, false positives/negatives, uncertainty/review rate, and human agreement. Do not infer performance from unit tests or a single image.
