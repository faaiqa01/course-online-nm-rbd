# Langkah-langkah Modifikasi Ikon di `index.html`

Berikut adalah panduan langkah demi langkah untuk menambahkan ikon ke bagian "Mengapa Memilih Kami?" di file `templates/index.html`.

## 1. Buka File `index.html`

Buka file berikut di editor teks atau IDE Anda:
`C:\Users\abdil\Downloads\Nusa Mandiri\RBD\lms_flask_mysql\templates\index.html`

## 2. Temukan Bagian "Mengapa Memilih Kami?"

Cari bagian dalam file yang memiliki judul `Mengapa Memilih Kami?`. Anda akan menemukan struktur seperti ini:

```html
<!-- Features Section -->
<div class="features-section">
    <div class="container">
        <h2 class="section-title">Mengapa Memilih Kami?</h2>
        <div class="row">
            <div class="col-md-3">
                <div class="feature-item">
                    <div class="feature-icon">?</div>
                    <h3>Instruktur Ahli</h3>
                    <p>Materi disusun dan diajarkan langsung oleh para profesional berpengalaman di industrinya.</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="feature-item">
                    <div class="feature-icon">?</div>
                    <h3>Sertifikat Kelulusan</h3>
                    <p>Dapatkan sertifikat resmi setelah menyelesaikan kursus untuk menunjang karir Anda.</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="feature-item">
                    <div class="feature-icon">?</div>
                    <h3>Belajar Fleksibel</h3>
                    <p>Akses semua materi kursus kapan saja dan di mana saja sesuai dengan kecepatan Anda.</p>
                </div>
            </div>
            <div class="col-md-3">
                <div class="feature-item">
                    <div class="feature-icon">?</div>
                    <h3>Kemitraan Resmi</h3>
                    <p>Kami bekerja sama dengan berbagai institusi dan perusahaan terkemuka untuk materi yang relevan.</p>
                </div>
            </div>
        </div>
    </div>
</div>
```

## 3. Ganti Placeholder Ikon dengan Tag `<img>`

Untuk setiap `div` dengan kelas `feature-icon` yang berisi `?`, Anda perlu menggantinya dengan tag `<img>` yang menunjuk ke gambar ikon yang sesuai.

**Penting:** Path yang benar untuk `url_for` adalah `url_for('static', filename='file_pendukung/logo/nama_file_icon.png')`.

Berikut adalah perubahan yang perlu Anda lakukan untuk setiap item:

### a. Instruktur Ahli

Ganti baris:
```html
                    <div class="feature-icon">?</div>
```
Menjadi:
```html
                    <div class="feature-icon"><img src="{{ url_for('static', filename='file_pendukung/logo/instruktur-ahli-icon.png') }}" alt="Instruktur Ahli" width="60"></div>
```

### b. Sertifikat Kelulusan

Ganti baris:
```html
                    <div class="feature-icon">?</div>
```
Menjadi:
```html
                    <div class="feature-icon"><img src="{{ url_for('static', filename='file_pendukung/logo/sertifikat-kelulusan-icon.png') }}" alt="Sertifikat Kelulusan" width="60"></div>
```

### c. Belajar Fleksibel

Ganti baris:
```html
                    <div class="feature-icon">?</div>
```
Menjadi:
```html
                    <div class="feature-icon"><img src="{{ url_for('static', filename='file_pendukung/logo/belajar-fleksibel-icon.png') }}" alt="Belajar Fleksibel" width="60"></div>
```

### d. Kemitraan Resmi

Ganti baris:
```html
                    <div class="feature-icon">?</div>
```
Menjadi:
```html
                    <div class="feature-icon"><img src="{{ url_for('static', filename='file_pendukung/logo/kemitraan-resmi-icon.png') }}" alt="Kemitraan Resmi" width="60"></div>
```

Setelah semua perubahan diterapkan, simpan file `index.html`.

```