# Panduan Umum Aplikasi LMS

## Akun & Keamanan

### Cara Register (Daftar Akun Baru)
1. Buka halaman Register (`/register`) atau klik tombol "Register" di menu atas.
2. Masukkan **Nama Lengkap**.
3. Masukkan **Email** yang aktif (harus unik).
4. Masukkan **Password** (minimal 6 karakter).
5. Pilih **Peran (Role)**:
   - **Student**: Untuk belajar dan mengikuti kursus.
   - **Instructor**: Untuk mengajar dan membuat kursus.
6. Klik tombol **Register**.
7. Setelah registrasi, Anda akan diarahkan ke halaman Login. (Aplikasi saat ini meminta Anda untuk login setelah mendaftar.)

### Cara Login
1. Buka halaman Login (`/login`) atau klik tombol "Login".
2. Masukkan **Email** yang terdaftar.
3. Masukkan **Password**.
4. (Opsional) Centang "Remember Me" agar tetap login.
5. Klik tombol **Login**.

### Cara Logout
1. Klik menu profil atau nama Anda di pojok kanan atas.
2. Klik opsi **Logout**.
3. Anda akan diarahkan kembali ke halaman Login.

### Cara Reset Password (Lupa Password)
1. Di halaman Login, klik link "Lupa Password?".
2. Masukkan email Anda dan password baru pada formulir yang disediakan.
3. Jika email terdaftar, sistem akan langsung mengubah password Anda (implementasi saat ini melakukan perubahan langsung pada akun jika email ditemukan).
4. Catatan: fitur reset via email (token) hanya bekerja jika server email dikonfigurasi; pada instalasi pengembang biasanya proses ini disimulasikan atau di-handle langsung oleh server.

### Mengelola Profil
1. Klik menu **Profil** di navigasi atas.
2. Anda dapat mengubah:
   - Nama Lengkap
   - Foto Profil (Upload gambar)
   - Password Baru (jika ingin mengganti)
3. Khusus Instruktur, dapat melengkapi:
   - Bidang Keahlian
   - Asal Lembaga
   - Lama Mengajar
4. Klik **Simpan Perubahan**.

## Fitur AI Chatbot
- Klik menu **AI Assistant** di navigasi.
- Ketik pertanyaan Anda di kolom chat.
- AI dapat menjawab pertanyaan seputar penggunaan aplikasi, informasi kursus, dan panduan teknis.
- Klik **Clear Chat** untuk menghapus riwayat percakapan.
