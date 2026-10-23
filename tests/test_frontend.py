"""Exercise the real rendered JS without a browser, using Node's built-in VM only."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class FrontendPersistenceTests(unittest.TestCase):
    def test_save_failures_retry_and_standalone_using_rendered_application(self):
        node=shutil.which('node')
        self.assertIsNotNone(node,'Node.js is required for the frontend persistence regression test')
        spec=importlib.util.spec_from_file_location('render_fixture',ROOT/'tests/test_registration.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        fixture=module.RegistrationTests
        fixture.setUpClass()
        instance=fixture();instance.setUp()
        try:
            instance.module.REQUIRED_CHALLENGE_LANGUAGE='en'
            instance.module.LANGUAGE_INFO={'en':{'flag':'🇬🇧','name':'English'}}
            instance.module.DIFFICULTY_POOLS={level:['en'] for level in ('easy','medium','hard')}
            pages={}
            for enabled in (True,False):
                instance.module.TOURNAMENT_ENABLED=enabled
                pages[str(enabled).lower()]=instance.client.get('/').get_data(as_text=True)
            with tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'pages.json';path.write_text(json.dumps(pages))
                result=subprocess.run([node,str(ROOT/'tests/frontend-persistence.cjs'),str(path)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        finally:
            instance.doCleanups();fixture.doClassCleanups()
