from flask import render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
import database

def register_routes(app):
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if session.get("pelari_id") is not None or session.get("admin_id") is not None:
            return redirect(url_for("index"))

        if request.method == "POST":
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            nama = request.form.get("nama", "").strip()
            usia = request.form.get("usia", "").strip()
            level = request.form.get("level", "").strip()
            pr_5k = request.form.get("pr_5k_menit", "").strip()

            db = database.get_db()
            
            # Validasi duplikat username (admin/pelari)
            existing_pelari = db.execute("SELECT id FROM pelari WHERE username = ?", (username,)).fetchone()
            existing_admin = db.execute("SELECT id FROM admin WHERE username = ?", (username,)).fetchone()
            
            if existing_pelari or existing_admin:
                flash("Username sudah digunakan, silakan pilih yang lain.", "danger")
                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)
            db.execute(
                """INSERT INTO pelari (username, password_hash, nama, usia, level, pr_5k_menit) 
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (username, password_hash, nama, int(usia) if usia else 25, level, float(pr_5k) if pr_5k else 0.0)
            )
            db.commit()
            flash("Pendaftaran berhasil! Silakan login.", "success")
            return redirect(url_for("login"))

        return render_template("register.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            role = request.form.get("role")
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")

            db = database.get_db()

            if role == "admin":
                # Cek Admin
                admin_user = db.execute("SELECT * FROM admin WHERE username = ?", (username,)).fetchone()
                if admin_user and check_password_hash(admin_user["password_hash"], password):
                    session.clear()
                    session["admin_id"] = admin_user["id"]
                    flash("Login admin berhasil.", "success")
                    return redirect(url_for("admin_dashboard"))
                flash("Username atau password admin salah.", "danger")
            else:
                # Cek Pelari
                pelari = db.execute("SELECT * FROM pelari WHERE username = ?", (username,)).fetchone()
                if pelari and check_password_hash(pelari["password_hash"], password):
                    session.clear()
                    session["pelari_id"] = pelari["id"]
                    flash(f"Selamat datang kembali, {pelari['nama']}!", "success")
                    return redirect(url_for("index"))
                flash("Username atau password pelari salah.", "danger")

        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("Anda telah logout.", "info")
        return redirect(url_for("login"))
