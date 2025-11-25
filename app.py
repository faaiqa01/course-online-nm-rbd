from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import TYPE_CHECKING
from sqlalchemy import inspect, text, func
import re
import os
import logging
from logging.handlers import RotatingFileHandler
import requests
from dotenv import load_dotenv

from sqlalchemy.orm import joinedload

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover - dependency issue surfaced at runtime
    Image = ImageDraw = ImageFont = None

if TYPE_CHECKING:
    from PIL.ImageFont import FreeTypeFont as PILFreeTypeFont
elif ImageFont is not None and hasattr(ImageFont, 'FreeTypeFont'):
    PILFreeTypeFont = ImageFont.FreeTypeFont
else:
    class PILFreeTypeFont:  # pragma: no cover - simple fallback type when Pillow unavailable
        pass

load_dotenv()

try:
    from flask_migrate import Migrate
except ImportError:
    Migrate = None

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')  # ganti di produksi
# Koneksi MySQL Laragon (ubah nama DB/password jika berbeda)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
if 'Migrate' in globals() and Migrate:
    migrate = Migrate(app, db)
else:
    migrate = None

login_manager = LoginManager(app)
login_manager.login_view = 'login'
# Setup rotating file log handler
LOG_DIR = Path(app.root_path) / 'logs'
LOG_DIR.mkdir(exist_ok=True)
log_file_path = LOG_DIR / 'app.log'
if not any(isinstance(handler, RotatingFileHandler) for handler in app.logger.handlers):
    file_handler = RotatingFileHandler(log_file_path, maxBytes=512000, backupCount=5, encoding='utf-8')
    file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)


ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
THUMBNAIL_UPLOAD_DIR = Path(app.static_folder) / 'uploads' / 'thumbnails'

ALLOWED_CERTIFICATE_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg'}
CERTIFICATE_UPLOAD_DIR = Path(app.static_folder) / 'uploads' / 'certificates'

def call_openrouter(messages, *, max_tokens=600):
    """Kirim permintaan ke OpenRouter dan kembalikan respons teks."""
    if os.getenv('AI_PROVIDER', '').lower() != 'openrouter':
        app.logger.warning('AI_PROVIDER bukan openrouter; chatbot dinonaktifkan.')
        return None

    api_key = os.getenv('AI_API_KEY')
    if not api_key:
        app.logger.warning('OpenRouter API key belum diatur.')
        return None

    base_url = os.getenv('AI_BASE_URL', 'https://openrouter.ai/api/v1/chat/completions')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'HTTP-Referer': os.getenv('APP_BASE_URL', 'http://localhost:5000'),
        'X-Title': 'LMS AI Assistant',
    }
    payload = {
        'model': os.getenv('AI_MODEL', 'openrouter/auto'),
        'messages': messages,
        'max_tokens': max_tokens,
    }

    app.logger.info('Mengirim permintaan AI model %s dengan %d pesan', payload['model'], len(messages))

    try:
        response = requests.post(base_url, headers=headers, json=payload, timeout=20)
    except requests.RequestException:
        app.logger.exception('Gagal memanggil OpenRouter')
        return None

    if response.status_code >= 400:
        app.logger.error('OpenRouter error %s: %s', response.status_code, response.text)
        return None

    try:
        data = response.json()
    except ValueError:
        app.logger.error('Respons OpenRouter bukan JSON valid: %s', response.text)
        return None

    choices = data.get('choices') or []
    if not choices:
        app.logger.error('OpenRouter tidak mengembalikan pilihan respons: %s', data)
        return None

    message = choices[0].get('message') or {}
    content = message.get('content')

    if isinstance(content, list):
        filtered_segments = []
        for part in content:
            if isinstance(part, dict):
                segment_type = (part.get('type') or '').lower()
                text = part.get('text', '')
                if segment_type in {'reasoning', 'thinking', 'chain_of_thought', 'analysis'}:
                    continue
                if text:
                    filtered_segments.append(text)
            else:
                filtered_segments.append(str(part))
        content = ' '.join(filtered_segments).strip()



    if not content:
        reasoning = message.get('reasoning')
        if isinstance(reasoning, list):
            collected = []
            for part in reasoning:
                if isinstance(part, dict):
                    text = part.get('text', '')
                    if text:
                        collected.append(text)
                else:
                    collected.append(str(part))
            reasoning = "\n".join(collected)
        if isinstance(reasoning, str):
            chunks = [section.strip() for section in re.split(r"\n\s*\n", reasoning) if section.strip()]
            if chunks:
                content = chunks[-1]
            elif reasoning.strip():
                content = reasoning.strip()

    if not content:
        app.logger.error('OpenRouter tidak mengembalikan konten pesan: %s', message)
        return None

    return content.strip()

SYSTEM_PROMPT = (
    "Kamu adalah Asisten AI TechNova. Bantu pengguna dalam Bahasa Indonesia dengan gaya natural dan ringkas. "
    "PENTING: Sesuaikan panjang jawaban dengan kompleksitas pertanyaan - pertanyaan sederhana dijawab singkat, pertanyaan detail dijawab lengkap. "
    "Gunakan informasi katalog kursus yang diberikan untuk menjawab dengan data konkret (nama kursus, harga, instruktur). "
    "Prioritaskan jawaban praktis dan langsung ke poin, hindari penjelasan bertele-tele. "
    "Jika user meminta kamu melakukan aksi (reset password, enroll, checkout, dll), SELALU jelaskan bahwa kamu tidak bisa melakukan aksi tersebut, "
    "hanya bisa memberikan panduan langkah-langkahnya. "
    "Jika data tidak tersedia, arahkan pengguna ke halaman Kursus atau hubungi admin dengan sopan."
)
FALLBACK_AI_REPLY = 'Maaf, asisten AI sedang tidak dapat merespons. Coba lagi nanti'
STUDENT_FEATURES_CONTEXT = (
    "Fitur role student mencakup: menjelajahi katalog kursus lengkap dengan filter materi, status premium, dan pencarian; "
    "melihat detail kursus termasuk profil instruktur, daftar materi, status enrollment, dan progres belajar; menambahkan atau "
    "menghapus kursus premium dari keranjang lalu melakukan checkout manual setelah konfirmasi; mengelola halaman Kursus Saya "
    "untuk memantau progres materi/quiz/latihan; menandai materi selesai; mengirim latihan satu kali; mengikuti kuis satu kali "
    "dengan syarat enrollment aktif; serta mengunduh sertifikat setelah seluruh syarat terpenuhi. "
    "PENTING: Asisten AI TIDAK BISA melakukan aksi apapun (enroll, checkout, reset password, submit tugas, dll) - "
    "hanya memberikan panduan langkah demi langkah. Selalu jelaskan bahwa user harus melakukan sendiri."
)

INSTRUCTOR_FEATURES_CONTEXT = (
    "Fitur role instructor mencakup: membuat kursus baru dengan mengisi judul, deskripsi, status premium/gratis, harga (jika premium), "
    "dan thumbnail; mengelola kursus yang sudah dibuat melalui halaman Dashboard Instruktur; menambahkan materi (lesson) ke kursus "
    "dengan judul, konten teks, dan video URL (YouTube/Vimeo); membuat soal kuis multiple choice dengan 4 pilihan jawaban; "
    "menandai jawaban yang benar untuk setiap soal; melihat daftar siswa yang terdaftar di kursus mereka; melihat statistik "
    "kursus (jumlah siswa, jumlah materi); mengedit atau menghapus kursus, materi, dan soal kuis yang sudah dibuat. "
    "PENTING: Asisten AI TIDAK BISA melakukan aksi apapun (buat kursus, tambah materi, hapus soal, dll) - "
    "hanya memberikan panduan langkah demi langkah. Selalu jelaskan bahwa user harus melakukan sendiri melalui interface yang tersedia."
)


AUTH_FEATURES_CONTEXT = (
    "Setiap pengguna dapat membuat akun baru melalui halaman Register dengan memasukkan nama, email unik, kata sandi, dan memilih peran student atau instructor. "
    "Setelah registrasi, pengguna login lewat halaman Login memakai email dan kata sandi; halaman Forgot/Reset Password mengizinkan penggantian sandi dengan memasukkan email, kata sandi baru, dan konfirmasi ketika diperlukan; menu Logout mengakhiri sesi. "
    "Halaman Profil dipakai untuk memperbarui nama serta email; instruktur juga dapat menambahkan keahlian, institusi, pengalaman mengajar, serta mengelola unggahan atau tautan sertifikat verifikasi."
)

PLATFORM_FEATURES_CONTEXT = (
    "Halaman Tentang TechNova Academy merangkum visi, misi, dan gambaran singkat platform sebagai pusat pembelajaran digital. "
    "Dashboard utama menampilkan ringkasan kursus aktif, progres belajar, dan pintasan menuju tugas atau materi terbaru sesuai peran pengguna. "
    "Menu Lihat Kursus menampilkan katalog lengkap dengan pencarian, filter materi, dan status premium agar pengguna mudah menelusuri program yang tersedia."
)

def build_catalog_context() -> str:
    """Ambil ringkasan kursus untuk dimasukkan ke prompt AI."""
    try:
        total_courses = Course.query.count()
        free_courses = Course.query.filter_by(is_premium=False).count()
        premium_courses = Course.query.filter_by(is_premium=True).count()
        
        # Query SEMUA kursus dengan info ringkas (judul, harga, instruktur) - Opsi 3
        all_courses = (
            Course.query
            .options(joinedload(Course.instructor))
            .order_by(Course.title.asc())
            .all()
        )
        
        # Query kursus populer dengan detail lengkap (harga, instruktur, deskripsi, jumlah lesson)
        popular_courses_query = (
            db.session.query(
                Course,
                func.count(Enrollment.id).label('enrolled'),
                func.count(Lesson.id).label('lesson_count')
            )
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .outerjoin(Lesson, Lesson.course_id == Course.id)
            .options(joinedload(Course.instructor))
            .group_by(Course.id)
            .order_by(func.count(Enrollment.id).desc(), Course.title.asc())
            .limit(5)
            .all()
        )
        
        latest_courses = (
            Course.query
            .options(joinedload(Course.instructor))
            .order_by(Course.id.desc())
            .limit(3)
            .all()
        )
    except Exception:  # pragma: no cover - defensive
        app.logger.exception('Gagal menyiapkan konteks katalog AI')
        return ''

    parts = []
    if total_courses:
        parts.append(f'Tersedia {total_courses} kursus (gratis: {free_courses}, premium: {premium_courses}).')

    # Daftar SEMUA kursus dengan info ringkas (Opsi 3)
    if all_courses:
        all_courses_list = []
        for course in all_courses:
            if not getattr(course, 'title', None):
                continue
            
            # Format ringkas: "Judul (Status-Harga, Instruktur: Nama)"
            instructor_name = getattr(course.instructor, 'name', 'Tidak diketahui') if course.instructor else 'Tidak diketahui'
            
            if course.is_premium:
                price_str = f'Rp{course.price:,}' if course.price else 'Rp0'
                all_courses_list.append(f"{course.title} (Premium-{price_str}, Instruktur: {instructor_name})")
            else:
                all_courses_list.append(f"{course.title} (Gratis, Instruktur: {instructor_name})")
        
        if all_courses_list:
            parts.append('Daftar semua kursus: ' + ', '.join(all_courses_list) + '.')


    # Format kursus populer dengan detail lengkap
    if popular_courses_query:
        popular_details = []
        for course, enrolled_count, lesson_count in popular_courses_query:
            if not course or not course.title:
                continue
            
            # Format: "Judul Kursus (Status - Harga, Instruktur: Nama, X materi, Y siswa)"
            detail_parts = [course.title]
            
            # Status dan harga
            if course.is_premium:
                price_str = f'Rp {course.price:,}' if course.price else 'Rp 0'
                detail_parts.append(f'Premium - {price_str}')
            else:
                detail_parts.append('Gratis')
            
            # Instruktur
            instructor_name = getattr(course.instructor, 'name', 'Tidak diketahui') if course.instructor else 'Tidak diketahui'
            detail_parts.append(f'Instruktur: {instructor_name}')
            
            # Jumlah materi
            if lesson_count:
                detail_parts.append(f'{int(lesson_count)} materi')
            
            # Deskripsi singkat (max 100 karakter)
            if course.description:
                short_desc = course.description[:100].strip()
                if len(course.description) > 100:
                    short_desc += '...'
                detail_parts.append(f'Deskripsi: {short_desc}')
            
            # Jumlah siswa
            if enrolled_count:
                detail_parts.append(f'{int(enrolled_count)} siswa')
            
            popular_details.append(f"{course.title} ({', '.join(detail_parts[1:])})")
        
        if popular_details:
            parts.append('Kursus terpopuler: ' + '; '.join(popular_details) + '.')

    # Format kursus terbaru dengan detail
    if latest_courses:
        latest_details = []
        for course in latest_courses:
            if not getattr(course, 'title', None):
                continue
            
            detail_parts = [course.title]
            
            # Status dan harga
            if course.is_premium:
                price_str = f'Rp {course.price:,}' if course.price else 'Rp 0'
                detail_parts.append(f'Premium - {price_str}')
            else:
                detail_parts.append('Gratis')
            
            # Instruktur
            instructor_name = getattr(course.instructor, 'name', 'Tidak diketahui') if course.instructor else 'Tidak diketahui'
            detail_parts.append(f'Instruktur: {instructor_name}')
            
            latest_details.append(f"{course.title} ({', '.join(detail_parts[1:])})")
        
        if latest_details:
            parts.append('Kursus terbaru: ' + '; '.join(latest_details) + '.')

    return ' '.join(parts)

def build_instructor_context(instructor_id: int) -> str:
    """Ambil ringkasan kursus yang dibuat oleh instructor untuk dimasukkan ke prompt AI."""
    try:
        # Query kursus yang dibuat oleh instructor ini
        instructor_courses = (
            db.session.query(
                Course,
                func.count(Enrollment.id).label('student_count'),
                func.count(Lesson.id).label('lesson_count')
            )
            .outerjoin(Enrollment, Enrollment.course_id == Course.id)
            .outerjoin(Lesson, Lesson.course_id == Course.id)
            .filter(Course.instructor_id == instructor_id)
            .group_by(Course.id)
            .order_by(Course.title.asc())
            .all()
        )
        
        if not instructor_courses:
            return "Anda belum membuat kursus apapun."
        
        parts = []
        parts.append(f"Anda telah membuat {len(instructor_courses)} kursus:")
        
        course_details = []
        for course, student_count, lesson_count in instructor_courses:
            if not getattr(course, 'title', None):
                continue
            
            # Format: "Judul (Status-Harga, X siswa, Y materi)"
            detail_parts = []
            
            if course.is_premium:
                price_str = f'Rp{course.price:,}' if course.price else 'Rp0'
                detail_parts.append(f'Premium-{price_str}')
            else:
                detail_parts.append('Gratis')
            
            detail_parts.append(f'{student_count} siswa')
            detail_parts.append(f'{lesson_count} materi')
            
            course_details.append(f"{course.title} ({', '.join(detail_parts)})")
        
        if course_details:
            parts.append('; '.join(course_details) + '.')
        
        return ' '.join(parts)
    
    except Exception:
        app.logger.exception('Gagal menyiapkan konteks instructor')
        return ''

def build_chat_messages(user_message: str, *, user=None, include_history=True) -> list[dict]:
    """Siapkan payload percakapan untuk OpenRouter."""
    user_context = []
    if user:
        role_label = 'instruktur' if getattr(user, 'role', 'student') == 'instructor' else 'siswa'
        user_context.append(f'Pengguna bernama {getattr(user, "name", "Pengguna")} berperan sebagai {role_label}.')
        expertise = getattr(user, 'expertise', None)
        if expertise:
            user_context.append(f'Keahlian: {expertise}.')
    system_message = SYSTEM_PROMPT
    if user_context:
        system_message += ' Informasi pengguna: ' + ' '.join(user_context)
    system_message += ' Informasi platform: ' + PLATFORM_FEATURES_CONTEXT
    system_message += ' Panduan akun: ' + AUTH_FEATURES_CONTEXT
    
    # Role-specific features context
    if getattr(user, 'role', None) == 'student':
        system_message += ' Panduan fitur siswa: ' + STUDENT_FEATURES_CONTEXT
        # Student: tampilkan katalog semua kursus
        catalog_context = build_catalog_context()
        if catalog_context:
            system_message += ' Informasi katalog: ' + catalog_context
    elif getattr(user, 'role', None) == 'instructor':
        system_message += ' Panduan fitur instruktur: ' + INSTRUCTOR_FEATURES_CONTEXT
        # Instructor: tampilkan kursus yang mereka buat
        instructor_context = build_instructor_context(user.id)
        if instructor_context:
            system_message += ' Kursus Anda: ' + instructor_context


    messages = [{'role': 'system', 'content': system_message}]
    
    # Load conversation history (10 chat terakhir untuk context)
    if include_history and user:
        try:
            # Auto-expire: hanya load chat dalam 1 jam terakhir
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            history = (
                ChatHistory.query
                .filter_by(user_id=user.id)
                .filter(ChatHistory.created_at >= one_hour_ago)  # Filter: hanya chat <1 jam
                .order_by(ChatHistory.created_at.desc())
                .limit(10)
                .all()
            )
            # Reverse agar urutan chronological (oldest first)
            for chat in reversed(history):
                messages.append({
                    'role': chat.role,
                    'content': chat.message
                })
        except Exception:
            app.logger.exception('Gagal load chat history untuk user %s', user.id)
    
    # Tambahkan pertanyaan user saat ini
    messages.append({'role': 'user', 'content': user_message.strip()})
    
    return messages



def build_certificate_pdf(*, background_path: Path, student_name: str, instructor_name: str,
                          material_type: str, course_title: str, issued_date: str) -> BytesIO:
    if Image is None or ImageDraw is None or ImageFont is None:
        raise RuntimeError('Pillow tidak tersedia untuk membuat sertifikat.')

    background = Image.open(background_path).convert('RGB')
    draw = ImageDraw.Draw(background)
    width, height = background.size
    text_color = (20, 45, 85)

    font_directories = [
        Path(app.root_path) / 'file_pendukung' / 'sertifikat',
        Path(app.root_path) / 'file_pendukung',
        Path.home() / 'fonts',
        Path('C:/Windows/Fonts'),
        Path('/usr/share/fonts/truetype'),
        Path('/usr/share/fonts/truetype/dejavu'),
        Path('/Library/Fonts'),
        None,
    ]

    def load_font(size: int, *, bold: bool = False) -> PILFreeTypeFont:
        regular_candidates = ['Arial.ttf', 'arial.ttf', 'DejaVuSans.ttf', 'LiberationSans-Regular.ttf']
        bold_candidates = ['Arial Bold.ttf', 'arialbd.ttf', 'DejaVuSans-Bold.ttf', 'LiberationSans-Bold.ttf']
        candidates = bold_candidates if bold else regular_candidates
        for directory in font_directories:
            for candidate in candidates:
                try:
                    if directory is None:
                        font = ImageFont.truetype(candidate, size=size)
                    else:
                        font_path = directory / candidate
                        if not font_path.exists():
                            continue
                        font = ImageFont.truetype(str(font_path), size=size)
                    return font
                except (OSError, IOError):
                    continue
        return ImageFont.load_default()

    student_font = load_font(72, bold=True)
    body_font = load_font(38)
    info_font = load_font(30)
    signature_font = load_font(32, bold=True)

    def draw_centered(text: str, center_x: float, y: float, font: PILFreeTypeFont,
                      *, fill=text_color, line_gap: int = 10) -> float:
        if not text:
            return y
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = int(center_x - text_width / 2)
        draw.text((x, int(y)), text, font=font, fill=fill)
        return y + text_height + line_gap

    def measure_width(value: str, font: PILFreeTypeFont) -> float:
        if hasattr(draw, 'textlength'):
            return draw.textlength(value, font=font)
        bbox = draw.textbbox((0, 0), value, font=font)
        return bbox[2] - bbox[0]

    def wrap_text(value: str, font: PILFreeTypeFont, max_width: float) -> list[str]:
        words = value.split()
        lines = []
        current = ''
        for word in words:
            candidate = (current + ' ' + word).strip()
            if candidate and measure_width(candidate, font) <= max_width:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or ['']

    center_x = width / 2

    student_y = height * 0.42
    body_y = draw_centered(student_name, center_x, student_y, student_font, line_gap=50)

    body_lines = []
    course_title = (course_title or '').strip()
    material_label = (material_type or '').strip()
    if material_label and course_title:
        program_label = f'{material_label} - {course_title}'
    elif material_label:
        program_label = material_label
    elif course_title:
        program_label = course_title
    else:
        program_label = 'Program'

    paragraph = (
        'Telah mengikuti dan menyelesaikan seluruh materi serta latihan pada program kursus '
        f'{program_label} dan dinyatakan lulus dengan hasil yang memuaskan.'
    )
    body_lines.extend(wrap_text(paragraph, body_font, max_width=width * 0.75))

    for line in body_lines:
        body_y = draw_centered(line, center_x, body_y, body_font)

    body_y = draw_centered(f'Diterbitkan pada {issued_date}', center_x, body_y + 30, info_font)

    signature_y = height * 0.84
    draw_centered(instructor_name, width * 0.27, signature_y, signature_font, line_gap=0)
    draw_centered('TechNova Academy', width * 0.73, signature_y, signature_font, line_gap=0)

    output = BytesIO()
    background.save(output, format='PDF')
    output.seek(0)
    return output

# ---------- Models ----------
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='student')  # student or instructor
    expertise = db.Column(db.String(100), nullable=True) # Bidang keahlian
    institution = db.Column(db.String(150), nullable=True) # Asal Lembaga
    teaching_experience = db.Column(db.Integer, nullable=True) # Lama Mengajar (tahun)
    certificate_type = db.Column(db.String(50), default='default') # Tipe sertifikat (default, pdf, image, link)
    certificate_data = db.Column(db.String(500), nullable=True) # Data sertifikat (path file atau URL)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_verified(self):
        if self.role != 'instructor':
            return False
        return self.certificate_type != 'default' and bool(self.certificate_data)

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    is_premium = db.Column(db.Boolean, default=False)
    price = db.Column(db.Integer, default=0)
    instructor_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    instructor = db.relationship('User')
    thumbnail_path = db.Column(db.String(500), default='')
    material_type = db.Column(db.String(100), nullable=True) # Jenis Materi
    quiz_start_date = db.Column(db.DateTime, nullable=True)
    quiz_end_date = db.Column(db.DateTime, nullable=True)

class Lesson(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, default='')
    video_url = db.Column(db.String(500), default='')
    meeting_url = db.Column(db.String(500), default='') # New field for meeting links
    start_date = db.Column(db.DateTime, nullable=True)

class Enrollment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    unlocked = db.Column(db.Boolean, default=False)  # simulate payment unlock

class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)

class Choice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    text = db.Column(db.String(255), nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

class Attempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Integer, default=0)
    passed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)

    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', name='uq_cart_user_course'),)

class ChatHistory(db.Model):
    """Model untuk menyimpan riwayat percakapan AI chatbot."""
    __tablename__ = 'chat_history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # 'user' or 'assistant'
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    user = db.relationship('User', backref='chat_history')
    
    def __repr__(self):
        return f'<ChatHistory {self.id} {self.role}>'





class LessonProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lesson_id = db.Column(db.Integer, db.ForeignKey('lesson.id'), nullable=False)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'lesson_id', name='uq_user_lesson'),)

class Exercise(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False, unique=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, default='')
    exercise_url = db.Column(db.String(500), default='')
    start_date = db.Column(db.DateTime, nullable=True)
    end_date = db.Column(db.DateTime, nullable=True)

class ExerciseSubmission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    submission_url = db.Column(db.String(500), nullable=False)
    score = db.Column(db.Integer, nullable=False, default=0)

    __table_args__ = (db.UniqueConstraint('user_id', 'course_id', name='uq_exercise_submission_user_course'),)


def ensure_course_thumbnail_column():
    try:
        inspector = inspect(db.engine)
        columns = {col['name'] for col in inspector.get_columns('course')}
        if 'thumbnail_path' not in columns:
            with db.engine.begin() as conn:
                conn.execute(text("ALTER TABLE course ADD COLUMN thumbnail_path VARCHAR(500)"))
    except Exception as exc:
        app.logger.warning('Could not ensure thumbnail column: %s', exc)

def _is_allowed_image(filename):
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def save_course_thumbnail(file_storage):
    filename = secure_filename(file_storage.filename) if getattr(file_storage, 'filename', None) else ''
    if not filename or not _is_allowed_image(filename):
        return None
    THUMBNAIL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    sanitized = f"{timestamp}_{filename}"
    destination = THUMBNAIL_UPLOAD_DIR / sanitized
    file_storage.save(destination)
    relative_path = Path('uploads') / 'thumbnails' / sanitized
    return str(relative_path).replace('\\', '/')

def is_valid_thumbnail_url(url):
    if not url:
        return False
    parsed = urlparse(url)
    return parsed.scheme in ('http', 'https') and bool(parsed.netloc)

def delete_course_thumbnail(thumbnail_path):
    if not thumbnail_path or thumbnail_path.startswith('http'):
        return
    try:
        base = Path(app.static_folder).resolve()
        target = (base / thumbnail_path).resolve()
        if base in target.parents or target == base:
            if target.is_file():
                target.unlink()
    except Exception as exc:
        app.logger.warning('Failed to delete thumbnail %s: %s', thumbnail_path, exc)

def resolve_thumbnail_input(thumbnail_file, thumbnail_url, existing_path=None, mode=None):
    mode = (mode or '').lower()
    url_value = (thumbnail_url or '').strip()
    has_file = bool(thumbnail_file and getattr(thumbnail_file, 'filename', ''))
    if has_file:
        saved_path = save_course_thumbnail(thumbnail_file)
        if not saved_path:
            return None, 'File thumbnail harus berupa gambar (png/jpg/jpeg/gif/webp).'
        if existing_path and not existing_path.startswith('http'):
            delete_course_thumbnail(existing_path)
        return saved_path, None
    if url_value:
        if is_valid_thumbnail_url(url_value):
            if existing_path and not existing_path.startswith('http'):
                delete_course_thumbnail(existing_path)
            return url_value, None
        return None, 'URL thumbnail tidak valid (gunakan awalan http/https).'
    if mode == 'url':
        if existing_path and not existing_path.startswith('http'):
            delete_course_thumbnail(existing_path)
        return '', None
    return (existing_path or ''), None


def resolve_thumbnail_input(thumbnail_file, thumbnail_url, existing_path=None, mode=None):
    mode = (mode or '').lower()
    url_value = (thumbnail_url or '').strip()
    has_file = bool(thumbnail_file and getattr(thumbnail_file, 'filename', ''))
    if has_file:
        saved_path = save_course_thumbnail(thumbnail_file)
        if not saved_path:
            return None, 'File thumbnail harus berupa gambar (png/jpg/jpeg/gif/webp).'
        if existing_path and not existing_path.startswith('http'):
            delete_course_thumbnail(existing_path)
        return saved_path, None
    if url_value:
        if is_valid_thumbnail_url(url_value):
            if existing_path and not existing_path.startswith('http'):
                delete_course_thumbnail(existing_path)
            return url_value, None
        return None, 'URL thumbnail tidak valid (gunakan awalan http/https).'
    if mode == 'url':
        if existing_path and not existing_path.startswith('http'):
            delete_course_thumbnail(existing_path)
        return '', None
    return (existing_path or ''), None


def _is_allowed_certificate_file(filename):
    if not filename or '.' not in filename:
        return False
    return filename.rsplit('.', 1)[1].lower() in ALLOWED_CERTIFICATE_EXTENSIONS


def save_certificate_file(file_storage):
    filename = secure_filename(file_storage.filename) if getattr(file_storage, 'filename', None) else ''
    if not filename or not _is_allowed_certificate_file(filename):
        return None
    CERTIFICATE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    sanitized = f"{timestamp}_{filename}"
    destination = CERTIFICATE_UPLOAD_DIR / sanitized
    file_storage.save(destination)
    relative_path = Path('uploads') / 'certificates' / sanitized
    return str(relative_path).replace('\\', '/')

def delete_certificate_file(certificate_path):
    if not certificate_path or certificate_path.startswith('http'):
        return
    try:
        base = Path(app.static_folder).resolve()
        target = (base / certificate_path).resolve()
        if base in target.parents or target == base:
            if target.is_file():
                target.unlink()
    except Exception as exc:
        app.logger.warning('Failed to delete certificate %s: %s', certificate_path, exc)

def is_valid_url(url):
    return is_valid_thumbnail_url(url)

def prepare_video_embed(video_url):
    if not video_url:
        return None
    url = video_url.strip()
    if not url:
        return None
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path or ''
    if 'youtu.be' in netloc:
        video_id = path.strip('/')
        if video_id:
            return {'type': 'iframe', 'provider': 'youtube', 'embed_url': f"https://www.youtube.com/embed/{video_id}"}
    if 'youtube.com' in netloc:
        query = parse_qs(parsed.query)
        video_id = query.get('v', [None])[0]
        if not video_id:
            segments = [segment for segment in path.split('/') if segment]
            if segments and segments[0] in ('embed', 'v') and len(segments) > 1:
                video_id = segments[1]
        if video_id:
            return {'type': 'iframe', 'provider': 'youtube', 'embed_url': f"https://www.youtube.com/embed/{video_id}"}
    if 'vimeo.com' in netloc:
        segments = [segment for segment in path.split('/') if segment]
        video_id = segments[-1] if segments else None
        if video_id:
            return {'type': 'iframe', 'provider': 'vimeo', 'embed_url': f"https://player.vimeo.com/video/{video_id}"}
    lower_url = url.lower()
    if lower_url.endswith(('.mp4', '.webm', '.ogg', '.mov')):
        return {'type': 'video', 'provider': 'file', 'embed_url': url}
    return {'type': 'iframe', 'provider': 'external', 'embed_url': url}

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- Init DB on first requests ----------
@app.before_request
def create_tables():
    db.create_all()

@app.before_request
def check_instructor_verification():
    # Cek jika user terautentikasi, adalah seorang pengajar, dan belum terverifikasi
    if current_user.is_authenticated and current_user.role == 'instructor' and not current_user.is_verified:
        # Izinkan akses ke halaman profil, logout, dan file statis
        if request.endpoint and request.endpoint not in ['profile', 'logout', 'static', 'delete_instructor_certificate']:
            return redirect(url_for('profile'))

# ---------- Routes ----------

@app.route('/ai-chat')
@login_required
def ai_chat_page():
    return render_template('ai_chat.html', title='Asisten AI')

@app.route('/api/ai-chat', methods=['POST'])
@login_required
def api_ai_chat():
    payload = request.get_json(silent=True) or {}
    user_message = (payload.get('message') or '').strip()

    if not user_message:
        return jsonify({'error': 'Pesan tidak boleh kosong.'}), 400

    if len(user_message) > 500:
        return jsonify({'error': 'Pesan terlalu panjang. Maksimal 500 karakter.'}), 400

    app.logger.info('AI chat request user_id=%s role=%s len=%s', getattr(current_user, 'id', 'anon'), getattr(current_user, 'role', 'unknown'), len(user_message))

    # Simpan pertanyaan user ke database
    try:
        user_chat = ChatHistory(
            user_id=current_user.id,
            role='user',
            message=user_message
        )
        db.session.add(user_chat)
        db.session.commit()
    except Exception:
        app.logger.exception('Gagal simpan user message ke chat history')
        db.session.rollback()

    # Build messages dengan conversation history
    messages = build_chat_messages(user_message, user=current_user, include_history=True)
    ai_reply = call_openrouter(messages)

    if not ai_reply:
        return jsonify({'reply': FALLBACK_AI_REPLY})

    # Simpan jawaban AI ke database
    try:
        ai_chat = ChatHistory(
            user_id=current_user.id,
            role='assistant',
            message=ai_reply
        )
        db.session.add(ai_chat)
        db.session.commit()
    except Exception:
        app.logger.exception('Gagal simpan AI reply ke chat history')
        db.session.rollback()

    return jsonify({'reply': ai_reply})

@app.route('/api/ai-chat/clear', methods=['DELETE'])
@login_required
def clear_chat_history():
    """Hapus semua chat history user saat ini."""
    try:
        deleted = ChatHistory.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        app.logger.info('Cleared %d chat history for user %s', deleted, current_user.id)
        return jsonify({'success': True, 'deleted': deleted})
    except Exception:
        app.logger.exception('Failed to clear chat history for user %s', current_user.id)
        db.session.rollback()
        return jsonify({'error': 'Gagal menghapus riwayat chat'}), 500


@app.route('/')
def index():
    # Query untuk kursus terpopuler berdasarkan jumlah pendaftar
    popular_courses = db.session.query(
        Course, func.count(Enrollment.id).label('enrollment_count')
    ).outerjoin(Enrollment, Course.id == Enrollment.course_id)\
    .group_by(Course.id)\
    .order_by(func.count(Enrollment.id).desc())\
    .limit(4)\
    .all()

    # Query untuk kursus terbaru
    newest_courses = Course.query.order_by(Course.id.desc()).limit(4).all()
    
    # Karena hasil popular_courses adalah tuple (Course, enrollment_count), kita ekstrak objek Course saja
    popular_courses_objects = [course for course, count in popular_courses]

    return render_template('index.html', popular_courses=popular_courses_objects, newest_courses=newest_courses)

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        password = request.form['password']
        role = request.form['role']
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register'))
        u = User(name=name, email=email, role=role)
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        flash('Registered. Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        u = User.query.filter_by(email=email).first()
        if not u or not u.check_password(password):
            flash('Invalid credentials', 'error')
            return redirect(url_for('login'))
        login_user(u)
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET','POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        confirm = request.form['confirm_password']
        if password != confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('forgot_password'))
        if len(password) < 6:
            flash('Password must be at least 6 characters', 'error')
            return redirect(url_for('forgot_password'))
        user = User.query.filter_by(email=email).first()
        if user:
            user.set_password(password)
            db.session.commit()
        flash('If the email is registered, the password has been reset. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out', 'success')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip().lower()
        expertise = request.form.get('expertise') # Ambil data keahlian
        institution = request.form.get('institution') # Ambil data institusi
        teaching_experience_str = request.form.get('teaching_experience')

        # Check if email is already taken by another user
        existing_user = User.query.filter(User.email == email, User.id != current_user.id).first()
        if existing_user:
            flash('Email already registered by another user.', 'error')
            return redirect(url_for('profile'))

        current_user.name = name
        current_user.email = email
        if current_user.role == 'instructor':
            current_user.expertise = expertise
            current_user.institution = institution
            # Konversi ke integer, tangani jika kosong atau tidak valid
            if teaching_experience_str and teaching_experience_str.isdigit():
                current_user.teaching_experience = int(teaching_experience_str)
            else:
                current_user.teaching_experience = None

            # Handle certificate upload/link
            old_certificate_data = current_user.certificate_data
            old_certificate_type = current_user.certificate_type

            certificate_type = request.form.get('certificate_type', 'default')
            certificate_file = request.files.get('certificate_file')
            certificate_link = request.form.get('certificate_link', '').strip()

            new_certificate_data = None
            error_message = None

            if certificate_type == 'default':
                new_certificate_data = None
            elif certificate_type in ['pdf', 'image']:
                if certificate_file and certificate_file.filename:
                    saved_path = save_certificate_file(certificate_file)
                    if not saved_path:
                        error_message = 'File sertifikat tidak valid (hanya PDF, PNG, JPG, JPEG).'
                    else:
                        new_certificate_data = saved_path
                elif old_certificate_type == certificate_type and old_certificate_data and not old_certificate_data.startswith('http'):
                    # Keep existing file if no new file is uploaded and type is same
                    new_certificate_data = old_certificate_data
                else:
                    # If type is pdf/image, but no file uploaded and no old file to keep, then it's effectively cleared
                    new_certificate_data = None
            elif certificate_type == 'link':
                if certificate_link:
                    if is_valid_url(certificate_link):
                        new_certificate_data = certificate_link
                    else:
                        error_message = 'Link sertifikat tidak valid (gunakan awalan http/https).'
                elif old_certificate_type == certificate_type and old_certificate_data and old_certificate_data.startswith('http'):
                    # Keep existing link if no new link is provided and type is same
                    new_certificate_data = old_certificate_data
                else:
                    # If type is link, but no link provided and no old link to keep, then it's effectively cleared
                    new_certificate_data = None
            
            if error_message:
                flash(error_message, 'error')
                return redirect(url_for('profile'))

            # Delete old file if type changed or new file uploaded
            if old_certificate_data and not old_certificate_data.startswith('http'):
                if certificate_type != old_certificate_type or (certificate_type in ['pdf', 'image'] and new_certificate_data != old_certificate_data):
                    delete_certificate_file(old_certificate_data)

            current_user.certificate_type = certificate_type
            current_user.certificate_data = new_certificate_data

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('profile'))

    show_warning = (current_user.role == 'instructor' and not current_user.is_verified)
    return render_template('profile.html', show_verification_warning=show_warning)

@app.route('/profile/delete_certificate', methods=['POST'])
@login_required
def delete_instructor_certificate():
    if current_user.role != 'instructor':
        flash('Instructor only', 'error')
        return redirect(url_for('profile'))

    if current_user.certificate_data and not current_user.certificate_data.startswith('http'):
        delete_certificate_file(current_user.certificate_data)
    
    current_user.certificate_type = 'default'
    current_user.certificate_data = None
    db.session.commit()
    flash('Sertifikat berhasil dihapus.', 'success')
    return redirect(url_for('profile'))

@app.route('/courses')
def courses():
    material_type = request.args.get('material_type', '')
    is_premium = request.args.get('is_premium', '')
    search = request.args.get('search', '')

    query = Course.query.options(joinedload(Course.instructor))

    if current_user.is_authenticated and current_user.role == 'instructor':
        query = query.filter(Course.instructor_id == current_user.id)

    if material_type:
        query = query.filter(Course.material_type == material_type)
    
    if is_premium:
        premium_bool = is_premium.lower() == 'yes'
        query = query.filter(Course.is_premium == premium_bool)

    if search:
        query = query.filter(Course.title.ilike(f'%{search}%'))

    cs = query.order_by(Course.id.desc()).all()

    lesson_titles_map = {}
    course_ids = [course.id for course in cs]
    if course_ids:
        lessons = Lesson.query.filter(Lesson.course_id.in_(course_ids)).order_by(Lesson.id).all()
        for lesson in lessons:
            lesson_titles_map.setdefault(lesson.course_id, []).append(lesson.title)
    enrolled_ids = []
    cart_course_ids = []
    is_student = False
    if current_user.is_authenticated:
        is_student = current_user.role == 'student'
        if is_student:
            enrolled_ids = [en.course_id for en in Enrollment.query.filter_by(user_id=current_user.id).all()]
            cart_course_ids = [item.course_id for item in CartItem.query.filter_by(user_id=current_user.id).all()]
    return render_template('courses.html', courses=cs, enrolled_ids=enrolled_ids, is_student=is_student,
                           lesson_titles_map=lesson_titles_map, cart_course_ids=cart_course_ids,
                           selected_material_type=material_type, selected_is_premium=is_premium, search_query=search)

@app.route('/my-courses')
@login_required
def my_courses():
    material_type = request.args.get('material_type', '')
    is_premium = request.args.get('is_premium', '')
    search = request.args.get('search', '')

    enrollments = Enrollment.query.filter_by(user_id=current_user.id).order_by(Enrollment.id.asc()).all()
    if not enrollments:
        return render_template('my_courses.html', courses=[], progress_map={}, enrollment_status={},
                               selected_material_type=material_type, selected_is_premium=is_premium, search_query=search)

    course_ids = [enrollment.course_id for enrollment in enrollments]
    query = Course.query.options(joinedload(Course.instructor)).filter(Course.id.in_(course_ids))

    if material_type:
        query = query.filter(Course.material_type == material_type)
    
    if is_premium:
        premium_bool = is_premium.lower() == 'yes'
        query = query.filter(Course.is_premium == premium_bool)

    if search:
        query = query.filter(Course.title.ilike(f'%{search}%'))

    courses = query.order_by(Course.title.asc()).all()
    
    final_course_ids = [c.id for c in courses]

    lessons = Lesson.query.filter(Lesson.course_id.in_(final_course_ids)).all() if final_course_ids else []
    lessons_by_course = {}
    lesson_course_map = {}
    for lesson in lessons:
        lessons_by_course.setdefault(lesson.course_id, []).append(lesson)
        lesson_course_map[lesson.id] = lesson.course_id
    
    completed_counts = {}
    if lesson_course_map:
        progresses = LessonProgress.query.filter(
            LessonProgress.user_id == current_user.id,
            LessonProgress.lesson_id.in_(lesson_course_map.keys())
        ).all()
        for progress in progresses:
            course_id = lesson_course_map.get(progress.lesson_id)
            if course_id is not None:
                completed_counts[course_id] = completed_counts.get(course_id, 0) + 1
    
    progress_map = {}
    for course in courses:
        total_lessons = len(lessons_by_course.get(course.id, []))
        completed = completed_counts.get(course.id, 0)
        percent = int((completed / total_lessons) * 100) if total_lessons else 0
        progress_map[course.id] = {
            'completed': completed,
            'total': total_lessons,
            'percent': percent
        }
    
    enrollment_status = {enrollment.course_id: enrollment.unlocked for enrollment in enrollments}
    
    return render_template('my_courses.html', courses=courses, progress_map=progress_map, enrollment_status=enrollment_status,
                           selected_material_type=material_type, selected_is_premium=is_premium, search_query=search)

@app.route('/course/<int:course_id>')
def course_detail(course_id):
    c = Course.query.get_or_404(course_id)
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    lesson_ids = [lesson.id for lesson in lessons]
    completed_ids = set()
    exercise_submission = None # Initialize exercise_submission
    exercise = None # Initialize exercise
    for lesson in lessons:
        lesson.embed = prepare_video_embed(lesson.video_url)
        lesson.is_completed = False
    questions = Question.query.filter_by(course_id=course_id).all()
    exercise = Exercise.query.filter_by(course_id=course_id).first()
    is_enrolled = False
    is_unlocked = False
    attempt = None
    completed_count = 0
    is_in_cart = False
    exercise_submission = None
    if current_user.is_authenticated:
        if current_user.role == 'student':
            is_in_cart = CartItem.query.filter_by(user_id=current_user.id, course_id=course_id).first() is not None
            exercise_submission = ExerciseSubmission.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        e = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if e:
            is_enrolled = True
            is_unlocked = (not c.is_premium) or e.unlocked
            if lesson_ids:
                completed_records = LessonProgress.query.filter(
                    LessonProgress.user_id == current_user.id,
                    LessonProgress.lesson_id.in_(lesson_ids)
                ).all()
                completed_ids = {record.lesson_id for record in completed_records}
                completed_count = len(completed_ids)
        attempt = Attempt.query.filter_by(user_id=current_user.id, course_id=course_id).order_by(Attempt.id.desc()).first()
    for lesson in lessons:
        if lesson.id in completed_ids:
            lesson.is_completed = True
    # New progress calculation based on components
    total_components = 0
    completed_components = 0

    # Component 1: Lessons
    if lessons:
        total_components += 1
        if is_enrolled and completed_count == len(lessons):
            completed_components += 1

    # Component 2: Quiz
    if questions: # If there are any questions, a quiz exists
        total_components += 1
        if is_enrolled and attempt and attempt.score == 100:
            completed_components += 1

    # Component 3: Exercise
    # exercise is already fetched: exercise = Exercise.query.filter_by(course_id=course_id).first()
    if exercise:
        total_components += 1
        # exercise_submission is already fetched: exercise_submission = ExerciseSubmission.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if is_enrolled and exercise_submission and exercise_submission.score is not None: # Assuming score is set upon submission/grading
            completed_components += 1

    percent = int((completed_components / total_components) * 100) if total_components else 0
    progress = {
        'completed': completed_components if is_enrolled else 0,
        'total': total_components,
        'percent': percent if is_enrolled else 0,
        'enrolled': is_enrolled,
        'unlocked': is_unlocked
    }
    return render_template('course_detail.html', course=c, lessons=lessons, questions=questions,
                           is_enrolled=is_enrolled, is_unlocked=is_unlocked, is_in_cart=is_in_cart, 
                           attempt=attempt, progress=progress, exercise=exercise, exercise_submission=exercise_submission, now=datetime.utcnow() + timedelta(hours=7))

@app.route('/course/<int:course_id>/syllabus')
def view_syllabus(course_id):
    course = Course.query.get_or_404(course_id)
    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.id).all()
    questions = Question.query.filter_by(course_id=course_id).all()
    exercise = Exercise.query.filter_by(course_id=course_id).first()
    
    return render_template('syllabus.html', 
                           course=course, 
                           lessons=lessons, 
                           questions=questions, 
                           exercise=exercise)

@app.route('/cart')
@login_required
def cart():
    if current_user.role != 'student':
        flash('Fitur keranjang hanya untuk student.', 'error')
        return redirect(url_for('index'))
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    course_ids = [item.course_id for item in items]
    courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
    course_map = {course.id: course for course in courses}
    entries = []
    for item in items:
        course = course_map.get(item.course_id)
        if course:
            entries.append({'item': item, 'course': course})
    subtotal = sum((entry['course'].price or 0) for entry in entries)
    total = subtotal
    return render_template('cart.html', items=entries, subtotal=subtotal, total=total)

@app.route('/cart/add/<int:course_id>', methods=['POST'])
@login_required
def add_to_cart(course_id):
    course = Course.query.get_or_404(course_id)
    next_page = request.args.get('next')

    def _redirect_destination():
        if next_page == 'courses':
            return redirect(url_for('courses'))
        if next_page == 'detail':
            return redirect(url_for('course_detail', course_id=course_id))
        if next_page == 'my_courses':
            return redirect(url_for('my_courses'))
        return redirect(url_for('cart'))

    if current_user.role != 'student':
        flash('Fitur keranjang hanya untuk student.', 'error')
        return _redirect_destination()

    if not course.is_premium:
        flash('Kursus gratis tidak perlu dimasukkan ke keranjang.', 'info')
        return _redirect_destination()

    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if enrollment:
        if enrollment.unlocked:
            flash('Anda sudah terdaftar di course ini.', 'info')
        else:
            flash('Selesaikan pembayaran untuk membuka course.', 'info')
        return _redirect_destination()

    cart_item = CartItem.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if cart_item:
        flash('Course sudah ada di keranjang.', 'info')
        return _redirect_destination()

    new_item = CartItem(user_id=current_user.id, course_id=course_id)
    db.session.add(new_item)
    db.session.commit()
    flash('Course ditambahkan ke keranjang.', 'success')
    return _redirect_destination()

@app.route('/cart/remove/<int:course_id>', methods=['POST'])
@login_required
def remove_from_cart(course_id):
    if current_user.role != 'student':
        flash('Fitur keranjang hanya untuk student.', 'error')
        return redirect(url_for('index'))
    next_page = request.args.get('next')

    def _redirect_destination():
        if next_page == 'courses':
            return redirect(url_for('courses'))
        if next_page == 'detail':
            return redirect(url_for('course_detail', course_id=course_id))
        if next_page == 'my_courses':
            return redirect(url_for('my_courses'))
        return redirect(url_for('cart'))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not cart_item:
        flash('Course tidak ditemukan di keranjang.', 'info')
        return _redirect_destination()

    db.session.delete(cart_item)
    db.session.commit()
    flash('Course dihapus dari keranjang.', 'success')
    return _redirect_destination()

@app.route('/cart/checkout', methods=['POST'])
@login_required
def checkout_cart():
    if current_user.role != 'student':
        return jsonify({'message': 'Fitur keranjang hanya untuk student.'}), 403
    items = CartItem.query.filter_by(user_id=current_user.id).all()
    if not items:
        return jsonify({'message': 'Keranjang kosong.'}), 400
    course_ids = [item.course_id for item in items]
    courses = Course.query.filter(Course.id.in_(course_ids)).all() if course_ids else []
    course_map = {course.id: course for course in courses}
    enrolled_ids = []
    for item in items:
        course = course_map.get(item.course_id)
        if not course:
            db.session.delete(item)
            continue
        enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course.id).first()
        if not enrollment:
            enrollment = Enrollment(user_id=current_user.id, course_id=course.id, unlocked=True)
            db.session.add(enrollment)
        else:
            enrollment.unlocked = True
        enrolled_ids.append(course.id)
        db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'enrolled_course_ids': enrolled_ids})

@app.route('/instructor')
@login_required
def instructor_dashboard():
    if current_user.role != 'instructor':
        flash('Instructor only', 'error')
        return redirect(url_for('index'))
    my = Course.query.filter_by(instructor_id=current_user.id).all()
    for course in my:
        print(f"Course id: {course.id}")
    return render_template('instructor_dashboard.html', courses=my)

@app.route('/manage_enrollments/<int:course_id>')
@login_required
def manage_enrollments(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    enrollments = Enrollment.query.filter_by(course_id=course_id).all()
    enrolled_students = []
    for enrollment in enrollments:
        student = User.query.get(enrollment.user_id)
        if student:
            enrolled_students.append(student)

    return render_template('manage_enrollments.html', course=course, enrolled_students=enrolled_students)

@app.route('/manage_enrollments/<int:course_id>/unenroll/<int:user_id>', methods=['POST'])
@login_required
def unenroll_student(course_id, user_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('manage_enrollments', course_id=course_id))

    enrollment = Enrollment.query.filter_by(course_id=course_id, user_id=user_id).first()
    if enrollment:
        # Delete all related data for the student in this course
        Attempt.query.filter_by(user_id=user_id, course_id=course_id).delete(synchronize_session=False)
        ExerciseSubmission.query.filter_by(user_id=user_id, course_id=course_id).delete(synchronize_session=False)
        
        # To delete LessonProgress, we need to find lessons associated with the course first
        lessons_in_course = Lesson.query.filter_by(course_id=course_id).with_entities(Lesson.id).all()
        lesson_ids_in_course = [lesson.id for lesson in lessons_in_course]
        if lesson_ids_in_course:
            LessonProgress.query.filter(LessonProgress.user_id == user_id, LessonProgress.lesson_id.in_(lesson_ids_in_course)).delete(synchronize_session=False)
        
        CartItem.query.filter_by(user_id=user_id, course_id=course_id).delete(synchronize_session=False)

        db.session.delete(enrollment)
        db.session.commit()
        flash('Siswa berhasil dihapus dari kursus beserta semua data terkait.', 'success')
    else:
        flash('Siswa tidak terdaftar di kursus ini.', 'error')

    return redirect(url_for('manage_enrollments', course_id=course_id))

@app.route('/manage_enrollments/<int:course_id>/student_detail/<int:user_id>')
@login_required
def student_detail_for_instructor(course_id, user_id):
    course = Course.query.get_or_404(course_id)
    student = User.query.get_or_404(user_id)

    # Pastikan hanya instruktur pemilik kursus yang bisa melihat
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('instructor_dashboard'))

    # Ambil semua pelajaran di kursus ini
    lessons = Lesson.query.filter_by(course_id=course_id).order_by(Lesson.id).all()
    total_lessons = len(lessons)

    # Ambil progress pelajaran siswa
    completed_lessons_progress = LessonProgress.query.filter_by(user_id=user_id).join(Lesson).filter(Lesson.course_id == course_id).all()
    completed_lesson_ids = {lp.lesson_id for lp in completed_lessons_progress}
    completed_count = len(completed_lesson_ids)

    # Hitung persentase progress
    progress_percent = int((completed_count / total_lessons) * 100) if total_lessons > 0 else 0

    # Ambil nilai kuis terakhir siswa
    latest_attempt = Attempt.query.filter_by(user_id=user_id, course_id=course_id).order_by(Attempt.created_at.desc()).first()

    # Ambil submission latihan siswa
    exercise_submission = ExerciseSubmission.query.filter_by(user_id=user_id, course_id=course_id).first()

    # Siapkan daftar materi yang diselesaikan
    completed_materials = [lesson.title for lesson in lessons if lesson.id in completed_lesson_ids]

    return render_template('student_detail_for_instructor.html',
                           course=course,
                           student=student,
                           lessons=lessons,
                           completed_materials=completed_materials,
                           progress_percent=progress_percent,
                           latest_attempt=latest_attempt,
                           exercise_submission=exercise_submission)

@app.route('/manage_enrollments/<int:course_id>/student_detail/<int:user_id>/update_exercise_score', methods=['POST'])
@login_required
def update_exercise_score(course_id, user_id):
    course = Course.query.get_or_404(course_id)
    student = User.query.get_or_404(user_id)

    # Pastikan hanya instruktur pemilik kursus yang bisa mengupdate nilai
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('student_detail_for_instructor', course_id=course_id, user_id=user_id))

    exercise_submission = ExerciseSubmission.query.filter_by(course_id=course_id, user_id=user_id).first()

    if not exercise_submission:
        flash('Siswa ini belum mengirimkan latihan untuk kursus ini.', 'error')
        return redirect(url_for('student_detail_for_instructor', course_id=course_id, user_id=user_id))

    try:
        new_score = int(request.form['exercise_score'])
        if not (0 <= new_score <= 100):
            flash('Nilai harus antara 0 dan 100.', 'error')
            return redirect(url_for('student_detail_for_instructor', course_id=course_id, user_id=user_id))
        
        exercise_submission.score = new_score
        db.session.commit()
        flash('Nilai latihan berhasil diperbarui.', 'success')
    except ValueError:
        flash('Nilai tidak valid.', 'error')
    
    return redirect(url_for('student_detail_for_instructor', course_id=course_id, user_id=user_id))

@app.route('/course/create', methods=['GET','POST'])
@login_required
def create_course():
    if current_user.role != 'instructor':
        flash('Instructor only', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        is_premium = request.form.get('is_premium') == 'yes'
        raw_price = request.form.get('price', '0')
        numeric_price = int(re.sub(r'\D', '', raw_price) or 0)
        price = numeric_price if is_premium else 0
        material_type = request.form.get('material_type') # Ambil Jenis Materi
        thumbnail_file = request.files.get('thumbnail_file')
        thumbnail_url = request.form.get('thumbnail_url', '')
        thumbnail_mode = request.form.get('thumbnail_mode', 'file')
        thumbnail_path, error_message = resolve_thumbnail_input(thumbnail_file, thumbnail_url, mode=thumbnail_mode)
        if error_message:
            flash(error_message, 'error')
            return redirect(url_for('create_course'))
        
        quiz_start_date_str = request.form.get('quiz_start_date')
        quiz_end_date_str = request.form.get('quiz_end_date')

        quiz_start_date = datetime.strptime(quiz_start_date_str, '%Y-%m-%dT%H:%M') if quiz_start_date_str else None
        quiz_end_date = datetime.strptime(quiz_end_date_str, '%Y-%m-%dT%H:%M') if quiz_end_date_str else None

        c = Course(title=title, description=description, is_premium=is_premium, price=price, instructor_id=current_user.id,
                   thumbnail_path=thumbnail_path or '', material_type=material_type, quiz_start_date=quiz_start_date, quiz_end_date=quiz_end_date)
        db.session.add(c)
        db.session.commit()
        flash('Course created', 'success')
        return redirect(url_for('course_detail', course_id=c.id))
    return render_template('create_course.html', course=None)

@app.route('/course/<int:course_id>/edit', methods=['GET','POST'])
@login_required
def edit_course(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    if request.method == 'POST':
        course.title = request.form['title']
        course.description = request.form['description']
        course.is_premium = request.form.get('is_premium') == 'yes'
        course.material_type = request.form.get('material_type') # Ambil Jenis Materi
        raw_price = request.form.get('price', '0')
        numeric_price = int(re.sub(r'\D', '', raw_price) or 0)
        course.price = numeric_price if course.is_premium else 0
        thumbnail_file = request.files.get('thumbnail_file')
        thumbnail_url = request.form.get('thumbnail_url', '')
        thumbnail_mode = request.form.get('thumbnail_mode', 'file')
        current_thumbnail = course.thumbnail_path or ''
        updated_thumbnail, error_message = resolve_thumbnail_input(thumbnail_file, thumbnail_url, existing_path=current_thumbnail, mode=thumbnail_mode)
        if error_message:
            flash(error_message, 'error')
            return redirect(url_for('edit_course', course_id=course_id))
        course.thumbnail_path = updated_thumbnail or ''

        quiz_start_date_str = request.form.get('quiz_start_date')
        quiz_end_date_str = request.form.get('quiz_end_date')

        course.quiz_start_date = datetime.strptime(quiz_start_date_str, '%Y-%m-%dT%H:%M') if quiz_start_date_str else None
        course.quiz_end_date = datetime.strptime(quiz_end_date_str, '%Y-%m-%dT%H:%M') if quiz_end_date_str else None

        db.session.commit()
        flash('Course updated', 'success')
        return redirect(url_for('edit_course', course_id=course_id))
    return render_template('create_course.html', course=course)

@app.route('/course/<int:course_id>/delete', methods=['POST'])
@login_required
def delete_course(course_id):
    print(f"Deleting course with id: {course_id}")
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    
    # Hapus semua data terkait terlebih dahulu
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    lesson_ids = [lesson.id for lesson in lessons]
    if lesson_ids:
        LessonProgress.query.filter(LessonProgress.lesson_id.in_(lesson_ids)).delete(synchronize_session=False)
    
    Lesson.query.filter_by(course_id=course_id).delete(synchronize_session=False)
    
    questions = Question.query.filter_by(course_id=course_id).all()
    question_ids = [question.id for question in questions]
    if question_ids:
        Choice.query.filter(Choice.question_id.in_(question_ids)).delete(synchronize_session=False)
    
    Question.query.filter_by(course_id=course_id).delete(synchronize_session=False)
    Enrollment.query.filter_by(course_id=course_id).delete(synchronize_session=False)
    Attempt.query.filter_by(course_id=course_id).delete(synchronize_session=False)
    CartItem.query.filter_by(course_id=course_id).delete(synchronize_session=False)
    ExerciseSubmission.query.filter_by(course_id=course_id).delete(synchronize_session=False)
    Exercise.query.filter_by(course_id=course_id).delete(synchronize_session=False)

    db.session.delete(course)
    db.session.commit()
    
    flash('Course deleted', 'success')
    return redirect(url_for('instructor_dashboard'))

@app.route('/course/<int:course_id>/lesson/create', methods=['GET','POST'])
@login_required
def create_lesson(course_id):
    c = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or c.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    if request.method == 'POST':
        title = request.form['title']
        category = request.form.get('category')
        video_url = request.form.get('video_url', '')
        meeting_url = request.form.get('meeting_url', '')
        content = request.form.get('content', '')
        start_date_str = request.form.get('start_date')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M') if start_date_str else None

        if category == 'video':
            meeting_url = ''
        elif category == 'meeting':
            video_url = ''
        else:
            video_url = ''
            meeting_url = ''

        l = Lesson(course_id=course_id, title=title, content=content, video_url=video_url, meeting_url=meeting_url, start_date=start_date)
        db.session.add(l)
        db.session.commit()
        flash('Lesson added', 'success')
        return redirect(url_for('course_detail', course_id=course_id))
    return render_template('create_lesson.html', course=c, lesson=None)

@app.route('/course/<int:course_id>/lesson/<int:lesson_id>/edit', methods=['GET','POST'])
@login_required
def edit_lesson(course_id, lesson_id):
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first_or_404()
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    if request.method == 'POST':
        lesson.title = request.form['title']
        lesson.content = request.form.get('content', '')
        category = request.form.get('category')
        video_url = request.form.get('video_url', '')
        meeting_url = request.form.get('meeting_url', '')
        start_date_str = request.form.get('start_date')
        lesson.start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M') if start_date_str else None

        if category == 'video':
            lesson.video_url = video_url
            lesson.meeting_url = ''
        elif category == 'meeting':
            lesson.meeting_url = meeting_url
            lesson.video_url = ''
        else:
            lesson.video_url = ''
            lesson.meeting_url = ''

        db.session.commit()
        flash('Lesson updated', 'success')
        return redirect(url_for('course_detail', course_id=course_id))
    return render_template('create_lesson.html', course=course, lesson=lesson)


@app.route('/course/<int:course_id>/lesson/<int:lesson_id>/delete', methods=['POST'])
@login_required
def delete_lesson(course_id, lesson_id):
    course = Course.query.get_or_404(course_id)
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first_or_404()
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    LessonProgress.query.filter_by(lesson_id=lesson_id).delete(synchronize_session=False)
    db.session.delete(lesson)
    db.session.commit()
    flash('Lesson deleted', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/course/<int:course_id>/exercise/manage', methods=['GET', 'POST'])
@login_required
def manage_exercise(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    exercise = Exercise.query.filter_by(course_id=course_id).first()

    if request.method == 'POST':
        name = request.form['name']
        description = request.form.get('description', '')
        exercise_url = request.form.get('exercise_url', '')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%dT%H:%M') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%dT%H:%M') if end_date_str else None

        if exercise:
            exercise.name = name
            exercise.description = description
            exercise.exercise_url = exercise_url
            exercise.start_date = start_date
            exercise.end_date = end_date
            flash('Latihan updated', 'success')
        else:
            exercise = Exercise(
                course_id=course_id,
                name=name,
                description=description,
                exercise_url=exercise_url,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(exercise)
            flash('Latihan created', 'success')
        
        db.session.commit()
        return redirect(url_for('course_detail', course_id=course_id))

    return render_template('manage_exercise.html', course=course, exercise=exercise)

@app.route('/course/<int:course_id>/exercise/submit', methods=['GET', 'POST'])
@login_required
def submit_exercise(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'student':
        flash('Hanya siswa yang dapat mengirimkan latihan.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    submission = ExerciseSubmission.query.filter_by(
        user_id=current_user.id,
        course_id=course_id
    ).first()

    if request.method == 'POST':
        if submission:
            flash('Anda sudah mengirimkan latihan dan tidak dapat mengeditnya lagi.', 'error')
        else:
            submission_url = request.form.get('submission_url')
            if not submission_url:
                flash('URL pengiriman tidak boleh kosong.', 'error')
            else:
                submission = ExerciseSubmission(
                    user_id=current_user.id,
                    course_id=course_id,
                    submission_url=submission_url
                )
                db.session.add(submission)
                db.session.commit()
                flash('Latihan Anda telah dikirim.', 'success')

    return render_template('submit_exercise.html', course=course, submission=submission)

@app.route('/course/<int:course_id>/lesson/<int:lesson_id>/complete', methods=['POST'])
@login_required
def complete_lesson(course_id, lesson_id):
    lesson = Lesson.query.filter_by(id=lesson_id, course_id=course_id).first_or_404()
    course = Course.query.get_or_404(course_id)
    if current_user.role == 'instructor':
        flash('Students only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        flash('Enroll first', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    if course.is_premium and not enrollment.unlocked:
        flash('Unlock the course first', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    progress = LessonProgress.query.filter_by(user_id=current_user.id, lesson_id=lesson_id).first()
    if not progress:
        progress = LessonProgress(user_id=current_user.id, lesson_id=lesson_id)
        db.session.add(progress)
        db.session.commit()
        flash('Lesson marked as complete', 'success')
    else:
        flash('Lesson already completed', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/course/<int:course_id>/enroll', methods=['POST'])
def enroll(course_id):
    course = Course.query.get_or_404(course_id)
    next_page = request.args.get('next')

    def _redirect_destination():
        if next_page == 'courses':
            return redirect(url_for('courses'))
        if next_page == 'my_courses':
            return redirect(url_for('my_courses'))
        return redirect(url_for('course_detail', course_id=course_id))

    if not current_user.is_authenticated:
        flash('Anda belum login, silahkan login terlebih dahulu.', 'error')
        return _redirect_destination()
    if current_user.role != 'student':
        flash('Hanya student yang dapat mendaftar course ini.', 'error')
        return _redirect_destination()

    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()

    if course.is_premium:
        if enrollment:
            if enrollment.unlocked:
                flash('Anda sudah terdaftar di course ini.', 'info')
            else:
                flash('Selesaikan pembayaran untuk membuka course.', 'info')
        else:
            flash('Tambahkan course premium ke keranjang untuk melanjutkan.', 'error')
        return _redirect_destination()

    if enrollment:
        flash('Anda sudah terdaftar di course ini.', 'info')
        return _redirect_destination()

    enrollment = Enrollment(user_id=current_user.id, course_id=course_id, unlocked=True)
    db.session.add(enrollment)
    db.session.commit()
    flash('Berhasil mendaftar course.', 'success')
    return _redirect_destination()

@app.route('/course/<int:course_id>/unlock', methods=['POST'])
@login_required
def unlock_course(course_id):
    c = Course.query.get_or_404(course_id)
    e = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not e:
        flash('Enroll first', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    e.unlocked = True  # simulate payment success
    db.session.commit()
    flash('Unlocked (simulated)', 'success')
    return redirect(url_for('course_detail', course_id=course_id))

@app.route('/course/<int:course_id>/question/add', methods=['GET','POST'])
@login_required
def add_question(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    if request.method == 'POST':
        qtext = request.form['qtext'].strip()
        if not qtext:
            flash('Question text is required', 'error')
            return redirect(url_for('add_question', course_id=course_id))
        correct_idx = request.form.get('correct_idx', '1')
        texts = [request.form.get(f'choice{i}', '').strip() for i in range(1,5)]
        if not any(texts):
            flash('Minimal satu pilihan jawaban diperlukan.', 'error')
            return redirect(url_for('add_question', course_id=course_id))
        if correct_idx not in {'1','2','3','4'} or not texts[int(correct_idx)-1]:
            flash('Pilihan jawaban benar harus diisi.', 'error')
            return redirect(url_for('add_question', course_id=course_id))
        question = Question(course_id=course_id, text=qtext)
        db.session.add(question)
        db.session.flush()
        for idx, text_value in enumerate(texts, start=1):
            if not text_value:
                continue
            choice = Choice(question_id=question.id, text=text_value, is_correct=(str(idx) == correct_idx))
            db.session.add(choice)
        db.session.commit()
        flash('Question added', 'success')
        return redirect(url_for('manage_quiz', course_id=course_id))
    choices = [{'index': i, 'text': '', 'id': ''} for i in range(1,5)]
    return render_template('add_question.html', course=course, question=None, choices=choices)


@app.route('/course/<int:course_id>/quiz/manage', methods=['GET', 'POST'])


@login_required



def manage_quiz(course_id):



    course = Course.query.get_or_404(course_id)


    if current_user.role != 'instructor' or course.instructor_id != current_user.id:



        flash('Instructor only', 'error')


        return redirect(url_for('course_detail', course_id=course_id))






    questions = Question.query.filter_by(course_id=course_id).order_by(Question.id.asc()).all()


    question_ids = [q.id for q in questions]



    choices_map = {qid: [] for qid in question_ids}



    if question_ids:



        all_choices = Choice.query.filter(Choice.question_id.in_(question_ids)).order_by(Choice.id.asc()).all()


        for choice in all_choices:



            choices_map.setdefault(choice.question_id, []).append(choice)


    data = []



    for question in questions:



        data.append({'question': question, 'choices': choices_map.get(question.id, [])})


    return render_template('manage_quiz.html', course=course, questions=data)






@app.route('/course/<int:course_id>/quiz/dates/manage', methods=['GET', 'POST'])


@login_required



def manage_quiz_dates(course_id):



    course = Course.query.get_or_404(course_id)


    if current_user.role != 'instructor' or course.instructor_id != current_user.id:



        flash('Instructor only', 'error')


        return redirect(url_for('course_detail', course_id=course_id))






    if request.method == 'POST':



        quiz_start_date_str = request.form.get('quiz_start_date')


        quiz_end_date_str = request.form.get('quiz_end_date')






        course.quiz_start_date = datetime.strptime(quiz_start_date_str, '%Y-%m-%dT%H:%M') if quiz_start_date_str else None



        course.quiz_end_date = datetime.strptime(quiz_end_date_str, '%Y-%m-%dT%H:%M') if quiz_end_date_str else None



        



        db.session.commit()


        flash('Quiz dates updated successfully.', 'success')


        return redirect(url_for('manage_quiz_dates', course_id=course_id))






    return render_template('manage_quiz_dates.html', course=course)

@app.route('/course/<int:course_id>/question/<int:question_id>/edit', methods=['GET','POST'])
@login_required
def edit_question(course_id, question_id):
    course = Course.query.get_or_404(course_id)
    question = Question.query.filter_by(id=question_id, course_id=course_id).first_or_404()
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    if request.method == 'POST':
        qtext = request.form['qtext'].strip()
        if not qtext:
            flash('Question text is required', 'error')
            return redirect(url_for('edit_question', course_id=course_id, question_id=question_id))
        texts = [request.form.get(f'choice{i}', '').strip() for i in range(1,5)]
        correct_idx = request.form.get('correct_idx', '1')
        if not any(texts):
            flash('Minimal satu pilihan jawaban diperlukan.', 'error')
            return redirect(url_for('edit_question', course_id=course_id, question_id=question_id))
        if correct_idx not in {'1','2','3','4'} or not texts[int(correct_idx)-1]:
            flash('Pilihan jawaban benar harus diisi.', 'error')
            return redirect(url_for('edit_question', course_id=course_id, question_id=question_id))
        question.text = qtext
        for idx in range(1,5):
            text_value = texts[idx-1]
            choice_id = request.form.get(f'choice_id{idx}')
            choice = None
            if choice_id and choice_id.isdigit():
                choice = Choice.query.filter_by(id=int(choice_id), question_id=question_id).first()
            if text_value:
                if choice:
                    choice.text = text_value
                    choice.is_correct = (str(idx) == correct_idx)
                else:
                    new_choice = Choice(question_id=question.id, text=text_value, is_correct=(str(idx) == correct_idx))
                    db.session.add(new_choice)
            else:
                if choice:
                    db.session.delete(choice)
        db.session.commit()
        flash('Question updated', 'success')
        return redirect(url_for('manage_quiz', course_id=course_id))
    choices = Choice.query.filter_by(question_id=question_id).order_by(Choice.id.asc()).all()
    choice_slots = []
    for idx in range(1,5):
        choice = choices[idx-1] if idx-1 < len(choices) else None
        choice_slots.append({
            'index': idx,
            'id': choice.id if choice else '',
            'text': choice.text if choice else '',
            'is_correct': choice.is_correct if choice else False
        })
    current_correct = next((slot['index'] for slot in choice_slots if slot['is_correct']), '1')
    return render_template('add_question.html', course=course, question=question, choices=choice_slots, current_correct=str(current_correct))

@app.route('/course/<int:course_id>/question/<int:question_id>/delete', methods=['POST'])
@login_required
def delete_question(course_id, question_id):
    course = Course.query.get_or_404(course_id)
    question = Question.query.filter_by(id=question_id, course_id=course_id).first_or_404()
    if current_user.role != 'instructor' or course.instructor_id != current_user.id:
        flash('Instructor only', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    Choice.query.filter_by(question_id=question_id).delete(synchronize_session=False)
    db.session.delete(question)
    db.session.commit()
    flash('Question deleted', 'success')
    return redirect(url_for('manage_quiz', course_id=course_id))

@app.route('/course/<int:course_id>/quiz', methods=['GET','POST'])
@login_required
def take_quiz(course_id):
    c = Course.query.get_or_404(course_id)
    e = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not e or (c.is_premium and not e.unlocked):
        flash('Enroll and unlock first', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    qs = Question.query.filter_by(course_id=course_id).all()
    latest_attempt = None
    if current_user.role == 'student':
        latest_attempt = Attempt.query.filter_by(user_id=current_user.id, course_id=course_id).order_by(Attempt.id.desc()).first()
        if latest_attempt and request.method == 'GET':
            flash('Anda sudah menyelesaikan kuis ini. Kuis hanya dapat dikerjakan satu kali.', 'error')
            return redirect(url_for('course_detail', course_id=course_id))

    if request.method == 'POST':
        if current_user.role == 'student' and latest_attempt:
            flash('Kuis hanya dapat dikirim satu kali.', 'error')
            return redirect(url_for('course_detail', course_id=course_id))
        correct = 0
        total = len(qs)
        for q in qs:
            chosen = request.form.get(f"q_{q.id}")
            if not chosen:
                continue
            ch = Choice.query.get(int(chosen))
            if ch and ch.is_correct:
                correct += 1
        score = int((correct/total)*100) if total else 0
        passed = score >= 60
        att = Attempt(user_id=current_user.id, course_id=course_id, score=score, passed=passed)
        db.session.add(att)
        db.session.commit()
        flash(f'Quiz submitted. Score: {score}', 'success')
        return redirect(url_for('course_detail', course_id=course_id))
    # GET
    data = []
    for q in qs:
        choices = Choice.query.filter_by(question_id=q.id).all()
        data.append({'id': q.id, 'text': q.text, 'choices': choices})
    return render_template('quiz.html', course=c, questions=data)

@app.route('/course/<int:course_id>/certificate/download')
@login_required
def download_certificate(course_id):
    course = Course.query.get_or_404(course_id)
    if current_user.role != 'student':
        flash('Fitur ini hanya untuk student.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    enrollment = Enrollment.query.filter_by(user_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        flash('Daftar course terlebih dahulu.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    # Check for exercise submission and score
    exercise = Exercise.query.filter_by(course_id=course_id).first()
    if exercise:
        exercise_submission = ExerciseSubmission.query.filter_by(user_id=current_user.id, course_id=course_id).first()
        if not exercise_submission or exercise_submission.score is None or exercise_submission.score <= 0:
            flash('Anda harus menyelesaikan latihan dan mendapatkan skor sebelum mengunduh sertifikat.', 'error')
            return redirect(url_for('course_detail', course_id=course_id))
    else:
        # If no exercise is defined for the course, this condition is considered met.
        # Flash a message to clarify this behavior to the user.
        flash('Tidak ada latihan yang ditentukan untuk kursus ini, sehingga penyelesaian latihan tidak diperlukan untuk sertifikat.', 'info')

    attempt = Attempt.query.filter_by(user_id=current_user.id, course_id=course_id).order_by(Attempt.id.desc()).first()
    if not attempt or attempt.score < 100:
        flash('Dapatkan skor 100 pada kuis terlebih dahulu sebelum mengunduh sertifikat.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    # Check for all lessons completed
    lessons = Lesson.query.filter_by(course_id=course_id).all()
    total_lessons = len(lessons)
    completed_lessons_count = LessonProgress.query.filter_by(user_id=current_user.id).join(Lesson).filter(Lesson.course_id == course_id).count()

    if total_lessons > 0 and completed_lessons_count < total_lessons:
        flash('Anda harus menyelesaikan semua materi pelajaran sebelum mengunduh sertifikat.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    background_path = Path(app.root_path) / 'file_pendukung' / 'sertifikat' / 'docx' / 'template Sertifikat LMS.png'
    if not background_path.exists():
        flash('Template sertifikat tidak ditemukan.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    if Image is None or ImageDraw is None or ImageFont is None:
        app.logger.error('Pillow belum tersedia untuk membuat sertifikat.')
        flash('Pustaka gambar belum tersedia. Hubungi administrator.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    student_name = current_user.name
    instructor_name = course.instructor.name if course.instructor else 'Instruktur'
    material_type = course.material_type or course.title or 'Program'
    issued_date = datetime.utcnow().strftime('%d %B %Y')

    try:
        pdf_buffer = build_certificate_pdf(
            background_path=background_path,
            student_name=student_name,
            instructor_name=instructor_name,
            material_type=material_type,
            course_title=course.title,
            issued_date=issued_date,
        )
    except Exception as exc:  # pragma: no cover - requires runtime environment
        app.logger.exception('Gagal membuat sertifikat: %s', exc)
        flash('Gagal membuat sertifikat.', 'error')
        return redirect(url_for('course_detail', course_id=course_id))

    safe_title = ''.join(ch if ch.isalnum() else '_' for ch in course.title).strip('_') or 'course'
    filename = f'Sertifikat_{safe_title}.pdf'
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )

@app.route('/course/<int:course_id>/certificate')
@login_required
def certificate(course_id):
    c = Course.query.get_or_404(course_id)
    att = Attempt.query.filter_by(user_id=current_user.id, course_id=course_id, passed=True).order_by(Attempt.id.desc()).first()
    if not att:
        flash('Pass the quiz first', 'error')
        return redirect(url_for('course_detail', course_id=course_id))
    return render_template('certificate.html', user=current_user, course=c, date=datetime.utcnow().date())

if __name__ == '__main__':
    is_debug = os.getenv('FLASK_DEBUG', 'False').lower() in ['true', '1', 't']
    app.run(debug=is_debug)



































