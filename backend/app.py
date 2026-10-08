"""Single-origin Flask API + frontend; SQLite database, per-account workspace."""
import hashlib, hmac, json, secrets, sqlite3, time
from flask import Flask, request, jsonify, send_from_directory
from . import core

def create_app(db_path=None, testing=False):
    if db_path is not None: core.DB=core.Path(db_path)
    core.initialize()
    with core.connection() as c:
        c.execute('CREATE TABLE IF NOT EXISTS auth_attempts (attempt_key TEXT PRIMARY KEY, failures INTEGER NOT NULL, window_start INTEGER NOT NULL)')
    app=Flask(__name__,static_folder=None)
    app.config.update(TESTING=testing,MAX_CONTENT_LENGTH=150000)
    secure=core.os.environ.get('SECURE_COOKIES','false').lower()=='true'
    def response(data,status=200): return jsonify(data),status
    def user():
        token=request.cookies.get('cb_session','')
        with core.connection() as c:
            return c.execute('SELECT u.id,u.email FROM sessions s JOIN users u ON s.user_id=u.id WHERE s.token_hash=? AND s.expires>?',(hashlib.sha256(token.encode()).hexdigest(),int(time.time()))).fetchone()
    @app.before_request
    def guard():
        if request.path.startswith('/api/') and request.method in ['POST','PUT']:
            if request.headers.get('X-CareerBridge')!='1' or not request.is_json:return response({'error':'JSON and request header required.'},403)
            origin=request.headers.get('Origin')
            allowed=core.os.environ.get('APP_ORIGIN',request.host_url.rstrip('/'))
            if origin and origin.rstrip('/')!=allowed.rstrip('/'):return response({'error':'Request origin rejected.'},403)
    @app.after_request
    def headers(res):
        res.headers['X-Content-Type-Options']='nosniff';res.headers['Referrer-Policy']='same-origin';res.headers['X-Frame-Options']='SAMEORIGIN'
        if request.path.startswith('/api/'):res.headers['Cache-Control']='no-store'
        return res
    @app.errorhandler(413)
    def too_big(e):return response({'error':'Request too large.'},413)
    @app.errorhandler(400)
    def bad_json(e):return response({'error':'Invalid JSON request.'},400)
    @app.errorhandler(sqlite3.Error)
    def database_error(e):return response({'error':'Database unavailable. Try again.'},503)
    @app.get('/api/health')
    def health():
        with core.connection() as c:c.execute('SELECT COUNT(*) FROM users').fetchone()
        return response({'ok':True,'storage':'sqlite'})
    @app.post('/api/auth/<action>')
    def auth(action):
        data=request.get_json()
        if not isinstance(data,dict):return response({'error':'JSON object required.'},400)
        if action=='logout':
            if not user():return response({'error':'Sign in to access your account.'},401)
            with core.connection() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(hashlib.sha256(request.cookies.get('cb_session','').encode()).hexdigest(),))
            res=jsonify({'ok':True});res.delete_cookie('cb_session',path='/',secure=secure,httponly=True,samesite='Strict');return res
        if action not in ['register','login']:return response({'error':'Endpoint not found.'},404)
        email=data.get('email','');password=data.get('password','')
        if not isinstance(email,str) or not isinstance(password,str):return response({'error':'Enter email and password.'},400)
        email=email.strip().lower()
        if len(email)>254 or '@' not in email or '.' not in email.split('@')[-1] or any(x.isspace() for x in email) or not 10<=len(password)<=128:return response({'error':'Valid email and 10–128 character password required.'},400)
        ratekey=hashlib.sha256((request.remote_addr or 'unknown').encode()).hexdigest();now=int(time.time())
        with core.connection() as c:
            attempt=c.execute('SELECT failures,window_start FROM auth_attempts WHERE attempt_key=?',(ratekey,)).fetchone()
            if attempt and attempt[1]>now-900 and attempt[0]>=10:return response({'error':'Too many attempts. Try in 15 minutes.'},429)
            count=attempt[0]+1 if attempt and attempt[1]>now-900 else 1;start=attempt[1] if attempt and attempt[1]>now-900 else now
            c.execute('INSERT INTO auth_attempts VALUES(?,?,?) ON CONFLICT(attempt_key) DO UPDATE SET failures=excluded.failures,window_start=excluded.window_start',(ratekey,count,start))
        with core.connection() as c:
            if action=='register':
                uid=secrets.token_hex(16);salt=secrets.token_hex(16)
                try:c.execute('INSERT INTO users VALUES(?,?,?,?,?)',(uid,email,salt,core.password_hash(password,salt),now))
                except sqlite3.IntegrityError:return response({'error':'Account exists. Sign in instead.'},409)
                c.execute('INSERT INTO states VALUES(?,?,?)',(uid,json.dumps(core.DEFAULT),now))
            else:
                row=c.execute('SELECT id,salt,password_hash FROM users WHERE email=?',(email,)).fetchone();candidate=core.password_hash(password,row[1] if row else '00'*16)
                if not row or not hmac.compare_digest(candidate,row[2]):return response({'error':'Email or password is incorrect.'},401)
                uid=row[0]
            c.execute('DELETE FROM auth_attempts WHERE attempt_key=?',(ratekey,));c.execute('DELETE FROM sessions WHERE expires<=?',(now,));token=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,now+604800))
        res=jsonify({'email':email});res.set_cookie('cb_session',token,max_age=604800,secure=secure,httponly=True,samesite='Strict');return res
    @app.get('/api/auth/me')
    def me():
        who=user();return response({'email':who[1]}) if who else response({'error':'Sign in to access your account.'},401)
    @app.route('/api/state',methods=['GET','PUT'])
    def state():
        who=user()
        if not who:return response({'error':'Sign in to access your account.'},401)
        if request.method=='PUT':
            try:valid=core.validate_state(request.get_json())
            except (ValueError,TypeError):return response({'error':'Check profile fields and input limits.'},400)
            with core.connection() as c:c.execute('UPDATE states SET payload=?,updated=? WHERE user_id=?',(json.dumps(valid),int(time.time()),who[0]))
            return response({'ok':True})
        with core.connection() as c:row=c.execute('SELECT payload FROM states WHERE user_id=?',(who[0],)).fetchone()
        return response(json.loads(row[0]) if row else core.DEFAULT)
    @app.get('/api/recommendations')
    def recommendations():
        who=user()
        if not who:return response({'error':'Sign in to access your account.'},401)
        with core.connection() as c:row=c.execute('SELECT payload FROM states WHERE user_id=?',(who[0],)).fetchone()
        return response({'careers':core.recommendations(json.loads(row[0]) if row else core.DEFAULT)})
    @app.get('/')
    def home():return send_from_directory(core.ROOT/'dist','index.html')
    @app.get('/<path:filename>')
    def assets(filename):
        if filename.startswith('api/'):return response({'error':'Endpoint not found.'},404)
        return send_from_directory(core.ROOT/'dist',filename)
    return app
