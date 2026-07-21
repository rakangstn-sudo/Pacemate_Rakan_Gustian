# pace_engine.py
#
# Modul ini berisi SELURUH logika perhitungan PaceMate:
#   - hitung_vdot()      : estimasi VDOT (kapasitas aerobik efektif) dari waktu PR 5K
#   - vdot_ke_pace()     : menurunkan target pace dari VDOT untuk suatu %VO2max
#   - generate_jadwal()  : menyusun jadwal latihan 7 hari berdasarkan level & VDOT
#   - prediksi_waktu()   : estimasi waktu race di jarak lain (Riegel Formula)
#   - format_pace()      : mengubah pace desimal (menit/km) -> format menit:detik
#
# Referensi:
#   Daniels, J. & Gilbert, J. (1979). Oxygen Power: Performance Tables
#   for Distance Runners.
#   Riegel, P. (1977). Athletic Records and Human Endurance. Runner's World.

import math


# ---------------------------------------------------------------------------
# KONSTANTA: persentase %VO2max standar per zona latihan (tabel baku Daniels)
# Ditaruh di level module (bukan di dalam fungsi) supaya jadi "sumber kebenaran"
# tunggal yang mudah dikutip/dijelaskan di laporan, dan gampang diubah kalau
# perlu kalibrasi ulang tanpa menyentuh logika fungsi.
# ---------------------------------------------------------------------------
ZONA_PERSEN = {
    "Easy": 0.70,
    "Long Run": 0.70,
    "Tempo": 0.86,      # setara "Threshold pace" pada tabel Daniels
    "Interval": 0.98,
}

# Pola hari aktif (Senin..Minggu) per level pelari.
POLA_LATIHAN = {
    "pemula":   ["Easy", "Rest", "Easy", "Rest", "Easy", "Rest", "Long Run"],
    "menengah": ["Easy", "Interval", "Rest", "Tempo", "Rest", "Easy", "Long Run"],
    "lanjutan": ["Easy", "Interval", "Easy", "Tempo", "Rest", "Easy", "Long Run"],
}

# Jarak target (km) per jenis latihan, per level.
JARAK_TARGET = {
    "pemula":   {"Easy": 3, "Tempo": 3, "Interval": 0, "Long Run": 5},
    "menengah": {"Easy": 5, "Tempo": 4, "Interval": 4, "Long Run": 8},
    "lanjutan": {"Easy": 6, "Tempo": 5, "Interval": 5, "Long Run": 12},
}

NAMA_HARI = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]

# Jarak race standar (km) untuk fitur prediksi waktu (Riegel Formula).
JARAK_RACE = {
    "10K": 10.0,
    "Half Marathon": 21.0975,
    "Marathon": 42.195,
}


def hitung_vdot(waktu_pr_menit):
    """
    Mengestimasi VDOT (VO2max "efektif") seorang pelari dari waktu PR lari 5K.

    Maksud rumus:
    VDOT bukan VO2max fisiologis murni, melainkan ukuran kapasitas aerobik
    fungsional yang diturunkan dari performa race aktual (bukan tes lab).
    Idenya: dari waktu tempuh 5K, kita hitung kecepatan race (v_race), lalu
    pakai regresi Daniels-Gilbert untuk menaksir konsumsi oksigen (VO2) pada
    kecepatan tsb. Karena pelari tidak memakai 100% VO2max saat race 5K
    (ada faktor daya tahan terhadap kelelahan yang bergantung pada durasi
    race), hasil VO2 itu dibagi dengan persentase VO2max yang secara
    empiris "terpakai" untuk race sepanjang waktu_pr_menit tersebut.
    Hasil pembagian inilah yang disebut VDOT: VO2max effort penuh yang
    ekivalen dengan performa race tersebut.
    """
    # Kecepatan race dalam meter/menit (jarak 5000 m dibagi waktu tempuh)
    v_race = 5000 / waktu_pr_menit

    # Estimasi VO2 (ml/kg/menit) pada kecepatan v_race,
    # berdasarkan regresi polinomial derajat 2 dari data Daniels-Gilbert.
    vo2 = -4.60 + 0.182258 * v_race + 0.000104 * (v_race ** 2)

    # Persentase VO2max yang secara efektif terpakai untuk race sepanjang
    # waktu_pr_menit ini. Race yang lebih lama -> persentase makin turun
    # (tubuh tidak bisa mempertahankan %VO2max setinggi race pendek).
    # Bentuk penjumlahan dua fungsi eksponensial ini adalah hasil fitting
    # kurva Daniels-Gilbert terhadap data lapangan.
    persen_max = (
        0.8
        + 0.1894393 * math.exp(-0.012778 * waktu_pr_menit)
        + 0.2989558 * math.exp(-0.1932605 * waktu_pr_menit)
    )

    vdot = vo2 / persen_max
    return vdot


def vdot_ke_pace(vdot, persen_zona):
    """
    Menurunkan target pace (menit/km) untuk suatu zona latihan, dari VDOT
    pelari dan target %VO2max zona tersebut.

    Maksud rumus:
    Ini adalah kebalikan dari hitung_vdot(). Kalau di hitung_vdot() kita
    mencari VO2 dari kecepatan (v -> vo2), di sini kita punya target VO2
    (vdot * persen_zona) dan ingin mencari kecepatan v yang menghasilkan
    VO2 tersebut. Karena rumus asal vo2 = -4.60 + 0.182258*v + 0.000104*v^2
    adalah kuadrat dalam v, maka membalikkannya berarti menyelesaikan
    persamaan kuadrat a*v^2 + b*v + c = 0 dengan rumus abc, lalu mengambil
    akar yang bernilai positif (karena kecepatan tidak mungkin negatif).
    Kecepatan v (meter/menit) itu lalu dikonversi menjadi pace (menit/km).
    """
    vo2_target = vdot * persen_zona

    a = 0.000104
    b = 0.182258
    c = -4.60 - vo2_target

    diskriminan = b ** 2 - 4 * a * c
    v = (-b + math.sqrt(diskriminan)) / (2 * a)  # akar positif

    pace_menit_per_km = 1000 / v
    return pace_menit_per_km


def format_pace(menit_desimal):
    """
    Mengubah pace dalam bentuk desimal (misal 5.4167 menit/km) menjadi
    format menit:detik yang lazim dipakai pelari (misal '5:25').
    Dipisah dari perhitungan matematis (vdot_ke_pace) karena ini murni
    urusan presentasi/format, bukan logika fisiologis.
    """
    if menit_desimal is None:
        return "-"
    menit = int(menit_desimal)
    detik = round((menit_desimal - menit) * 60)
    # Penanganan pembulatan: jika detik jadi 60, naikkan 1 menit
    if detik == 60:
        menit += 1
        detik = 0
    return f"{menit}:{detik:02d}"


def generate_jadwal(pr_menit, level, bonus_vdot=0.0):
    """
    Menggabungkan seluruh komponen (VDOT, pola latihan, jarak target, pace
    per zona) menjadi jadwal latihan 7 hari (Senin-Minggu).

    Mengembalikan list of dict, satu dict per hari:
        {"hari": ..., "jenis": ..., "jarak_km": ..., "pace": "menit:detik"}
    Untuk hari "Rest", jarak_km dan pace ditampilkan "-".
    """
    vdot_awal = hitung_vdot(pr_menit)
    vdot = vdot_awal + bonus_vdot
    pola = POLA_LATIHAN[level]
    jarak = JARAK_TARGET[level]

    # Hitung pace tiap zona SEKALI di awal (bukan berulang per hari) supaya
    # efisien -- VDOT pelari tetap sama untuk seluruh minggu.
    pace_per_zona = {
        zona: vdot_ke_pace(vdot, persen) for zona, persen in ZONA_PERSEN.items()
    }

    jadwal = []
    for hari, jenis in zip(NAMA_HARI, pola):
        if jenis == "Rest":
            jadwal.append({"hari": hari, "jenis": "Rest", "jarak_km": "-", "pace": "-"})
        else:
            jadwal.append({
                "hari": hari,
                "jenis": jenis,
                "jarak_km": jarak[jenis],
                "pace": format_pace(pace_per_zona[jenis]),
            })

    return jadwal, vdot


def prediksi_waktu(waktu_pr_menit, jarak_target_km, jarak_pr_km=5.0):
    """
    Memprediksi waktu tempuh di jarak lain menggunakan Riegel Formula.

    Maksud rumus:
    Riegel mengamati bahwa performa endurance manusia menurun secara
    konsisten mengikuti hukum pangkat (power law) terhadap jarak, bukan
    linear. Faktor eksponen 1.06 (bukan 1.0) mencerminkan bahwa menempuh
    jarak 2x lebih jauh butuh waktu LEBIH dari 2x lipat -- ada kelelahan
    tambahan yang terakumulasi. Formula ini dipakai untuk mengekstrapolasi
    satu data performa (PR 5K) menjadi estimasi di jarak lain (10K, HM, Full
    Marathon) tanpa perlu data race sungguhan di jarak tersebut.
    """
    t2 = waktu_pr_menit * (jarak_target_km / jarak_pr_km) ** 1.06
    return t2


def format_jam_menit_detik(menit_desimal):
    """Mengubah durasi dalam menit (desimal) menjadi format jam:menit:detik."""
    total_detik = round(menit_desimal * 60)
    jam = total_detik // 3600
    sisa = total_detik % 3600
    menit = sisa // 60
    detik = sisa % 60
    if jam > 0:
        return f"{jam}:{menit:02d}:{detik:02d}"
    return f"{menit}:{detik:02d}"


def hitung_prediksi_race(pr_menit):
    """
    Menghasilkan prediksi waktu race untuk semua jarak standar di JARAK_RACE,
    sudah dalam format jam:menit:detik siap tampil.
    """
    hasil = {}
    for nama_jarak, km in JARAK_RACE.items():
        t_menit = prediksi_waktu(pr_menit, km)
        hasil[nama_jarak] = format_jam_menit_detik(t_menit)
    return hasil