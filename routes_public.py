from flask import render_template, request, redirect, url_for, session, flash
import database
import pace_engine
from utils import pelari_required

def register_routes(app):
    @app.route("/", methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route("/jadwal", methods=["GET"])
    @pelari_required
    def jadwal():
        db = database.get_db()
        pelari_id = session.get("pelari_id")
        pelari = db.execute("SELECT pr_5k_menit, level FROM pelari WHERE id = %s", (pelari_id,)).fetchone()
        
        if not pelari or not pelari["pr_5k_menit"]:
            flash("Mohon perbarui data waktu PR 5K Anda agar sistem bisa membuat jadwal.", "warning")
            return redirect(url_for("index"))

        # --- FITUR PROGRESSION OTOMATIS ---
        # Hitung berapa banyak sesi yang sudah dilaporkan pelari ini
        total_sesi = db.execute("SELECT COUNT(*) AS c FROM sesi_latihan WHERE pelari_id = %s", (pelari_id,)).fetchone()["c"]
        
        # Logika: Setiap kelipatan 4 sesi latihan, Kapasitas Aerobik (VDOT) pelari otomatis 
        # naik 0.5 poin, membuat target pace lebih cepat secara ilmiah.
        # Maksimal bonus VDOT adalah 2.5 poin (setara 20 sesi latihan).
        bonus_vdot = (total_sesi // 4) * 0.5
        if bonus_vdot > 2.5:
            bonus_vdot = 2.5
            
        jadwal_hasil, vdot = pace_engine.generate_jadwal(pelari["pr_5k_menit"], pelari["level"], bonus_vdot=bonus_vdot)
        prediksi_race = pace_engine.hitung_prediksi_race(pelari["pr_5k_menit"])

        return render_template(
            "jadwal.html",
            jadwal_hasil=jadwal_hasil,
            prediksi_race=prediksi_race,
            vdot=vdot,
            bonus_vdot=bonus_vdot,
            total_sesi=total_sesi
        )

    @app.route("/lapor", methods=["GET", "POST"])
    @pelari_required
    def lapor():
        db = database.get_db()
        from utils import JENIS_LATIHAN_VALID
        pelari_id = session.get("pelari_id")

        if request.method == "POST":
            tanggal = request.form.get("tanggal", "").strip()
            jarak_km_raw = request.form.get("jarak_km", "").strip()
            waktu_menit_raw = request.form.get("waktu_menit", "").strip()
            jenis_latihan = request.form.get("jenis_latihan", "").strip()

            error = None
            if not all([tanggal, jarak_km_raw, waktu_menit_raw, jenis_latihan]):
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
                flash("Sesi latihan berhasil dicatat.", "success")
                return redirect(url_for("lapor"))

        return render_template("lapor.html")

    @app.route("/progres", methods=["GET"])
    @pelari_required
    def progres():
        db = database.get_db()
        pelari_id = session.get("pelari_id")

        pelari = db.execute("SELECT * FROM pelari WHERE id = %s", (pelari_id,)).fetchone()

        # SQLite: date('now', '-6 days') -> Postgres: CURRENT_DATE - INTERVAL '6 days'
        total_km_minggu = db.execute(
            """SELECT COALESCE(SUM(jarak_km), 0) AS total
               FROM sesi_latihan
               WHERE pelari_id = %s
                 AND tanggal >= CURRENT_DATE - INTERVAL '6 days'""",
            (pelari_id,),
        ).fetchone()["total"]

        sesi_terbaru = db.execute(
            """SELECT * FROM sesi_latihan
               WHERE pelari_id = %s
               ORDER BY tanggal DESC, id DESC
               LIMIT 5""",
            (pelari_id,),
        ).fetchall()

        data_progres = [{
            "pelari": pelari,
            "total_km_minggu": total_km_minggu,
            "sesi_terbaru": sesi_terbaru,
        }]

        return render_template("progres.html", data_progres=data_progres, format_pace=pace_engine.format_pace)

    @app.route("/hapus_peringatan", methods=["POST"])
    @pelari_required
    def hapus_peringatan():
        pelari_id = session.get("pelari_id")
        db = database.get_db()
        db.execute("UPDATE pelari SET peringatan_admin = NULL WHERE id = %s", (pelari_id,))
        db.commit()
        return redirect(url_for("index"))
