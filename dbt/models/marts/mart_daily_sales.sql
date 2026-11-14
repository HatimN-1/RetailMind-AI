select transaction_day, count(*) as orders,
 round(sum(case when payment_status='paid' then total_amount else 0 end), 2) as revenue_mad,
 sum(case when payment_status='failed' then 1 else 0 end) as failed_payments,
 sum(is_anomaly) as injected_anomalies
from {{ ref('stg_transactions') }}
group by transaction_day
