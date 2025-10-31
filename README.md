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
- **Kuis Sekali Coba** (Okt 2025): Siswa hanya dapat mengirim kuis satu kali. Jawaban sementara tersimpan otomatis di browser dan tombol submit menampilkan konfirmasi sebelum penyimpanan final.
- **Sertifikat**: Unduh sertifikat (format `.docx`) setelah menyelesaikan semua materi dan mendapatkan skor kuis 100.
- **Catatan Pembaruan Sertifikat (Okt 2025)**: Generator kini menghasilkan file PDF langsung dari template gambar `file_pendukung/sertifikat/docx/template Sertifikat LMS.png` menggunakan Pillow. Jalankan `pip install -r requirements.txt` setelah menarik pembaruan ini.
- **Asisten AI Terintegrasi**: Pengguna yang login dapat membuka halaman chatbot (menggunakan OpenRouter API) untuk tanya jawab materi dan bantuan navigasi platform.
- **Profil Platform Interaktif**: Tombol judul "TechNova Academy" di navigasi menampilkan modal About yang menjelaskan layanan kursus Microsoft Office beserta tautan Instagram dan TikTok.
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

    #Aktifkan diGitbash
    source venv/Scripts/activate
    ...

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

### Konfigurasi Opsional: Asisten AI

Untuk mengaktifkan chatbot yang terintegrasi:

1. Pastikan Anda memiliki akun dan API key OpenRouter (atau penyedia lain yang kompatibel dengan format OpenAI API).
2. Isi variabel berikut di `.env`:
    - `AI_PROVIDER=openrouter`
    - `AI_API_KEY=<API_KEY_ANDA>`
    - `AI_MODEL=openrouter/auto` (atau model lain yang tersedia)
    - `AI_BASE_URL=https://openrouter.ai/api/v1/chat/completions` (default, boleh dikosongkan jika sama)
    - `APP_BASE_URL` opsional untuk header referer.
3. Jika variabel tidak diisi atau provider bukan `openrouter`, tombol Asisten AI tetap ada tetapi akan memberi pesan fallback.

> Catatan: File log chatbot disimpan di direktori `logs/app.log` dengan rotasi otomatis (`RotatingFileHandler`).

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
4.  Klik label **TechNova Academy** di navigasi untuk membuka modal About yang menjelaskan layanan kursus serta menyediakan tautan Instagram & TikTok.
5.  Gunakan menu **Asisten AI** (dengan kredensial API yang valid) untuk mendapatkan bantuan materi atau rekomendasi kursus secara instan.

## Panduan Menggunakan Ngrok

Untuk membuat aplikasi lokal Anda dapat diakses dari internet (misalnya untuk demo), gunakan Ngrok. File `ngrok.exe` sudah tersedia.

1.  Pastikan aplikasi Flask sedang berjalan.
2.  Buka terminal baru di direktori proyek.
3.  Jalankan perintah:
    ```bash

    ./ngrok.exe http 3000

    ```
4.  Ngrok akan memberikan URL publik yang bisa Anda gunakan.

## Aset Media & Styling

- Ikon sosial media untuk modal About disimpan di `static/images/Instagram_icon.png` dan `static/images/tiktok_icon.png`. Pastikan direktori ini tersedia jika Anda men-deploy ke hosting baru.
- Seluruh styling utama berada di `static/styles.css`. Komponen modal About dan tombol brand menggunakan kelas `.about-modal-*`, `.about-social-links`, dan `.nav-brand`.

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

## Panduan Verifikasi Instruktur

- Instruktur yang baru mendaftar akan diarahkan ke halaman profil sampai mengunggah bukti kredensial. Lengkapi nama, email, beserta data profesional agar kursus dapat diterbitkan.
- Isi bidang `Bidang Keahlian`, `Asal Lembaga`, dan `Lama Mengajar (tahun)` supaya detail instruktur terlihat di katalog.
- Pilih tipe sertifikat: `PDF`/`Gambar` untuk unggah file (tersimpan di `static/uploads/certificates`) atau `Link Eksternal` bila sertifikat disimpan di luar aplikasi. Tipe `Default` menandakan belum ada bukti yang diunggah.
- Tombol `Hapus Sertifikat` akan membersihkan file/link sehingga status kembali belum terverifikasi. Saat status belum terverifikasi, instruktur hanya bisa membuka profil dan logout.
- Setelah data tersimpan dan valid, badge profil berubah menjadi `Terverifikasi` dan seluruh menu instruktur kembali dapat diakses.

## Manajemen Latihan & Penilaian

- Setiap kursus dapat memiliki satu latihan yang dikelola melalui tombol **Details Latihan** di detail kursus instruktur.
- Atur nama, deskripsi, URL latihan, serta jadwal mulai/akhir (format `datetime-local`). Siswa hanya dapat melihat dan mengerjakan latihan dalam rentang jadwal yang diizinkan.
- Siswa membuka tombol **Mulai Latihan** untuk mengirim tautan pekerjaan. Setiap siswa hanya memiliki satu submission per kursus.
- Instruktur menilai submission lewat halaman **Detail Siswa** → **Update Exercise Score**. Nilai ini akan muncul kembali di detail kursus siswa.
- Untuk penerbitan sertifikat otomatis, pastikan setiap submission dinilai **> 0** jika kursus mensyaratkan latihan.

## Pengelolaan Media Kursus & Branding

- Thumbnail kursus dapat berasal dari unggahan file atau URL eksternal. File tersimpan di `static/uploads/thumbnails`; direktori dibuat otomatis saat upload pertama.
- Template sertifikat berada di `file_pendukung/sertifikat/docx/`. Aset ikon brand (Instagram/TikTok) tersedia di `file_pendukung/logo/` dan digandakan ke `static/images/` untuk dipakai modal About.
- Materi per pelajaran mendukung teks, link video (YouTube/Vimeo), link meeting, serta jadwal publikasi (`start_date`).
- Simpan file tambahan (misalnya hasil export modul) di folder `static/uploads/` agar dapat diakses publik, atau gunakan storage eksternal bila file berukuran besar.

## Logging & Monitoring

- Aplikasi menulis log rotasi otomatis ke `logs/app.log` (maksimal ±500 KB per file, dengan 5 cadangan). File ini berguna untuk melacak error, aktivitas login, dan panggilan API OpenRouter.
- Kegagalan konfigurasi chatbot (misal API key kosong) juga dicatat ke log. Periksa file ini ketika tombol Asisten AI hanya menampilkan pesan fallback.

## Catatan Sinkronisasi Database

- Setelah menarik pembaruan terbaru, jalankan `flask db upgrade` untuk menerapkan migrasi yang tersimpan pada folder `migrations/`.
- File `DB_SYNC_INSTRUCTIONS.txt` merangkum DDL penting (penambahan harga kursus dan tabel keranjang) bila Anda perlu menerapkannya secara manual.
- Jika database lama belum memiliki kolom `thumbnail_path`, ikuti panduan pada `fix_thumbnail_column.txt` atau jalankan migrasi terbaru sebelum menggunakan fitur upload thumbnail.
