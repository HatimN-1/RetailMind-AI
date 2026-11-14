-- Run from dbt directory, after running the Python bootstrap.
select
  cast(transaction_id as varchar) as transaction_id,
  cast(day as date) as transaction_day,
  cast(region as varchar) as region,
  cast(category as varchar) as category,
  cast(channel as varchar) as channel,
  cast(payment_status as varchar) as payment_status,
  cast(quantity as integer) as quantity,
  cast(total_amount as double) as total_amount,
  cast(is_anomaly as integer) as is_anomaly,
  cast(anomaly_type as varchar) as anomaly_type
from read_csv_auto('../data/curated/transactions_clean.csv', header=true)
