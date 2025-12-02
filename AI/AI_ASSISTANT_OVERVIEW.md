# Sistem Asisten Chatbot LMS - TechNova Academy

## Gambaran Umum
- Asisten chatbot memberikan dukungan percakapan berbahasa Indonesia kepada pengguna yang sudah login di platform LMS.
- Integrasi memanfaatkan OpenRouter API (kompatibel format OpenAI) dan dibuat langsung dari backend Flask (`app.py`).
- Antarmuka pengguna tersaji di `templates/ai_chat.html` dengan perilaku interaktif di `static/js/ai_chat.js`.
- **Update Terbaru (Desember 2024)**: Chatbot sekarang dapat mengakses informasi **semua kursus** di database, **payment gateway Midtrans**, **shopping cart**, mengingat konteks percakapan, dan dilengkapi fitur Clear Chat serta petunjuk penggunaan lengkap.

## Implementasi UI

### Routing & Template
- **Routing**: `app.py` mendefinisikan `/ai-chat` (mengembalikan `ai_chat.html`) serta `/api/ai-chat` untuk permintaan AJAX; keduanya dilindungi `@login_required`.
- **Struktur Template** (`templates/ai_chat.html`):
  - Meng-extend `base.html`, sehingga komponen navigasi, flash message, dan styling global ikut termuat.
  - Menyediakan info box dengan tips penggunaan chatbot
  - Tombol suggested questions untuk pertanyaan umum
  - Panel percakapan (`.ai-chat-page`, `.ai-chat-log`, `.ai-chat-form`) dan textarea dengan `maxlength="500"`
  - Tombol "Clear Chat" untuk menghapus riwayat percakapan
  - Menyematkan `marked.js` untuk rendering Markdown dan `static/js/ai_chat.js` untuk interaksi

### Styling & Interaksi
- **Gaya Visual**: Kelas CSS `ai-chat-*` didefinisikan di `static/styles.css` (layout bubble, scroll log, warna tombol, info box, suggestion buttons). Perubahan styling dapat dilakukan terpusat di file ini tanpa menyentuh Python.
- **Perilaku Klien** (`static/js/ai_chat.js`):
  - Mengikat event `submit` pada form; memblokir pengiriman default lalu mengirim `fetch` POST ke `/api/ai-chat`.
  - Menyisipkan pesan user/bot ke DOM melalui `appendMessage` dengan Markdown rendering untuk bot messages
  - Mengelola status loading, menonaktifkan tombol selama permintaan berlangsung
  - Handler untuk tombol Clear Chat dengan konfirmasi sebelum menghapus
  - Handler untuk suggested question buttons yang auto-fill textarea
  - Mendukung pemulihan fokus ke textarea setelah balasan diterima

## Alur Kerja Permintaan

1. **Akses UI** – Pengguna membuka `/ai-chat` dan melihat panel chat dengan info box dan suggested questions.
2. **Pengiriman Pesan** – JavaScript mengirim JSON `{"message": "..."}` ke `/api/ai-chat`.
3. **Simpan User Message** – Backend menyimpan pertanyaan user ke table `chat_history`.
4. **Validasi Backend** – `api_ai_chat()` menolak pesan kosong atau >500 karakter, mencatat request (`app.logger.info`), lalu menyiapkan payload percakapan.
5. **Penyusunan Prompt** – `build_chat_messages()` menambahkan:
   - `system`: `SYSTEM_PROMPT` (dengan instruksi ringkas dan relevan), info pengguna (nama, peran, keahlian), ringkasan katalog kursus lengkap, dan—jika role student—`STUDENT_FEATURES_CONTEXT` berisi daftar fitur UI siswa serta **batasan tegas** bahwa chatbot tidak bisa melakukan aksi apapun.
   - `history`: 10 chat terakhir dalam 1 jam (auto-expire) untuk konteks percakapan
   - `user`: input tertrim.
6. **Panggilan OpenRouter** – `call_openrouter()` memanfaatkan konfigurasi `.env` dengan timeout 20 detik dan **`max_tokens=600`**.
7. **Simpan AI Reply** – Backend menyimpan jawaban chatbot ke table `chat_history`.
8. **Pembersihan Respons** – Segment reasoning/chain-of-thought dibuang, list konten digabung.
9. **Fallback** – Error, timeout, atau respons tidak valid memicu pengiriman `FALLBACK_AI_REPLY` ke klien.

## Database Schema

### Table: `chat_history`

```sql
CREATE TABLE chat_history (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    role VARCHAR(20) NOT NULL,  -- 'user' or 'assistant'
    message TEXT NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_created (user_id, created_at),
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);
```

**Fungsi:**
- Menyimpan riwayat percakapan antara user dan chatbot
- Memungkinkan chatbot mengingat konteks percakapan
- Auto-delete saat user dihapus (CASCADE)

## Konteks Prompting

### SYSTEM_PROMPT
Prompt sistem telah diperbarui untuk:
- **Gaya natural dan ringkas**: Tidak formal berlebihan, mudah dipahami
- **Sesuaikan panjang jawaban**: Pertanyaan sederhana dijawab singkat, pertanyaan detail dijawab lengkap
- **Gunakan data konkret**: Prioritaskan menyebutkan nama kursus, harga, instruktur dari database
- **Langsung ke poin**: Hindari penjelasan bertele-tele
- **Batasan jelas**: Jika user meminta chatbot melakukan aksi (reset password, enroll, checkout, dll), **SELALU** jelaskan bahwa chatbot tidak bisa melakukan aksi tersebut, hanya bisa memberikan panduan langkah-langkahnya

### STUDENT_FEATURES_CONTEXT
Konteks fitur siswa telah diperkuat dengan:
- Daftar lengkap fitur yang tersedia:
  - **Katalog Kursus**: Browse, filter, search kursus
  - **Shopping Cart**: Add to cart, checkout multiple courses
  - **Payment Gateway**: Midtrans integration dengan berbagai metode pembayaran
  - **Kuis**: Take quiz dengan one-time submission
  - **Latihan**: Submit exercise dengan deadline
  - **Sertifikat**: Download PDF certificate
  - **Progress Tracking**: Monitor learning progress
  - **Payment History**: View transaction history, retry payment
- **PENTING**: Penekanan tegas bahwa "Asisten chatbot TIDAK BISA melakukan aksi apapun (enroll, checkout, reset password, submit tugas, dll) - hanya memberikan panduan langkah demi langkah. Selalu jelaskan bahwa user harus melakukan sendiri."

### build_catalog_context() - Opsi 3

Fungsi ini sekarang mengambil dan memformat:

1. **Daftar SEMUA kursus** (ringkas):
   - Query: `Course.query.options(joinedload(Course.instructor)).order_by(Course.title.asc()).all()`
   - Format: "Judul (Status-Harga, Instruktur: Nama)"
   - Contoh: "Paket Office 2 (Premium-Rp200,000, Instruktur: Citra Dewi)"
   - **Manfaat**: Chatbot bisa menjawab pertanyaan tentang **semua kursus** di database, tidak hanya yang populer

2. **5 Kursus Terpopuler** (detail lengkap):
   - Query dengan JOIN ke Enrollment dan Lesson untuk hitung jumlah siswa dan materi
   - Format: "Judul (Status-Harga, Instruktur: Nama, X materi, Deskripsi: ..., Y siswa)"
   - Menggunakan `joinedload()` untuk optimasi query (menghindari N+1 problem)
   - Deskripsi dibatasi 100 karakter untuk efisiensi token

3. **3 Kursus Terbaru** (detail):
   - Query: `Course.query.options(joinedload(Course.instructor)).order_by(Course.id.desc()).limit(3)`
   - Format: "Judul (Status-Harga, Instruktur: Nama)"

### INSTRUCTOR_FEATURES_CONTEXT

Konteks fitur instruktur mencakup:
- **Course Management**: Create, edit, delete courses dengan thumbnail upload
- **Lesson Management**: Add, edit, delete lessons (Text/Video/Meeting)
- **Quiz Management**: Create questions, set quiz dates (start & end)
- **Exercise Management**: Create exercises dengan deadline, grade submissions
- **Student Management**: View enrollments, student progress, grade exercises
- **Instructor Verification**: Upload credentials (PDF/Image/Link) untuk verifikasi
- **Revenue Tracking**: Monitor total revenue dari premium courses
- **PENTING**: Chatbot tidak bisa melakukan aksi, hanya memberikan panduan langkah demi langkah

## Fitur Utama

### 1. Conversation History
- Chatbot menyimpan semua percakapan ke database
- Saat user bertanya, chatbot load 10 chat terakhir sebagai context
- Memungkinkan percakapan yang lebih natural (user tidak perlu ulang konteks)
- **Auto-expire**: Chat >1 jam otomatis diabaikan untuk privacy

**Implementasi:**
- Model `ChatHistory` di `app.py`
- Migration table `chat_history`
- Update `build_chat_messages()` untuk load history
- Update `/api/ai-chat` untuk save chat

### 2. Clear Chat Button
- Tombol "🗑️ Clear Chat" di header halaman
- Menghapus semua riwayat chat user dari database
- Konfirmasi dialog sebelum menghapus
- UI update otomatis setelah clear

**Implementasi:**
- Endpoint `/api/ai-chat/clear` (DELETE method)
- CSS styling untuk tombol merah dengan hover effect
- JavaScript handler dengan konfirmasi

### 3. Auto-Expire (1 Jam)
- Chat history >1 jam otomatis diabaikan
- Privacy: chat lama tidak di-load ke context
- Hemat token: tidak load chat yang sudah tidak relevan

**Implementasi:**
```python
one_hour_ago = datetime.utcnow() - timedelta(hours=1)
history = ChatHistory.query.filter(ChatHistory.created_at >= one_hour_ago)...
```

### 4. Markdown Rendering
- Jawaban chatbot di-render sebagai HTML dari Markdown
- Bullet points tampil rapi, bold text berfungsi
- User messages tetap plain text (security)

**Implementasi:**
- Library `marked.js` via CDN
- Update `appendMessage()` untuk render Markdown

### 5. User Hints
- **Info Box**: Tips penggunaan chatbot (kemampuan, batasan, fitur)
- **Suggested Questions**: 4 tombol pertanyaan siap pakai yang bisa diklik
- Membantu user yang bingung mau tanya apa

**Implementasi:**
- HTML: info box dan suggestion buttons
- CSS: styling untuk info box biru dan tombol abu-abu
- JavaScript: handler untuk auto-fill textarea saat klik

## Kemampuan Chatbot

### ✅ Yang BISA Dijawab:

1. **Informasi Semua Kursus**:
   - Harga kursus apa saja (termasuk yang tidak populer)
   - Instruktur kursus apa saja
   - Status premium/gratis semua kursus
   - Material type (Text/Video/Meeting)

2. **Detail Kursus Populer**:
   - Jumlah materi/lesson
   - Deskripsi singkat
   - Jumlah siswa yang terdaftar

3. **Panduan Platform Student**:
   - Cara enroll kursus gratis
   - Cara beli kursus premium via shopping cart
   - Cara menggunakan shopping cart
   - Cara checkout dengan Midtrans
   - Metode pembayaran yang tersedia
   - Cara retry payment untuk transaksi pending
   - Cara mengikuti kuis (one-time submission)
   - Cara submit exercise
   - Cara download sertifikat (syarat: 100% progress, quiz score 100)
   - Cara melihat payment history

4. **Panduan Platform Instructor**:
   - Cara create/edit/delete course
   - Cara add/edit/delete lesson
   - Cara create quiz questions
   - Cara set quiz dates
   - Cara create exercise
   - Cara grade student submissions
   - Cara verifikasi instruktur (upload credentials)

5. **Informasi Payment Gateway**:
   - Metode pembayaran: GoPay, OVO, DANA, Bank Transfer, Credit Card, dll
   - Cara retry payment
   - Cara cek status pembayaran
   - Informasi tentang invoice dan expiry time

6. **Rekomendasi**:
   - Saran kursus berdasarkan minat
   - Kursus populer dan terbaru dengan data konkret

7. **Konteks Percakapan**:
   - Chatbot ingat percakapan dalam 1 jam terakhir
   - User tidak perlu ulang konteks

### ❌ Yang TIDAK BISA Dilakukan:

- **Melakukan aksi langsung**: enroll, checkout, reset password, submit tugas, process payment, dll
- **Hanya memberikan panduan**: Chatbot akan selalu menjelaskan bahwa user harus melakukan aksi sendiri melalui interface yang tersedia
- **Tidak tahu detail materi**: Isi lesson, file tugas, jawaban kuis tidak ada di context
- **Tidak tahu data user lain**: Privacy dijaga, hanya info user yang login
- **Tidak bisa akses Midtrans**: Chatbot tidak bisa create transaction, check payment status, atau process payment
- **Tidak bisa grade**: Chatbot tidak bisa grade exercise atau quiz

## Validasi & Pembatasan

- Endpoint hanya dapat digunakan setelah login
- Pesan >500 karakter ditolak dengan HTTP 400
- Jika `AI_PROVIDER` bukan `openrouter` atau `AI_API_KEY` kosong, backend mencatat peringatan dan langsung memberi balasan fallback
- Timeout dan pemeriksaan HTTP status >=400 menangani kegagalan API
- Semua error dicatat ke `logs/app.log` dengan `RotatingFileHandler` (512 KB, 5 cadangan)

## Konfigurasi Lingkungan

Set variabel berikut di `.env`:
```
AI_PROVIDER=openrouter
AI_API_KEY=<API_KEY_ANDA>
AI_MODEL=google/gemma-3-27b-it:free
AI_BASE_URL=https://openrouter.ai/api/v1/chat/completions
APP_BASE_URL=http://localhost:5000
```

### Model yang Direkomendasikan
- **Google Gemma 3 27B Instruct (free)**: Model gratis yang cukup baik untuk chatbot LMS, mendukung Bahasa Indonesia
- **OpenRouter Auto**: Otomatis memilih model terbaik yang tersedia (mungkin berbayar)

## Teknis Implementasi

### Context Injection
- Chatbot **tidak** langsung query database saat user bertanya
- Backend menyiapkan context dari database terlebih dahulu via `build_catalog_context()`
- Context dikirim sebagai bagian dari system message ke OpenRouter
- **Keuntungan**: Cepat, aman (chatbot tidak bisa ubah data), hemat (query database hanya 1x per request)

### Optimasi Query Database
- Menggunakan `joinedload(Course.instructor)` untuk menghindari N+1 query problem
- Query semua kursus dilakukan sekali, bukan per-kursus
- Deskripsi dibatasi 100 karakter untuk efisiensi token
- Hanya 5 kursus populer dan 3 terbaru yang mendapat detail lengkap

### Token Management
- **Max Tokens**: 600 (dinaikkan dari 300)
- Cukup untuk jawaban detail tanpa kepotong
- Tetap aman untuk model gratis
- Bisa dinaikkan jadi 800-1000 jika diperlukan

### Conversation History Management
- Simpan setiap user message dan chatbot reply ke database
- Load 10 chat terakhir (dalam 1 jam) sebagai context
- Auto-expire: chat >1 jam diabaikan
- Clear chat: hapus semua history user dari database

## Perluasan & Modifikasi

- **Prompt** – Perluas `SYSTEM_PROMPT`/`STUDENT_FEATURES_CONTEXT` untuk skenario tambahan
- **Model** – Ganti `AI_MODEL` dengan model lain dari OpenRouter
- **Konteks Tambahan** – Modifikasi `build_catalog_context()` untuk menambahkan info lain
- **Max Tokens** – Sesuaikan `max_tokens` di `call_openrouter()` jika diperlukan
- **Auto-expire Duration** – Ubah `timedelta(hours=1)` sesuai kebutuhan
- **Suggested Questions** – Edit pertanyaan di `ai_chat.html`
- **Testing** – Gunakan mocking `requests.post` di tes unit/integrasi

## Troubleshooting Cepat

- **Tidak ada respons** – Cek konfigurasi `.env`, lalu baca `logs/app.log` untuk detail error
- **Timeout** – Pastikan akses jaringan ke OpenRouter tersedia, atau tingkatkan nilai `timeout`
- **Jawaban keluar konteks** – Revisi isi `SYSTEM_PROMPT`/`STUDENT_FEATURES_CONTEXT`
- **Jawaban kepotong** – Tingkatkan `max_tokens` di `call_openrouter()` (default: 600)
- **Jawaban terlalu panjang** – Perkuat instruksi "ringkas" di `SYSTEM_PROMPT`
- **Chatbot bilang "bisa" melakukan aksi** – Pastikan `STUDENT_FEATURES_CONTEXT` dan `SYSTEM_PROMPT` sudah update dengan batasan yang jelas
- **Chatbot tidak tahu kursus tertentu** – Pastikan kursus ada di database; cek apakah `build_catalog_context()` berhasil query semua kursus
- **Chatbot tidak ingat konteks** – Cek apakah chat tersimpan di table `chat_history`
- **Clear chat tidak berfungsi** – Cek endpoint `/api/ai-chat/clear` dan JavaScript handler

## Changelog

### Desember 2024 - Payment Gateway & Shopping Cart Integration
- ✅ **Payment Gateway Midtrans**: Chatbot sekarang bisa memberikan panduan tentang payment gateway
  - Informasi metode pembayaran (GoPay, OVO, DANA, Bank Transfer, Credit Card, dll)
  - Panduan checkout dengan Midtrans Snap
  - Cara retry payment untuk transaksi pending/expired
  - Informasi tentang invoice dan expiry time
  - Cara cek status pembayaran
- ✅ **Shopping Cart**: Panduan lengkap penggunaan shopping cart
  - Cara add to cart
  - Cara checkout multiple courses
  - Cara remove from cart
- ✅ **Instructor Features**: Konteks fitur instruktur ditambahkan
  - Course management (create, edit, delete)
  - Lesson management (Text/Video/Meeting)
  - Quiz management dengan quiz dates
  - Exercise management dengan grading
  - Student management dan progress tracking
  - Instructor verification system
- ✅ **Enhanced Student Features**: Panduan lebih detail untuk student
  - One-time quiz submission
  - Exercise submission dengan deadline
  - Certificate download requirements (100% progress, quiz score 100)
  - Payment history tracking
- ✅ `INSTRUCTOR_FEATURES_CONTEXT` ditambahkan untuk support instruktur
- ✅ Kemampuan chatbot diperluas untuk cover semua fitur platform

### November 2024 - Major Upgrade
- ✅ Chatbot sekarang mengakses **semua kursus** di database (Opsi 3)
- ✅ **Conversation History**: Chatbot ingat konteks percakapan (1 jam)
- ✅ **Clear Chat Button**: User bisa reset konteks kapan saja
- ✅ **Auto-expire**: Chat >1 jam otomatis diabaikan
- ✅ **Markdown Rendering**: Jawaban tampil rapi dengan format
- ✅ **User Hints**: Info box dan suggested questions
- ✅ `SYSTEM_PROMPT` diperbarui untuk jawaban lebih ringkas dan relevan
- ✅ `STUDENT_FEATURES_CONTEXT` diperkuat dengan batasan chatbot yang lebih jelas
- ✅ `max_tokens` dinaikkan dari 300 → 600
- ✅ `build_catalog_context()` ditingkatkan dengan query semua kursus
- ✅ Optimasi query dengan `joinedload()` untuk performa
- ✅ Model default: `google/gemma-3-27b-it:free`