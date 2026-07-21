from flask import render_template, request, redirect, url_for, flash
from werkzeug.security import generate_password_hash
import database
import pace_engine
from utils import admin_required

def register_routes(app):
    @app.route("/admin/dashboard")
    @admin_required
    def admin_dashboard():
        db = database.get_db()

        # --- Kartu ringkasan ---
        total_pelari = db.execute("SELECT COUNT(*) AS c FROM pelari").fetchone()["c"]
        total_sesi = db.execute("SELECT COUNT(*) AS c FROM sesi_latihan").fetchone()["c"]

        # SQLite: date('now', '-6 days') -> Postgres: CURRENT_DATE - INTERVAL '6 days'
        total_km_minggu = db.execute(
            """SELECT COALESCE(SUM(jarak_km), 0) AS total
               FROM sesi_latihan
               WHERE tanggal >= CURRENT_DATE - INTERVAL '6 days'"""
        ).fetchone()["total"]

        # --- Data grafik: rata-rata pace 4 minggu terakhir ---
        # SQLite: strftime('%Y-W%W', tanggal) -> Postgres: to_char(tanggal, 'IYYY-"W"IW')
        # to_char menggunakan IYYY (ISO year) dan IW (ISO week number) agar
        # penomoran minggu konsisten dengan standar ISO 8601.
        # SQLite: date('now', '-27 days') -> Postgres: CURRENT_DATE - INTERVAL '27 days'
        rows = db.execute(
            """SELECT to_char(tanggal, 'IYYY-"W"IW') AS minggu_label,
                      AVG(pace_hasil) AS avg_pace
               FROM sesi_latihan
               WHERE tanggal >= CURRENT_DATE - INTERVAL '27 days'
               GROUP BY minggu_label
               ORDER BY minggu_label"""
        ).fetchall()

        chart_labels = [r["minggu_label"] for r in rows]
        chart_values = [round(float(r["avg_pace"]), 2) for r in rows]

        # --- Hitung pelari berisiko lonjakan volume ---
        TARGET_MINGGUAN = {"pemula": 14, "menengah": 26, "lanjutan": 40}
        daftar_pelari_all = db.execute("SELECT id, level FROM pelari").fetchall()
        jumlah_berisiko = 0
        for p in daftar_pelari_all:
            # SQLite: date('now', '-6 days') -> Postgres: CURRENT_DATE - INTERVAL '6 days'
            km_minggu_ini = db.execute(
                "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = %s AND tanggal >= CURRENT_DATE - INTERVAL '6 days'",
                (p["id"],)
            ).fetchone()["total"]
            # SQLite: date('now', '-34 days') & date('now', '-6 days')
            # -> Postgres: CURRENT_DATE - INTERVAL '34 days' & CURRENT_DATE - INTERVAL '6 days'
            km_4minggu = db.execute(
                "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = %s AND tanggal >= CURRENT_DATE - INTERVAL '34 days' AND tanggal < CURRENT_DATE - INTERVAL '6 days'",
                (p["id"],)
            ).fetchone()["total"]
            rata2 = km_4minggu / 4
            baseline = rata2 if rata2 > 0 else TARGET_MINGGUAN.get(p["level"], 14)
            if (km_minggu_ini / baseline) > 1.3:
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

    @app.route("/admin/risiko")
    @admin_required
    def admin_risiko():
        db = database.get_db()
        daftar_pelari = db.execute("SELECT id, nama, level FROM pelari ORDER BY nama").fetchall()
        TARGET_MINGGUAN = {"pemula": 14, "menengah": 26, "lanjutan": 40}
        
        data_risiko = []
        for p in daftar_pelari:
            # SQLite: date('now', '-6 days') -> Postgres: CURRENT_DATE - INTERVAL '6 days'
            total_km_minggu_ini = db.execute(
                "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = %s AND tanggal >= CURRENT_DATE - INTERVAL '6 days'", (p["id"],)
            ).fetchone()["total"]
            
            # SQLite: date('now', '-34 days') & date('now', '-6 days')
            # -> Postgres: CURRENT_DATE - INTERVAL '34 days' & CURRENT_DATE - INTERVAL '6 days'
            total_km_4minggu = db.execute(
                "SELECT COALESCE(SUM(jarak_km), 0) AS total FROM sesi_latihan WHERE pelari_id = %s AND tanggal >= CURRENT_DATE - INTERVAL '34 days' AND tanggal < CURRENT_DATE - INTERVAL '6 days'", (p["id"],)
            ).fetchone()["total"]
            
            rata2_km_4minggu = total_km_4minggu / 4
            baseline = rata2_km_4minggu if rata2_km_4minggu > 0 else TARGET_MINGGUAN.get(p["level"], 14)
            
            rasio = total_km_minggu_ini / baseline
            berisiko = rasio > 1.3
                    
            data_risiko.append({
                "id": p["id"],
                "nama": p["nama"],
                "level": p["level"],
                "total_km_minggu_ini": total_km_minggu_ini,
                "rata2_km_4minggu": rata2_km_4minggu,
                "baseline": baseline,
                "rasio": rasio,
                "berisiko": berisiko
            })
            
        data_risiko.sort(key=lambda x: (not x["berisiko"], x["nama"]))
        return render_template("admin_risiko.html", active_menu="risiko", data_risiko=data_risiko)

    @app.route("/admin/pelari/<int:pelari_id>/peringatkan", methods=["POST"])
    @admin_required
    def admin_pelari_peringatkan(pelari_id):
        pesan = request.form.get("pesan", "").strip()
        if not pesan:
            flash("Pesan peringatan tidak boleh kosong.", "danger")
            return redirect(url_for("admin_risiko"))
            
        db = database.get_db()
        db.execute("UPDATE pelari SET peringatan_admin = %s WHERE id = %s", (pesan, pelari_id))
        db.commit()
        flash("Peringatan berhasil dikirim ke pelari.", "success")
        return redirect(url_for("admin_risiko"))

    @app.route("/admin/pelari")
    @admin_required
    def admin_pelari_list():
        db = database.get_db()
        daftar_pelari = db.execute("SELECT * FROM pelari ORDER BY nama").fetchall()
        return render_template("admin_pelari.html", active_menu="pelari", daftar_pelari=daftar_pelari)

    @app.route("/admin/pelari/tambah", methods=["GET", "POST"])
    @admin_required
    def admin_pelari_tambah():
        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            usia_raw = request.form.get("usia", "").strip()
            level = request.form.get("level", "").strip()
            pr_raw = request.form.get("pr_5k_menit", "").strip()

            error = None
            if not nama or not username or not password:
                error = "Nama, Username, dan Password wajib diisi."

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
                    
            db = database.get_db()
            if error is None:
                existing = db.execute("SELECT id FROM pelari WHERE username = %s", (username,)).fetchone()
                if existing:
                    error = "Username sudah digunakan."

            if error:
                flash(error, "danger")
            else:
                password_hash = generate_password_hash(password)
                db.execute(
                    "INSERT INTO pelari (username, password_hash, nama, usia, level, pr_5k_menit) VALUES (%s, %s, %s, %s, %s, %s)",
                    (username, password_hash, nama, usia, level, pr_5k),
                )
                db.commit()
                flash(f"Pelari '{nama}' berhasil ditambahkan.", "success")
                return redirect(url_for("admin_pelari_list"))

        return render_template("admin_pelari_form.html", active_menu="pelari", pelari=None)

    @app.route("/admin/pelari/<int:pelari_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_pelari_edit(pelari_id):
        db = database.get_db()
        pelari = db.execute("SELECT * FROM pelari WHERE id = %s", (pelari_id,)).fetchone()

        if pelari is None:
            flash("Data pelari tidak ditemukan.", "danger")
            return redirect(url_for("admin_pelari_list"))

        if request.method == "POST":
            nama = request.form.get("nama", "").strip()
            username = request.form.get("username", "").strip()
            password = request.form.get("password", "")
            usia_raw = request.form.get("usia", "").strip()
            level = request.form.get("level", "").strip()
            pr_raw = request.form.get("pr_5k_menit", "").strip()

            error = None
            if not nama or not username:
                error = "Nama dan Username tidak boleh kosong."

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
                    
            if error is None:
                existing = db.execute("SELECT id FROM pelari WHERE username = %s AND id != %s", (username, pelari_id)).fetchone()
                if existing:
                    error = "Username sudah digunakan oleh pengguna lain."

            if error:
                flash(error, "danger")
            else:
                if password:
                    password_hash = generate_password_hash(password)
                    db.execute(
                        "UPDATE pelari SET username = %s, password_hash = %s, nama = %s, usia = %s, level = %s, pr_5k_menit = %s WHERE id = %s",
                        (username, password_hash, nama, usia, level, pr_5k, pelari_id),
                    )
                else:
                    db.execute(
                        "UPDATE pelari SET username = %s, nama = %s, usia = %s, level = %s, pr_5k_menit = %s WHERE id = %s",
                        (username, nama, usia, level, pr_5k, pelari_id),
                    )
                db.commit()
                flash("Data pelari berhasil diperbarui.", "success")
                return redirect(url_for("admin_pelari_list"))

        return render_template("admin_pelari_form.html", active_menu="pelari", pelari=pelari)

    @app.route("/admin/pelari/<int:pelari_id>/hapus", methods=["POST"])
    @admin_required
    def admin_pelari_hapus(pelari_id):
        db = database.get_db()
        pelari = db.execute("SELECT nama FROM pelari WHERE id = %s", (pelari_id,)).fetchone()

        if pelari is None:
            flash("Data pelari tidak ditemukan.", "danger")
        else:
            db.execute("DELETE FROM pelari WHERE id = %s", (pelari_id,))
            db.commit()
            flash(f"Pelari '{pelari['nama']}' beserta seluruh sesi latihannya berhasil dihapus.", "success")

        return redirect(url_for("admin_pelari_list"))

    @app.route("/admin/sesi")
    @admin_required
    def admin_sesi_list():
        db = database.get_db()
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
    @admin_required
    def admin_sesi_tambah():
        db = database.get_db()
        from utils import JENIS_LATIHAN_VALID

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
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil),
                )
                db.commit()
                flash("Sesi latihan berhasil ditambahkan.", "success")
                return redirect(url_for("admin_sesi_list"))

        daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
        return render_template("admin_sesi_form.html", active_menu="sesi", sesi=None, daftar_pelari=daftar_pelari)

    @app.route("/admin/sesi/<int:sesi_id>/edit", methods=["GET", "POST"])
    @admin_required
    def admin_sesi_edit(sesi_id):
        db = database.get_db()
        from utils import JENIS_LATIHAN_VALID
        sesi = db.execute("SELECT * FROM sesi_latihan WHERE id = %s", (sesi_id,)).fetchone()

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
                       SET pelari_id=%s, tanggal=%s, jarak_km=%s,
                           waktu_menit=%s, jenis_latihan=%s, pace_hasil=%s
                       WHERE id=%s""",
                    (pelari_id, tanggal, jarak_km, waktu_menit, jenis_latihan, pace_hasil, sesi_id),
                )
                db.commit()
                flash("Sesi latihan berhasil diperbarui.", "success")
                return redirect(url_for("admin_sesi_list"))

        daftar_pelari = db.execute("SELECT id, nama FROM pelari ORDER BY nama").fetchall()
        return render_template("admin_sesi_form.html", active_menu="sesi", sesi=sesi, daftar_pelari=daftar_pelari)

    @app.route("/admin/sesi/<int:sesi_id>/hapus", methods=["POST"])
    @admin_required
    def admin_sesi_hapus(sesi_id):
        db = database.get_db()
        sesi = db.execute("SELECT id FROM sesi_latihan WHERE id = %s", (sesi_id,)).fetchone()

        if sesi is None:
            flash("Data sesi latihan tidak ditemukan.", "danger")
        else:
            db.execute("DELETE FROM sesi_latihan WHERE id = %s", (sesi_id,))
            db.commit()
            flash("Sesi latihan berhasil dihapus.", "success")

        return redirect(url_for("admin_sesi_list"))
