# seed.py
# Script kecil untuk membuat SATU akun admin awal.
# Jalankan sekali saja setelah database dibuat:
#
#   1) flask init-db      -> membuat tabel dari schema.sql
#   2) python seed.py     -> membuat akun admin pertama
#
# Password akan otomatis di-hash menggunakan werkzeug.security sebelum disimpan.

import sqlite3
from werkzeug.security import generate_password_hash

DATABASE = "pacemate.db"

# Ganti sesuai kebutuhan sebelum dijalankan
USERNAME_ADMIN = "admin"
PASSWORD_ADMIN = "admin123"


def seed_admin():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # Cek dulu apakah username sudah ada, agar tidak duplikat
    existing = cur.execute(
        "SELECT id FROM admin WHERE username = ?", (USERNAME_ADMIN,)
    ).fetchone()

    if existing:
        print(f"Akun admin '{USERNAME_ADMIN}' sudah ada. Tidak ada perubahan.")
    else:
        password_hash = generate_password_hash(PASSWORD_ADMIN)
        cur.execute(
            "INSERT INTO admin (username, password_hash) VALUES (?, ?)",
            (USERNAME_ADMIN, password_hash),
        )
        conn.commit()
        print(f"Akun admin awal berhasil dibuat -> username: '{USERNAME_ADMIN}', password: '{PASSWORD_ADMIN}'")
        print("PENTING: segera ganti password default ini setelah login pertama kali.")

    conn.close()


if __name__ == "__main__":
    seed_admin()
