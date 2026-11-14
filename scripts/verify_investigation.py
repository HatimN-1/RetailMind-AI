"""Real HTTP + optional Chrome/Edge regression checks, with isolated owned servers.

Uses the existing synthetic warehouse and cached embeddings, without indexing,
training or modifying transactions. Existing user servers are never stopped.
"""
from __future__ import annotations
import argparse
from contextlib import ExitStack
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def request(base, path, body=None, timeout=65):
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(base + path, data, {'Content-Type': 'application/json'})
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read().decode('utf-8')
        return response.status, json.loads(raw)


def free_port():
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def start(stack, command, cwd, env, log):
    stream = stack.enter_context(log.open('w', encoding='utf-8'))
    process = subprocess.Popen(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))

    def stop():
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)

    stack.callback(stop)
    return process


def wait_http(process, url, log):
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f'Test server exited. Inspect {log}')
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.2)
    raise TimeoutError(f'Test server not ready. Inspect {log}')


def http_checks(api, frontend):
    rows = []
    for label, base in [('direct', api), ('vite_proxy', frontend + '/api')]:
        status, health = request(base, '/health')
        assert status == 200 and health['warehouse_ready']
        rows.append({'case': label + '_health', 'status': status})
        for graph in [False, True]:
            status, data = request(base, '/investigate', {
                'question': 'Analyse la transaction TX-0003699', 'use_langgraph': graph})
            assert status == 200, data
            assert data['evidence'][0]['transaction_id'] == 'TX-0003699'
            assert data['sql_proofs'][0]['rows'] == data['evidence']
            assert data['workflow_backend'] == ('langgraph' if graph else 'sequential')
            assert data['retrieval_backend'] == 'qdrant' and len(data['steps']) == 9
            assert not data['ollama_attempted'] and not data['ollama_used']
            rows.append({'case': label + ('_graph' if graph else '_sequential'), 'status': status,
                         'mode': data['mode'], 'steps': len(data['steps']),
                         'sql_rows': len(data['evidence']), 'latency_ms': data['latency_ms']})
        status, data = request(base, '/investigate', {
            'question': 'Que vérifier après un échec Airflow ?', 'use_langgraph': True})
        assert status == 200 and data['sources']
        assert all('airflow' in s['source'] and s['score'] > 0 for s in data['sources'])
        assert not data['ollama_used']
        rows.append({'case': label + '_airflow', 'status': status, 'mode': data['mode'],
                     'sources': [s['source'] for s in data['sources']]})
        status, data = request(base, '/investigate', {'question': ' ', 'use_langgraph': True})
        assert status == 422 and isinstance(data['detail'], list)
        rows.append({'case': label + '_validation', 'status': status})
    return rows


def browser_checks(frontend, output, channel):
    from playwright.sync_api import sync_playwright, expect
    # Import only in the admin test runner, never in the investigation tool surface.
    from retailmind import retrieval
    errors, console, checks = [], [], []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel=channel, headless=True)
        try:
            context = browser.new_context(viewport={'width': 1440, 'height': 1100})
            page = context.new_page()
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            page.on('console', lambda message: console.append(message.text) if message.type == 'error' else None)
            page.goto(frontend, wait_until='domcontentloaded')
            native_scroll = page.evaluate('''() => {
                const value=document.body.scrollIntoView({behavior:'smooth'});
                return {thenable:typeof value?.then==='function',userAgent:navigator.userAgent};
            }''')
            # Regression remains meaningful on browsers where native scrolling returns void.
            context.add_init_script('''(() => {
                const original=Element.prototype.scrollIntoView;
                Element.prototype.scrollIntoView=function(...args) {
                    original.apply(this,args);
                    return Promise.resolve();
                };
            })();''')
            page.reload(wait_until='domcontentloaded')
            page.locator('nav button[title="Investigation IA"]').click()
            textbox = page.get_by_role('textbox', name='Question d’investigation')
            expect(textbox).to_be_visible()

            def submit(question):
                textbox.fill(question)
                with page.expect_response(lambda r: r.url.endswith('/api/investigate'), timeout=70000) as pending:
                    page.get_by_role('button', name='Envoyer', exact=True).click()
                response = pending.value
                expect(page.get_by_role('button', name='Envoyer', exact=True)).to_be_disabled()
                # Input is empty, so the button remains disabled after completion too.
                expect(page.locator('.messages')).to_have_attribute('aria-busy', 'false', timeout=70000)
                # A screenshot/assertion taken before smooth scrolling finishes can
                # still show the preceding reply while the evidence panel is updated.
                page.wait_for_function('''() => {
                    const box=document.querySelector('.messages');
                    const replies=box.querySelectorAll('.message.assistant .message-body');
                    const reply=replies[replies.length-1].getBoundingClientRect();
                    const viewport=box.getBoundingClientRect();
                    return reply.bottom<=viewport.bottom+1 && reply.bottom>=viewport.top;
                }''')
                return response

            transaction = submit('Analyse la transaction TX-0003699')
            data = transaction.json()
            assert transaction.status == 200 and data['mode'] == 'langgraph+qdrant+deterministic'
            assert transaction.request.post_data_json['use_langgraph'] is True
            expect(page.locator('.messages .investigation-report').last).to_contain_text('TX-0003699')
            expect(page.locator('.source-list')).to_contain_text('SELECT transaction_id')
            expect(page.locator('.workflow-steps li')).to_have_count(9)
            checks.append({'case': 'transaction_sql_rendered', 'http_status': transaction.status, 'mode': data['mode']})

            page.get_by_role('checkbox', name='Utiliser LangGraph').uncheck()
            sequential = submit('Analyse la transaction TX-0003699')
            assert sequential.json()['workflow_backend'] == 'sequential'
            assert sequential.request.post_data_json['use_langgraph'] is False
            checks.append({'case': 'sequential_request_and_render', 'http_status': sequential.status})
            page.get_by_role('checkbox', name='Utiliser LangGraph').check()

            airflow = submit('Que vérifier après un échec Airflow ?')
            assert airflow.status == 200 and airflow.json()['sources']
            report = page.locator('.messages .investigation-report').last
            for heading in ['FAITS OBSERVÉS', 'HYPOTHÈSES', 'VÉRIFICATIONS RECOMMANDÉES', 'SOURCES']:
                expect(report.get_by_role('heading', name=heading, exact=True)).to_be_visible()
            expect(report).to_contain_text('04_airflow_retry.md')
            expect(page.locator('.source-list')).to_contain_text('score')
            first_source = page.locator('.source-list > details').first
            first_source.locator('summary').click()
            with page.expect_response(lambda r: '/api/rag/documents/' in r.url) as pending:
                first_source.get_by_role('button', name='Consulter le document complet').click()
            assert pending.value.status == 200
            expect(page.locator('.runbook-text')).to_contain_text('retailmind_data_ml_pipeline')
            checks.append({'case': 'airflow_sources_scores_full_document', 'http_status': airflow.status})

            # Hold a genuine filesystem lock in this process while the independent API tries to read it.
            with retrieval._client():
                locked = submit('Que vérifier après un échec Airflow ?')
            assert locked.status == 200 and locked.json()['retrieval_backend'] == 'tfidf'
            assert locked.json()['retrieval_diagnostics'][0]['code'] == 'qdrant_locked'
            expect(page.locator('.messages .investigation-report').last).to_contain_text('verrouillé')
            checks.append({'case': 'actual_qdrant_lock_visible_fallback', 'http_status': locked.status,
                           'mode': locked.json()['mode']})

            # Backend-generated Pydantic validation error, with only the outgoing body changed by the test.
            def invalid_request(route):
                route.continue_(post_data=json.dumps({'question': ' ', 'use_langgraph': True}))

            page.route('**/api/investigate', invalid_request)
            invalid = submit('Question envoyée pour vérifier la validation')
            page.unroute('**/api/investigate', invalid_request)
            assert invalid.status == 422
            expect(page.get_by_role('alert').last).to_contain_text('question :')
            checks.append({'case': 'actual_pydantic_422_readable', 'http_status': invalid.status})

            # Controlled transport/contract failures exercise the UI; these are not claimed as real outages.
            failure_cases = [
                ('http_503', 503, {'detail': 'Entrepôt SQLite indisponible.', 'error_type': 'OperationalError',
                                  'correlation_id': 'test-browser-correlation'}, 'OperationalError'),
                ('http_504', 504, {'detail': 'Délai d’investigation dépassé.', 'error_type': 'TimeoutError'}, 'TimeoutError'),
                ('invalid_contract', 200, {'answer': 'incomplete'}, 'incompatible'),
            ]
            for label, status, body, expected in failure_cases:
                def simulated(route, _request, *, status=status, body=body):
                    route.fulfill(status=status, json=body)

                page.route('**/api/investigate', simulated)
                response = submit('Vérification contrôlée du message d’erreur')
                page.unroute('**/api/investigate', simulated)
                assert response.status == status
                expect(page.get_by_role('alert').last).to_contain_text(expected)
                checks.append({'case': label, 'controlled_response': True, 'http_status': status})

            with page.expect_response(lambda r: r.url.endswith('/api/investigate'), timeout=70000) as pending:
                page.get_by_role('button', name='Réessayer cette question').last.click()
            assert pending.value.status == 200
            expect(page.locator('.messages')).to_have_attribute('aria-busy', 'false', timeout=70000)
            expect(page.get_by_role('textbox', name='Question d’investigation')).to_be_visible()
            checks.append({'case': 'retry_real_request', 'http_status': pending.value.status})

            # StrictMode cleanup on navigation and updates also used to cause the white page.
            page.get_by_role('button', name='Changer le thème').click()
            page.locator('nav button[title="Vue exécutive"]').click()
            page.locator('nav button[title="Investigation IA"]').click()
            expect(textbox).to_be_visible()
            final = submit('Analyse la transaction TX-0003699')
            assert final.status == 200
            page.screenshot(path=str(output / 'investigation_light.png'), full_page=True)
            page.get_by_role('button', name='Changer le thème').click()
            page.screenshot(path=str(output / 'investigation_dark.png'), full_page=True)
            page.set_viewport_size({'width': 390, 'height': 844})
            # Wait for the existing sidebar/main-area CSS transitions before
            # checking the actual mobile layout or taking a full-page screenshot.
            page.wait_for_function('''() => {
                const area=document.querySelector('.main-area').getBoundingClientRect();
                return Math.abs(area.left)<1 && Math.abs(area.width-innerWidth)<1 &&
                    document.documentElement.scrollWidth<=innerWidth+1;
            }''')
            textbox.scroll_into_view_if_needed()
            expect(textbox).to_be_in_viewport()
            assert textbox.bounding_box()['width'] >= 100
            mobile = submit('Que vérifier après un échec Airflow ?')
            assert mobile.status == 200 and mobile.json()['sources']
            page.evaluate("window.scrollTo({top:0,left:0,behavior:'instant'})")
            page.wait_for_function('window.scrollY === 0')
            page.screenshot(path=str(output / 'investigation_mobile.png'), full_page=True)
            checks.append({'case': 'remount_themes_mobile', 'http_status': final.status,
                           'mobile_http_status': mobile.status})
            assert errors == [], errors
            assert not any('must not return' in message or 'destroy is not a function' in message for message in console)
            return {'native_scroll': native_scroll, 'promise_scroll_regression_enabled': True,
                    'page_errors': errors, 'console_errors': console, 'checks': checks,
                    'scope': 'Real UI/proxy/API/SQL/Qdrant without Ollama; controlled failures explicitly labelled.'}
        except Exception as exc:
            failure = {'error_type': type(exc).__name__, 'checks': checks,
                       'page_errors': errors, 'console_errors': console}
            if 'page' in locals() and not page.is_closed():
                page.screenshot(path=str(output / 'browser_failure.png'), full_page=True)
                failure['body'] = page.locator('body').inner_text()
            (output / 'browser_failure.json').write_text(json.dumps(failure, indent=2, ensure_ascii=False), encoding='utf-8')
            raise
        finally:
            browser.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', action='store_true')
    parser.add_argument('--channel', choices=['chrome', 'msedge'], default='chrome')
    parser.add_argument('--output', type=Path, default=ROOT / '.test-temp' / 'investigation-e2e')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    node = shutil.which('node')
    if not node:
        parser.error('Node.js is required to test the Vite proxy')
    api_url = f'http://127.0.0.1:{free_port()}'
    frontend_port = free_port()
    frontend_url = f'http://127.0.0.1:{frontend_port}'
    env = {**os.environ, 'RETAILMIND_RETRIEVAL': 'qdrant', 'RETAILMIND_OLLAMA_MODEL': ''}
    report = {'api_url': api_url, 'frontend_url': frontend_url, 'passed': False}
    with ExitStack() as stack:
        api_log, vite_log = output / 'api.log', output / 'vite.log'
        backend = start(stack, [sys.executable, '-m', 'uvicorn', 'retailmind.api:app', '--host', '127.0.0.1',
                               '--port', api_url.rsplit(':', 1)[1]], ROOT, env, api_log)
        wait_http(backend, api_url + '/health', api_log)
        vite = start(stack, [node, str(ROOT / 'frontend/node_modules/vite/bin/vite.js'), '--host', '127.0.0.1',
                            '--port', str(frontend_port), '--strictPort'], ROOT / 'frontend',
                     {**env, 'RETAILMIND_API_PROXY_TARGET': api_url, 'VITE_API_BASE': '/api'}, vite_log)
        wait_http(vite, frontend_url, vite_log)
        report['http'] = http_checks(api_url, frontend_url)
        print('Real HTTP checks passed', flush=True)
        try:
            if args.browser:
                # Keep the local admin client aligned with the isolated API configuration.
                os.environ.update({'RETAILMIND_RETRIEVAL': 'qdrant', 'RETAILMIND_OLLAMA_MODEL': ''})
                report['browser'] = browser_checks(frontend_url, output, args.channel)
            report['passed'] = True
        finally:
            (output / 'results.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    main()
