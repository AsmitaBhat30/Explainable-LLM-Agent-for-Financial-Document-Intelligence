Run the RAG pipeline evaluation suite and report quality metrics.

```bash
python scripts/run_evaluation.py 2>&1
```

The evaluation measures:
- **Faithfulness**: does the answer stay within retrieved context?
- **Citation coverage**: are all cited documents actually retrieved?
- **Compliance accuracy**: is the risk level correctly classified?
- **Latency**: end-to-end response time

After running, report:
1. Each metric with its score
2. Which test cases failed and why (see `evaluation/test_cases.py`)
3. Any regressions compared to previous runs if a baseline exists
4. Recommended next steps if scores are below threshold