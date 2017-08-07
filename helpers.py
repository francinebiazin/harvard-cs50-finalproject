from flask import redirect, render_template, request, session, url_for
from functools import wraps
from hashlib import md5

def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.11/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def hash_password(password):
    """Hashes a password to keep it protected"""
    
    hashed = md5(password.encode('utf-8')).hexdigest()
    
    return hashed
    