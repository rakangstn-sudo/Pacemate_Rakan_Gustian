# app.py
# Aplikasi utama Flask untuk PaceMate - Sistem Informasi Pengatur Pace Lari
# Mencakup: route publik (beranda, jadwal, lapor, progres),
#           autentikasi admin, dan CRUD admin (dashboard, pelari, sesi latihan).

from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import check_password_hash

import database
import pace_engine

app = Flask(__name__)
app.secret_key = "ganti-dengan-secret-key-yang-lebih-aman"  # dipakai untuk session & flash message

# Daftarkan fungsi terkait database (close_db, CLI 'flask init-db') ke app
database.init_app(app)

# Jenis latihan yang valid, dipakai untuk validasi form /lapor dan CRUD sesi
JENIS_LATIHAN_VALID = ["easy", "tempo", "interval", "long_run"]


# ---------------------------------------------------------------------------
# DECORATOR: login_required
# Melindungi route agar hanya bisa diakses jika admin sudah login (ada session).
# ---------------------------------------------------------------------------
def login_required(view_func):
    @wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if session.get("admin_id") is None:
            flash("Silakan login terlebih dahulu untuk mengakses halaman ini.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped_view


# ===========================================================================
# ROUTE PUBLIK
# ===========================================================================

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


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

        error = None
        try:
            pr_menit_input = float(pr_menit_raw)
        except ValueError:
            error = "Waktu PR harus berupa angka."
        else:
            if not (10 <= pr_menit_input <= 60):
                error = "Waktu PR 5K harus antara 10 dan 60 menit (nilai yang realistis)."

        if level_input not in ("pemula", "menengah", "lanjutan"):
            error = "Level harus dipilih: pemula, menengah, atau lanjutan."

        if error:
            flash(error, "danger")
        else:
            jadwal_hasil, vdot = pace_engine.generate_jadwal(pr_menit_input, level_input)
            prediksi_race = pace_engine.hitung_prediksi_race(pr_menit_input)

    return render_template(
        "jadwal.html",
        jadwal_hasil=jadwal_hasil,
        prediksi_race=prediksi_race,
        vdot=vdot,
        pr_menit_input=pr_menit_input,
        level_input=level_input,
    )


@app.route("/lapor", methods=["GET", "POST"])
def lapor():
    db = database.get_db()

    if request.method == "POST":
        pelari_id = request.form.get("pelari_id", "").strip()
        tanggal = request.form.get("tanggal", "").strip()
        jarak_km_raw = request.form.get("jarak_km", "").strip()
        waktu_menit_raw = request.form.get("waktu_menit", "").strip()
        jenis_latihan = request.form.get("jenis_latihan", "").strip()

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

    daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
    return render_template("lapor.html", daftar_pelari=daftar_pelari)


@app.route("/progres", methods=["GET"])
def progres():
    db = database.get_db()

    daftar_pelari = db.execute("SELECT * FROM pelari ORDER BY nama").fetchall()

    data_progres = []
    for p in daftar_pelari:
        total_km_minggu = db.execute(
            """SELECT COALESCE(SUM(jarak_km), 0) AS total
               FROM sesi_latihan
               WHERE pelari_id = ?
                 AND tanggal >= date('now', '-6 days')""",
            (p["id"],),
        ).fetchone()["total"]

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


# ===========================================================================
# ROUTE: Login & Logout
# ===========================================================================

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("admin_id") is not None:
        return redirect(url_for("admin_dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        db = database.get_db()
        admin = db.execute(
            "SELECT * FROM admin WHERE username = ?", (username,)
        ).fetchone()

        if admin is None or not check_password_hash(admin["password_hash"], password):
            flash("Username atau password salah.", "danger")
            return redirect(url_for("login"))

        session.clear()
        session["admin_id"] = admin["id"]
        session["username"] = admin["username"]
        flash(f"Selamat datang kembali, {admin['username']}!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah logout.", "info")
    return redirect(url_for("login"))


# ===========================================================================
# ROUTE ADMIN: Dashboard
# Menampilkan ringkasan statistik dan grafik pace mingguan.
# ===========================================================================

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    db = database.get_db()

    # --- Kartu ringkasan ---
    total_pelari = db.execute("SELECT COUNT(*) AS c FROM pelari").fetchone()["c"]
    total_sesi = db.execute("SELECT COUNT(*) AS c FROM sesi_latihan").fetchone()["c"]
    total_km_minggu = db.execute(
        """SELECT COALESCE(SUM(jarak_km), 0) AS total
           FROM sesi_latihan
           WHERE tanggal >= date('now', '-6 days')"""
    ).fetchone()["total"]

    # --- Data grafik: rata-rata pace 4 minggu terakhir ---
    # Query ini mengelompokkan sesi berdasarkan minggu (ISO week number)
    # lalu menghitung rata-rata pace_hasil per minggu. strftime('%W', tanggal)
    # menghasilkan nomor minggu (00-53), digabung tahun agar unik lintas tahun.
    rows = db.execute(
        """SELECT strftime('%Y-W%W', tanggal) AS minggu_label,
                  AVG(pace_hasil) AS avg_pace
           FROM sesi_latihan
           WHERE tanggal >= date('now', '-27 days')
           GROUP BY minggu_label
           ORDER BY minggu_label"""
    ).fetchall()

    chart_labels = [r["minggu_label"] for r in rows]
    chart_values = [round(r["avg_pace"], 2) for r in rows]

    # --- Hitung pelari berisiko lonjakan volume ---
    daftar_pelari_all = db.execute("SELECT id FROM pelari").fetchall()
    jumlah_berisiko = 0
    for p in daftar_pelari_all:
        km_minggu_ini = db.execute(
            "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = ? AND tanggal >= date('now', '-6 days')",
            (p["id"],)
        ).fetchone()["total"]
        km_4minggu = db.execute(
            "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = ? AND tanggal >= date('now', '-34 days') AND tanggal < date('now', '-6 days')",
            (p["id"],)
        ).fetchone()["total"]
        rata2 = km_4minggu / 4
        if rata2 > 0 and (km_minggu_ini / rata2) > 1.3:
            jumlah_berisiko += 1

    return render_template(
        "admin_dashboard.html",
        active_menu="dashboard",
        total_pelari=total_pelari,
        total_sesi=total_sesi,
        total_km_minggu=total_km_minggu,
        chart_labels=chart_labels,
        chart_values=chart_values,
        jumlah_berisiko=jumlah_berisiko,
    )


# ===========================================================================
# ROUTE ADMIN: Deteksi Risiko
# ===========================================================================

@app.route("/admin/risiko")
@login_required
def admin_risiko():
    db = database.get_db()
    daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
    
    data_risiko = []
    for p in daftar_pelari:
        # total_km_minggu_ini = 7 hari terakhir (hari ini - 6 hari)
        total_km_minggu_ini = db.execute(
            "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = ? AND tanggal >= date('now', '-6 days')", (p["id"],)
        ).fetchone()["total"]
        
        # total 4 minggu sebelumnya = 28 hari (dari -34 hari s.d. -7 hari)
        total_km_4minggu = db.execute(
            "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = ? AND tanggal >= date('now', '-34 days') AND tanggal < date('now', '-6 days')", (p["id"],)
        ).fetchone()["total"]
        
        rata2_km_4minggu = total_km_4minggu / 4
        rasio = None
        berisiko = False
        
        if rata2_km_4minggu > 0:
            rasio = total_km_minggu_ini / rata2_km_4minggu
            if rasio > 1.3:
                berisiko = True
                
        data_risiko.append({
            "nama": p["nama"],
            "total_km_minggu_ini": total_km_minggu_ini,
            "rata2_km_4minggu": rata2_km_4minggu,
            "rasio": rasio,
            "berisiko": berisiko
        })
        
    # Urutkan agar yang berisiko tampil di atas
    data_risiko.sort(key=lambda x: (not x["berisiko"], x["nama"]))
    
    return render_template("admin_risiko.html", active_menu="risiko", data_risiko=data_risiko)


# ===========================================================================
# ROUTE ADMIN: CRUD Pelari
# ===========================================================================

@app.route("/admin/pelari")
@login_required
def admin_pelari_list():
    db = database.get_db()
    daftar_pelari = db.execute("SELECT * FROM pelari ORDER BY nama").fetchall()
    return render_template("admin_pelari.html", active_menu="pelari", daftar_pelari=daftar_pelari)


@app.route("/admin/pelari/tambah", methods=["GET", "POST"])
@login_required
def admin_pelari_tambah():
    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        usia_raw = request.form.get("usia", "").strip()
        level = request.form.get("level", "").strip()
        pr_raw = request.form.get("pr_5k_menit", "").strip()

        # --- Validasi server-side ---
        error = None
        if not nama:
            error = "Nama pelari tidak boleh kosong."

        usia = None
        if error is None:
            try:
                usia = int(usia_raw)
                if usia <= 0:
                    error = "Usia harus berupa angka positif."
            except ValueError:
                error = "Usia harus berupa angka."

        if error is None and level not in ("pemula", "menengah", "lanjutan"):
            error = "Level harus dipilih: pemula, menengah, atau lanjutan."

        pr_5k = None
        if error is None and pr_raw:
            try:
                pr_5k = float(pr_raw)
                if pr_5k <= 0:
                    error = "PR 5K harus berupa angka positif."
            except ValueError:
                error = "PR 5K harus berupa angka."

        if error:
            flash(error, "danger")
        else:
            db = database.get_db()
            db.execute(
                "INSERT INTO pelari (nama, usia, level, pr_5k_menit) VALUES (?, ?, ?, ?)",
                (nama, usia, level, pr_5k),
            )
            db.commit()
            flash(f"Pelari '{nama}' berhasil ditambahkan.", "success")
            return redirect(url_for("admin_pelari_list"))

    return render_template("admin_pelari_form.html", active_menu="pelari", pelari=None)


@app.route("/admin/pelari/<int:pelari_id>/edit", methods=["GET", "POST"])
@login_required
def admin_pelari_edit(pelari_id):
    db = database.get_db()
    pelari = db.execute("SELECT * FROM pelari WHERE id = ?", (pelari_id,)).fetchone()

    if pelari is None:
        flash("Data pelari tidak ditemukan.", "danger")
        return redirect(url_for("admin_pelari_list"))

    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        usia_raw = request.form.get("usia", "").strip()
        level = request.form.get("level", "").strip()
        pr_raw = request.form.get("pr_5k_menit", "").strip()

        error = None
        if not nama:
            error = "Nama pelari tidak boleh kosong."

        usia = None
        if error is None:
            try:
                usia = int(usia_raw)
                if usia <= 0:
                    error = "Usia harus berupa angka positif."
            except ValueError:
                error = "Usia harus berupa angka."

        if error is None and level not in ("pemula", "menengah", "lanjutan"):
            error = "Level harus dipilih: pemula, menengah, atau lanjutan."

        pr_5k = None
        if error is None and pr_raw:
            try:
                pr_5k = float(pr_raw)
                if pr_5k <= 0:
                    error = "PR 5K harus berupa angka positif."
            except ValueError:
                error = "PR 5K harus berupa angka."

        if error:
            flash(error, "danger")
        else:
            db.execute(
                "UPDATE pelari SET nama=?, usia=?, level=?, pr_5k_menit=? WHERE id=?",
                (nama, usia, level, pr_5k, pelari_id),
            )
            db.commit()
            flash(f"Data pelari '{nama}' berhasil diperbarui.", "success")
            return redirect(url_for("admin_pelari_list"))

    return render_template("admin_pelari_form.html", active_menu="pelari", pelari=pelari)


@app.route("/admin/pelari/<int:pelari_id>/hapus", methods=["POST"])
@login_required
def admin_pelari_hapus(pelari_id):
    db = database.get_db()
    pelari = db.execute("SELECT nama FROM pelari WHERE id = ?", (pelari_id,)).fetchone()

    if pelari is None:
        flash("Data pelari tidak ditemukan.", "danger")
    else:
        # CASCADE di schema.sql akan otomatis menghapus sesi_latihan terkait
        db.execute("DELETE FROM pelari WHERE id = ?", (pelari_id,))
        db.commit()
        flash(f"Pelari '{pelari['nama']}' beserta seluruh sesi latihannya berhasil dihapus.", "success")

    return redirect(url_for("admin_pelari_list"))


# ===========================================================================
# ROUTE ADMIN: CRUD Sesi Latihan
# ===========================================================================

@app.route("/admin/sesi")
@login_required
def admin_sesi_list():
    db = database.get_db()
    # JOIN ke tabel pelari untuk menampilkan nama pelari di daftar sesi
    daftar_sesi = db.execute(
        """SELECT s.*, p.nama AS nama_pelari
           FROM sesi_latihan s
           JOIN pelari p ON s.pelari_id = p.id
           ORDER BY s.tanggal DESC, s.id DESC"""
    ).fetchall()
    return render_template(
        "admin_sesi.html",
        active_menu="sesi",
        daftar_sesi=daftar_sesi,
        format_pace=pace_engine.format_pace,
    )


@app.route("/admin/sesi/tambah", methods=["GET", "POST"])
@login_required
def admin_sesi_tambah():
    db = database.get_db()

    if request.method == "POST":
        pelari_id = request.form.get("pelari_id", "").strip()
        tanggal = request.form.get("tanggal", "").strip()
        jarak_km_raw = request.form.get("jarak_km", "").strip()
        waktu_menit_raw = request.form.get("waktu_menit", "").strip()
        jenis_latihan = request.form.get("jenis_latihan", "").strip()

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
            pace_hasil = waktu_menit / jarak_km
            db.execute(
                """INSERT INTO sesi_latihan
                   (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil),
            )
            db.commit()
            flash("Sesi latihan berhasil ditambahkan.", "success")
            return redirect(url_for("admin_sesi_list"))

    daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
    return render_template("admin_sesi_form.html", active_menu="sesi", sesi=None, daftar_pelari=daftar_pelari)


@app.route("/admin/sesi/<int:sesi_id>/edit", methods=["GET", "POST"])
@login_required
def admin_sesi_edit(sesi_id):
    db = database.get_db()
    sesi = db.execute("SELECT * FROM sesi_latihan WHERE id = ?", (sesi_id,)).fetchone()

    if sesi is None:
        flash("Data sesi latihan tidak ditemukan.", "danger")
        return redirect(url_for("admin_sesi_list"))

    if request.method == "POST":
        pelari_id = request.form.get("pelari_id", "").strip()
        tanggal = request.form.get("tanggal", "").strip()
        jarak_km_raw = request.form.get("jarak_km", "").strip()
        waktu_menit_raw = request.form.get("waktu_menit", "").strip()
        jenis_latihan = request.form.get("jenis_latihan", "").strip()

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
            pace_hasil = waktu_menit / jarak_km
            db.execute(
                """UPDATE sesi_latihan
                   SET pelari_id=?, tanggal=?, jarak_km=?, waktu_menit=?,
                       jenis_latihan=?, pace_hasil=?
                   WHERE id=?""",
                (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil, sesi_id),
            )
            db.commit()
            flash("Sesi latihan berhasil diperbarui.", "success")
            return redirect(url_for("admin_sesi_list"))

    daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
    return render_template("admin_sesi_form.html", active_menu="sesi", sesi=sesi, daftar_pelari=daftar_pelari)


@app.route("/admin/sesi/<int:sesi_id>/hapus", methods=["POST"])
@login_required
def admin_sesi_hapus(sesi_id):
    db = database.get_db()
    sesi = db.execute("SELECT id FROM sesi_latihan WHERE id = ?", (sesi_id,)).fetchone()

    if sesi is None:
        flash("Data sesi latihan tidak ditemukan.", "danger")
    else:
        db.execute("DELETE FROM sesi_latihan WHERE id = ?", (sesi_id,))
        db.commit()
        flash("Sesi latihan berhasil dihapus.", "success")

    return redirect(url_for("admin_sesi_list"))


# ===========================================================================
# ROUTE LAMA: redirect /dashboard ke /admin/dashboard
# Menjaga kompatibilitas jika ada link lama yang mengarah ke /dashboard.
# ===========================================================================

@app.route("/dashboard")
@login_required
def dashboard():
    return redirect(url_for("admin_dashboard"))


if __name__ == "__main__":
    app.run(debug=True)