"""Additional API contract tests for the React frontend (all synthetic)."""
from fastapi.testclient import TestClient
from retailmind.api import app

client = TestClient(app)


def test_analytics_periods_and_totals():
    all_data = client.get('/analytics').json()
    seven = client.get('/analytics?period=7d').json()
    assert all_data['synthetic'] is True
    assert all_data['summary']['orders'] >= seven['summary']['orders'] > 0
    assert sum(x['orders'] for x in all_data['regions']) == all_data['summary']['orders']
    assert sum(x['count'] for x in all_data['anomaly_types']) == all_data['summary']['anomalies']


def test_transactions_pagination_search_and_sort():
    page = client.get('/transactions-page?limit=5&sort=amount_desc').json()
    assert len(page['items']) == 5
    assert page['total'] >= 5
    assert page['items'][0]['total_amount'] >= page['items'][1]['total_amount']
    ident = page['items'][0]['transaction_id']
    search = client.get('/transactions-page', params={'search': ident}).json()
    assert search['total'] == 1
    assert search['items'][0]['transaction_id'] == ident


def test_anomaly_pages_only_return_injected_labels():
    data = client.get('/alerts-page?limit=20').json()
    assert data['items']
    assert all(x['is_anomaly'] == 1 for x in data['items'])


def test_invalid_sort_rejected_and_cors_local_only():
    assert client.get('/transactions-page?sort=DROP%20TABLE').status_code == 422
    response = client.options('/analytics', headers={
        'Origin': 'http://localhost:5173',
        'Access-Control-Request-Method': 'GET',
    })
    assert response.headers.get('access-control-allow-origin') == 'http://localhost:5173'
