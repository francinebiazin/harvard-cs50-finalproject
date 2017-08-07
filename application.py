from flask import Flask
from flask import (flash, g, redirect, render_template, request, session, url_for)
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
import sqlite3
import os
import datetime

from helpers import *

# configure application
app = Flask(__name__)

# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# configure database
DATABASE = 'database.db'

def connect_db(db_name):
    return sqlite3.connect(db_name)

@app.before_request
def before_request():
    g.db = connect_db(DATABASE)
    

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register new user"""
    
    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure username was submitted
        if not request.form.get("username"):
            flash("You must provide a username")
            return render_template("register.html")
        
        # check if username already exists before registering new user
        cursor = g.db.execute("SELECT * FROM users WHERE username=:username;", {'username': request.form.get("username")})
        if cursor.fetchone() is not None:
            flash("Username is already taken")
            return render_template("register.html")
        
        # ensure password was submitted
        if not request.form.get("password"):
            flash("You must provide a password")
            return render_template("register.html")
        
        # ensure password at least 6 characters long
        if len(request.form.get("password")) < 6:
            flash("Your password must be at least 6 characters long")
            return render_template("register.html")
        
        # ensure password was confirmed
        if not request.form.get("confirmpassword"):
            flash("You must confirm your password")
            return render_template("register.html")
            
        # ensure password was typed correctly
        if not request.form.get("password") == request.form.get("confirmpassword"):
            flash("Passwords do not match")
            return render_template("register.html")
            
        # ensure first name was submitted
        if not request.form.get("firstname"):
            flash("You must provide a first name")
            return render_template("register.html")
        
        # ensure last_name was submitted
        if not request.form.get("lastname"):
            flash("You must provide a last name")
            return render_template("register.html")
            
        # protect password
        hashed_password = hash_password(request.form.get("password"))
        
        # insert user into database
        query = """
            INSERT INTO users
            (username, password, first_name, last_name)
            VALUES(:username, :password, :first_name, :last_name);
        """
        params = {
            'username': request.form.get("username"),
            'password': hashed_password,
            'first_name': request.form.get("firstname"),
            'last_name': request.form.get("lastname"),
        }
        g.db.execute(query, params)
        g.db.commit()
        flash("Your registration is complete!")
        
        # query database for username
        rows = g.db.execute("SELECT * FROM users WHERE username=:username;", {'username': request.form.get("username")})
        user = rows.fetchone()

        # log in user
        session["user_id"] = user[0]

        # redirect user to home page
        return redirect(url_for("index"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/")
def index():
    """Show index page."""
    return render_template('index.html')


@app.route("/login", methods=['GET', 'POST'])
def login():
    """Log user in"""
    
    # forget any user_id
    session.clear()
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == 'POST':
        
        # ensure username was submitted
        if not request.form.get("username"):
            flash("You must provide a username")
            return render_template('login.html')

        # ensure password was submitted
        if not request.form.get("password"):
            flash("You must provide a password")
            return render_template('login.html')
        
        # save username and password
        username = request.form['username']
        password = hash_password(request.form['password'])
        
        # query database for user details
        cursor = g.db.execute('SELECT * FROM users WHERE username=:username AND password=:password;', {'username': username, 'password': password})
        
        # check if user and password match
        try:
            user = cursor.fetchone()
            session['user_id'] = user[0]
            return redirect(url_for("index"))
        except:
            flash("Invalid username or password")
            return render_template('login.html')
        

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        if 'user_id' in session:
            return redirect(url_for("index"))
        return render_template('login.html')


@app.route("/today", methods=['GET', 'POST'])
@login_required
def today():
    """Display today's water intake and allow user to submit more"""
    
    # get history from database
    cursor = g.db.execute('SELECT * FROM water WHERE user_id=:user_id;', {'user_id': session['user_id']})
    history = cursor.fetchall()
    
    # loop through history to get today's:
    total = 0
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    for entry in history:
        if date in entry[2]:
            total += entry[3]
    litres = "%.2f" % ( total / 1000 )
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # ensure quantity was submitted
        if not request.form.get("quantity"):
            flash("Must provide quantity")
            return render_template('today.html')
            
        # ensure quantity was numerical
        try:
            quantity = float(request.form.get("quantity"))
        except:
            flash("Must provide numerical quantity")
            return render_template('today.html')
        
        # insert quantity into database
        query = """
            INSERT INTO water
            (user_id, quantity)
            VALUES(:user_id, :quantity);
        """
        params = {
            'user_id': session['user_id'],
            'quantity': quantity,
        }
        g.db.execute(query, params)
        g.db.commit()
        flash("Your water intake was submitted!")

        # refresh
        return render_template("today.html", quantity=litres)

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("today.html", quantity=litres)


@app.route("/history")
@login_required
def history():
    """Show history of water intake."""
    
    # query database for user's complete history
    cursor = g.db.execute("SELECT post_date, quantity FROM water WHERE user_id=:user_id ORDER BY datetime(post_date) DESC;", {'user_id': session["user_id"]})
    rows = cursor.fetchall()
    
    # build complete history array
    history1 = [dict(date=entry[0], quantity="%.1f" % entry[1]) for entry in rows]
    
    # build temporary dictionary of day by day history
    temp = {}
    for entry in rows:
        if entry[0][:10] not in temp.keys():
            temp[entry[0][:10]] = entry[1]
        else:
            temp[entry[0][:10]] += entry[1]
    
    # build day by day array
    hist = [dict(date=entry, quantity="%.2f" % (float(temp[entry]) / 1000)) for entry in temp]
    
    # sort day by day array
    # idea taken from https://stackoverflow.com/a/40117195
    history2 = sorted(hist, key=lambda d: d['date'], reverse=True)


    return render_template("history.html", history1=history1[:30], history2=history2[:30])


@app.route("/logout")
@login_required
def logout():
    """Log user out."""
    
    session.pop('user_id')
    
    return render_template('index.html')


@app.route("/change", methods=['GET', 'POST'])
@login_required
def change():
    """Change password."""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
    
        # query database for user info
        cursor = g.db.execute("SELECT * FROM users WHERE id=:user_id;", {'user_id': session['user_id']})
        user = cursor.fetchone()
        
        # ensure password was submitted
        if not request.form.get("password"):
            flash("You must provide your current password")
            return render_template('change.html')
        
        # ensure password is correct
        old = hash_password(request.form.get("password"))
        if old != user[2]:
            flash("Your current password is incorrect")
            return render_template('change.html')
        
        # ensure new password was submitted
        if not request.form.get("newpassword"):
            flash("You must provide a new password")
            return render_template('change.html')
        
        # ensure password was confirmed
        if not request.form.get("confirmpassword"):
            flash("You must confirm your password")
            return render_template('change.html')
        
        # ensure new password is different from old password
        if request.form.get("newpassword") == request.form.get("password"):
            flash("Your new password must be different from your old one")
            return render_template('change.html')
        
        # ensure password at least 6 characters long
        if len(request.form.get("newpassword")) < 6:
            flash("Your password must be at least 6 characters long")
            return render_template('change.html')
            
        # ensure password was typed correctly
        if not request.form.get("newpassword") == request.form.get("confirmpassword"):
            flash("Passwords do not match")
            return render_template('change.html')
        
        # protect password
        hashed_password = hash_password(request.form.get("newpassword"))
        
        # change password in database
        g.db.execute("UPDATE users SET password=:password WHERE id=:user_id;", {'password': hashed_password, 'user_id': session['user_id']})
        g.db.commit()
        flash("Your password has been successfully changed!")
        
        return render_template('index.html')
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("change.html")


@app.route("/delete", methods=['GET', 'POST'])
@login_required
def delete():
    """Delete user account and history."""
    
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == 'POST':
        
        # query database for user info
        cursor = g.db.execute("SELECT * FROM users WHERE id=:user_id;", {'user_id': session['user_id']})
        user = cursor.fetchone()
        
        # ensure password was submitted
        if not request.form.get("password"):
            flash("You must provide your password")
            return render_template('delete.html')
        
        # ensure password is correct
        password = hash_password(request.form.get("password"))
        if password != user[2]:
            flash("Your password is incorrect")
            return render_template('delete.html')
        
        # query database for user history
        rows = g.db.execute("SELECT * FROM water WHERE user_id=:user_id;", {'user_id': session['user_id']})
        history = rows.fetchall()
        
        # delete each entry to water from user
        if history is not None:
            for entry in history:
                g.db.execute("DELETE FROM water WHERE id={};".format(entry[0]))
                g.db.commit()
        
        # delete user
        if user is not None:
            g.db.execute("DELETE FROM users WHERE id={};".format(session['user_id']))
            g.db.commit()
            flash("Your account has been successfully deleted!")
        
        logout()

        return render_template('index.html')
    
    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("delete.html")


# configure flask for C9
if __name__ == '__main__':
    app.debug = True
    host = os.environ.get('IP', '0.0.0.0')
    port = int(os.environ.get('PORT', 8080))
    app.run(host=host, port=port)