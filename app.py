# app.py
# Aplikasi utama Flask untuk PaceMate - Sistem Informasi Pengatur Pace Lari
# Tahap ini fokus pada: autentikasi admin (login/logout) + proteksi dashboard.

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash

import database
import pace_engine

app = Flask(__name__)
app.secret_key = "ganti-dengan-secret-key-yang-lebih-aman"  # dipakai untuk session & flash message

# Daftarkan fungsi terkait database (close_db, CLI 'flask init-db') ke app
database.init_app(app)

# Jenis latihan yang valid, dipakai untuk validasi form /lapor
JENIS_LATIHAN_VALID = ["easy", "tempo", "interval", "long_run"]


# ---------------------------------------------------------------------------
# DECORATOR: login_required
# Melindungi route agar hanya bisa diakses jika admin sudah login (ada session).
# Cara pakai: taruh @login_required tepat di atas @app.route pada fungsi view.
# ---------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("admin_id") is None:
            flash("Silakan login terlebih dahulu untuk mengakses halaman ini.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


# ---------------------------------------------------------------------------
# ROUTE PUBLIK: Beranda
# Tidak butuh login sama sekali -- ini halaman pengenalan aplikasi.
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# ---------------------------------------------------------------------------
# ROUTE PUBLIK: Generator Jadwal Latihan Mingguan
# GET  -> tampilkan form kosong
# POST -> validasi input, hitung jadwal lewat pace_engine, tampilkan hasil
# ---------------------------------------------------------------------------
@app.route("/jadwal", methods=["GET", "POST"])
def jadwal():
    jadwal_hasil = None
    prediksi_race = None
    vdot = None
    pr_menit_input = None
    level_input = None

    if request.method == "POST":
        pr_menit_raw = request.form.get("pr_menit", "").strip()
        level_input = request.form.get("level", "").strip()

        # --- Validasi server-side (tetap wajib walau sudah ada validasi HTML5) ---
        error = None
        try:
            pr_menit_input = float(pr_menit_raw)
        except ValueError:
            error = "Waktu PR harus berupa angka."
        else:
            # Batas realistis waktu tempuh 5K: 10-60 menit
            if not (10 <= pr_menit_input <= 60):
                error = "Waktu PR 5K harus antara 10 dan 60 menit (nilai yang realistis)."

        if level_input not in ("pemula", "menengah", "lanjutan"):
            error = "Level harus dipilih: pemula, menengah, atau lanjutan."

        if error:
            flash(error, "danger")
        else:
            # Hitung jadwal 7 hari + VDOT lewat pace_engine
            jadwal_hasil, vdot = pace_engine.generate_jadwal(pr_menit_input, level_input)
            # Bonus: prediksi waktu race di jarak lain (Riegel Formula)
            prediksi_race = pace_engine.hitung_prediksi_race(pr_menit_input)

    return render_template(
        "jadwal.html",
        jadwal_hasil=jadwal_hasil,
        prediksi_race=prediksi_race,
        vdot=vdot,
        pr_menit_input=pr_menit_input,
        level_input=level_input,
    )


# ---------------------------------------------------------------------------
# ROUTE PUBLIK: Form Submit Sesi Latihan
# GET  -> tampilkan form (dropdown pelari diambil dari tabel pelari)
# POST -> validasi, hitung pace_hasil otomatis, simpan ke tabel sesi_latihan
# ---------------------------------------------------------------------------
@app.route("/lapor", methods=["GET", "POST"])
def lapor():
    db = database.get_db()

    if request.method == "POST":
        pelari_id = request.form.get("pelari_id", "").strip()
        tanggal = request.form.get("tanggal", "").strip()
        jarak_km_raw = request.form.get("jarak_km", "").strip()
        waktu_menit_raw = request.form.get("waktu_menit", "").strip()
        jenis_latihan = request.form.get("jenis_latihan", "").strip()

        # --- Validasi: semua field wajib diisi ---
        error = None
        if not all([pelari_id, tanggal, jarak_km_raw, waktu_menit_raw, jenis_latihan]):
            error = "Semua field wajib diisi."

        jarak_km = waktu_menit = None
        if error is None:
            try:
                jarak_km = float(jarak_km_raw)
                waktu_menit = float(waktu_menit_raw)
            except ValueError:
                error = "Jarak dan waktu harus berupa angka."

        if error is None and (jarak_km <= 0 or waktu_menit <= 0):
            error = "Jarak dan waktu harus bernilai positif."

        if error is None and jenis_latihan not in JENIS_LATIHAN_VALID:
            error = "Jenis latihan tidak valid."

        if error:
            flash(error, "danger")
        else:
            # Hitung pace_hasil otomatis: menit per km = waktu total / jarak total
            pace_hasil = waktu_menit / jarak_km
            db.execute(
                """INSERT INTO sesi_latihan
                   (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil),
            )
            db.commit()
            flash("Sesi latihan berhasil dicatat.", "success")
            return redirect(url_for("lapor"))

    # Ambil daftar pelari untuk dropdown
    daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
    return render_template("lapor.html", daftar_pelari=daftar_pelari)


# ---------------------------------------------------------------------------
# ROUTE PUBLIK: Progres — rekap sesi latihan dikelompokkan per pelari
# ---------------------------------------------------------------------------
@app.route("/progres", methods=["GET"])
def progres():
    db = database.get_db()

    daftar_pelari = db.execute("SELECT * FROM pelari ORDER BY nama").fetchall()

    data_progres = []
    for p in daftar_pelari:
        # Total km 7 hari terakhir (minggu berjalan, dihitung dari tanggal hari ini)
        total_km_minggu = db.execute(
            """SELECT COALESCE(SUM(jarak_km), 0) AS total
               FROM sesi_latihan
               WHERE pelari_id = ?
                 AND tanggal >= date('now', '-6 days')""",
            (p["id"],),
        ).fetchone()["total"]

        # 5 sesi terbaru milik pelari ini
        sesi_terbaru = db.execute(
            """SELECT * FROM sesi_latihan
               WHERE pelari_id = ?
               ORDER BY tanggal DESC, id DESC
               LIMIT 5""",
            (p["id"],),
        ).fetchall()

        data_progres.append({
            "pelari": p,
            "total_km_minggu": total_km_minggu,
            "sesi_terbaru": sesi_terbaru,
        })

    return render_template("progres.html", data_progres=data_progres, format_pace=pace_engine.format_pace)


# ---------------------------------------------------------------------------
# ROUTE: Login
# ---------------------------------------------------------------------------
@app.route("/login", methods=["GET", "POST"])
def login():
    # Jika admin sudah login, langsung lempar ke dashboard
    if session.get("admin_id") is not None:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = database.get_db()
        admin = db.execute(
            "SELECT * FROM admin WHERE username = ?", (username,)
        ).fetchone()

        # Verifikasi username ada DAN password cocok dengan hash yang tersimpan
        if admin is None or not check_password_hash(admin["password_hash"], password):
            flash("Username atau password salah.", "danger")
            return redirect(url_for("login"))

        # Login berhasil -> simpan identitas admin ke session
        session.clear()
        session["admin_id"] = admin["id"]
        session["username"] = admin["username"]
        flash(f"Selamat datang kembali, {admin['username']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# ROUTE: Dashboard (contoh halaman yang diproteksi login_required)
# ---------------------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html", username=session.get("username"))


if __name__ == "__main__":
    app.run(debug=True)