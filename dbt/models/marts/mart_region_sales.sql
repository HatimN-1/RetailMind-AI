select region, count(*) as orders, round(sum(case when payment_status='paid' then total_amount else 0 end), 2) as revenue_mad,
 sum(is_anomaly) as injected_anomalies
from {{ ref('stg_transactions') }}
group by region
