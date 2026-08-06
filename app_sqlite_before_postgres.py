#!/usr/bin/env python3
"""
Agribank Tho Xuan - Quan ly File Tai san
Version 2.0 - Complete Rewrite
"""
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for, session
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from functools import wraps
import sqlite3
import os
import logging
import hashlib
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / 'tai_san_manager.db'
UPLOAD_DIR = BASE_DIR / 'uploads'
LOG_DIR = BASE_DIR / 'logs'

app = Flask(__name__)
app.secret_key = 'tai-san-manager-secret-loc-2026'
app.config['UPLOAD_FOLDER'] = str(UPLOAD_DIR)
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024 * 1024  # 5GB
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

UPLOAD_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(LOG_DIR / 'app.log'),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# ============ UNIT CODES ============
# Only 2 units: Hoi so and PGD Xuan Lai
UNIT_CODES = {
    'Hội sở': 'HS',
    'PGD Xuân Lai': 'XL'
}

def get_db():
    return sqlite3.connect(str(DB_PATH))

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user' not in session:
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Unauthorized'}), 401
            return redirect(url_for('login_page'))
        return view_func(*args, **kwargs)
    return wrapped

def admin_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if 'user' not in session or session.get('role') != 'admin':
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Forbidden'}), 403
            return redirect(url_for('index'))
        return view_func(*args, **kwargs)
    return wrapped

def generate_ma_kh(unit_code_short: str, record_type: str) -> str:
    """Generate customer code: AB17 + unit_code (4 digits) + sequence (4 digits)"""
    if unit_code_short not in UNIT_CODES:
        unit_code_short = 'THX'
    
    unit_num = UNIT_CODES[unit_code_short]
    prefix = f"AB17{unit_num}"
    
    conn = get_db()
    c = conn.cursor()
    
    # Get next sequence for this unit and record type
    table = 'bao_dam_records' if record_type == 'bao_dam' else 'giu_ho_records'
    c.execute(f"SELECT COUNT(*) FROM {table} WHERE ma_kh LIKE ?", (f"{prefix}%",))
    count = c.fetchone()[0]
    
    sequence = count + 1
    sequence_str = f"{sequence:04d}"
    
    conn.close()
    return f"{prefix}{sequence_str}"

def init_db():
    conn = get_db()
    c = conn.cursor()
    
    # Users table with permissions
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        full_name TEXT,
        role TEXT DEFAULT 'user',
        unit_code TEXT,
        can_upload INTEGER DEFAULT 0,
        can_delete INTEGER DEFAULT 0,
        can_view_all INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )''')
    
    # Sao ke tai san bao dam
    c.execute('''CREATE TABLE IF NOT EXISTS bao_dam_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_kh TEXT NOT NULL,
        ten_kh TEXT NOT NULL,
        so_ts_lcl TEXT UNIQUE,
        ngay_nhap TEXT,
        serial TEXT,
        vi_tri TEXT,
        don_vi TEXT,
        pdf_file TEXT,
        pdf_upload_date TEXT,
        created_at TEXT NOT NULL
    )''')
    
    # Sao ke tai san giu ho
    c.execute('''CREATE TABLE IF NOT EXISTS giu_ho_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ma_kh TEXT NOT NULL,
        ten_kh TEXT NOT NULL,
        so_ts_lcl TEXT UNIQUE,
        ngay_nhap TEXT,
        serial TEXT,
        vi_tri TEXT,
        don_vi TEXT,
        pdf_file TEXT,
        pdf_upload_date TEXT,
        created_at TEXT NOT NULL
    )''')
    
    # Seed admin user
    c.execute('''INSERT OR IGNORE INTO users 
        (username, password_hash, full_name, role, unit_code, can_upload, can_delete, can_view_all, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('admin', hash_password('admin'), 'Administrator', 'admin', None, 1, 1, 1, datetime.now().isoformat()))
    
    # Seed THXDTTP user
    c.execute('''INSERT OR IGNORE INTO users 
        (username, password_hash, full_name, role, unit_code, can_upload, can_delete, can_view_all, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        ('THXDTTP', hash_password('123456'), 'THXDTTP', 'user', 'THX', 1, 0, 0, datetime.now().isoformat()))
    
    conn.commit()
    conn.close()
    logging.info("Database initialized")

# ============ AUTH ROUTES ============

@app.route('/login')
def login_page():
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json(silent=True) or request.form
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''SELECT username, password_hash, full_name, role, unit_code, 
                 can_upload, can_delete, can_view_all FROM users WHERE username = ?''', (username,))
    row = c.fetchone()
    conn.close()
    
    if not row or row[1] != hash_password(password):
        logging.warning(f'Login failed for user: {username}')
        return jsonify({'success': False, 'error': 'Sai tên đăng nhập hoặc mật khẩu'}), 401
    
    session['user'] = row[0]
    session['full_name'] = row[2]
    session['role'] = row[3]
    session['unit_code'] = row[4]
    session['can_upload'] = bool(row[5])
    session['can_delete'] = bool(row[6])
    session['can_view_all'] = bool(row[7])
    
    logging.info(f'Login success: {row[0]}')
    return jsonify({
        'success': True, 
        'username': row[0], 
        'full_name': row[2],
        'role': row[3],
        'unit_code': row[4]
    })

@app.route('/logout')
def logout():
    username = session.get('user', 'unknown')
    session.clear()
    logging.info(f'Logout: {username}')
    return redirect(url_for('login_page'))

@app.route('/api/me')
@login_required
def api_me():
    return jsonify({
        'authenticated': True,
        'username': session.get('user'),
        'full_name': session.get('full_name'),
        'role': session.get('role'),
        'unit_code': session.get('unit_code'),
        'can_upload': session.get('can_upload'),
        'can_delete': session.get('can_delete'),
        'can_view_all': session.get('can_view_all')
    })

# ============ MAIN PAGES ============

@app.route('/')
@login_required
def index():
    return render_template('index.html',
        username=session.get('user'),
        full_name=session.get('full_name'),
        role=session.get('role'),
        unit_code=session.get('unit_code'),
        can_upload=session.get('can_upload'),
        can_delete=session.get('can_delete'),
        can_view_all=session.get('can_view_all'),
        units=UNIT_CODES
    )

@app.route('/admin/users')
@login_required
@admin_required
def admin_users_page():
    return render_template('admin_users.html',
        username=session.get('user'),
        full_name=session.get('full_name'),
        units=UNIT_CODES
    )

# ============ EXCEL IMPORT ============

@app.route('/api/import-excel/<record_type>', methods=['POST'])
@login_required
def import_excel(record_type):
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền import'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not (file.filename.endswith('.xls') or file.filename.endswith('.xlsx')):
        return jsonify({'error': 'Chỉ chấp nhận file Excel (.xls, .xlsx)'}), 400
    
    try:
        import xlrd
        import tempfile
        
        # Save temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xls') as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Read Excel
        book = xlrd.open_workbook(tmp_path)
        sheet = book.sheet_by_index(0)
        
        # Find header row (contains "STT")
        header_row = -1
        for i in range(min(20, sheet.nrows)):
            row = sheet.row_values(i)
            if row and str(row[0]).strip() == 'STT':
                header_row = i
                break
        
        if header_row == -1:
            return jsonify({'error': 'Không tìm thấy dòng tiêu đề (STT)'}), 400
        
        # Validate column count based on record type
        header = sheet.row_values(header_row)
        num_cols = len([c for c in header if c])  # Count non-empty columns
        
        if record_type == 'bao-dam':
            # Bao dam should have 13 columns (A-M)
            if num_cols < 12:
                return jsonify({'error': 'File không đúng định dạng Sao kê tài sản bảo đảm (thiếu cột). Vui lòng kiểm tra lại.'}), 400
        else:  # giu-ho
            # Giu ho should have 9 columns (A-I)
            if num_cols > 10:
                return jsonify({'error': 'File không đúng định dạng Sao kê tài sản giữ hộ (quá nhiều cột). Có thể bạn đang upload nhầm file Sao kê bảo đảm?'}), 400
            if num_cols < 8:
                return jsonify({'error': 'File không đúng định dạng Sao kê tài sản giữ hộ (thiếu cột). Vui lòng kiểm tra lại.'}), 400
        
        # Parse records
        conn = get_db()
        c = conn.cursor()
        imported = 0
        errors = []
        
        unit_code = request.form.get('unit_code', session.get('unit_code', 'THX'))
        
        for i in range(header_row + 2, sheet.nrows):  # Skip header and number row
            row = sheet.row_values(i)
            if not row or not str(row[0]).strip() or str(row[0]).strip() in ['LẬP BIỂU', '']:
                continue
            
            try:
                if record_type == 'bao-dam':
                    # Bao dam: STT, Ma KH vay, Ten KH, Ten chu TSBD, Loai TSBD, So TS (LCL), So LCP, Ngay nhap, ..., Serial, Vi tri
                    ma_kh = str(row[1]).strip() if len(row) > 1 else ''
                    ten_kh = str(row[2]).strip() if len(row) > 2 else ''
                    so_ts_lcl = str(row[5]).strip() if len(row) > 5 else ''
                    ngay_nhap = str(row[7]).strip() if len(row) > 7 else ''
                    serial = str(row[11]).strip() if len(row) > 11 else ''
                    vi_tri = str(row[12]).strip() if len(row) > 12 else ''
                    
                    if not ten_kh or not ma_kh:
                        continue
                    
                    c.execute('''INSERT OR IGNORE INTO bao_dam_records 
                        (ma_kh, ten_kh, so_ts_lcl, ngay_nhap, serial, vi_tri, don_vi, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (ma_kh, ten_kh, so_ts_lcl, ngay_nhap, serial, vi_tri, session.get('unit_code', 'Hội sở'), datetime.now().isoformat()))
                    
                else:  # giu-ho
                    # Giu ho: STT, Ma chu so huu, Ten chu so huu, Dia chi, Loai TS, So TS (LCL), Ngay nhap, Serial, Vi tri
                    ma_kh = str(row[1]).strip() if len(row) > 1 else ''
                    ten_kh = str(row[2]).strip() if len(row) > 2 else ''
                    so_ts_lcl = str(row[5]).strip() if len(row) > 5 else ''
                    ngay_nhap = str(row[6]).strip() if len(row) > 6 else ''
                    serial = str(row[7]).strip() if len(row) > 7 else ''
                    vi_tri = str(row[8]).strip() if len(row) > 8 else ''
                    
                    if not ten_kh or not ma_kh:
                        continue
                    
                    c.execute('''INSERT OR IGNORE INTO giu_ho_records 
                        (ma_kh, ten_kh, so_ts_lcl, ngay_nhap, serial, vi_tri, don_vi, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                        (ma_kh, ten_kh, so_ts_lcl, ngay_nhap, serial, vi_tri, session.get('unit_code', 'Hội sở'), datetime.now().isoformat()))
                
                imported += 1
                
            except Exception as e:
                errors.append(f"Dòng {i+1}: {str(e)}")
                continue
        
        conn.commit()
        conn.close()
        
        # Clean up temp file
        import os
        os.unlink(tmp_path)
        
        logging.info(f"Imported {imported} records from Excel by {session['user']}")
        
        return jsonify({
            'success': True,
            'imported': imported,
            'errors': errors[:10]  # Return first 10 errors
        })
        
    except Exception as e:
        logging.error(f"Excel import error: {str(e)}")
        return jsonify({'error': f'Lỗi đọc file Excel: {str(e)}'}), 400

# ============ API: BAO DAM RECORDS ============

@app.route('/api/bao-dam', methods=['GET'])
@login_required
def get_bao_dam_records():
    conn = get_db()
    c = conn.cursor()
    
    # Filter by unit if user can only view their own unit's data
    # Also exclude records with "Cầm cố" in vi_tri
    if not session.get('can_view_all') and session.get('unit_code'):
        c.execute('''SELECT * FROM bao_dam_records 
                     WHERE don_vi = ? AND (vi_tri IS NULL OR vi_tri NOT LIKE '%Cầm cố%')
                     ORDER BY created_at DESC''', (session['unit_code'],))
    else:
        c.execute('''SELECT * FROM bao_dam_records 
                     WHERE vi_tri IS NULL OR vi_tri NOT LIKE '%Cầm cố%'
                     ORDER BY created_at DESC''')
    
    records = []
    for row in c.fetchall():
        records.append({
            'id': row[0],
            'ma_kh': row[1],
            'ten_kh': row[2],
            'so_ts_lcl': row[3],
            'ngay_nhap': row[4],
            'serial': row[5],
            'vi_tri': row[6],
            'don_vi': row[7],
            'pdf_file': row[8],
            'pdf_upload_date': row[9],
            'created_at': row[10]
        })
    conn.close()
    return jsonify(records)

@app.route('/api/bao-dam', methods=['POST'])
@login_required
def create_bao_dam_record():
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền tạo bản ghi'}), 403
    
    data = request.get_json()
    unit_code = data.get('unit_code', session.get('unit_code', 'THX'))
    
    # Auto-generate ma_kh
    ma_kh = generate_ma_kh(unit_code, 'bao_dam')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO bao_dam_records 
        (ma_kh, ten_kh, so_ts_lcl, ngay_nhap, serial, vi_tri, don_vi, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (ma_kh, data['ten_kh'], data.get('so_ts_lcl'), data.get('ngay_nhap'),
         data.get('serial'), data.get('vi_tri'), session.get('unit_code', 'Hội sở'), datetime.now().isoformat()))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    
    logging.info(f"Created bao_dam record: {ma_kh} by {session['user']}")
    return jsonify({'success': True, 'id': record_id, 'ma_kh': ma_kh})

@app.route('/api/bao-dam/<int:record_id>', methods=['PUT'])
@login_required
def update_bao_dam_record(record_id):
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền cập nhật'}), 403
    
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute('''UPDATE bao_dam_records SET 
        ten_kh = ?, so_ts_lcl = ?, ngay_nhap = ?, serial = ?, vi_tri = ?
        WHERE id = ?''',
        (data['ten_kh'], data.get('so_ts_lcl'), data.get('ngay_nhap'),
         data.get('serial'), data.get('vi_tri'), record_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/bao-dam/<int:record_id>', methods=['DELETE'])
@login_required
def delete_bao_dam_record(record_id):
    if not session.get('can_delete'):
        return jsonify({'error': 'Không có quyền xóa'}), 403
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT pdf_file FROM bao_dam_records WHERE id = ?', (record_id,))
    row = c.fetchone()
    
    if row and row[0]:
        pdf_path = UPLOAD_DIR / row[0]
        if pdf_path.exists():
            pdf_path.unlink()
    
    c.execute('DELETE FROM bao_dam_records WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    logging.info(f"Deleted bao_dam record {record_id} by {session['user']}")
    return jsonify({'success': True})

# ============ API: GIU HO RECORDS ============

@app.route('/api/giu-ho', methods=['GET'])
@login_required
def get_giu_ho_records():
    conn = get_db()
    c = conn.cursor()
    
    # Filter by unit if user can only view their own unit's data
    # Also exclude records with "Cầm cố" in vi_tri
    if not session.get('can_view_all') and session.get('unit_code'):
        c.execute('''SELECT * FROM giu_ho_records 
                     WHERE don_vi = ? AND (vi_tri IS NULL OR vi_tri NOT LIKE '%Cầm cố%')
                     ORDER BY created_at DESC''', (session['unit_code'],))
    else:
        c.execute('''SELECT * FROM giu_ho_records 
                     WHERE vi_tri IS NULL OR vi_tri NOT LIKE '%Cầm cố%'
                     ORDER BY created_at DESC''')
    
    records = []
    for row in c.fetchall():
        records.append({
            'id': row[0],
            'ma_kh': row[1],
            'ten_kh': row[2],
            'so_ts_lcl': row[3],
            'ngay_nhap': row[4],
            'serial': row[5],
            'vi_tri': row[6],
            'don_vi': row[7],
            'pdf_file': row[8],
            'pdf_upload_date': row[9],
            'created_at': row[10]
        })
    conn.close()
    return jsonify(records)

@app.route('/api/giu-ho', methods=['POST'])
@login_required
def create_giu_ho_record():
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền tạo bản ghi'}), 403
    
    data = request.get_json()
    unit_code = data.get('unit_code', session.get('unit_code', 'THX'))
    
    ma_kh = generate_ma_kh(unit_code, 'giu_ho')
    
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO giu_ho_records 
        (ma_kh, ten_kh, so_ts_lcl, ngay_nhap, serial, vi_tri, don_vi, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (ma_kh, data['ten_kh'], data.get('so_ts_lcl'), data.get('ngay_nhap'),
         data.get('serial'), data.get('vi_tri'), session.get('unit_code', 'Hội sở'), datetime.now().isoformat()))
    conn.commit()
    record_id = c.lastrowid
    conn.close()
    
    logging.info(f"Created giu_ho record: {ma_kh} by {session['user']}")
    return jsonify({'success': True, 'id': record_id, 'ma_kh': ma_kh})

@app.route('/api/giu-ho/<int:record_id>', methods=['PUT'])
@login_required
def update_giu_ho_record(record_id):
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền cập nhật'}), 403
    
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    c.execute('''UPDATE giu_ho_records SET 
        ten_kh = ?, so_ts_lcl = ?, ngay_nhap = ?, serial = ?, vi_tri = ?
        WHERE id = ?''',
        (data['ten_kh'], data.get('so_ts_lcl'), data.get('ngay_nhap'),
         data.get('serial'), data.get('vi_tri'), record_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

@app.route('/api/giu-ho/<int:record_id>', methods=['DELETE'])
@login_required
def delete_giu_ho_record(record_id):
    if not session.get('can_delete'):
        return jsonify({'error': 'Không có quyền xóa'}), 403
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT pdf_file FROM giu_ho_records WHERE id = ?', (record_id,))
    row = c.fetchone()
    
    if row and row[0]:
        pdf_path = UPLOAD_DIR / row[0]
        if pdf_path.exists():
            pdf_path.unlink()
    
    c.execute('DELETE FROM giu_ho_records WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()
    logging.info(f"Deleted giu_ho record {record_id} by {session['user']}")
    return jsonify({'success': True})

# ============ PDF ATTACHMENT ============

@app.route('/api/attach-pdf/<record_type>/<int:record_id>', methods=['POST'])
@login_required
def attach_pdf(record_type, record_id):
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền đính kèm file'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Chỉ chấp nhận file PDF'}), 400
    
    # Check if record already has a PDF file
    table = 'bao_dam_records' if record_type == 'bao-dam' else 'giu_ho_records'
    conn = get_db()
    c = conn.cursor()
    c.execute(f'SELECT pdf_file FROM {table} WHERE id = ?', (record_id,))
    existing = c.fetchone()
    
    if existing and existing[0]:
        # Return info that file exists, let frontend handle confirmation
        conn.close()
        return jsonify({
            'warning': 'exists',
            'existing_file': existing[0],
            'message': 'Bản ghi này đã được đính file tài sản. Bạn có muốn thay thế bằng file mới?'
        }), 200
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = secure_filename(f"{record_type}_{record_id}_{timestamp}_{file.filename}")
    filepath = UPLOAD_DIR / filename
    file.save(str(filepath))
    
    # Update database
    c.execute(f'UPDATE {table} SET pdf_file = ?, pdf_upload_date = ? WHERE id = ?',
              (filename, datetime.now().isoformat(), record_id))
    conn.commit()
    conn.close()
    
    logging.info(f"PDF attached to {record_type} record {record_id}: {filename}")
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/attach-pdf-confirm/<record_type>/<int:record_id>', methods=['POST'])
@login_required
def attach_pdf_confirm(record_type, record_id):
    """Confirm replacement of existing PDF"""
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền đính kèm file'}), 403
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.endswith('.pdf'):
        return jsonify({'error': 'Chỉ chấp nhận file PDF'}), 400
    
    # Delete old file if exists
    table = 'bao_dam_records' if record_type == 'bao-dam' else 'giu_ho_records'
    conn = get_db()
    c = conn.cursor()
    c.execute(f'SELECT pdf_file FROM {table} WHERE id = ?', (record_id,))
    old_file = c.fetchone()
    
    if old_file and old_file[0]:
        old_path = UPLOAD_DIR / old_file[0]
        if old_path.exists():
            old_path.unlink()
    
    # Generate unique filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = secure_filename(f"{record_type}_{record_id}_{timestamp}_{file.filename}")
    filepath = UPLOAD_DIR / filename
    file.save(str(filepath))
    
    # Update database
    c.execute(f'UPDATE {table} SET pdf_file = ?, pdf_upload_date = ? WHERE id = ?',
              (filename, datetime.now().isoformat(), record_id))
    conn.commit()
    conn.close()
    
    logging.info(f"PDF replaced for {record_type} record {record_id}: {filename}")
    return jsonify({'success': True, 'filename': filename})

@app.route('/api/batch-attach', methods=['POST'])
@login_required
def batch_attach_pdf():
    """Batch attach PDFs by matching filename to LCL number - searches both tables"""
    if not session.get('can_upload'):
        return jsonify({'error': 'Không có quyền đính kèm file'}), 403
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files uploaded'}), 400
    
    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files selected'}), 400
    
    allow_overwrite = request.form.get('allow_overwrite') == '1'
    
    conn = get_db()
    c = conn.cursor()
    
    results = {
        'success': [],
        'errors': [],
        'total': len(files)
    }
    
    for file in files:
        if not file.filename:
            continue
            
        filename = file.filename
        
        # Check if PDF
        if not filename.lower().endswith('.pdf'):
            results['errors'].append({
                'file': filename,
                'reason': 'Không phải file PDF'
            })
            continue
        
        # Extract LCL from filename
        # Format: "3511LCL201201759.pdf" or "1201759.pdf"
        basename = filename.rsplit('.', 1)[0]
        
        # Try to find LCL pattern
        lcl_number = None
        if 'LCL' in basename.upper():
            # Full format: 3511LCL201201759
            lcl_number = basename
        else:
            # Short format: 1201759 -> map to 3511LCL201201759
            lcl_number = f"3511LCL20{basename}"
        
        if not lcl_number:
            results['errors'].append({
                'file': filename,
                'reason': 'Tên file sai định dạng (không tìm thấy số LCL)'
            })
            continue
        
        # Search in both tables
        record = None
        table = None
        record_type = None
        
        # Try bao_dam first
        c.execute('SELECT id, pdf_file FROM bao_dam_records WHERE so_ts_lcl = ?', (lcl_number,))
        row = c.fetchone()
        if row:
            record = row
            table = 'bao_dam_records'
            record_type = 'bao-dam'
        else:
            # Try giu_ho
            c.execute('SELECT id, pdf_file FROM giu_ho_records WHERE so_ts_lcl = ?', (lcl_number,))
            row = c.fetchone()
            if row:
                record = row
                table = 'giu_ho_records'
                record_type = 'giu-ho'
        
        if not record:
            results['errors'].append({
                'file': filename,
                'lcl': lcl_number,
                'reason': 'Không tìm thấy bản ghi có số LCL này'
            })
            continue
        
        record_id = record[0]
        existing_pdf = record[1]
        
        # Check if file exists and overwrite is not allowed
        if existing_pdf and not allow_overwrite:
            results['errors'].append({
                'file': filename,
                'lcl': lcl_number,
                'reason': f'Bản ghi đã có file: {existing_pdf} (bật ghi đè để thay thế)'
            })
            continue
        
        # Delete old file if overwriting
        if existing_pdf and allow_overwrite:
            old_path = UPLOAD_DIR / existing_pdf
            if old_path.exists():
                old_path.unlink()
        
        # Save file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        new_filename = secure_filename(f"{record_type}_{record_id}_{timestamp}_{filename}")
        filepath = UPLOAD_DIR / new_filename
        file.save(str(filepath))
        
        # Update database
        c.execute(f'UPDATE {table} SET pdf_file = ?, pdf_upload_date = ? WHERE id = ?',
                  (new_filename, datetime.now().isoformat(), record_id))
        
        results['success'].append({
            'file': filename,
            'lcl': lcl_number,
            'table': 'Bảo đảm' if table == 'bao_dam_records' else 'Giữ hộ',
            'saved_as': new_filename,
            'replaced': bool(existing_pdf)
        })
    
    conn.commit()
    conn.close()
    
    logging.info(f"Batch attach: {len(results['success'])} success, {len(results['errors'])} errors by {session['user']}")
    
    return jsonify(results)

@app.route('/uploads/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ============ ADMIN USER MANAGEMENT ============

@app.route('/api/users', methods=['GET'])
@login_required
@admin_required
def get_users():
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT id, username, full_name, role, unit_code, can_upload, can_delete, can_view_all, created_at FROM users')
    users = []
    for row in c.fetchall():
        users.append({
            'id': row[0],
            'username': row[1],
            'full_name': row[2],
            'role': row[3],
            'unit_code': row[4],
            'can_upload': bool(row[5]),
            'can_delete': bool(row[6]),
            'can_view_all': bool(row[7]),
            'created_at': row[8]
        })
    conn.close()
    return jsonify(users)

@app.route('/api/users', methods=['POST'])
@login_required
@admin_required
def create_user():
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO users (username, password_hash, full_name, role, unit_code, 
                     can_upload, can_delete, can_view_all, created_at)
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (data['username'], hash_password(data['password']), data.get('full_name'),
             data.get('role', 'user'), data.get('unit_code'),
             1 if data.get('can_upload') else 0,
             1 if data.get('can_delete') else 0,
             1 if data.get('can_view_all') else 0,
             datetime.now().isoformat()))
        conn.commit()
        logging.info(f"Created user: {data['username']} by {session['user']}")
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username đã tồn tại'}), 400
    finally:
        conn.close()

@app.route('/api/users/<int:user_id>', methods=['PUT'])
@login_required
@admin_required
def update_user(user_id):
    data = request.get_json()
    conn = get_db()
    c = conn.cursor()
    
    # Don't allow removing admin privileges from the last admin
    if data.get('role') != 'admin':
        c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
        admin_count = c.fetchone()[0]
        c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        current_role = c.fetchone()
        if admin_count <= 1 and current_role and current_role[0] == 'admin':
            return jsonify({'error': 'Không thể xóa quyền admin của user cuối cùng'}), 400
    
    updates = []
    params = []
    if 'full_name' in data:
        updates.append('full_name = ?')
        params.append(data['full_name'])
    if 'unit_code' in data:
        updates.append('unit_code = ?')
        params.append(data['unit_code'])
    if 'can_upload' in data:
        updates.append('can_upload = ?')
        params.append(1 if data['can_upload'] else 0)
    if 'can_delete' in data:
        updates.append('can_delete = ?')
        params.append(1 if data['can_delete'] else 0)
    if 'can_view_all' in data:
        updates.append('can_view_all = ?')
        params.append(1 if data['can_view_all'] else 0)
    if 'role' in data:
        updates.append('role = ?')
        params.append(data['role'])
    if 'password' in data and data['password']:
        updates.append('password_hash = ?')
        params.append(hash_password(data['password']))
    
    if updates:
        params.append(user_id)
        c.execute(f'UPDATE users SET {", ".join(updates)} WHERE id = ?', params)
        conn.commit()
    
    conn.close()
    return jsonify({'success': True})

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_user(user_id):
    conn = get_db()
    c = conn.cursor()
    
    # Don't allow deleting the last admin
    c.execute('SELECT COUNT(*) FROM users WHERE role = "admin"')
    admin_count = c.fetchone()[0]
    c.execute('SELECT role FROM users WHERE id = ?', (user_id,))
    user_role = c.fetchone()
    
    if admin_count <= 1 and user_role and user_role[0] == 'admin':
        return jsonify({'error': 'Không thể xóa admin cuối cùng'}), 400
    
    c.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()
    logging.info(f"Deleted user {user_id} by {session['user']}")
    return jsonify({'success': True})

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=3511, debug=False)
