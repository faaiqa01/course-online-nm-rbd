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
- **Integrasi Payment Gateway**: Sistem pembayaran real menggunakan Midtrans dengan support berbagai metode pembayaran (GoPay, OVO, DANA, Bank Transfer, Kartu Kredit, dll).
- **Manajemen Pembayaran**:
    - Halaman checkout dengan Snap Midtrans yang aman dan user-friendly.
    - Invoice digital dengan countdown timer untuk batas waktu pembayaran.
    - Riwayat pembayaran lengkap dengan detail transaksi.
    - Retry payment untuk transaksi yang pending atau expired.
    - Cek status pembayaran manual dari Midtrans.
- **Silabus Kursus**: Halaman preview silabus yang menampilkan daftar materi sebelum siswa mendaftar kursus.
- **Manajemen Jadwal Kuis**: Instruktur dapat mengatur tanggal mulai dan akhir kuis untuk mengontrol kapan siswa dapat mengikuti kuis.

## Teknologi yang Digunakan

- **Backend**: Flask
- **Database**: MySQL (via `PyMySQL`)
- **ORM**: Flask-SQLAlchemy
- **Migrasi Database**: Flask-Migrate (Alembic)
- **Payment Gateway**: Midtrans (via `midtransclient`)
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
    - `MIDTRANS_SERVER_KEY`: Server key dari dashboard Midtrans Anda.
    - `MIDTRANS_CLIENT_KEY`: Client key dari dashboard Midtrans Anda.
    - `MIDTRANS_IS_PRODUCTION`: Atur ke `False` untuk sandbox mode, `True` untuk production.

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


### Konfigurasi Opsional: Asisten Chatbot

Platform ini menyediakan fitur chatbot interaktif yang membantu pengguna mencari informasi kursus dan panduan penggunaan platform. Chatbot terintegrasi dengan OpenRouter API.

#### Fitur Chatbot

Chatbot dapat membantu dengan:

1. **Informasi Kursus**:
   - Menjawab pertanyaan tentang harga, instruktur, dan status (gratis/premium) untuk semua kursus yang tersedia
   - Memberikan detail lengkap untuk kursus populer seperti deskripsi, jumlah materi, dan jumlah siswa terdaftar
   - Contoh: "Berapa harga kursus Paket Office 2?" akan dijawab dengan informasi harga yang akurat

2. **Panduan Penggunaan**:
   - Menjelaskan cara mendaftar kursus, melakukan checkout, mengikuti kuis, dan mengunduh sertifikat
   - Memberikan informasi tentang fitur-fitur yang tersedia di platform
   - Menjawab pertanyaan seputar akun seperti registrasi, login, dan reset password

3. **Rekomendasi**:
   - Memberikan saran kursus berdasarkan minat pengguna
   - Menampilkan kursus populer dan terbaru dengan data yang relevan

4. **Fitur Tambahan**:
   - **Riwayat Percakapan**: Chatbot mengingat konteks percakapan dalam 1 jam terakhir, sehingga pengguna tidak perlu mengulang informasi
   - **Clear Chat**: Tombol untuk menghapus riwayat dan memulai percakapan baru
   - **Suggested Questions**: Tombol pertanyaan umum yang bisa diklik langsung
   - **Tips Penggunaan**: Info box yang menjelaskan kemampuan chatbot

**Catatan Penting**: Chatbot hanya memberikan informasi dan panduan. Untuk melakukan tindakan seperti mendaftar kursus atau checkout, pengguna tetap harus melakukannya sendiri melalui interface yang tersedia.

#### Cara Mengaktifkan

Untuk mengaktifkan chatbot, ikuti langkah berikut:

1. Daftar akun di OpenRouter (atau penyedia API lain yang kompatibel dengan format OpenAI)
2. Tambahkan konfigurasi berikut di file `.env`:
   ```
   AI_PROVIDER=openrouter
   AI_API_KEY=<API_KEY_ANDA>
   AI_MODEL=google/gemma-3-27b-it:free
   AI_BASE_URL=https://openrouter.ai/api/v1/chat/completions
   APP_BASE_URL=http://localhost:5000
   ```
3. Jika konfigurasi tidak lengkap, tombol chatbot tetap muncul tapi akan menampilkan pesan fallback

#### Model yang Disarankan

- **Google Gemma 3 27B Instruct (free)**: Model gratis yang cukup baik untuk kebutuhan chatbot LMS
- **OpenRouter Auto**: Memilih model terbaik secara otomatis (mungkin berbayar)

#### Detail Teknis

- Chatbot mengakses data kursus melalui backend, bukan langsung ke database
- Maksimal 600 token per respons untuk memastikan jawaban lengkap
- Riwayat chat otomatis expire setelah 1 jam untuk menjaga privasi
- Semua aktivitas tercatat di `logs/app.log` dengan rotasi otomatis

> Log chatbot tersimpan di `logs/app.log` dengan sistem rotasi file otomatis.


### Konfigurasi Midtrans Payment Gateway

Platform ini menggunakan Midtrans sebagai payment gateway untuk memproses pembayaran kursus premium secara real-time.

#### Fitur Payment Gateway

1. **Metode Pembayaran Lengkap**:
   - E-Wallet: GoPay, OVO, DANA, LinkAja, ShopeePay
   - Bank Transfer: BCA, BNI, BRI, Mandiri, Permata
   - Kartu Kredit/Debit: Visa, Mastercard, JCB
   - Convenience Store: Indomaret, Alfamart
   - Cicilan: Kredivo, Akulaku

2. **Keamanan Transaksi**:
   - Enkripsi SSL/TLS untuk semua transaksi
   - 3D Secure untuk kartu kredit
   - Fraud detection system dari Midtrans
   - Webhook notification untuk update status otomatis

3. **Manajemen Pembayaran**:
   - Invoice dengan countdown timer (default 24 jam)
   - Notifikasi real-time status pembayaran
   - Riwayat transaksi lengkap
   - Retry payment untuk transaksi pending
   - Auto-enrollment setelah pembayaran berhasil

#### Cara Mengaktifkan

1. **Daftar Akun Midtrans**:
   - Kunjungi [https://dashboard.midtrans.com/register](https://dashboard.midtrans.com/register)
   - Daftar akun baru (gunakan email bisnis jika ada)
   - Verifikasi email Anda

2. **Dapatkan API Keys**:
   - Login ke [Midtrans Dashboard](https://dashboard.midtrans.com)
   - Pilih environment **Sandbox** untuk testing atau **Production** untuk live
   - Buka menu **Settings** → **Access Keys**
   - Salin **Server Key** dan **Client Key**

3. **Konfigurasi di `.env`**:
   ```
   MIDTRANS_SERVER_KEY=SB-Mid-server-xxxxxxxxxxxxxxxx
   MIDTRANS_CLIENT_KEY=SB-Mid-client-xxxxxxxxxxxxxxxx
   MIDTRANS_IS_PRODUCTION=False
   ```

4. **Testing di Sandbox Mode**:
   - Gunakan kartu kredit test: `4811 1111 1111 1114`
   - CVV: `123`, Exp: `01/25`
   - Untuk e-wallet, gunakan nomor test yang tersedia di [dokumentasi Midtrans](https://docs.midtrans.com/docs/testing-payment-on-sandbox)

#### Detail Teknis

- Payment webhook endpoint: `/payment/notification`
- Transaksi otomatis expire setelah 24 jam (dapat dikonfigurasi)
- Status pembayaran: `pending`, `settlement`, `cancel`, `deny`, `expire`
- Auto-enrollment ke kursus setelah status `settlement`
- Cart items otomatis terhapus setelah pembayaran berhasil
- Semua aktivitas tercatat di `logs/app.log`

> **Catatan Penting**: 
> - Untuk production, pastikan menggunakan HTTPS
> - Jangan commit API keys ke repository
> - Gunakan Sandbox mode untuk development dan testing
> - Webhook URL harus publicly accessible (gunakan ngrok untuk testing lokal)


## Menjalankan Aplikasi

Setelah instalasi selesai, jalankan aplikasi dengan perintah:
```bash
python app.py
```
Aplikasi akan berjalan di `http://127.0.0.1:5000`.

## Alur Demo

1.  Buka aplikasi dan **Daftar** dua akun: satu sebagai **Instruktur**, satu lagi sebagai **Siswa**.
2.  Masuk sebagai **Instruktur**:
    - Lengkapi profil instruktur dengan mengunggah sertifikat kredensial.
    - Buka dasbor instruktur.
    - **Buat Kursus** baru (bisa gratis atau premium).
    - Masuk ke detail kursus, lalu tambahkan beberapa **Materi** dan **Soal Kuis**.
    - Atur **Jadwal Kuis** dengan menentukan tanggal mulai dan akhir.
    - Kelola **Latihan** untuk kursus (opsional).
3.  Masuk sebagai **Siswa**:
    - Di halaman utama, klik **Cari Kursus**.
    - Klik kursus untuk melihat **Silabus** dan detail materi.
    - Untuk kursus gratis, klik **Daftar**.
    - Untuk kursus premium, klik **Tambah Ke Keranjang** atau **Beli Sekarang**.
    - Buka menu **Keranjang**, tinjau item, lalu klik **Checkout**.
    - Pilih metode pembayaran di Midtrans Snap dan selesaikan pembayaran (gunakan test card di sandbox mode).
    - Setelah pembayaran berhasil, Anda akan diarahkan ke halaman **Invoice**.
    - Buka menu **Kursus Saya** untuk melihat kursus yang sudah terdaftar.
    - Selesaikan semua materi dan ikuti kuis hingga mendapat skor 100 untuk dapat mengunduh **Sertifikat**.
    - Lihat **Riwayat Pembayaran** untuk melihat semua transaksi Anda.
4.  Klik label **TechNova Academy** di navigasi untuk membuka modal About yang menjelaskan layanan kursus serta menyediakan tautan Instagram & TikTok.
5.  Gunakan menu **Asisten AI** (dengan kredensial API yang valid) untuk mendapatkan bantuan materi atau rekomendasi kursus secara instan.

## Panduan Menggunakan Ngrok

Untuk membuat aplikasi lokal Anda dapat diakses dari internet (misalnya untuk demo), gunakan Ngrok. File `ngrok.exe` sudah tersedia.

1.  Pastikan aplikasi Flask sedang berjalan.
2.  Buka terminal baru di direktori proyek.
3.  Jalankan perintah:
    ```bash

    ./ngrok.exe http 5000

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
├── logs/
│   └── app.log
├── migrations/
│   ├── alembic.ini
│   ├── env.py
│   ├── README
│   ├── script.py.mako
│   └── versions/
├── models/
│   ├── __init__.py
│   └── payment.py
├── routes/
│   ├── __init__.py
│   ├── cart_payment_routes.py
│   └── payment_routes.py
├── services/
│   ├── __init__.py
│   └── midtrans_service.py
├── static/
│   ├── styles.css
│   ├── images/
│   └── uploads/
│       ├── certificates/
│       └── thumbnails/
└── templates/
    ├── add_question.html
    ├── ai_chat.html
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
    ├── manage_quiz_dates.html
    ├── my_courses.html
    ├── payment/
    │   ├── checkout.html
    │   ├── invoice.html
    │   ├── payment_history.html
    │   └── success.html
    ├── profile.html
    ├── quiz.html
    ├── register.html
    ├── student_detail_for_instructor.html
    ├── submit_exercise.html
    └── syllabus.html
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

## Panduan Payment Gateway

### Alur Pembayaran

1. **Single Course Checkout**:
   - Siswa klik tombol "Beli Sekarang" di detail kursus
   - Diarahkan ke halaman checkout
   - Klik "Bayar Sekarang" untuk membuka Snap Midtrans
   - Pilih metode pembayaran dan selesaikan transaksi
   - Setelah berhasil, otomatis enrolled ke kursus

2. **Cart Checkout**:
   - Siswa menambahkan beberapa kursus ke keranjang
   - Buka halaman keranjang dan review items
   - Klik "Checkout" untuk membuka Snap Midtrans
   - Pilih metode pembayaran dan selesaikan transaksi
   - Setelah berhasil, otomatis enrolled ke semua kursus di keranjang

3. **Payment Status**:
   - `pending`: Menunggu pembayaran
   - `settlement`: Pembayaran berhasil, enrolled ke kursus
   - `expire`: Transaksi expired (lewat 24 jam)
   - `cancel`: Transaksi dibatalkan
   - `deny`: Transaksi ditolak

### Retry Payment

Jika pembayaran pending atau expired, siswa dapat retry payment:
1. Buka menu "Riwayat Pembayaran"
2. Klik invoice dengan status pending/expired
3. Klik tombol "Bayar Sekarang" untuk retry
4. Sistem akan membuat order baru dengan suffix `-RETRY-xxxxx`

### Webhook Configuration

Untuk production, konfigurasikan webhook di Midtrans Dashboard:
1. Login ke Midtrans Dashboard
2. Buka **Settings** → **Configuration**
3. Isi **Payment Notification URL**: `https://yourdomain.com/payment/notification`
4. Isi **Finish Redirect URL**: `https://yourdomain.com/payment/success`
5. Simpan konfigurasi

### Testing Payment

Gunakan test credentials berikut di Sandbox mode:

**Kartu Kredit (Berhasil)**:
- Nomor: `4811 1111 1111 1114`
- CVV: `123`
- Exp: `01/25`

**GoPay**:
- Nomor: `081234567890`
- PIN: `123456`

**Bank Transfer**:
- Semua bank transfer akan otomatis settlement di sandbox

Lihat [dokumentasi lengkap Midtrans](https://docs.midtrans.com/docs/testing-payment-on-sandbox) untuk test credentials lainnya.

## Catatan Sinkronisasi Database

- Setelah menarik pembaruan terbaru, jalankan `flask db upgrade` untuk menerapkan migrasi yang tersimpan pada folder `migrations/`.
- File `DB_SYNC_INSTRUCTIONS.txt` merangkum DDL penting (penambahan harga kursus dan tabel keranjang) bila Anda perlu menerapkannya secara manual.
- Jika database lama belum memiliki kolom `thumbnail_path`, ikuti panduan pada `fix_thumbnail_column.txt` atau jalankan migrasi terbaru sebelum menggunakan fitur upload thumbnail.
- **Tabel Payments**: Migrasi terbaru menambahkan tabel `payments` untuk menyimpan data transaksi Midtrans. Pastikan menjalankan `flask db upgrade` setelah pull kode terbaru.
