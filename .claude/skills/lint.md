Run the full linting and type-checking suite (black, flake8, mypy) and report any failures.

```bash
echo "=== black ===" && black --check . 2>&1
echo "=== flake8 ===" && flake8 . 2>&1
echo "=== mypy ===" && mypy . --ignore-missing-imports 2>&1
```

If black reports files would be reformatted, run `black .` to fix them, then re-run the check.
Report a summary: which tools passed, which failed, and the specific errors for failures.