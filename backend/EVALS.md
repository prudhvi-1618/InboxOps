# Evaluation Framework

## Overview
This document describes the evaluation framework for the Sales Inbox Task Router, measuring routing accuracy, hygiene classification precision/recall, priority calculation, and business entity extraction.

## Metrics
1. **Routing Accuracy**: Exact match of assigned sales rep (`assignee_id`) against ground truth.
2. **Hygiene Precision & Recall**: Accuracy in classifying `SPAM`, `NEWSLETTER`, `OUT_OF_OFFICE`, and `ACTIONABLE`.
3. **Priority Correctness**: Validation against the 72-hour timeline and high-value deal policies.
4. **Financial Extraction Precision**: Accurate parsing of Indian currency formats (`₹25L`, `1.2cr`, etc.).

## Evaluation Runner
Execute:
```bash
python -m tests.evals.evaluate
```
