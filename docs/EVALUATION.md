# Evaluation Methodology

## Procedure
The Evaluation Framework runs the internal `DecisionEngine` natively separated from API endpoint limits, comparing the generated `DecisionRecord` results against verified independent Human Subject Matter Expert (SME) Ground Truth labels.

Two human operators independently label each of the 50 "unseen" (non-development) physical packages creating deterministic Ground Truth for Identity, Completeness, and Condition. Dispositions are calculated automatically via system mapping rules based on these ground truths. 

## Command
You may evaluate the system metrics locally using:
```bash
python evaluation/evaluate.py
```

## Failure Mode Profiling
Current baseline metrics reveal safely operating failure boundaries focusing on False Positives / Uncertainty over False Negatives:
1. **Low Visibility Boundaries**: Small parts (like USB adaptors) frequently drop below Vision models confidence thresholds invoking safe `UNCERTAIN` limits routing to `pending_review` reliably rather than incorrectly marking `MISSING`.
2. **Surface Defect False Positives**: Reflections on glossy finishes can sometimes trigger surface-scratch detections lowering condition tags unnecessarily. This requires Human Override tuning.
