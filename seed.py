# seed.py
# Script kecil untuk membuat SATU akun admin awal di database PostgreSQL (Supabase).
# Jalankan sekali saja setelah schema dibuat di Supabase SQL Editor:
#
#   py seed.py    -> membuat akun admin pertama
#
# Password akan otomatis di-hash menggunakan werkzeug.security sebelum disimpan.

import os
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")

# Ganti sesuai kebutuhan sebelum dijalankan
USERNAME_ADMIN = "admin"
PASSWORD_ADMIN = "admin123"


def seed_admin():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Cek dulu apakah username sudah ada, agar tidak duplikat
    cur.execute("SELECT id FROM admin WHERE username = %s", (USERNAME_ADMIN,))
    existing = cur.fetchone()

    if existing:
        print(f"Akun admin '{USERNAME_ADMIN}' sudah ada. Tidak ada perubahan.")
    else:
        password_hash = generate_password_hash(PASSWORD_ADMIN)
        cur.execute(
            "INSERT INTO admin (username, password_hash) VALUES (%s, %s)",
            (USERNAME_ADMIN, password_hash),
        )
        conn.commit()
        print(f"Akun admin awal berhasil dibuat -> username: '{USERNAME_ADMIN}', password: '{PASSWORD_ADMIN}'")
        print("PENTING: segera ganti password default ini setelah login pertama kali.")

    conn.close()


if __name__ == "__main__":
    seed_admin()
