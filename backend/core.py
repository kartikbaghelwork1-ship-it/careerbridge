"""CareerBridge local backend. Python 3.10+, standard library only."""
import hashlib, hmac, json, math, os, secrets, sqlite3, time
from http.cookies import SimpleCookie
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = Path(os.environ.get('CAREERBRIDGE_DB', ROOT / 'backend' / 'data' / 'careerbridge.sqlite3'))
PORT = int(os.environ.get('PORT', '8000'))
DEFAULT = {'profile': {'name':'Aarav Sharma','degree':'B.Tech · Computer Science','year':'3','cgpa':8.2,'interest':'Software development','skills':'JavaScript, HTML, CSS, Python, Git','hours':6}, 'tasks':[], 'saved':[], 'resume':'', 'answers':{}}
ROLES = [('Frontend Developer','Software development',['HTML','CSS','JavaScript','React','Git','Testing']),('Data Analyst','Data & analytics',['Python','SQL','Excel','Statistics','Visualization','Communication']),('UX Designer','Design',['Figma','Research','Prototyping','Accessibility','Communication','Testing']),('Backend Developer','Software development',['Python','SQL','APIs','Git','Testing','Databases'])]

from contextlib import contextmanager

@contextmanager
def connection():
    c = sqlite3.connect(DB, timeout=10)
    c.execute('PRAGMA foreign_keys=ON')
    try:
        with c:
            yield c
    finally:
        c.close()

def initialize():
    DB.parent.mkdir(parents=True, exist_ok=True)
    with connection() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL,created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS states(user_id TEXT PRIMARY KEY REFERENCES users(id),payload TEXT NOT NULL,updated INTEGER NOT NULL);''')
    DB.chmod(0o600)

def password_hash(password, salt):
    return hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex()

def validate_state(data):
    if not isinstance(data,dict): raise ValueError('State must be an object.')
    p=data.get('profile')
    if not isinstance(p,dict): raise ValueError('Profile is required.')
    for key,limit in [('name',70),('degree',100),('skills',1500)]:
        if not isinstance(p.get(key),str) or not p[key].strip() or len(p[key])>limit: raise ValueError('Invalid '+key+'.')
    if p.get('year') not in ['1','2','3','4','Graduate']: raise ValueError('Invalid study year.')
    if p.get('interest') not in [x[1] for x in ROLES]: raise ValueError('Invalid interest.')
    for key,low,high in [('cgpa',0,10),('hours',1,40)]:
        v=p.get(key)
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not low<=v<=high: raise ValueError('Invalid '+key+'.')
    tasks=data.get('tasks',[]); saved=data.get('saved',[]); answers=data.get('answers',{}); resume=data.get('resume','')
    if not isinstance(tasks,list) or len(tasks)>100 or any(not isinstance(x,str) or len(x)>100 for x in tasks): raise ValueError('Invalid progress.')
    if not isinstance(saved,list) or len(saved)>4 or any(type(x)!=int or x not in [1,2,3,4] for x in saved): raise ValueError('Invalid saved opportunities.')
    if not isinstance(resume,str) or len(resume)>30000: raise ValueError('Resume exceeds 30,000 characters.')
    if not isinstance(answers,dict) or any(k not in ['0','1','2','3'] or not isinstance(v,str) or len(v)>10000 for k,v in answers.items()): raise ValueError('Invalid interview answers.')
    return {'profile':{k:p[k] for k in DEFAULT['profile']},'tasks':list(dict.fromkeys(tasks)),'saved':list(dict.fromkeys(saved)),'resume':resume,'answers':answers}

def recommendations(data):
    p=validate_state(data)['profile']; skills={s.strip().lower() for s in p['skills'].split(',')}; result=[]
    for name,domain,required in ROLES:
        known=[s for s in required if s.lower() in skills]; gaps=[s for s in required if s.lower() not in skills]
        score=math.floor(len(known)/len(required)*100+.5)
        result.append({'name':name,'domain':domain,'skills':required,'known':known,'gaps':gaps,'score':score,'weeks':max(4,math.ceil((len(gaps)*12+24)/p['hours']))})
    return sorted(result,key=lambda r:r['score']+(12 if r['domain']==p['interest'] else 0),reverse=True)
