# Proyek LMS (Learning Management System) - Flask & MySQL

Sistem manajemen pembelajaran (LMS) minimalis yang dibangun dengan Flask dan MySQL. Aplikasi ini dirancang sebagai demo untuk ide bisnis kursus online, mendukung peran instruktur dan siswa, kursus gratis dan premium, manajemen materi, kuis, dan alur keranjang belanja.

## Fitur Utama

- **Manajemen Pengguna**: Sistem registrasi dan login dengan dua peran: **Instruktur** dan **Siswa**.
- **Dasbor Instruktur**:
    - Membuat, membaca, memperbarui, dan menghapus (CRUD) kursus.
    - Menambahkan dan mengelola materi pelajaran (teks, video, atau link meeting).
    - Membuat dan mengelola soal kuis untuk setiap kursus.
    - Mengelola siswa yang terdaftar di kursusnya.
- **Katalog Kursus**:
    - Siswa dapat menjelajahi semua kursus yang tersedia.
    - Filter kursus berdasarkan jenis materi, status premium/gratis, dan pencarian judul.
    - Menampilkan thumbnail untuk setiap kursus (diunggah atau dari URL).
- **Alur Kursus Premium**:
    - Siswa dapat menambahkan kursus premium ke keranjang belanja.
    - Halaman keranjang untuk meninjau kursus dan melanjutkan ke pembayaran (simulasi).
    - Pendaftaran otomatis setelah "pembayaran" berhasil.
- **Area Siswa**:
    - Halaman **Kursus Saya** untuk melihat semua kursus yang telah diikuti.
    - Melacak kemajuan belajar (materi yang telah selesai).
    - Mengikuti kuis dan melihat skor.
- **Sertifikat**: Unduh sertifikat (format `.docx`) setelah menyelesaikan semua materi dan mendapatkan skor kuis 100.
- **Catatan Pembaruan Sertifikat (Okt 2025)**: Generator kini menghasilkan file PDF langsung dari template gambar `file_pendukung/sertifikat/docx/template Sertifikat LMS.png` menggunakan Pillow. Jalankan `pip install -r requirements.txt` setelah menarik pembaruan ini.
- **Lokalisasi**: Antarmuka pengguna sebagian besar telah diterjemahkan ke dalam Bahasa Indonesia.

## Teknologi yang Digunakan

- **Backend**: Flask
- **Database**: MySQL (via `PyMySQL`)
- **ORM**: Flask-SQLAlchemy
- **Migrasi Database**: Flask-Migrate (Alembic)
- **Manajemen Dependensi**: Pip
- **Variabel Lingkungan**: python-dotenv

## Persiapan

- Python 3.10+
- Server MySQL (misalnya dari Laragon, XAMPP, atau instalasi mandiri).
- Git (opsional, untuk kloning repositori).

## Instalasi dan Konfigurasi

1.  **Clone atau Unduh Repositori**
    ```bash
    git clone <URL_REPOSITORI_ANDA>
    cd lms_flask_mysql
    ```

2.  **Buat dan Aktifkan Virtual Environment**
    Ini akan mengisolasi dependensi proyek Anda.
    ```bash
    # Buat environment
    python -m venv venv

    # Aktifkan di Windows (PowerShell/CMD)
    .\venv\Scripts\activate

    # Aktifkan di macOS/Linux
    source venv/bin/activate
    ```

3.  **Konfigurasi Environment (.env)**
    Buat file `.env` di direktori root dengan menyalin dari `.env.example`.
    ```bash
    # Windows
    copy .env.example .env

    # macOS/Linux
    cp .env.example .env
    ```
    Buka file `.env` dan sesuaikan nilainya:
    - `SECRET_KEY`: Ganti dengan string acak yang aman.
    - `SQLALCHEMY_DATABASE_URI`: Sesuaikan dengan kredensial database MySQL Anda. Contoh: `mysql+pymysql://root:@127.0.0.1:3306/lms_flask`
    - `FLASK_DEBUG`: Atur ke `True` untuk mode pengembangan.

4.  **Instal Dependensi**
    Pastikan `Flask-Migrate` tidak dikomentari di `requirements.txt` untuk mengelola skema database.
    ```
    # requirements.txt
    ...
    Flask-Migrate==4.1.0
    ```
    Kemudian instal semua paket:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Inisialisasi Database**
    Dengan `Flask-Migrate`, Anda dapat menerapkan semua migrasi yang ada untuk menyiapkan skema database.
    ```bash
    # Atur variabel FLASK_APP
    # Windows (PowerShell)
    $env:FLASK_APP="app.py"
    # Windows (CMD)
    set FLASK_APP=app.py
    # macOS/Linux
    export FLASK_APP=app.py

    # Jalankan upgrade untuk membuat semua tabel
    flask db upgrade
    ```
    Ini akan membuat database (jika belum ada) dan semua tabel sesuai dengan skema terakhir.

## Menjalankan Aplikasi

Setelah instalasi selesai, jalankan aplikasi dengan perintah:
```bash
python app.py
```
Aplikasi akan berjalan di `http://127.0.0.1:5000`.

## Alur Demo

1.  Buka aplikasi dan **Daftar** dua akun: satu sebagai **Instruktur**, satu lagi sebagai **Siswa**.
2.  Masuk sebagai **Instruktur**:
    - Buka dasbor instruktur.
    - **Buat Kursus** baru (bisa gratis atau premium).
    - Masuk ke detail kursus, lalu tambahkan beberapa **Materi** dan **Soal Kuis**.
3.  Masuk sebagai **Siswa**:
    - Di halaman utama, klik **Cari Kursus**.
    - Untuk kursus gratis, klik **Daftar**.
    - Untuk kursus premium, klik **Tambah Ke Keranjang**.
    - Buka menu **Keranjang**, tinjau item, lalu selesaikan "pembayaran" (simulasi).
    - Buka menu **Kursus Saya** untuk melihat kursus yang sudah terdaftar.
    - Selesaikan semua materi dan ikuti kuis hingga mendapat skor 100 untuk dapat mengunduh **Sertifikat**.

## Panduan Menggunakan Ngrok

Untuk membuat aplikasi lokal Anda dapat diakses dari internet (misalnya untuk demo), gunakan Ngrok. File `ngrok.exe` sudah tersedia.

1.  Pastikan aplikasi Flask sedang berjalan.
2.  Buka terminal baru di direktori proyek.
3.  Jalankan perintah:
    ```bash
    .\ngrok.exe http 5000
    ```
4.  Ngrok akan memberikan URL publik yang bisa Anda gunakan.

## Struktur Proyek

```
lms_flask_mysql/
├── .env.example
├── .gitignore
├── app.py
├── DB_SYNC_INSTRUCTIONS.txt
├── ngrok.exe
├── README.md
├── requirements.txt
├── file_pendukung/
│   └── sertifikat/
├── lain/
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
├── static/
│   ├── styles.css
│   └── uploads/
└── templates/
    ├── add_question.html
    ├── base.html
    ├── cart.html
    ├── certificate.html
    ├── course_detail.html
    ├── courses.html
    ├── create_course.html
    ├── create_lesson.html
    ├── forgot_password.html
    ├── index.html
    ├── instructor_dashboard.html
    ├── login.html
    ├── manage_enrollments.html
    ├── manage_exercise.html
    ├── manage_quiz.html
    ├── my_courses.html
    ├── profile.html
    ├── quiz.html
    ├── register.html
    ├── student_detail_for_instructor.html
    └── submit_exercise.html
```
