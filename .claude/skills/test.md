Run the test suite with coverage and report results.

```bash
pytest tests/ -v --cov=. --cov-report=term-missing 2>&1
```

If the user specifies a scope, run:
- Unit only: `pytest tests/unit/ -v`
- Integration only: `pytest tests/integration/ -v`
- Specific file: `pytest tests/path/to/test_file.py -v`

After running, report:
1. Total passed / failed / errors
2. Coverage percentage per module
3. Full tracebacks for any failures
4. Any tests that were skipped and why