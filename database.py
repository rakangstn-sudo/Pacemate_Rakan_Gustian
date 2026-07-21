# database.py
# Modul untuk mengelola koneksi ke database PostgreSQL (Supabase).
# Menggunakan pola "get_db()" agar satu koneksi dipakai per request (via Flask 'g').
#
# === Perbedaan utama dari versi SQLite sebelumnya ===
#
# 1. Driver: sqlite3 (built-in) -> psycopg2 (library pihak ketiga).
#    psycopg2 adalah adapter PostgreSQL paling populer untuk Python.
#
# 2. Connection string: Dari file lokal "pacemate.db" -> DATABASE_URL dari
#    environment variable. Ini best practice karena:
#    - Kredensial tidak ter-hardcode di source code.
#    - Mudah beda-beda antara development (lokal) dan production (Vercel).
#
# 3. Row factory: sqlite3.Row -> psycopg2.extras.RealDictCursor.
#    Keduanya membuat hasil query bisa diakses seperti dict (row["nama"]),
#    sehingga template Jinja yang sudah ada TIDAK perlu diubah.
#    Bedanya, RealDictCursor mengembalikan dict Python biasa, sedangkan
#    sqlite3.Row adalah objek khusus yang mendukung akses key DAN index.
#
# 4. Foreign key: Di SQLite harus diaktifkan manual via "PRAGMA foreign_keys = ON"
#    setiap koneksi baru. Di PostgreSQL, foreign key selalu aktif secara default,
#    jadi tidak perlu PRAGMA lagi.
#
# 5. Placeholder parameter: SQLite pakai "?" sedangkan PostgreSQL pakai "%s".
#    Semua query di routes_*.py perlu disesuaikan.
#
# 6. init_db() dihapus: Skema sekarang dikelola lewat Supabase SQL Editor
#    (file schema_postgres.sql), bukan lewat kode Python.
#
# 7. DbWrapper: psycopg2 connection TIDAK punya method .execute() langsung
#    (beda dengan sqlite3). Kita membuat class DbWrapper agar pola pemanggilan
#    di routes (db.execute(...).fetchone()) tetap sama persis seperti versi
#    SQLite, sehingga migrasi lebih mudah dan kode routes tidak perlu
#    diubah strukturnya secara drastis.

import os
import psycopg2
import psycopg2.extras
from flask import g
from dotenv import load_dotenv

# Muat variabel dari file .env (untuk development lokal).
# Di production (Vercel), environment variable di-set lewat dashboard,
# jadi load_dotenv() tidak berpengaruh apa-apa (aman dipanggil).
load_dotenv()

# Connection string ke Supabase Postgres, diambil dari environment variable.
# Contoh format: postgresql://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
DATABASE_URL = os.environ.get("DATABASE_URL")


class DbWrapper:
    """
    Wrapper tipis di atas psycopg2 connection agar bisa dipanggil dengan pola
    yang sama persis seperti sqlite3:
        db = get_db()
        row = db.execute("SELECT ...", (param,)).fetchone()
        db.commit()

    Tanpa wrapper ini, psycopg2 mengharuskan membuat cursor terpisah:
        cur = conn.cursor()
        cur.execute("SELECT ...", (param,))
        row = cur.fetchone()

    Wrapper ini menyederhanakan migrasi karena semua kode di routes_*.py
    tidak perlu diubah strukturnya.
    """

    def __init__(self, conn):
        self._conn = conn

    def execute(self, query, params=None):
        """Buat cursor RealDictCursor, jalankan query, return cursor-nya."""
        cur = self._conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(query, params)
        return cur

    def commit(self):
        """Commit transaksi saat ini."""
        self._conn.commit()

    def close(self):
        """Tutup koneksi."""
        self._conn.close()


def get_db():
    """
    Mengambil koneksi database untuk request saat ini.
    Jika belum ada koneksi di objek 'g', buat koneksi baru.

    Mengembalikan DbWrapper (bukan raw connection) agar pola
    db.execute(...).fetchone() tetap berfungsi seperti versi SQLite.
    """
    if "db" not in g:
        conn = psycopg2.connect(DATABASE_URL)
        g.db = DbWrapper(conn)
    return g.db


def close_db(e=None):
    """Menutup koneksi database di akhir request (dipanggil lewat teardown)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    """
    Mendaftarkan fungsi close_db agar otomatis dipanggil setiap
    request selesai, dan menambahkan CLI command 'flask init-db'.
    """
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """
        Perintah CLI: flask init-db

        Skema database sekarang dikelola lewat Supabase SQL Editor
        (file schema_postgres.sql), bukan lewat kode Python.
        """
        print("INFO: Skema database dikelola lewat Supabase Dashboard.")
        print("Buka Supabase SQL Editor, lalu jalankan isi file schema_postgres.sql.")
