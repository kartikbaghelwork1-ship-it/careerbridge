import json,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from backend.app import create_app
class FullProjectTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.db=Path(self.temp.name)/'db.sqlite3';self.app=create_app(self.db,True);self.a=self.app.test_client();self.b=self.app.test_client();self.h={'X-CareerBridge':'1','Origin':'http://localhost'}
 def tearDown(self):self.temp.cleanup()
 def register(self,c,email='first@example.com'):
  r=c.post('/api/auth/register',json={'email':email,'password':'example-password-123'},headers=self.h);self.assertEqual(r.status_code,200);return r
 def test_full_workspace_survives_signout_and_login(self):
  self.register(self.a);s=self.a.get('/api/state').json;s.update(tasks=['interview'],saved=[2],resume='Education and project text',answers={'0':'My project answer'});s['profile'].update(name='Demo Student',skills='Python, SQL, Excel, Statistics, Visualization, Communication',interest='Data & analytics')
  self.assertEqual(self.a.put('/api/state',json=s,headers=self.h).status_code,200)
  self.assertEqual(self.a.get('/api/recommendations').json['careers'][0]['score'],100)
  self.a.post('/api/auth/logout',json={},headers=self.h);self.assertEqual(self.a.get('/api/state').status_code,401)
  self.assertEqual(self.a.post('/api/auth/login',json={'email':'first@example.com','password':'example-password-123'},headers=self.h).status_code,200)
  self.assertEqual(self.a.get('/api/state').json,s)
  another=create_app(self.db,True).test_client();another.post('/api/auth/login',json={'email':'first@example.com','password':'example-password-123'},headers=self.h);self.assertEqual(another.get('/api/state').json,s)
 def test_users_are_isolated(self):
  self.register(self.a);self.register(self.b,'second@example.com');s=self.a.get('/api/state').json;s['saved']=[3];self.a.put('/api/state',json=s,headers=self.h);self.assertEqual(self.b.get('/api/state').json['saved'],[])
 def test_validation_and_csrf(self):
  self.register(self.a);s=self.a.get('/api/state').json;s['profile']['hours']=0
  self.assertEqual(self.a.put('/api/state',json=s,headers=self.h).status_code,400)
  self.assertEqual(self.a.put('/api/state',json=s,headers={'X-CareerBridge':'1','Origin':'https://foreign.example'}).status_code,403)
  self.assertEqual(self.a.put('/api/state',json=s).status_code,403)
 def test_wrong_password_rate_limit(self):
  self.register(self.a)
  for i in range(10):self.assertEqual(self.b.post('/api/auth/login',json={'email':'first@example.com','password':'wrong-password-123'},headers=self.h).status_code,401)
  self.assertEqual(self.b.post('/api/auth/login',json={'email':'first@example.com','password':'wrong-password-123'},headers=self.h).status_code,429)
 def test_assets_and_private_files(self):
  r=self.a.get('/');self.assertEqual(r.status_code,200);r.close();r=self.a.get('/backend.js');self.assertEqual(r.status_code,200);r.close();self.assertEqual(self.a.get('/backend/data/careerbridge.sqlite3').status_code,404);self.assertEqual(self.a.get('/../wsgi.py').status_code,404)
 def test_passwords_and_tokens_not_stored_plaintext(self):
  self.register(self.a)
  from backend import core
  with core.connection() as c:
   row=c.execute('SELECT password_hash FROM users').fetchone();self.assertNotIn('example-password',row[0]);token=c.execute('SELECT token_hash FROM sessions').fetchone()[0];self.assertEqual(len(token),64)
if __name__=='__main__':unittest.main()
