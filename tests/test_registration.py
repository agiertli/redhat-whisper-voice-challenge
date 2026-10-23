"""Exercise both registration modes against real Flask routes and isolated SQLite."""
import concurrent.futures
import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class RegistrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.boot = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.boot.cleanup)
        name = 'whisper_registration_tests'
        spec = importlib.util.spec_from_file_location(name, ROOT / 'src/app_streaming.py')
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[name] = cls.module
        cls.addClassCleanup(sys.modules.pop, name, None)
        with patch.dict(os.environ, DB_PATH=str(Path(cls.boot.name) / 'boot.db'),
                        REGISTRATION_MODE='full', ADMIN_TOKEN='admin-test-password',
                        TOURNAMENT_SECRET='registration-test-signing-secret-32-characters'):
            with patch('kubernetes.config.load_incluster_config', side_effect=RuntimeError('offline test')):
                spec.loader.exec_module(cls.module)
        cls.module.app.config['TESTING'] = True

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.module.DB_PATH = str(Path(self.tmp.name) / 'tournament.db')
        self.module.TOURNAMENT_ENABLED = True
        self.module.CHALLENGE_COUNT = 5
        self.module.REGISTRATION_MODE = 'username'
        self.module.init_db()
        self.client = self.module.app.test_client()

    def join(self, **data):
        return self.client.post('/api/register', json=data)

    def players(self):
        with sqlite3.connect(self.module.DB_PATH) as db:
            return db.execute('SELECT id, nickname, name, email FROM players').fetchall()

    def test_username_registers_and_resumes_one_player(self):
        first = self.join(username='BoothPlayer')
        self.assertEqual(first.status_code, 201)
        again = self.join(username='BoothPlayer')
        self.assertEqual(again.status_code, 200)
        self.assertEqual(first.json['player_id'], again.json['player_id'])
        self.assertEqual(len(self.players()), 1)
        me = self.client.get('/api/player/me', headers={'Authorization': 'Bearer ' + again.json['token']})
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json['nickname'], 'BoothPlayer')

    def test_username_ignores_name_email_even_from_legacy_clients(self):
        self.assertEqual(self.join(nickname='LegacyUser', name='Do not store', email='discard@example.test').status_code, 201)
        self.assertEqual(self.players()[0][1:], ('LegacyUser', '', ''))

    def test_invalid_usernames_and_malformed_bodies_create_no_players(self):
        for username in ('', 'x', 'x' * 21, 'two words', '<script>', 'person@example.test', 42, [], None):
            with self.subTest(username=username):
                self.assertEqual(self.join(username=username).status_code, 400)
        for body in ([], 'bad', 42, None):
            self.assertEqual(self.client.post('/api/register', json=body).status_code, 400)
        self.assertEqual(self.players(), [])

    def test_username_page_has_one_form_and_no_personal_fields_or_tabs(self):
        page = self.client.get('/').get_data(as_text=True)
        self.assertEqual(page.count('<form '), 1)
        self.assertIn('id="regUsername"', page)
        for field in ('id="regName"', 'id="regEmail"', 'id="regReturnForm"', 'id="modeNewBtn"', 'id="modeReturnBtn"'):
            self.assertNotIn(field, page)
        registration = self.client.get('/register', follow_redirects=True)
        self.assertEqual(registration.status_code, 200)
        self.assertIn('id="regUsername"', registration.get_data(as_text=True))

    def test_full_mode_retains_required_fields_and_duplicate_handling(self):
        self.module.REGISTRATION_MODE = 'full'
        self.assertEqual(self.join(nickname='FullUser').status_code, 400)
        self.assertEqual(self.join(nickname='FullUser', name='Full User', email='invalid').status_code, 400)
        payload = dict(nickname='FullUser', name='Full User', email='full@example.test')
        self.assertEqual(self.join(**payload).status_code, 201)
        self.assertEqual(self.join(**payload).status_code, 409)
        self.assertEqual(self.players()[0][1:], ('FullUser', 'Full User', 'full@example.test'))
        page = self.client.get('/').get_data(as_text=True)
        self.assertIn('id="modeReturnBtn"', page)
        self.assertIn('id="regEmail"', page)
        self.assertNotIn('id="regUsername"', page)

    def test_switching_modes_preserves_existing_player_and_scores(self):
        self.module.REGISTRATION_MODE = 'full'
        player = self.join(nickname='Existing', name='Existing Player', email='existing@example.test').json
        auth = {'Authorization': 'Bearer ' + player['token']}
        game = self.client.post('/api/game/start', json={'difficulty': 'easy'}, headers=auth).json
        with sqlite3.connect(self.module.DB_PATH) as db:
            db.execute('UPDATE games SET total_score=100, avg_accuracy=1, completed_at=started_at WHERE id=?', (game['game_id'],))
        self.module.REGISTRATION_MODE = 'username'
        resumed = self.join(username='Existing')
        self.assertEqual(resumed.json['player_id'], player['player_id'])
        self.assertEqual(self.client.get('/api/player/me', headers=auth).json['best_score'], 100)
        self.assertEqual(self.players()[0][2:], ('Existing Player', 'existing@example.test'))
        self.module.REGISTRATION_MODE = 'full'
        self.assertEqual(self.client.post('/api/login', json={'nickname': 'Existing'}).status_code, 200)

    def test_simultaneous_username_joins_create_one_player(self):
        def join_once(_):
            with self.module.app.test_client() as client:
                response = client.post('/api/register', json={'username': 'SameUser'})
                return response.status_code, response.json['player_id']
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            results = list(pool.map(join_once, range(8)))
        self.assertEqual(sum(status == 201 for status, _ in results), 1)
        self.assertEqual({status for status, _ in results}, {200, 201})
        self.assertEqual(len({player for _, player in results}), 1)
        self.assertEqual(len(self.players()), 1)

    def test_documented_score_examples_and_normalization(self):
        score = self.module.compute_total_score
        self.assertEqual(score('medium', 0.90, 60), 148.5)
        self.assertEqual(score('medium', 0.90, 120), 135.0)
        self.assertEqual(score('medium', 0.90, 240), 108.0)
        self.assertEqual(score('medium', 0.90, 600), 108.0)
        self.assertEqual(score('easy', 1.0, 0), 120.0)
        self.assertEqual(score('hard', 1.0, 0), 240.0)
        self.assertEqual(self.module.levenshtein_similarity('  HELLO,   world! ', 'hello world'), 1.0)
        self.assertLess(self.module.levenshtein_similarity('cafe', 'café'), 1.0)

    def test_skip_submissions_are_rejected_without_consuming_an_attempt(self):
        player = self.join(username='NoSkips').json
        auth = {'Authorization': 'Bearer ' + player['token']}
        phrase = self.module.CHALLENGE_PHRASES['en'][0]
        for difficulty in ('easy', 'medium', 'hard'):
            with self.subTest(difficulty=difficulty):
                game = self.client.post('/api/game/start', json={'difficulty': difficulty}, headers=auth).json
                path = '/api/game/' + str(game['game_id']) + '/attempt'
                attempt = {'attempt_index': 0, 'language': 'en', 'phrase': phrase, 'transcription': phrase}
                for status in ('skip', 'swap', 'win', 'fail'):
                    rejected = self.client.post(path, json=dict(attempt, status=status), headers=auth)
                    self.assertEqual(rejected.status_code, 400)
                with sqlite3.connect(self.module.DB_PATH) as db:
                    self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts WHERE game_id=?', (game['game_id'],)).fetchone()[0], 0)
                submitted = self.client.post(path, json=attempt, headers=auth)
                self.assertEqual(submitted.status_code, 200)
                self.assertEqual(submitted.json['accuracy'], 1.0)
                self.assertEqual(submitted.json['status'], 'win')

    def test_historical_skip_survives_backup_restore_and_keeps_its_scoring(self):
        player = self.join(username='Historical').json
        auth = {'Authorization': 'Bearer ' + player['token']}
        admin = {'Authorization': 'Bearer ' + self.module.ADMIN_TOKEN}
        game = self.client.post('/api/game/start', json={'difficulty': 'easy'}, headers=auth).json
        path = '/api/game/' + str(game['game_id'])
        phrase = self.module.CHALLENGE_PHRASES['en'][0]
        attempt = {'attempt_index': 0, 'language': 'en', 'phrase': phrase, 'transcription': phrase}
        self.assertEqual(self.client.post(path + '/attempt', json=attempt, headers=auth).status_code, 200)
        # Simulate an old persisted record, not a new skip API submission.
        with sqlite3.connect(self.module.DB_PATH) as db:
            db.execute('UPDATE games SET round_count=NULL WHERE id=?', (game['game_id'],))
            db.execute("INSERT INTO attempts (game_id,attempt_index,language,phrase,accuracy,status) VALUES (?,1,'en',?,0,'skip')", (game['game_id'], phrase))
        response = self.client.get('/api/admin/backup', headers=admin)
        snapshot = response.data
        response.close()
        self.module.DB_PATH = str(Path(self.tmp.name) / 'restored.db')
        self.module.init_db()
        restored = self.client.post('/api/admin/restore', headers=admin,
                                    data={'file': (io.BytesIO(snapshot), 'historical.db')})
        self.assertEqual(restored.status_code, 200)
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM attempts WHERE status='skip'").fetchone()[0], 1)
        result = self.client.post(path + '/complete', headers=auth)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json['avg_accuracy'], 1.0)
        self.assertTrue(result.json['won'])

    def test_empty_transcription_is_a_scored_failure_not_a_skip(self):
        player = self.join(username='EmptySpeech').json
        auth = {'Authorization': 'Bearer ' + player['token']}
        game = self.client.post('/api/game/start', json={'difficulty': 'easy'}, headers=auth).json
        attempt = {'attempt_index': 0, 'language': 'en', 'phrase': self.module.CHALLENGE_PHRASES['en'][0], 'transcription': ''}
        result = self.client.post('/api/game/' + str(game['game_id']) + '/attempt', json=attempt, headers=auth)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json, {'accuracy': 0.0, 'status': 'fail'})

    def test_runtime_assets_are_served_from_the_application(self):
        for path in ('/logo.svg', '/favicon.svg', '/architecture'):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 200, path)
            self.assertTrue(response.data)
            response.close()

    def test_username_player_can_play_export_and_backup(self):
        player = self.join(username='PlayerOnly').json
        auth = {'Authorization': 'Bearer ' + player['token']}
        self.assertEqual(self.client.post('/api/game/start', json={'difficulty': 'easy'}, headers=auth).status_code, 201)
        admin = {'Authorization': 'Bearer ' + self.module.ADMIN_TOKEN}
        for path in ('/api/admin/players', '/api/admin/export', '/api/admin/export-games'):
            self.assertEqual(self.client.get(path, headers=admin).status_code, 200)
        backup = self.client.get('/api/admin/backup', headers=admin)
        self.assertEqual(backup.status_code, 200)
        self.assertTrue(backup.data.startswith(b'SQLite format 3'))
        backup.close()

    def game_fixture(self, username='TestGame', difficulty='hard'):
        player = self.join(username=username).json
        auth = {'Authorization': 'Bearer ' + player['token']}
        game = self.client.post('/api/game/start', json={'difficulty': difficulty}, headers=auth).json
        return player, auth, '/api/game/' + str(game['game_id'])

    def attempt_payload(self, index=0):
        phrase = self.module.CHALLENGE_PHRASES['en'][0]
        return dict(attempt_index=index, language='en', phrase=phrase, transcription=phrase)

    def test_environment_flag_defaults_true_accepts_false_and_rejects_ambiguous_values(self):
        for setting, expected in ((None,True),('true',True),('false',False),('yes',None),('0',None)):
            with self.subTest(setting=setting):
                env=os.environ.copy()
                env['DB_PATH']=str(Path(self.tmp.name)/'flag.db')
                env.pop('TOURNAMENT_ENABLED',None)
                if setting is not None: env['TOURNAMENT_ENABLED']=setting
                code="import runpy; m=runpy.run_path('src/app_streaming.py'); print('FLAG='+str(m['TOURNAMENT_ENABLED']))"
                result=subprocess.run([sys.executable,'-c',code],cwd=ROOT,env=env,capture_output=True,text=True)
                if expected is None:
                    self.assertNotEqual(result.returncode,0)
                    self.assertIn('TOURNAMENT_ENABLED must be true or false',result.stderr)
                else:
                    self.assertEqual(result.returncode,0,result.stderr)
                    self.assertIn('FLAG='+str(expected),result.stdout)

    def test_standalone_blocks_tournament_routes_even_with_valid_token(self):
        _, auth, game = self.game_fixture()
        self.module.TOURNAMENT_ENABLED = False
        for method, path, data in [('post','/api/register',{'username':'Blocked'}),
                                   ('post','/api/login',{'nickname':'TestGame'}),
                                   ('get','/api/player/me',None), ('post','/api/game/start',{'difficulty':'hard'}),
                                   ('post',game+'/attempt',self.attempt_payload()),
                                   ('post',game+'/complete',{}), ('get','/api/leaderboard',None), ('get','/tv',None)]:
            with self.subTest(path=path):
                self.assertEqual(getattr(self.client,method)(path,json=data,headers=auth).status_code,404)
        self.assertEqual(len(self.players()),1)
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],0)
        admin={'Authorization':'Bearer '+self.module.ADMIN_TOKEN}
        for path in ('/api/admin/players','/api/admin/export','/admin'):
            self.assertEqual(self.client.get(path,headers=admin).status_code,200)
        response=self.client.get('/api/admin/backup',headers=admin)
        self.assertEqual(response.status_code,200);response.close()
        page=self.client.get('/').get_data(as_text=True)
        self.assertIn('const TOURNAMENT_ENABLED = false;',page)
        self.assertNotIn('<form ',page)
        self.assertEqual(self.client.get('/register').status_code,302)

    def test_switch_off_and_back_preserves_all_data_and_original_token(self):
        _, auth, path=self.game_fixture()
        for i in range(5):
            self.assertEqual(self.client.post(path+'/attempt',json=self.attempt_payload(i),headers=auth).status_code,200)
        result=self.client.post(path+'/complete',headers=auth).json
        def rows():
            with sqlite3.connect(self.module.DB_PATH) as db:
                return {t:db.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall() for t in ('players','games','attempts','settings')}
        before=rows()
        self.module.TOURNAMENT_ENABLED=False
        self.client.get('/')
        self.assertEqual(rows(),before)
        self.module.TOURNAMENT_ENABLED=True
        self.assertEqual(self.client.get('/api/player/me',headers=auth).json['best_score'],result['total_score'])
        self.assertEqual(rows(),before)

    def test_round_contract_and_completion_retry_are_stable(self):
        _, auth, path=self.game_fixture()
        self.assertEqual(self.client.post(path+'/complete',headers=auth).status_code,409)
        for index in (True,-1,5,1):
            self.assertEqual(self.client.post(path+'/attempt',json=self.attempt_payload(index),headers=auth).status_code,400)
        for i in range(5):
            result=self.client.post(path+'/attempt',json=self.attempt_payload(i),headers=auth)
            self.assertEqual(result.status_code,200)
        first=self.client.post(path+'/complete',headers=auth)
        self.assertEqual(first.status_code,200)
        second=self.client.post(path+'/complete',headers=auth)
        self.assertEqual(second.json,first.json)
        self.assertTrue(first.json['won'])
        self.assertEqual(first.json['avg_accuracy'],1.0)
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],5)

    def test_attempt_retry_is_idempotent_but_conflicting_payload_is_not(self):
        _, auth, path=self.game_fixture()
        payload=self.attempt_payload()
        first=self.client.post(path+'/attempt',json=payload,headers=auth)
        self.assertEqual(first.status_code,200)
        self.assertEqual(self.client.post(path+'/attempt',json=payload,headers=auth).json,first.json)
        self.assertEqual(self.client.post(path+'/attempt',json=dict(payload,transcription='different'),headers=auth).status_code,409)
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],1)

    def test_simultaneous_identical_attempt_retries_store_one_row(self):
        _, auth, path=self.game_fixture()
        def submit(_):
            with self.module.app.test_client() as client:
                return client.post(path+'/attempt',json=self.attempt_payload(),headers=auth).status_code
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            self.assertEqual(list(pool.map(submit,range(8))),[200]*8)
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertEqual(db.execute('SELECT COUNT(*) FROM attempts').fetchone()[0],1)

    def test_deleted_player_token_cannot_create_or_read_games(self):
        player, auth, path=self.game_fixture()
        admin={'Authorization':'Bearer '+self.module.ADMIN_TOKEN}
        self.assertEqual(self.client.delete('/api/admin/players/'+str(player['player_id']),headers=admin).status_code,200)
        self.assertEqual(self.client.get('/api/player/me',headers=auth).status_code,401)
        self.assertEqual(self.client.post('/api/game/start',json={'difficulty':'easy'},headers=auth).status_code,401)
        self.assertEqual(self.client.post(path+'/attempt',json=self.attempt_payload(),headers=auth).status_code,401)

    def test_malformed_attempts_never_become_perfect_empty_results(self):
        _, auth, path=self.game_fixture()
        for payload in ([],42,'bad',{},dict(self.attempt_payload(),language=[]),
                        dict(self.attempt_payload(),phrase=''), dict(self.attempt_payload(),language='zz',phrase=''),
                        dict(self.attempt_payload(),transcription=[]),dict(self.attempt_payload(),transcription='x'*10001)):
            self.assertEqual(self.client.post(path+'/attempt',json=payload,headers=auth).status_code,400)
        for path2 in ('/api/login','/api/game/start'):
            self.assertEqual(self.client.post(path2,json=['bad'],headers=auth).status_code,400)

    def test_new_game_keeps_its_round_count_when_configuration_changes(self):
        _, auth, path=self.game_fixture()
        self.module.CHALLENGE_COUNT=3
        for i in range(3):
            self.client.post(path+'/attempt',json=self.attempt_payload(i),headers=auth)
        self.assertEqual(self.client.post(path+'/complete',headers=auth).status_code,409)
        for i in range(3,5):
            self.assertEqual(self.client.post(path+'/attempt',json=self.attempt_payload(i),headers=auth).status_code,200)
        self.assertEqual(self.client.post(path+'/complete',headers=auth).status_code,200)

    def test_incompatible_restore_is_rejected_without_replacing_current_database(self):
        self.game_fixture()
        with sqlite3.connect(self.module.DB_PATH) as db:
            before=db.execute('SELECT * FROM players').fetchall()
        incompatible=Path(self.tmp.name)/'incompatible.db'
        with sqlite3.connect(incompatible) as db:
            for table in ('players','games','attempts'):
                db.execute('CREATE TABLE '+table+' (id INTEGER PRIMARY KEY)')
        admin={'Authorization':'Bearer '+self.module.ADMIN_TOKEN}
        result=self.client.post('/api/admin/restore',headers=admin,data={'file':(io.BytesIO(incompatible.read_bytes()),'incompatible.db')})
        self.assertEqual(result.status_code,400)
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertEqual(db.execute('SELECT * FROM players').fetchall(),before)

    def test_old_database_migrates_without_altering_rows_and_restores(self):
        _, auth, path=self.game_fixture()
        # Actual pre-integration table shape, without the additive column.
        with sqlite3.connect(self.module.DB_PATH) as db:
            db.execute('ALTER TABLE games DROP COLUMN round_count')
        admin={'Authorization':'Bearer '+self.module.ADMIN_TOKEN}
        response=self.client.get('/api/admin/backup',headers=admin)
        snapshot=response.data;response.close()
        self.module.init_db()
        with sqlite3.connect(self.module.DB_PATH) as db:
            self.assertIsNone(db.execute('SELECT round_count FROM games').fetchone()[0])
        restored=self.client.post('/api/admin/restore',headers=admin,data={'file':(io.BytesIO(snapshot),'old.db')})
        self.assertEqual(restored.status_code,200)
        self.assertEqual(self.client.get('/api/player/me',headers=auth).status_code,200)
        self.assertEqual(self.client.post(path+'/complete',headers=auth).status_code,200)


if __name__ == '__main__':
    unittest.main()
