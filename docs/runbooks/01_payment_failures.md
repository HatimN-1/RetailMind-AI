# Payment failures and declined transactions

Business domain: payments. When payment_status='failed', this is an observed transaction state,
not proof of fraud. Correlate exact transaction_id and timestamp, inspect payment gateway code,
verify retry count, idempotency key, token expiry and upstream availability.

Read-only diagnostic: compare payment failures by region and day, inspect recent anomalies.
Escalation: propose human review; NEVER automatically issue refunds, resend payment requests
or reset credentials based on a LLM explanation alone.

Synthetic data: a transaction may be labeled 'failed_high_value'. This is an injected test scenario.
