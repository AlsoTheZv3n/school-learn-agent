"""LLM concerns: embeddings, completion client, anonymization, prompts.

Only embeddings exist at M2 (needed by content ingestion + semantic retrieval).
The completion client and PII anonymization arrive with the agent loop (AG-3, M3).
"""
