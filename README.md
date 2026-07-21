# PaceMate

Sistem Informasi Pengatur Pace Lari. 
PaceMate membantu pelari, terutama pemula, menyusun jadwal latihan mingguan dengan **pace (kecepatan) yang tepat** sesuai dengan kemampuan (kapasitas aerobik/VDOT). Aplikasi ini juga dilengkapi dengan fitur **Deteksi Risiko Lonjakan Volume** untuk mencegah pelari dari cedera akibat *overtraining*.

## Fitur Utama

- **Generator Jadwal:** Tentukan level dan waktu PR 5K Anda, PaceMate akan menyusun jadwal 7 hari lengkap dengan target pace per zona latihan (menggunakan formula *VDOT Daniels-Gilbert*).
- **Prediksi Waktu Race:** Prediksi otomatis catatan waktu Anda untuk jarak 10K, Half Marathon, dan Marathon (menggunakan *Riegel Formula*).
- **Pencatatan Sesi Latihan:** Catat latihan Anda dan sistem akan menghitung pace aktual secara otomatis.
- **Progres Pelari:** Pantau total jarak (km) mingguan tiap pelari.
- **Deteksi Risiko (Admin):** Menganalisis lonjakan volume latihan pelari (jika volume minggu ini > 1.3x dari rata-rata 4 minggu sebelumnya, pelari akan ditandai berisiko cedera).
- **Dashboard & Kelola Data (Admin):** CRUD untuk data pelari dan sesi latihan, serta melihat grafik tren pace mingguan.

## Cara Instalasi & Menjalankan di Lokal

### 1. Clone Repositori
```bash
git clone https://github.com/USERNAME/pacemate.git
cd pacemate
```
*(Ganti URL clone dengan repositori GitHub Anda sendiri).*

### 2. Buat & Aktifkan Virtual Environment
Buka terminal dan jalankan:
- **Windows:**
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```
- **Mac/Linux:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

### 3. Install Dependensi
```bash
pip install -r requirements.txt
```

### 4. Inisialisasi Database & Buat Akun Admin
Jalankan perintah berikut satu per satu:
```bash
python -c "from database import init_db; init_db()"
python seed.py
```
Perintah ini akan membuat file `pacemate.db` dan memasukkan 1 akun admin default:
- **Username:** `admin`
- **Password:** `admin123`

### 5. Jalankan Aplikasi
```bash
python app.py
```
Aplikasi akan berjalan di `http://127.0.0.1:5000/`.

---

## Catatan Teori yang Dipakai

Aplikasi ini dibangun menggunakan dua rumus saintifik untuk pelari jarak jauh:
1. **VDOT Formula (Daniels & Gilbert, 1979)** — Digunakan untuk mengestimasi VO2max dari catatan waktu race dan menurunkan pace ideal (Easy, Tempo, Interval).
2. **Riegel Formula (Riegel, 1977)** — Digunakan untuk mengekstrapolasi performa dari satu jarak ke jarak lain (Prediksi waktu tempuh 10K/HM/Marathon).

## Keterangan Pengumpulan UAS
Aplikasi ini dikembangkan untuk memenuhi tugas UAS mata kuliah Pengantar Pemrograman.
