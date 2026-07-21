from functools import wraps
from flask import session, flash, redirect, url_for

# Jenis latihan yang valid, dipakai untuk validasi form /lapor dan CRUD sesi
JENIS_LATIHAN_VALID = ["easy", "tempo", "interval", "long_run"]

def admin_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("admin_id") is None:
            flash("Silakan login terlebih dahulu untuk mengakses halaman ini.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view

def pelari_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("pelari_id") is None:
            flash("Silakan login sebagai Pelari untuk mengakses halaman ini.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view
