Query the financial document intelligence system and display the full response with citations and compliance risk.

If the API server is running:
```bash
curl -s -X POST http://localhost:8000/query/stream \
  -H "Authorization: Bearer dev-token-12345" \
  -H "Content-Type: application/json" \
  -d '{"query": "<USER_QUERY>", "top_k": 5, "include_compliance_check": true}'
```

If the server is not running, use the script directly:
```bash
python scripts/query_system.py --query "<USER_QUERY>"
```

Display the response showing:
- The answer text
- All citations (doc_id, section, page_range)
- Confidence score
- Compliance risk level (HIGH / MEDIUM / LOW)
- Any potential risks flagged
- Latency

Remind the user that `dev-token-12345` is a development token only and must not be used in production.