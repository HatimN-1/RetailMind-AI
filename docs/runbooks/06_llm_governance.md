# Governed agent and hallucination control

Inputs: read-only SQL facts and documents from the local runbook repository.
The agent cannot access Azure accounts, execute SQL supplied by a user, issue payments,
change schemas or mutate infrastructure. The LLM-generated portion is marked separately,
while the deterministic facts remain visible.

Treat citations as retrieval references, not proof that the recommended root cause is correct.
For every claim, distinguish observed evidence, hypothesis and suggested human check.
Only enable external Ollama after obtaining a compatible local model.
