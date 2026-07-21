# database.py
# Modul untuk mengelola koneksi ke database SQLite.
# Menggunakan pola "get_db()" agar satu koneksi dipakai per request (via Flask 'g').

import sqlite3
from flask import g

DATABASE = "pacemate.db"


def get_db():
    """
    Mengambil koneksi database untuk request saat ini.
    Jika belum ada koneksi di objek 'g', buat koneksi baru.
    row_factory diset ke sqlite3.Row agar hasil query bisa diakses seperti dict.
    """
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        # Aktifkan foreign key constraint (SQLite mematikannya secara default)
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    """Menutup koneksi database di akhir request (dipanggil lewat teardown)."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """
    Membuat seluruh tabel berdasarkan schema.sql.
    Dipanggil sekali saat setup awal (atau lewat CLI command 'flask init-db').
    """
    db = sqlite3.connect(DATABASE)
    with open("schema.sql", "r") as f:
        db.executescript(f.read())
    db.close()
    print("Database berhasil diinisialisasi.")


def init_app(app):
    """
    Mendaftarkan fungsi close_db agar otomatis dipanggil setiap
    request selesai, dan menambahkan CLI command 'flask init-db'.
    """
    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    def init_db_command():
        """Perintah CLI: flask init-db -> membuat tabel dari schema.sql"""
        init_db()
