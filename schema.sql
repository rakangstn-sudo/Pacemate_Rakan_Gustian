-- schema.sql
-- Skema database untuk aplikasi PaceMate (Sistem Informasi Pengatur Pace Lari)
-- Dibuat menggunakan sqlite3 murni (tanpa ORM)

-- Tabel admin: menyimpan akun pengelola sistem
CREATE TABLE IF NOT EXISTS admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL
);

-- Tabel pelari: menyimpan data pelari yang dilatih/dipantau
CREATE TABLE IF NOT EXISTS pelari (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT NOT NULL,
    usia INTEGER NOT NULL,
    level TEXT NOT NULL CHECK (level IN ('pemula', 'menengah', 'lanjutan')),
    pr_5k_menit REAL  -- personal record lari 5K dalam satuan menit
);

-- Tabel sesi_latihan: mencatat setiap sesi latihan lari milik seorang pelari
CREATE TABLE IF NOT EXISTS sesi_latihan (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pelari_id INTEGER NOT NULL,
    tanggal TEXT NOT NULL,          -- format YYYY-MM-DD
    jarak_km REAL NOT NULL,
    waktu_menit REAL NOT NULL,
    jenis_latihan TEXT NOT NULL CHECK (
        jenis_latihan IN ('easy', 'tempo', 'interval', 'long_run')
    ),
    pace_hasil REAL,                -- pace hasil (menit per km), bisa dihitung otomatis
    FOREIGN KEY (pelari_id) REFERENCES pelari (id) ON DELETE CASCADE
);
