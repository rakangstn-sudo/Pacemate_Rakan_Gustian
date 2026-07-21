-- schema_postgres.sql
-- Skema database PaceMate untuk PostgreSQL (Supabase)
-- Jalankan via Supabase SQL Editor

CREATE TABLE admin (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username    TEXT    UNIQUE NOT NULL,
    password_hash TEXT  NOT NULL
);

CREATE TABLE pelari (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username        TEXT    UNIQUE NOT NULL,
    password_hash   TEXT    NOT NULL,
    nama            TEXT    NOT NULL,
    usia            INTEGER NOT NULL,
    level           TEXT    NOT NULL CHECK (level IN ('pemula', 'menengah', 'lanjutan')),
    pr_5k_menit     DOUBLE PRECISION,
    peringatan_admin TEXT
);

CREATE TABLE sesi_latihan (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pelari_id       INTEGER NOT NULL,
    tanggal         DATE    NOT NULL,
    jarak_km        DOUBLE PRECISION NOT NULL,
    waktu_menit     DOUBLE PRECISION NOT NULL,
    jenis_latihan   TEXT    NOT NULL CHECK (
        jenis_latihan IN ('easy', 'tempo', 'interval', 'long_run')
    ),
    pace_hasil      DOUBLE PRECISION,
    FOREIGN KEY (pelari_id) REFERENCES pelari (id) ON DELETE CASCADE
);
