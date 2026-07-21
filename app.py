# app.py
# Aplikasi utama Flask untuk PaceMate - Sistem Informasi Pengatur Pace Lari
# File ini telah direfactor dengan pendekatan Modular untuk mengorganisir routes

from flask import Flask, session
import database

# Import modul routes
import routes_auth
import routes_public
import routes_admin

app = Flask(__name__)
app.secret_key = "c6ee2b4b00d23d3a85c8a8512ef35993e72be21de38fdbdeed3b63e2c9501572"  # dipakai untuk session & flash message

# Daftarkan fungsi terkait database (close_db, CLI 'flask init-db') ke app
database.init_app(app)

# Inject current_pelari ke semua template
@app.context_processor
def inject_user():
    current_pelari = None
    if session.get("pelari_id"):
        db = database.get_db()
        current_pelari = db.execute("SELECT * FROM pelari WHERE id = %s", (session["pelari_id"],)).fetchone()
    return dict(current_pelari=current_pelari)

# Registrasi seluruh route dari modul-modul
routes_auth.register_routes(app)
routes_public.register_routes(app)
routes_admin.register_routes(app)

if __name__ == "__main__":
    app.run(debug=True)