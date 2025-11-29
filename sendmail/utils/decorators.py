"""
Authentication and authorization decorators.
"""
from functools import wraps
from flask import session, flash, redirect, url_for


# Admin email - change this to your admin email
ADMIN_EMAIL = "manuchaturvedi28mc@gmail.com"


def login_required(f):
    """
    Decorator to require user authentication.
    Redirects to login page if user is not logged in.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            flash("Please log in first!", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator to require admin authentication.
    Redirects to landing page if not logged in.
    Redirects to dashboard if logged in but not admin.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        print(f"[DEBUG] admin_required: Checking access for route {f.__name__}", flush=True)
        if "user" not in session:
            print("[DEBUG] admin_required: No user in session", flush=True)
            flash("Please log in first!", "warning")
            return redirect(url_for('landing'))
        
        # session['user'] is a string (email), not a dict
        user_email = session.get('user', '')
        print(f"[DEBUG] admin_required: User={user_email}, Admin={ADMIN_EMAIL}", flush=True)
        if user_email != ADMIN_EMAIL:
            print(f"[DEBUG] admin_required: Access denied - not admin", flush=True)
            flash("Access denied. Admin only!", "danger")
            return redirect(url_for('landing'))
        
        print(f"[DEBUG] admin_required: Access granted", flush=True)
        return f(*args, **kwargs)
    return decorated_function
