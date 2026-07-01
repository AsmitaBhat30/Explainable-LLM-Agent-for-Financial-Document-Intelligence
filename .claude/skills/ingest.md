Run the full document ingestion and embedding pipeline.

Steps:
1. Parse PDFs: `python ingestion/process_documents.py`
2. Validate quality: `python validation/run_checks.py`
3. Embed and index: `python transformation/embed_all_documents.py`

Run each step in sequence. After each step, check for errors before continuing.
Report: how many documents were processed, how many passed validation, how many chunks were embedded, and any failures with their reasons (missing metadata fields, text too short, etc.).

If the user specifies a single document, run: `python ingestion/process_documents.py --file <path>`