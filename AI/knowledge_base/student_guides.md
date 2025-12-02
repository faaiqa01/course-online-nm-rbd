# Panduan Lengkap Siswa (Student)

## Manajemen Kursus

### Cara Mencari & Melihat Kursus
1. Klik menu **Lihat Kursus** (`/courses`).
2. Gunakan fitur **Pencarian** untuk mencari berdasarkan judul.
3. Gunakan **Filter** untuk menyaring berdasarkan:
   - Tipe Materi (Text, Video, Meeting)
   - Status (Premium, Gratis)
4. Klik tombol **Lihat Detail** pada kartu kursus.
5. Di halaman detail, Anda bisa melihat deskripsi dan info instruktur.
6. Klik tombol **Lihat Silabus Lengkap** untuk melihat rincian materi, durasi, dan evaluasi sebelum mendaftar.

### Cara Mendaftar Kursus Gratis
1. Buka halaman detail kursus yang berstatus **Gratis**.
2. Klik tombol **Daftar Sekarang**.
3. Anda akan langsung terdaftar dan diarahkan ke materi kursus.

### Cara Membeli Kursus Premium
1. Buka halaman detail kursus yang berstatus **Premium**.
2. Klik tombol **Tambah ke Keranjang**.
3. Buka menu **Keranjang** (ikon keranjang di atas).
4. Periksa daftar kursus yang akan dibeli.
6. Klik **Checkout** untuk membayar.
7. Perilaku checkout tergantung konfigurasi server:
   - Pada beberapa pengaturan/development, checkout keranjang dapat langsung memproses pendaftaran (tanpa popup gateway) dan kursus akan otomatis terbuka.
   - Jika Midtrans atau gateway lain diaktifkan, popup Midtrans akan muncul; ikuti instruksi pembayaran di popup tersebut.
8. Selesaikan pembayaran sesuai instruksi (jika menggunakan Midtrans).
9. Setelah pembayaran berhasil, Anda akan diarahkan ke halaman Sukses dan kursus akan terbuka/di-unlock.

## Pembelajaran

### Mengakses Kursus Saya
1. Klik menu **Kursus Saya** (`/my-courses`).
2. Daftar kursus yang sudah Anda ikuti akan muncul beserta progress bar.
3. Klik **Lanjut Belajar** untuk masuk ke materi.

### Mengakses Materi (Lesson)
1. Di halaman detail kursus (setelah enroll), klik judul materi di daftar silabus.
2. Pelajari materi (baca teks, tonton video, atau join meeting).
3. Setelah selesai, klik tombol **Tandai Selesai** di bawah materi.
4. Progress Anda akan bertambah otomatis.

## Evaluasi & Sertifikat

### Mengerjakan Kuis
1. Kuis biasanya ada di akhir kursus atau modul.
2. Klik tombol **Mulai Kuis**.
3. Jawab semua pertanyaan pilihan ganda.
4. Klik **Submit**.
5. Peraturan percobaan (attempts) dapat berbeda untuk setiap kursus: beberapa kursus mengizinkan **lebih dari satu percobaan**, sedangkan lainnya dapat dibatasi menjadi satu percobaan. Periksa pengaturan kursus (atau tanyakan ke instruktur) sebelum memulai.
6. Nilai akan langsung muncul setelah submit.

### Mengumpulkan Tugas (Exercise)
1. Jika ada tugas, klik menu **Tugas/Exercise**.
2. Baca instruksi tugas.
3. Kerjakan tugas di file eksternal (misal: Google Docs, Word).
4. Masukkan **Link Tugas** Anda di form pengumpulan.
5. Klik **Kirim Tugas**.
6. Tunggu instruktur memberikan nilai dan feedback.

### Mengunduh Sertifikat
1. Syarat mendapatkan sertifikat bergantung pada pengaturan kursus, namun biasanya meliputi:
   - Progress materi lengkap (mis. semua pelajaran ditandai selesai).
   - Nilai kuis minimal sesuai `passing_grade` kursus (bukan selalu 100 — nilai minimal ditentukan oleh instruktur/pengaturan kursus).
2. Jika syarat terpenuhi, tombol **Download Sertifikat** akan aktif di halaman Kursus Saya atau detail kursus.
3. Klik tombol tersebut untuk mengunduh file PDF sertifikat.

## Pembayaran & Riwayat

### Melihat Riwayat Pembayaran
1. Klik menu profil -> **Riwayat Pembayaran** (`/payment/history`).
2. Anda bisa melihat status semua transaksi (Pending, Success, Failed).
3. Untuk transaksi yang **Pending** atau **Expired**, Anda bisa melakukan **Retry Payment** (Bayar Ulang) dengan klik tombol di invoice.

### Cek Status Pembayaran Manual
1. Jika pembayaran sudah dilakukan tapi status belum berubah, buka Invoice.
2. Klik tombol **Cek Status**.
3. Sistem akan sinkronisasi dengan Midtrans.
