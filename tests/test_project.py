import json, os, subprocess, sys, tempfile, time, unittest
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from Backend.policy import recommend

class PolicyTests(unittest.TestCase):
    def test_boundaries(self):
        for args,expected in [((9,10,1,1,False),('advance',2)),((3,10,6,2,False),('simplify',1)),((7,10,3,2,False),('maintain',2)),((9,10,0,2,True),('pause',2)),((1,2,0,2,False),('insufficient_evidence',2)),((10,10,0,3,False),('advance',3))]:
            self.assertEqual(recommend(*args)[:2],expected)

class APITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.base='http://127.0.0.1:18081'
        cls.proc=subprocess.Popen([sys.executable,'-m','Backend.app'],env={**os.environ,'MEMORY_DB':str(Path(cls.tmp.name)/'test.db'),'PORT':'18081'},stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                cls.call('/api/health');return
            except OSError: time.sleep(.1)
        cls.proc.terminate();cls.proc.wait();cls.tmp.cleanup()
        raise RuntimeError('Test server did not start')
    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate();cls.proc.wait(timeout=10);cls.tmp.cleanup()
    @classmethod
    def call(cls,path,payload=None):
        req=Request(cls.base+path,data=None if payload is None else json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=10) as response:return json.load(response)
    def test_full_flow_and_validation(self):
        payload=dict(correct=3,attempts=3,hints=0,level=1,paused=False)
        with self.assertRaises(HTTPError) as e:self.call('/api/sessions',payload)
        self.assertEqual(e.exception.code,403)
        self.call('/api/profile',dict(name='Test',consent=True))
        result=self.call('/api/sessions',payload)
        self.assertEqual(result['recommendation'],'advance')
        self.assertIn(result['model_action'],['advance','maintain','simplify','pause'])
        self.call('/api/memories',dict(title='<b>Family</b>',description='Fictional memory',approved=True))
        self.call('/api/reminders',dict(title='Drink water',due_at='2026-10-26T10:00'))
        d=self.call('/api/dashboard');rid=d['reminders'][0]['id']
        self.call(f'/api/reminders/{rid}/acknowledge',{})
        self.assertEqual(self.call('/api/dashboard')['reminders'][0]['acknowledged'],1)
        for bad in [dict(payload,correct=4),dict(payload,attempts=-1),dict(payload,paused='false'),dict(payload,level=99),dict(payload,correct=True)]:
            with self.assertRaises(HTTPError) as e:self.call('/api/sessions',bad)
            self.assertEqual(e.exception.code,400)
        self.call('/api/profile',dict(name='Test',consent=False))
        with self.assertRaises(HTTPError):self.call('/api/sessions',payload)
        self.assertEqual(len(self.call('/api/dashboard')['sessions']),1)
    def test_group_separation(self):
        report=json.loads(Path('ML/artifacts/evaluation.json').read_text())
        self.assertFalse(set(report['train_participants']) & set(report['test_participants']))
        self.assertEqual(report['train_rows']+report['test_rows'],960)
if __name__=='__main__':unittest.main()
