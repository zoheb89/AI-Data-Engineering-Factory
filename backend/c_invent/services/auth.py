
from __future__ import annotations
import os, sqlite3, uuid, json, time, hashlib, hmac, base64, secrets
from pathlib import Path

ROLES={"viewer":10,"analyst":20,"architect":30,"editor":40,"admin":50}
TOKEN_TTL_SECONDS=3600

class AuthError(RuntimeError): pass

def auth_required():
    v=os.getenv("AUTH_REQUIRED",os.getenv("AUTH_ENABLED","false"))
    return str(v).lower() in {"1","true","yes","on"}

def _secret():
    s=os.getenv("AUTH_SECRET","")
    if not s:
        s="local-development-secret-change-me"
    return s.encode()

def hash_password(password:str):
    if not isinstance(password,str) or len(password)<8:
        raise AuthError("Password must be at least 8 characters.")
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,310000)
    return "pbkdf2$310000$%s$%s"%(salt.hex(),digest.hex())

def verify_password(password:str,stored:str):
    try:
        scheme,iters,salt_hex,digest_hex=stored.split("$",3)
        if scheme!="pbkdf2": return False
        digest=hashlib.pbkdf2_hmac("sha256",password.encode(),bytes.fromhex(salt_hex),int(iters))
        return hmac.compare_digest(digest.hex(),digest_hex)
    except Exception:
        return False

def _b64(x): return base64.urlsafe_b64encode(x).rstrip(b"=").decode()
def _unb64(x): return base64.urlsafe_b64decode(x+"="*(-len(x)%4))

def issue_token(sub,role="viewer",name="",expires_seconds=None):
    if role not in ROLES: raise AuthError("Invalid role.")
    ttl=TOKEN_TTL_SECONDS if expires_seconds is None else expires_seconds
    payload=_b64(json.dumps({"sub":sub,"role":role,"name":name,
                             "exp":int(time.time())+int(ttl)},
                            separators=(",",":")).encode())
    sig=_b64(hmac.new(_secret(),payload.encode(),hashlib.sha256).digest())
    return f"{payload}.{sig}"

def verify_token(token):
    try:
        parts=token.split(".")
        if len(parts)!=2: raise AuthError("Invalid token.")
        payload,sig=parts
        expected=_b64(hmac.new(_secret(),payload.encode(),hashlib.sha256).digest())
        if not hmac.compare_digest(sig,expected): raise AuthError("Invalid token signature.")
        data=json.loads(_unb64(payload))
        if int(data.get("exp",0))<int(time.time()): raise AuthError("Token expired.")
        if data.get("role") not in ROLES: raise AuthError("Invalid token role.")
        return data
    except AuthError: raise
    except Exception as e: raise AuthError("Invalid token.") from e

def require_role(user,minimum):
    actual=ROLES.get((user or {}).get("role","viewer"),0)
    required=ROLES.get(minimum,0)
    if actual<required:
        raise AuthError(f"Role '{(user or {}).get('role','viewer')}' cannot perform '{minimum}' operations.")
    return True

class UserStore:
    def __init__(self,path=None):
        self.path=Path(path or os.getenv("AUTH_DB_PATH","data/auth.db"))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(self.path) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS users(
                id TEXT PRIMARY KEY,email TEXT UNIQUE,display_name TEXT,role TEXT,
                password_hash TEXT,created_at REAL,active INTEGER DEFAULT 1)""")

    def create(self,email,password,display_name="",role="viewer"):
        if role not in ROLES: raise AuthError("Invalid role.")
        email=email.strip().lower()
        if not email: raise AuthError("Email is required.")
        pwd=hash_password(password)
        try:
            with sqlite3.connect(self.path) as c:
                c.execute("INSERT INTO users VALUES(?,?,?,?,?,?,?)",
                          (str(uuid.uuid4()),email,display_name or email,role,pwd,time.time(),1))
        except sqlite3.IntegrityError as e:
            raise AuthError("User already exists.") from e
        return {"email":email,"name":display_name or email,"role":role}

    def bootstrap_admin(self):
        email=os.getenv("ADMIN_EMAIL","")
        password=os.getenv("ADMIN_PASSWORD","")
        if not email or not password: return None
        with sqlite3.connect(self.path) as c:
            exists=c.execute("SELECT 1 FROM users WHERE email=?",(email.lower(),)).fetchone()
        if exists: return None
        self.create(email,password,email,"admin")
        return email

    def authenticate(self,email,password):
        with sqlite3.connect(self.path) as c:
            row=c.execute("SELECT id,email,display_name,role,password_hash,active FROM users WHERE email=?",
                          (email.strip().lower(),)).fetchone()
        if not row or not row[5] or not verify_password(password,row[4]):
            raise AuthError("Invalid credentials.")
        return {"sub":row[0],"email":row[1],"name":row[2],"role":row[3]}

def enabled(): return auth_required()

def current_user():
    try:
        import streamlit as st
        if auth_required():
            user=getattr(st,"user",None)
            if not user or not getattr(user,"is_logged_in",False): return None
            email=getattr(user,"email","") or getattr(user,"preferred_username","")
            role=os.getenv("DEFAULT_AUTH_ROLE","viewer")
            return {"id":email,"sub":email,"email":email,"role":role,"name":getattr(user,"name",email)}
    except Exception: pass
    return {"id":"local-user","sub":"local-user","email":"local-user",
            "role":os.getenv("DEFAULT_AUTH_ROLE","admin"),"name":"Local User"}

def require(min_role="viewer"):
    u=current_user()
    if not u: return False,None
    return ROLES.get(u.get("role","viewer"),0)>=ROLES.get(min_role,10),u
