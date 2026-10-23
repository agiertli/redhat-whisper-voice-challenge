"""No cluster, credentials, registry or container engine required."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
HELM = shutil.which('helm')


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cluster = load('cluster', 'scripts/check-cluster.py')


def fixture_db(path):
    with contextlib.closing(sqlite3.connect(path)) as db:
        db.execute("PRAGMA journal_mode=DELETE")
        for name in ('players', 'games', 'attempts'):
            db.execute('CREATE TABLE ' + name + ' (id INTEGER PRIMARY KEY)')
        db.execute('INSERT INTO players VALUES (1)')
        db.commit()


class ChartTests(unittest.TestCase):
    def render(self, *args, success=True):
        result = subprocess.run([HELM, 'template', 'whisper', str(ROOT / 'helm/whisper'),
                                 '--namespace', 'venue', '--set', 'game.requiredLanguage=cs',
                                 '--set', 'tournament.secret=test-signing-secret-which-is-at-least-32-chars',
                                 '--set', 'tournament.adminToken=test-admin-password', *args],
                                capture_output=True, text=True)
        if not success:
            self.assertNotEqual(result.returncode, 0)
            return result
        self.assertEqual(result.returncode, 0, result.stderr)
        return {doc['kind']: doc for doc in yaml.safe_load_all(result.stdout)
                if doc and doc['kind'] in ('Deployment', 'ConfigMap', 'Secret', 'Job', 'PersistentVolumeClaim')}

    def test_sqlite_initializes_before_workers_fork(self):
        self.assertIn('--preload', self.render()['ConfigMap']['data']['GUNICORN_CMD_ARGS'])

    def test_registration_mode_is_explicit_and_validated(self):
        self.assertEqual(self.render()['ConfigMap']['data']['REGISTRATION_MODE'], 'full')
        self.assertEqual(self.render('--set', 'registration.mode=username')['ConfigMap']['data']['REGISTRATION_MODE'], 'username')
        self.render('--set', 'registration.mode=anonymous', success=False)

    def test_unused_win_count_setting_is_not_deployed(self):
        config = self.render('--set', 'game.winThreshold=999')['ConfigMap']['data']
        self.assertNotIn('WIN_THRESHOLD', config)
        self.assertEqual(config['CHALLENGE_COUNT'], '5')

    def test_tournament_flag_defaults_true_and_false_preserves_storage(self):
        enabled=self.render()
        disabled=self.render('--set','tournament.enabled=false')
        self.assertEqual(enabled['ConfigMap']['data']['TOURNAMENT_ENABLED'],'true')
        self.assertEqual(disabled['ConfigMap']['data']['TOURNAMENT_ENABLED'],'false')
        self.assertEqual(enabled['PersistentVolumeClaim'],disabled['PersistentVolumeClaim'])
        self.assertEqual(enabled['Secret'],disabled['Secret'])
        self.assertEqual(enabled['Deployment']['spec']['template']['spec']['volumes'],disabled['Deployment']['spec']['template']['spec']['volumes'])
        self.assertNotEqual(enabled['Deployment']['spec']['template']['metadata']['annotations']['checksum/config'],disabled['Deployment']['spec']['template']['metadata']['annotations']['checksum/config'])
        self.render('--set-string','tournament.enabled=false',success=False)

    def test_owner_must_choose_language(self):
        self.render('--set', 'game.requiredLanguage=', success=False)

    def test_unknown_language_rejected(self):
        self.render('--set', 'game.requiredLanguage=zz', success=False)

    def test_namespace_applies_to_every_resource(self):
        for document in self.render().values():
            self.assertEqual(document['metadata']['namespace'], 'venue')

    def test_language_change_rolls_ui(self):
        before = self.render()
        after = self.render('--set', 'game.requiredLanguage=en')
        self.assertEqual(after['ConfigMap']['data']['REQUIRED_CHALLENGE_LANGUAGE'], 'en')
        self.assertNotEqual(before['Deployment']['spec']['template']['metadata']['annotations'],
                            after['Deployment']['spec']['template']['metadata']['annotations'])

    def test_credential_rotation_rolls_ui(self):
        before = self.render()
        after = self.render('--set', 'tournament.adminToken=rotated-admin-password')
        key = 'checksum/credentials'
        self.assertNotEqual(before['Deployment']['spec']['template']['metadata']['annotations'][key],
                            after['Deployment']['spec']['template']['metadata']['annotations'][key])

    def test_secret_checksum_matches_rendered_keys(self):
        docs = self.render('--set', 'tournament.secret=', '--set', 'tournament.adminToken=')
        # Exact YAML serialization matters: helper uses Helm's alphabetic key order.
        import hashlib
        keys = docs['Secret']['stringData']
        serialized = '\n'.join(k + ': ' + keys[k] for k in sorted(keys))
        expected = hashlib.sha256(serialized.encode()).hexdigest()
        actual = docs['Deployment']['spec']['template']['metadata']['annotations']['checksum/credentials']
        self.assertEqual(actual, expected)
        other = self.render('--set', 'tournament.secret=', '--set', 'tournament.adminToken=')
        self.assertNotEqual(keys, other['Secret']['stringData'])

    def test_invalid_replica_gpu_image_and_pool_rejected(self):
        for value in ('replicaCount=2', 'gpu.memoryUtilization=0.3', 'image.tag=latest',
                      'difficultyPools={}', 'game.challengeCount=0'):
            with self.subTest(value=value):
                self.render('--set-string', value, success=False)

    def test_warmup_http_failure_fails_job(self):
        code = self.render()['Job']['spec']['template']['spec']['containers'][0]['command'][2]
        with patch('urllib.request.urlopen', side_effect=OSError('test backend failure')):
            with self.assertRaises(SystemExit):
                exec(compile(code, '<warmup>', 'exec'), {})

    def test_warmup_malformed_response_fails_job(self):
        code = self.render()['Job']['spec']['template']['spec']['containers'][0]['command'][2]
        with patch('urllib.request.urlopen', return_value=io.BytesIO(b'{"error":"bad"}')):
            with self.assertRaises(SystemExit):
                exec(compile(code, '<warmup>', 'exec'), {})

    def test_pvc_has_deletion_guard(self):
        self.assertEqual(self.render()['PersistentVolumeClaim']['metadata']['annotations']['helm.sh/resource-policy'], 'keep')

    def test_cluster_rbac_names_include_namespace(self):
        result = subprocess.check_output([HELM, 'template', 'whisper', str(ROOT / 'helm/whisper'),
                                          '--namespace', 'another-venue', '--set', 'game.requiredLanguage=en'], text=True)
        for doc in yaml.safe_load_all(result):
            if doc and doc['kind'] in ('ClusterRole', 'ClusterRoleBinding'):
                self.assertIn('another-venue', doc['metadata']['name'])
                if doc['kind'] == 'ClusterRoleBinding' and doc['roleRef']['name'] != 'cluster-monitoring-view':
                    self.assertIn('another-venue', doc['roleRef']['name'])

    def test_custom_storage_class(self):
        pvc = self.render('--set', 'tournament.storageClass=fast')['PersistentVolumeClaim']
        self.assertEqual(pvc['spec']['storageClassName'], 'fast')


class MonitoringTests(unittest.TestCase):
    def render(self, configuration, success=True):
        obj = {'apiVersion': 'v1', 'kind': 'ConfigMap',
               'metadata': {'name': 'cluster-monitoring-config', 'namespace': 'openshift-monitoring',
                            'resourceVersion': '123', 'annotations': {'owner': 'preserve'}},
               'data': {'config.yaml': configuration, 'other-key': 'preserve'}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as stream:
            json.dump(obj, stream)
            stream.flush()
            result = subprocess.run([HELM, 'template', 'monitoring-prerequisite',
                                     str(ROOT / 'helm/monitoring-prerequisite'), '--set-file',
                                     'existing=' + stream.name], capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return list(yaml.safe_load_all(result.stdout))[0] if result.stdout.strip() else None

    def test_preserves_unrelated_settings_metadata_and_resource_version(self):
        result = self.render('enableUserWorkload: false\nprometheusK8s:\n  retention: 7d\n')
        config = yaml.safe_load(result['data']['config.yaml'])
        self.assertTrue(config['enableUserWorkload'])
        self.assertEqual(config['prometheusK8s']['retention'], '7d')
        self.assertEqual(result['data']['other-key'], 'preserve')
        self.assertEqual(result['metadata']['resourceVersion'], '123')
        self.assertEqual(result['metadata']['annotations']['owner'], 'preserve')

    def test_already_enabled_has_no_update(self):
        self.assertIsNone(self.render('enableUserWorkload: true\nprometheusK8s: {}'))

    def test_json_style_monitoring_config_is_supported(self):
        result = self.render('{"enableUserWorkload": false, "prometheusK8s": {"retention": "7d"}}')
        self.assertTrue(yaml.safe_load(result['data']['config.yaml'])['enableUserWorkload'])

    def test_invalid_existing_config_fails_without_replacement(self):
        self.render('prometheusK8s: [invalid', success=False)


class InferenceChecksTests(unittest.TestCase):
    def test_manual_warmup_propagates_failure(self):
        code = (ROOT / 'scripts/warmup-vllm.sh').read_text().split("<<'PY'\n", 1)[1].rsplit('\nPY', 1)[0]
        with patch('sys.argv', ['warmup', 'http://fake.test', 'whisper']):
            with patch('urllib.request.urlopen', side_effect=OSError('test failure')):
                with self.assertRaises(SystemExit):
                    exec(compile(code, '<manual-warmup>', 'exec'), {})

    def smoke(self, stream, expected='cs', metrics=None, mode=None, page=None, enabled=None, public_tournament=False):
        class Response(io.BytesIO):
            status = 200
        def urlopen(request, timeout):
            url = request if isinstance(request, str) else request.full_url
            if url.endswith('/metrics'):
                return Response(json.dumps(metrics() if callable(metrics) else metrics if metrics is not None else {'vram_used': 20, 'temperature': 50, 'requests_processed': 1, 'vllm_generation_tokens': 10}).encode())
            if enabled is False and url.endswith(('/tv','/api/leaderboard')) and not public_tournament:
                import urllib.error
                raise urllib.error.HTTPError(url,404,'disabled',{},None)
            if url.endswith('/api/leaderboard'):
                return Response(b'{"leaderboard": []}')
            if url.endswith('/transcribe-stream'):
                return Response(stream)
            return Response(page if page is not None else b"const REQUIRED_LANGUAGE = 'cs';")
        with patch('urllib.request.urlopen', side_effect=urlopen):
            with patch('sys.argv', ['smoke', expected] + ([mode or '', str(enabled).lower()] if enabled is not None else [mode] if mode else [])), patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(b'RIFFtest'))):
                with contextlib.redirect_stdout(io.StringIO()):
                    exec(compile((ROOT / 'scripts/smoke-test.py').read_text(), '<smoke>', 'exec'), {})

    def test_smoke_accepts_completed_nonempty_transcription(self):
        self.smoke(b'data: {"text":"hello"}\n\ndata: {"done":true}\n\n')

    def test_smoke_rejects_empty_and_incomplete_transcription(self):
        for stream in (b'data: {"done":true}\n\n', b'data: {"text":"hello"}\n\n'):
            with self.subTest(stream=stream), self.assertRaises(SystemExit):
                self.smoke(stream)

    def test_smoke_tolerates_first_scrape_before_counter_increase(self):
        samples = iter([{}, {}, {}, {'vram_used': 20, 'temperature': 50, 'requests_processed': 1, 'vllm_generation_tokens': 10}])
        with patch('time.sleep'), patch('time.monotonic', side_effect=range(20)):
            self.smoke(b'data: {"text":"hello"}\n\ndata: {"done":true}\n\n', metrics=lambda: next(samples))

    def test_smoke_rejects_unusable_required_monitoring(self):
        with patch('time.monotonic', side_effect=[0, 121]):
            with self.assertRaises(SystemExit):
                self.smoke(b'data: {"text":"hello"}\n\ndata: {"done":true}\n\n', metrics={})

    def test_smoke_checks_actual_registration_mode_and_form(self):
        stream = b'data: {"text":"hello"}\n\ndata: {"done":true}\n\n'
        page = b'const REQUIRED_LANGUAGE = \'cs\'; const REGISTRATION_MODE = "username"; <input id="regUsername">'
        self.smoke(stream, mode='username', page=page)
        with self.assertRaisesRegex(SystemExit, 'wrong registration mode'):
            self.smoke(stream, mode='full', page=page)
        with self.assertRaisesRegex(SystemExit, 'form does not match'):
            self.smoke(stream, mode='username', page=page + b'<input id="regEmail">')

    def test_smoke_standalone_requires_disabled_public_surfaces_and_no_registration(self):
        page=b"const REQUIRED_LANGUAGE = 'cs'; const REGISTRATION_MODE = \"username\"; const TOURNAMENT_ENABLED = false;"
        stream=b'data: {"text":"hello"}\n\ndata: {"done":true}\n\n'
        self.smoke(stream,mode='username',page=page,enabled=False)
        with self.assertRaisesRegex(SystemExit,'exposes tournament surface'):
            self.smoke(stream,mode='username',page=page,enabled=False,public_tournament=True)
        with self.assertRaisesRegex(SystemExit,'exposes registration'):
            self.smoke(stream,mode='username',page=page+b'<form action="/api/register">',enabled=False)

    def test_smoke_rejects_stale_language(self):
        with self.assertRaises(SystemExit):
            self.smoke(b'', expected='en')


class ClusterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.operators = {'items': [{'metadata': {'name': 'rhods-operator.3.5.1'}, 'spec': {'version': '3.5.1'}, 'status': {'phase': 'Succeeded'}}]}
        self.nodes = {'items': [{'metadata': {'name': 'sno', 'labels': {'nvidia.com/gpu.present': 'true'}},
                                'status': {'allocatable': {'nvidia.com/gpu': '1'},
                                           'conditions': [{'type': 'Ready', 'status': 'True'}]}}]}
        self.storage = {'items': [{'metadata': {'name': 'default', 'annotations': {
            'storageclass.kubernetes.io/is-default-class': 'true'}}}]}
        self.pods = {'items': []}
        self.pvc = {}
        self.storage_class = ''

    def check(self, free=False):
        for name in ('operators', 'nodes', 'storage', 'pods', 'pvc'):
            (self.directory / (name + '.json')).write_text(json.dumps(getattr(self, name)))
        (self.directory / 'storage-class').write_text(self.storage_class)
        with contextlib.redirect_stdout(io.StringIO()):
            cluster.check(self.directory, 'venue', 'whisper', free)

    def pod(self, namespace='other', service='other', node='sno'):
        return {'metadata': {'namespace': namespace, 'name': 'predictor', 'labels': {
            'serving.kserve.io/inferenceservice': service}},
            'spec': {'nodeName': node, 'containers': [{'resources': {'limits': {'nvidia.com/gpu': '1'}}}]}}

    def test_wrong_operator_version_fails(self):
        self.operators['items'][0]['spec']['version'] = '2.9.0'
        with self.assertRaisesRegex(ValueError, 'OpenShift AI 3'):
            self.check()

    def test_ready_cluster(self):
        self.check()

    def test_gpu_not_ready(self):
        self.nodes['items'][0]['status']['conditions'][0]['status'] = 'False'
        with self.assertRaisesRegex(ValueError, 'No Ready'):
            self.check()

    def test_other_gpu_consumer_blocks_install(self):
        self.pods['items'] = [self.pod()]
        with self.assertRaisesRegex(ValueError, 'No GPU free'):
            self.check(True)

    def test_only_exact_rhdp_llama_is_allowed(self):
        self.pods['items'] = [self.pod('my-first-model', 'llama-32-3b-instruct')]
        with self.assertRaises(ValueError):
            self.check(False)
        self.check(True)

    def test_existing_whisper_can_upgrade(self):
        self.pods['items'] = [self.pod('venue', 'whisper')]
        self.check()

    def test_pending_competitor_blocks_install(self):
        self.pods['items'] = [self.pod(node='')]
        with self.assertRaisesRegex(ValueError, 'pending'):
            self.check()

    def test_no_storage_blocks_first_install(self):
        self.storage['items'] = []
        with self.assertRaisesRegex(ValueError, 'StorageClass'):
            self.check()
        self.pvc = {'metadata': {'name': 'whisper-tournament-db'}}
        self.check()

    def test_explicit_storage_class(self):
        self.storage_class = 'missing'
        with self.assertRaises(ValueError):
            self.check()
        self.storage_class = 'default'
        self.check()


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        self.fixture = self.directory / 'source.db'
        fixture_db(self.fixture)
        self.bin = self.directory / 'bin'
        self.bin.mkdir()
        # Curl is faked; no network/TLS connections are made by these tests.
        (self.bin / 'curl').write_text('''#!/bin/bash
if [[ "$*" == *secret-test-token* ]]; then exit 90; fi
while (($#)); do
  case "$1" in
    --output) output=$2; shift 2 ;;
    --config) config=$2; shift 2 ;;
    *) shift ;;
  esac
done
[[ $(< "$config") == *"Bearer secret-test-token"* ]] || exit 91
cp "$PAYLOAD" "$output"
''')
        for dependency in ('python3', 'oc', 'jq', 'sqlite3'):
            (self.bin / dependency).write_text('#!/bin/bash\nexit 92\n')
        (self.bin / 'sleep').write_text('#!/bin/bash\nexit 0\n')
        for item in self.bin.iterdir():
            item.chmod(0o755)
        self.token = self.directory / 'token'
        self.token.write_text('secret-test-token')
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        WHISPER_URL='https://test.example', ADMIN_TOKEN_FILE=str(self.token),
                        BACKUP_DIR=str(self.directory / 'backups'), KEEP_BACKUPS='1',
                        PAYLOAD=str(self.fixture))

    def run_backup(self, *args, success=True):
        result = subprocess.run(['bash', str(ROOT / 'scripts/backup.sh'), *args],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        self.assertNotIn('secret-test-token', result.stdout + result.stderr)
        return result

    def test_download_verified_and_private(self):
        self.run_backup()
        path = next((self.directory / 'backups').glob('tournament-*.db'))
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.read_bytes(), self.fixture.read_bytes())
        self.assertEqual(list(path.parent.glob('.whisper.*')), [])

    def test_bad_download_never_prunes_previous(self):
        self.run_backup()
        previous = next((self.directory / 'backups').glob('tournament-*.db'))
        bad = self.directory / 'bad'
        self.env['PAYLOAD'] = str(bad)
        for content in (b'<html>login failed</html>', self.fixture.read_bytes()[:100], b''):
            with self.subTest(size=len(content)):
                bad.write_bytes(content)
                self.run_backup(success=False)
                self.assertTrue(previous.exists())
                self.assertEqual(list(previous.parent.glob('.whisper.*')), [])

    def test_retention_keeps_new_snapshot_even_same_second(self):
        for _ in range(4):
            self.run_backup()
        paths = list((self.directory / 'backups').glob('tournament-*.db'))
        self.assertEqual(len(paths), 1)

    def test_standalone_validation(self):
        self.run_backup('--validate', str(self.fixture))

    def test_insecure_url_is_rejected(self):
        self.env['WHISPER_URL'] = 'http://test.example'
        self.run_backup(success=False)


# A fake oc always precedes the real CLI. Real Helm is used only for local rendering.
MOCK_OC = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
args = sys.argv[1:]
with open(os.environ['CALL_LOG'], 'a') as f:
    f.write(json.dumps(args) + '\n')
if args[:1] == ['--context']: args = args[2:]
scenario = os.environ.get('SCENARIO', '')
if scenario == 'api-failure' and args[:2] == ['get', 'nodes']:
    sys.exit(17)
if scenario == 'patch-failure' and args[0] == 'patch':
    sys.exit(18)
if scenario == 'wait-failure' and args[0] == 'wait':
    sys.exit(19)
if args[:2] == ['config', 'current-context']:
    print('mock-context')
elif args[:2] == ['auth', 'can-i']:
    print('yes')
elif args[:2] == ['whoami', '--show-server']:
    print('https://fake.test')
elif args[0] == 'api-resources':
    print('routes.route.openshift.io')
elif args[0] == 'whoami':
    print('test-admin')
elif args[:2] == ['get', 'csv']:
    print(Path(os.environ['FIXTURES'], 'operators.json').read_text())
elif args[:2] == ['get', 'nodes']:
    print(Path(os.environ['FIXTURES'], 'nodes.json').read_text())
elif args[:1] == ['exec']:
    payload=sys.stdin.buffer.read()
    command=args[args.index('--')+1:]
    count=int(command[3])
    assert len(command[2]) < 200, 'exec URL must not contain the entire smoke script'
    assert payload[count:count+4] == b'RIFF', 'script byte framing must preserve WAV input'
    if scenario == 'exec-transport-once':
        marker=Path(os.environ['FIXTURES'])/'exec-retried'
        if not marker.exists():
            marker.touch();print('error: remote error: tls: bad record MAC',file=sys.stderr);sys.exit(1)
    if scenario == 'exec-check-failure':
        print('ERROR: Running UI has the wrong required language',file=sys.stderr);sys.exit(1)
elif args[:2] == ['get', 'storageclasses']:
    print(Path(os.environ['FIXTURES'], 'storage.json').read_text())
elif args[:2] == ['get', 'pods'] and '-A' in args:
    print('{"items": []}')
elif args[:2] == ['get', 'inferenceservice']:
    if scenario != 'llama-absent': print('inferenceservice.serving.kserve.io/llama-32-3b-instruct')
elif args[:2] == ['get', 'deployment'] and '-o' in args and args[args.index('-o') + 1] == 'name':
    if 'llama-32-3b-instruct-predictor' in args: print('deployment.apps/llama-32-3b-instruct-predictor')
    elif scenario.startswith('upgrade'): print('deployment.apps/whisper-ui')
elif args[:2] == ['get', 'deployment'] and scenario.startswith('upgrade'):
    print('whisper')
elif args[:2] == ['get', 'secret'] and scenario == 'upgrade-backup-failure':
    sys.exit(24)
elif args[:2] == ['get', 'secret']:
    print('mock-admin-password')
elif args[:2] == ['get', 'pods'] and scenario in ('wait-failure', 'pods-remain'):
    print('pod/llama-still-running')
elif args[:2] == ['get', 'statefulset']:
    print('statefulset.apps/prometheus-user-workload')
elif args[:2] == ['get', 'route']:
    print('whisper.fake.test')
'''
MOCK_HELM = r'''#!/usr/bin/env python3
import os, subprocess, sys, json
args = sys.argv[1:]
if args[0] == 'upgrade':
    with open(os.environ['CALL_LOG'], 'a') as f: f.write('HELM-UPGRADE ' + json.dumps(args) + '\n')
    sys.exit(23 if os.environ.get('SCENARIO') == 'helm-failure' else 0)
sys.exit(subprocess.call([os.environ['REAL_HELM'], *args]))
'''


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        (self.directory / 'oc').write_text(MOCK_OC)
        (self.directory / 'helm').write_text(MOCK_HELM)
        for name in ('oc', 'helm'):
            (self.directory / name).chmod(0o755)
        self.log = self.directory / 'calls'
        self.env = dict(os.environ, PATH=str(self.directory) + os.pathsep + os.environ['PATH'],
                        CALL_LOG=str(self.log), REAL_HELM=HELM, FIXTURES=str(self.directory),
                        KUBECONFIG=str(self.directory / 'nonexistent-kubeconfig'))
        for name in ('IMAGE_REGISTRY', 'VERSION', 'NAMESPACE', 'HELM_VALUES', 'KUBE_CONTEXT', 'HELM_KUBECONTEXT'):
            self.env.pop(name, None)
        fixture = ClusterTests()
        fixture.setUp()
        (self.directory / 'operators.json').write_text(json.dumps(fixture.operators))
        (self.directory / 'nodes.json').write_text(json.dumps(fixture.nodes))
        (self.directory / 'storage.json').write_text(json.dumps(fixture.storage))
        fixture.doCleanups()

    def run_script(self, script, *args, scenario='', success=True):
        result = subprocess.run(['bash', str(ROOT / script), *args], env=dict(self.env, SCENARIO=scenario),
                                cwd='/tmp', capture_output=True, text=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def calls(self):
        return self.log.read_text() if self.log.exists() else ''

    def test_existing_installation_requires_backup_before_mutation(self):
        self.run_script('deploy.sh', '--language', 'cs', scenario='upgrade-backup-failure', success=False)
        self.assertNotIn('HELM-UPGRADE', self.calls())
        self.assertNotIn('"label"', self.calls())
        self.assertNotIn('"patch"', self.calls())

    def test_recovery_requires_valid_owner_selected_backup(self):
        snapshot = self.directory / 'snapshot.db'
        fixture_db(snapshot)
        self.run_script('deploy.sh', '--language', 'cs', '--backup-file', str(snapshot), scenario='upgrade-recovery')
        self.assertIn('HELM-UPGRADE', self.calls())
        self.log.write_text('')
        snapshot.write_text('not a snapshot')
        self.run_script('deploy.sh', '--language', 'cs', '--backup-file', str(snapshot), scenario='upgrade-recovery', success=False)
        self.assertNotIn('HELM-UPGRADE', self.calls())

    def test_values_file_resolves_relative_to_callers_directory(self):
        # run_script deliberately executes from /tmp, not the repository.
        with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.yaml', mode='w') as values:
            values.write('game:\n  requiredLanguage: de\n')
            values.flush()
            self.run_script('deploy.sh', '--preflight', '--values', Path(values.name).name)

    def test_language_rejects_helm_value_injection(self):
        self.run_script('deploy.sh', '--language', 'en,namespace=other', success=False)
        self.assertEqual(self.calls(), '')

    def test_access_summary_fails_without_disclosing_partial_details(self):
        result = self.run_script('scripts/show-access.sh', scenario='upgrade-backup-failure', success=False)
        self.assertNotIn('Admin password:', result.stdout)
        self.assertNotIn('Game URL:', result.stdout)

    def test_password_file_is_passed_without_password_in_arguments(self):
        password = self.directory / 'admin-token'
        password.write_text('test@password!')
        result = self.run_script('deploy.sh', '--language', 'de', '--admin-password-file', str(password))
        self.assertIn('tournament.adminToken=' + str(password), self.calls())
        self.assertNotIn('test@password!', self.calls())
        self.assertIn('Admin password: mock-admin-password', result.stdout)

    def test_transient_exec_transport_retries_without_hiding_failure(self):
        self.run_script('deploy.sh','--language','de',scenario='exec-transport-once')
        calls=[json.loads(line) for line in self.calls().splitlines() if line.startswith('[')]
        self.assertEqual(sum('exec' in call for call in calls),2)

    def test_failed_smoke_assertion_is_not_retried_or_declared_successful(self):
        result=self.run_script('deploy.sh','--language','de',scenario='exec-check-failure',success=False)
        calls=[json.loads(line) for line in self.calls().splitlines() if line.startswith('[')]
        self.assertEqual(sum('exec' in call for call in calls),1)
        self.assertNotIn('Deployment and internal smoke checks passed',result.stdout)

    def test_help_needs_no_cluster(self):
        self.run_script('deploy.sh', '--help')
        self.assertEqual(self.calls(), '')

    def test_missing_language_fails_before_cluster_access(self):
        self.run_script('deploy.sh', '--preflight', success=False)
        self.assertEqual(self.calls(), '')

    def test_monitoring_is_required_but_preflight_stays_read_only(self):
        result = self.run_script('deploy.sh', '--language', 'de', '--preflight')
        self.assertIn('User workload monitoring will be enabled', result.stdout)
        self.assertNotIn('"create"', self.calls())

    def test_read_only_preflight_from_other_directory(self):
        self.run_script('deploy.sh', '--language', 'cs', '--preflight', '--free-rhdp-gpu')
        for forbidden in ('HELM-UPGRADE', '"patch"', '"scale"', '"label"', '"exec"'):
            self.assertNotIn(forbidden, self.calls())

    def test_api_error_stops_before_mutation(self):
        self.run_script('deploy.sh', '--language', 'cs', scenario='api-failure', success=False)
        self.assertNotIn('HELM-UPGRADE', self.calls())
        self.assertNotIn('"label"', self.calls())

    def test_failed_helm_never_claims_success(self):
        result = self.run_script('deploy.sh', '--language', 'cs', scenario='helm-failure', success=False)
        self.assertNotIn('Deployment and internal smoke checks passed', result.stdout)
        self.assertIn('Resources were retained', result.stderr)

    def test_gpu_helper_propagates_patch_failure(self):
        self.run_script('scripts/free-gpu.sh', scenario='patch-failure', success=False)
        self.assertNotIn('"scale"', self.calls())

    def test_gpu_helper_propagates_wait_failure(self):
        self.run_script('scripts/free-gpu.sh', scenario='wait-failure', success=False)

    def test_gpu_helper_detects_remaining_pods(self):
        self.run_script('scripts/free-gpu.sh', scenario='pods-remain', success=False)

    def test_absent_llama_is_idempotent(self):
        self.run_script('scripts/free-gpu.sh', scenario='llama-absent')
        self.assertNotIn('"patch"', self.calls())

    def test_default_no_build_deploy_uses_requested_language(self):
        result = self.run_script('deploy.sh', '--language', 'cs', '--namespace', 'venue')
        self.assertIn('Admin URL: https://whisper.fake.test/admin', result.stdout)
        self.assertIn('Admin password: mock-admin-password', result.stdout)
        self.assertIn('language=cs', result.stdout)
        self.assertIn('"--kube-context", "mock-context"', self.calls())
        self.assertIn('HELM-UPGRADE', self.calls())
        self.assertIn('"create"', self.calls())
        self.assertIn('"exec"', self.calls())
        self.assertNotIn('"patch"', self.calls())


if __name__ == '__main__':
    unittest.main()
