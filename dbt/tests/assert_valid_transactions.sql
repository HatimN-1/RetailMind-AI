-- dbt singular test: every returned row means a failed quality rule.
select transaction_id
from {{ ref('stg_transactions') }}
where quantity <= 0
   or total_amount < 0
   or is_anomaly not in (0, 1)
   or payment_status not in ('paid', 'failed', 'pending')
