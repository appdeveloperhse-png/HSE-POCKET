# HSE-POCKET - Kivy HSE Management System
# Android-friendly single-file application.
# Existing modules are kept; this version adds:
# - Settings (company / project / logo)
# - Working gallery attachment
# - Observation register with selection
# - SOP Safety Observation Card drafting
# - One observation = one SOP card page; multiple observations = multiple pages
# - Local Android save dialog for PDF / Word / Excel / SOP cards
# - Observation PDF / Word / Excel exports

import os
import csv
import sqlite3
import base64
import mimetypes
import zlib
import struct
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.checkbox import CheckBox
from kivy.uix.image import Image

APP = 'HSE-POCKET'
NAVY = (.04, .10, .17, 1)
BLUE = (.06, .32, .62, 1)
RED = (.75, .10, .10, 1)
GREEN = (.08, .50, .28, 1)
TEAL = (.03, .46, .45, 1)
PURPLE = (.40, .22, .60, 1)
ORANGE = (.86, .45, .06, 1)
BG = (.94, .95, .97, 1)
WHITE = (1, 1, 1, 1)
TEXT = (.10, .13, .17, 1)
MUTED = (.40, .44, .49, 1)

OBS_TYPES = [
    'Safe Behavior/Positive Observation',
    'Unsafe Act',
    'Unsafe Condition',
    'Near Misses',
]

OBS_CATEGORIES = [
    'PPE Compliance',
    'Training & Competence',
    'Housekeeping',
    'Barrication / Signages',
    'Electrical Hazards',
    'Access / Egress',
    'Welfare Facilities',
    'Material Arrangement',
    'Scaffolding Erection',
    'Ergonomics & Handling',
    'COSHH / Chemicals Safety',
    'Environmental Impact',
    'Equipment & Machinery',
    'Permit to Work (PTW) Compliance',
    'Confined Space Entry (CSE)',
    'Hand & Power Tools',
    'Lifting Operation & Procedure',
    'Heat Stress / Weather Condition',
    'Excavation',
    'Sharp Object',
    'Traffic Rules',
    'Vehicle Incident',
    'Property Damage',
    'Work at Height',
    'Fire Hazard',
    'Slips, Trips & Falls',
    'Drop Object',
    'Other',
]

REQUEST_GALLERY = 7001
REQUEST_EXPORT = 7002


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def today():
    return datetime.now().strftime('%Y-%m-%d')


def L(t='', s=13, c=TEXT, b=False, h=34):
    x = Label(
        text=str(t), size_hint_y=None, height=dp(h), font_size=dp(s),
        color=c, bold=b, halign='left', valign='middle'
    )
    x.bind(width=lambda o, v: setattr(o, 'text_size', (max(1, v-dp(4)), None)))
    return x


def I(h='', ht=44, m=False):
    return TextInput(
        hint_text=h, size_hint_y=None, height=dp(ht), multiline=m,
        font_size=dp(13), padding=[dp(10), dp(9)],
        background_normal='', background_active='', background_color=WHITE,
        foreground_color=TEXT, hint_text_color=MUTED
    )


def B(t, c=BLUE, h=44, s=11):
    return Button(
        text=t, size_hint_y=None, height=dp(h), background_normal='',
        background_down='', background_color=c, color=WHITE, bold=True,
        font_size=dp(s)
    )


def msg(t, m):
    box = BoxLayout(orientation='vertical', padding=dp(10), spacing=dp(8))
    sc = ScrollView()
    lab = L(m, 13, TEXT, False, 100)
    lab.size_hint_y = None
    lab.bind(texture_size=lambda o, v: setattr(o, 'height', max(dp(100), v[1]+dp(15))))
    sc.add_widget(lab)
    box.add_widget(sc)
    q = B('CLOSE', NAVY, 44)
    box.add_widget(q)
    p = Popup(title=t, content=box, size_hint=(.94, .82), auto_dismiss=False)
    q.bind(on_release=p.dismiss)
    p.open()
    return p


class Card(BoxLayout):
    def __init__(self, bg=WHITE, **kw):
        super().__init__(**kw)
        with self.canvas.before:
            self.col = Color(*bg)
            self.rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self.sync, size=self.sync)

    def sync(self, *a):
        self.rect.pos = self.pos
        self.rect.size = self.size


class TableCell(Label):
    def __init__(self, text='', header=False, width=100, **kwargs):
        super().__init__(text=str(text), **kwargs)
        self.size_hint_x = None
        self.width = dp(width)
        self.size_hint_y = None
        self.height = dp(46 if not header else 42)
        self.font_size = dp(10 if not header else 10)
        self.color = WHITE if header else TEXT
        self.bold = header
        self.halign = 'left'
        self.valign = 'middle'
        self.text_size = (dp(width-8), None)
        with self.canvas.before:
            self.bgcol = Color(*(NAVY if header else WHITE))
            self.bgrect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(2)])
        self.bind(pos=self._sync, size=self._sync)

    def _sync(self, *args):
        self.bgrect.pos = self.pos
        self.bgrect.size = self.size


class DB:
    def __init__(self, p):
        self.c = sqlite3.connect(p)
        self.c.row_factory = sqlite3.Row
        self.make()

    def ensure_column(self, table, column, definition):
        cols = [r[1] for r in self.c.execute('PRAGMA table_info(%s)' % table).fetchall()]
        if column not in cols:
            self.c.execute('ALTER TABLE %s ADD COLUMN %s %s' % (table, column, definition))

    def make(self):
        c = self.c
        c.execute('''CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,value TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS observations(
            id INTEGER PRIMARY KEY,date,location,responsible,designation,type,category,
            observation,action,status,observed_by,evidence,created_at)''')
        c.execute('''CREATE TABLE IF NOT EXISTS incidents(
            id INTEGER PRIMARY KEY,date,time,location,project,activity,classification,severity,title,
            description,consequence,potential_consequence,people,injury,damage,environment,witnesses,
            immediate,evidence,investigator,team,scope,timeline,statements,icam_event,icam_individual,
            icam_task,icam_org,icam_defences,icam_actions,rca_method,direct_cause,underlying_cause,
            root_cause,contributing,five_whys,fishbone,bowtie,corrective,preventive,system_action,
            responsible,target,priority,status,verification,closeout,created_at)''')
        c.execute('''CREATE TABLE IF NOT EXISTS inspections(
            id INTEGER PRIMARY KEY,date,time,location,inspection_type,inspector,activity,checklist,
            unsafe_acts,unsafe_conditions,good_practices,ppe,excavation,wah,lifting,scaffolding,
            electrical,confined_space,hot_work,fire,housekeeping,vehicle,environment,emergency,
            findings,actions,responsible,target_date,status,evidence,created_at)''')
        c.execute('''CREATE TABLE IF NOT EXISTS audits(
            id INTEGER PRIMARY KEY,date,location,audit_type,auditor,scope,findings,nc,good_practices,
            actions,responsible,target,status,evidence,created_at)''')
        c.execute('''CREATE TABLE IF NOT EXISTS capa(
            id INTEGER PRIMARY KEY,date,source,location,finding,root_cause,corrective,preventive,
            responsible,target,priority,status,verification,closeout,evidence,created_at)''')
        c.execute('''CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY,module,record_id,path,description,created_at)''')
        self.ensure_column('observations', 'time', 'TEXT')
        self.ensure_column('observations', 'photo_path', 'TEXT')
        self.ensure_column('observations', 'observer_id', 'TEXT')
        self.ensure_column('observations', 'observer_designation', 'TEXT')
        self.ensure_column('observations', 'department', 'TEXT')
        # Database migration for older APK versions. Older HSE-POCKET builds
        # used the column name `target`; inspections now use `target_date`.
        # Adding the new column here prevents SQLite crashes on existing installs.
        self.ensure_column('inspections', 'target_date', 'TEXT')
        self.c.commit()

    def add(self, t, d):
        k = list(d)
        self.c.execute(
            'INSERT INTO ' + t + '(' + ','.join(k) + ') VALUES(' + ','.join(['?']*len(k)) + ')',
            [d[x] for x in k]
        )
        self.c.commit()
        return self.c.execute('select last_insert_rowid()').fetchone()[0]

    def count(self, t):
        return self.c.execute('select count(*) from ' + t).fetchone()[0]

    def st(self, t, s):
        return self.c.execute('select count(*) from ' + t + ' where status=?', (s,)).fetchone()[0]

    def rows(self, t):
        return self.c.execute('select * from ' + t + ' order by id desc limit 100').fetchall()

    def observation_rows(self):
        return self.c.execute('select * from observations order by id desc').fetchall()

    def recent(self):
        return self.c.execute(
            "select 'Observation',id,location,status,created_at from observations "
            "union all select 'Incident',id,location,status,created_at from incidents "
            "union all select 'Inspection',id,location,status,created_at from inspections "
            "union all select 'Audit',id,location,status,created_at from audits "
            "union all select 'CAPA',id,location,status,created_at from capa "
            "order by created_at desc limit 8"
        ).fetchall()

    def setting(self, key, default=''):
        r = self.c.execute('select value from settings where key=?', (key,)).fetchone()
        return r[0] if r else default

    def set_setting(self, key, value):
        self.c.execute('insert or replace into settings(key,value) values(?,?)', (key, value or ''))
        self.c.commit()


# ---------- PDF helpers ----------

def pdf_escape(text):
    s = str(text if text is not None else '')
    s = s.encode('latin-1', 'replace').decode('latin-1')
    return s.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)').replace('\r', '').replace('\n', ' ')


def pdf_text(x, y, text, size=9, font='/F1'):
    return 'BT %s %d Tf %d %d Td (%s) Tj ET\n' % (font, size, int(x), int(y), pdf_escape(text))


def pdf_line(x1, y1, x2, y2):
    return '%d %d m %d %d l S\n' % (x1, y1, x2, y2)


def _png_to_rgb(path):
    data = open(path, 'rb').read()
    if not data.startswith(b'\x89PNG\r\n\x1a\n'):
        raise ValueError('Not a PNG')
    pos = 8
    width = height = color_type = bit_depth = None
    raw = b''
    while pos + 8 <= len(data):
        n = struct.unpack('>I', data[pos:pos+4])[0]
        typ = data[pos+4:pos+8]
        chunk = data[pos+8:pos+8+n]
        pos += 12 + n
        if typ == b'IHDR':
            width, height, bit_depth, color_type, _, _, _ = struct.unpack('>IIBBBBB', chunk)
        elif typ == b'IDAT':
            raw += chunk
        elif typ == b'IEND':
            break
    if bit_depth != 8:
        raise ValueError('Only 8-bit PNG logos are supported')
    channels = {0: 1, 2: 3, 4: 2, 6: 4}.get(color_type)
    if not channels or color_type not in (0, 2, 6):
        raise ValueError('Unsupported PNG color type')
    decoded = zlib.decompress(raw)
    stride = width * channels
    out = bytearray()
    prev = bytearray(stride)
    p = 0
    for _ in range(height):
        ft = decoded[p]
        p += 1
        scan = bytearray(decoded[p:p+stride])
        p += stride
        for i in range(stride):
            left = scan[i-channels] if i >= channels else 0
            up = prev[i]
            ul = prev[i-channels] if i >= channels else 0
            if ft == 1:
                scan[i] = (scan[i] + left) & 255
            elif ft == 2:
                scan[i] = (scan[i] + up) & 255
            elif ft == 3:
                scan[i] = (scan[i] + ((left + up)//2)) & 255
            elif ft == 4:
                pp = left + up - ul
                pa = abs(pp-left); pb = abs(pp-up); pc = abs(pp-ul)
                pr = left if pa <= pb and pa <= pc else (up if pb <= pc else ul)
                scan[i] = (scan[i] + pr) & 255
            elif ft != 0:
                raise ValueError('Unsupported PNG filter')
        if color_type == 2:
            out.extend(scan)
        elif color_type == 6:
            for i in range(0, len(scan), 4):
                out.extend(scan[i:i+3])
        else:
            for v in scan:
                out.extend((v, v, v))
        prev = scan
    return width, height, bytes(out)


def _jpeg_size(data):
    p = 2
    while p + 9 < len(data):
        if data[p] != 0xFF:
            p += 1
            continue
        marker = data[p+1]
        p += 2
        if marker in (0xD8, 0xD9):
            continue
        if p + 2 > len(data):
            break
        ln = struct.unpack('>H', data[p:p+2])[0]
        if marker in range(0xC0, 0xC4):
            if p + 7 <= len(data):
                h, w = struct.unpack('>HH', data[p+3:p+7])
                return w, h
        p += ln
    raise ValueError('Could not read JPEG size')


def pdf_image_info(path):
    ext = os.path.splitext(path)[1].lower()
    data = open(path, 'rb').read()
    if ext in ('.jpg', '.jpeg'):
        w, h = _jpeg_size(data)
        return {'data': data, 'w': w, 'h': h, 'filter': '/DCTDecode'}
    if ext == '.png':
        w, h, rgb = _png_to_rgb(path)
        return {'data': zlib.compress(rgb, 6), 'w': w, 'h': h, 'filter': '/FlateDecode'}
    raise ValueError('Logo must be PNG or JPG/JPEG')


def build_pdf(pages, out_path, logo_path=''):
    # A4 portrait: 595 x 842 points. The SOP card is intentionally portrait.
    W, H = 595, 842
    objects = []
    objects.append(None)  # catalog
    objects.append(None)  # pages
    objects.append('<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    image_obj = None
    image_name = None
    if logo_path and os.path.isfile(logo_path):
        try:
            info = pdf_image_info(logo_path)
            cs = '/DeviceRGB'
            obj = '<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 /Filter %s /Length %d >>\nstream\n' % (
                info['w'], info['h'], cs, info['filter'], len(info['data'])
            )
            objects.append((obj, info['data']))
            image_obj = len(objects)
            image_name = '/Im1'
        except Exception:
            image_obj = None

    page_refs = []
    for page in pages:
        content = page
        resources = '<< /Font << /F1 3 0 R >>'
        if image_obj:
            resources += ' /XObject << /Im1 %d 0 R >>' % image_obj
        resources += ' >>'
        objects.append(('<< /Length %d >>\nstream\n' % len(content.encode('latin-1', 'replace')), content.encode('latin-1', 'replace')))
        content_obj = len(objects)
        objects.append('<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %d %d] /Resources %s /Contents %d 0 R >>' % (W, H, resources, content_obj))
        page_refs.append(len(objects))

    objects[0] = '<< /Type /Catalog /Pages 2 0 R >>'
    objects[1] = '<< /Type /Pages /Kids [%s] /Count %d >>' % (' '.join('%d 0 R' % x for x in page_refs), len(page_refs))

    with open(out_path, 'wb') as f:
        f.write(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
        offsets = [0]
        for i, obj in enumerate(objects, 1):
            offsets.append(f.tell())
            f.write(('%d 0 obj\n' % i).encode('ascii'))
            if isinstance(obj, tuple):
                header, payload = obj
                f.write(header.encode('latin-1'))
                f.write(payload)
                f.write(b'\nendstream\n')
            else:
                f.write(str(obj).encode('latin-1'))
                f.write(b'\n')
            f.write(b'endobj\n')
        xref = f.tell()
        f.write(('xref\n0 %d\n' % (len(objects)+1)).encode('ascii'))
        f.write(b'0000000000 65535 f \n')
        for off in offsets[1:]:
            f.write(('%010d 00000 n \n' % off).encode('ascii'))
        f.write(('trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objects)+1, xref)).encode('ascii'))


class AppHSE(App):
    def build(self):
        # IMPORTANT: Do not build every module during Android startup.
        # A single error in any secondary screen used to make the APK open
        # and immediately close. Only Home is created here; other modules
        # are created when the user opens them.
        Window.clearcolor = BG
        self.dir = os.path.join(self.user_data_dir, 'HSE_POCKET')
        self.export_dir = os.path.join(self.dir, 'Exports')
        self.photo_dir = os.path.join(self.dir, 'Photos')
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(self.photo_dir, exist_ok=True)
        self.selected_observations = {}
        self.gallery_callback = None
        self.pending_export = None
        self._android_activity = None
        self._activity_bound = False
        self.sm = ScreenManager()

        try:
            self.db = DB(os.path.join(self.dir, 'hse_pocket.db'))
            home_screen = Screen(name='home')
            home_screen.add_widget(self.home())
            self.sm.add_widget(home_screen)
            return self.sm
        except Exception as e:
            # Keep the APK open and show the actual startup error instead of
            # silently closing. This is especially useful for Android testing.
            import traceback
            error = traceback.format_exc()
            try:
                with open(os.path.join(self.dir, 'startup_error.txt'), 'w', encoding='utf-8') as f:
                    f.write(error)
            except Exception:
                pass
            return self.error_screen('STARTUP ERROR', error)

    def error_screen(self, title, details):
        root = BoxLayout(orientation='vertical', padding=dp(14), spacing=dp(10))
        root.add_widget(L('HSE-POCKET', 24, NAVY, True, 42))
        root.add_widget(L(title, 17, RED, True, 34))
        sc = ScrollView()
        lab = Label(text=str(details), color=TEXT, font_size=dp(11), halign='left', valign='top',
                    size_hint_y=None, text_size=(None, None))
        lab.bind(width=lambda o, v: setattr(o, 'text_size', (max(1, v-dp(10)), None)))
        lab.bind(texture_size=lambda o, v: setattr(o, 'height', max(dp(200), v[1]+dp(20))))
        sc.add_widget(lab)
        root.add_widget(sc)
        b = B('CLOSE APP', NAVY, 46)
        b.bind(on_release=lambda _: self.stop())
        root.add_widget(b)
        screen = Screen(name='error')
        screen.add_widget(root)
        self.sm.add_widget(screen)
        return self.sm

    def setup_android_activity(self):
        # Android activity binding is deliberately deferred until a gallery/export
        # operation is requested. This prevents startup crashes on Android builds
        # where the android.activity bridge is not ready during App.build().
        if self._activity_bound:
            return True
        try:
            from android import activity
            self._android_activity = activity
            activity.bind(on_activity_result=self.on_activity_result)
            self._activity_bound = True
            return True
        except Exception:
            self._android_activity = None
            self._activity_bound = False
            return False

    def on_activity_result(self, request_code, result_code, intent):
        if request_code == REQUEST_GALLERY:
            if result_code != -1 or intent is None:
                return
            try:
                uri = intent.getData()
                if uri is None:
                    return
                saved = self.copy_android_uri(uri)
                cb = self.gallery_callback
                self.gallery_callback = None
                if cb:
                    cb(saved)
            except Exception as e:
                msg('Gallery Error', str(e))
        elif request_code == REQUEST_EXPORT:
            if result_code != -1 or intent is None:
                self.pending_export = None
                return
            try:
                uri = intent.getData()
                if uri is None or not self.pending_export:
                    return
                self.write_file_to_uri(self.pending_export['source'], uri)
                name = self.pending_export['name']
                self.pending_export = None
                msg('Saved', '%s saved successfully.' % name)
            except Exception as e:
                self.pending_export = None
                msg('Save Error', str(e))

    def copy_android_uri(self, uri):
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        activity_obj = PythonActivity.mActivity
        resolver = activity_obj.getContentResolver()
        stream = resolver.openInputStream(uri)
        mime = resolver.getType(uri) or 'image/jpeg'
        ext = '.jpg'
        if 'png' in mime:
            ext = '.png'
        elif 'webp' in mime:
            ext = '.webp'
        name = 'photo_%s%s' % (datetime.now().strftime('%Y%m%d_%H%M%S_%f'), ext)
        dest = os.path.join(self.photo_dir, name)
        with open(dest, 'wb') as out:
            buf = bytearray(32768)
            while True:
                try:
                    n = stream.read(buf)
                except Exception:
                    n = -1
                if n is None or n <= 0:
                    break
                out.write(bytes(buf[:n]))
        try:
            stream.close()
        except Exception:
            pass
        return dest

    def write_file_to_uri(self, source, uri):
        from jnius import autoclass
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        resolver = PythonActivity.mActivity.getContentResolver()
        out = resolver.openOutputStream(uri)
        with open(source, 'rb') as src:
            while True:
                data = src.read(32768)
                if not data:
                    break
                try:
                    out.write(data)
                except Exception:
                    for b in data:
                        out.write(b)
        try:
            out.flush()
        except Exception:
            pass
        try:
            out.close()
        except Exception:
            pass

    def select_gallery_image(self, callback):
        self.gallery_callback = callback
        if not self.setup_android_activity():
            return msg('Gallery', 'Gallery selection is available on Android builds.')
        try:
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            intent = Intent(Intent.ACTION_OPEN_DOCUMENT)
            intent.setType('image/*')
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
            intent.addFlags(Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION)
            PythonActivity.mActivity.startActivityForResult(intent, REQUEST_GALLERY)
        except Exception as e:
            self.gallery_callback = None
            msg('Gallery Error', str(e))

    def request_save_file(self, source, display_name, mime_type):
        if not os.path.isfile(source):
            return msg('Export Error', 'The export file could not be created.')
        if not self.setup_android_activity():
            return msg('Saved', 'File created at:\n%s' % source)
        try:
            from jnius import autoclass
            Intent = autoclass('android.content.Intent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            intent = Intent(Intent.ACTION_CREATE_DOCUMENT)
            intent.addCategory(Intent.CATEGORY_OPENABLE)
            intent.setType(mime_type)
            intent.putExtra(Intent.EXTRA_TITLE, display_name)
            self.pending_export = {'source': source, 'name': display_name}
            PythonActivity.mActivity.startActivityForResult(intent, REQUEST_EXPORT)
        except Exception as e:
            self.pending_export = None
            msg('Export Error', str(e))

    def go(self, n):
        if n == 'home':
            self.sm.current = 'home'
            self.refresh()
            return

        # Lazy-load every secondary module. The old version called every
        # screen builder during App.build(), so one bad module could crash
        # the whole Android app before Home was displayed.
        if not self.sm.has_screen(n):
            builders = {
                'observations': self.observations,
                'incidents': self.incidents,
                'inspections': self.inspections,
                'audits': self.audits,
                'capa': self.capa,
                'files': self.files,
                'settings': self.settings,
            }
            builder = builders.get(n)
            if builder is None:
                return msg('Navigation Error', 'Unknown module: %s' % n)
            try:
                screen = Screen(name=n)
                screen.add_widget(builder())
                self.sm.add_widget(screen)
            except Exception as e:
                import traceback
                details = traceback.format_exc()
                try:
                    with open(os.path.join(self.dir, 'screen_error_%s.txt' % n), 'w', encoding='utf-8') as f:
                        f.write(details)
                except Exception:
                    pass
                return msg('%s Error' % n.upper(), details)

        self.sm.current = n

    def nav(self):
        x = BoxLayout(size_hint_y=None, height=dp(55), spacing=dp(2), padding=dp(2))
        items = [
            ('HOME', 'home'), ('OBS', 'observations'), ('INC', 'incidents'),
            ('INSP', 'inspections'), ('AUDIT', 'audits'), ('CAPA', 'capa'),
            ('FILES', 'files'), ('SET', 'settings')
        ]
        for t, n in items:
            b = B(t, NAVY, 50, 7)
            b.bind(on_release=lambda _, n=n: self.go(n))
            x.add_widget(b)
        return x

    def page(self, title, content):
        r = BoxLayout(orientation='vertical')
        h = BoxLayout(size_hint_y=None, height=dp(55), padding=[dp(12), dp(4)])
        h.add_widget(L(title, 19, NAVY, True, 47))
        r.add_widget(h)
        r.add_widget(content)
        r.add_widget(self.nav())
        return r

    def form(self):
        s = ScrollView(bar_width=dp(4))
        g = GridLayout(cols=1, spacing=dp(7), padding=dp(10), size_hint_y=None)
        g.bind(minimum_height=g.setter('height'))
        s.add_widget(g)
        return s, g

    # ---------- Home ----------
    def home(self):
        s, g = self.form()
        c = Card(orientation='vertical', padding=dp(13), size_hint_y=None, height=dp(110))
        c.add_widget(L('HSE-POCKET', 25, NAVY, True, 38))
        c.add_widget(L('Health, Safety & Environment Management', 12, MUTED, False, 25))
        c.add_widget(L(self.db.setting('company_name'), 11, TEXT, True, 22))
        g.add_widget(c)
        g.add_widget(L('CONTROL CENTER', 16, NAVY, True, 30))
        self.cards = GridLayout(cols=2, spacing=dp(7), size_hint_y=None)
        self.cards.bind(minimum_height=self.cards.setter('height'))
        g.add_widget(self.cards)
        g.add_widget(L('QUICK ACTIONS', 16, NAVY, True, 30))
        q = GridLayout(cols=2, spacing=7, size_hint_y=None, height=dp(140))
        for t, col, n in [
            ('NEW OBSERVATION', BLUE, 'observations'), ('NEW INCIDENT', RED, 'incidents'),
            ('NEW INSPECTION', TEAL, 'inspections'), ('NEW CAPA', PURPLE, 'capa'),
            ('SETTINGS', ORANGE, 'settings'), ('OBSERVATION REGISTER', NAVY, 'observations')
        ]:
            b = B(t, col, 43, 8)
            b.bind(on_release=lambda _, n=n: self.go(n))
            q.add_widget(b)
        g.add_widget(q)
        self.summary = L('', 12, TEXT, False, 85)
        cc = Card(orientation='vertical', padding=10, size_hint_y=None, height=dp(95))
        cc.add_widget(self.summary)
        g.add_widget(cc)
        g.add_widget(L('RECENT ACTIVITY', 16, NAVY, True, 30))
        self.recent = L('', 11, MUTED, False, 125)
        rc = Card(orientation='vertical', padding=10, size_hint_y=None, height=dp(135))
        rc.add_widget(self.recent)
        g.add_widget(rc)
        b = B('REFRESH DASHBOARD', NAVY, 44)
        b.bind(on_release=lambda _: self.refresh())
        g.add_widget(b)
        r = BoxLayout(orientation='vertical')
        r.add_widget(s)
        r.add_widget(self.nav())
        self.refresh()
        return r

    def refresh(self):
        if not hasattr(self, 'cards'):
            return
        self.cards.clear_widgets()
        names = [
            ('OBSERVATIONS', 'observations', BLUE), ('INCIDENTS', 'incidents', RED),
            ('INSPECTIONS', 'inspections', TEAL), ('AUDITS', 'audits', GREEN),
            ('CAPA', 'capa', PURPLE), ('FILES', 'files', ORANGE)
        ]
        for title, t, col in names:
            n = self.db.count(t)
            detail = 'Open %d | Closed %d' % (self.db.st(t, 'Open'), self.db.st(t, 'Closed')) if t != 'files' else 'Evidence references'
            c = Card(orientation='vertical', padding=9, size_hint_y=None, height=dp(88))
            c.add_widget(L(title, 11, col, True, 24))
            row = BoxLayout(size_hint_y=None, height=dp(43))
            row.add_widget(L(n, 24, NAVY, True, 40))
            b = B('OPEN', col, 36, 8)
            b.size_hint_x = .43
            b.bind(on_release=lambda _, t=t: self.go('files' if t == 'files' else t))
            row.add_widget(b)
            c.add_widget(row)
            self.cards.add_widget(c)
        total = sum(self.db.count(x) for x in ['observations', 'incidents', 'inspections', 'audits', 'capa'])
        op = sum(self.db.st(x, 'Open') for x in ['observations', 'incidents', 'inspections', 'audits', 'capa'])
        self.summary.text = 'TOTAL HSE RECORDS: %d\nOPEN ACTIONS: %d\nDATABASE: Local SQLite | %s' % (total, op, now())
        self.recent.text = '\n'.join('%s #%s | %s | %s | %s' % r for r in self.db.recent()) or 'No records yet.'

    # ---------- Observations ----------
    def observations(self):
        s, g = self.form()
        g.add_widget(L('OBSERVATION MANAGEMENT', 16, NAVY, True, 30))
        self.od = I('Date'); self.od.text = today()
        self.oti = I('Time'); self.oti.text = datetime.now().strftime('%H:%M')
        self.ol = I('Location *')
        self.orp = I('In-Charge / Responsible Person')
        self.odg = I('Designation')
        self.odept = Spinner(text='CIVIL', values=['CIVIL','MECH.'], size_hint_y=None, height=44)
        self.ot = Spinner(text=OBS_TYPES[2], values=OBS_TYPES, size_hint_y=None, height=44)
        self.oc = Spinner(text=OBS_CATEGORIES[0], values=OBS_CATEGORIES, size_hint_y=None, height=44)
        self.ox = I('Description of the Observation *', 110, True)
        self.oa = I('Immediate Corrective Action Taken', 100, True)
        self.os = Spinner(text='Open', values=['Open', 'Closed', 'STOP Work'], size_hint_y=None, height=44)
        self.ob = I("Observer's Name")
        self.obi = I("Observer's Employee No.")
        self.obd = I("Observer's Designation")
        self.oe = I('Evidence / Photo / File Reference', 70, True)
        self.photo_path = ''
        self.photo_label = L('No photo attached', 10, MUTED, False, 26)
        for w in [self.od, self.oti, self.ol, self.orp, self.odg, self.odept, self.ot, self.oc, self.ox, self.oa, self.os, self.ob, self.obi, self.obd, self.oe]:
            g.add_widget(w)
        pb = B('ATTACH PHOTO FROM GALLERY', TEAL, 44, 9)
        pb.bind(on_release=lambda _: self.select_gallery_image(self.observation_photo_selected))
        g.add_widget(pb)
        g.add_widget(self.photo_label)
        b = B('SAVE OBSERVATION', BLUE, 46)
        b.bind(on_release=lambda _: self.saveobs())
        g.add_widget(b)
        b = B('VIEW / SELECT OBSERVATION REGISTER', NAVY, 46)
        b.bind(on_release=lambda _: self.observation_register())
        g.add_widget(b)
        return self.page('Observations', s)

    def observation_photo_selected(self, path):
        self.photo_path = path or ''
        self.photo_label.text = os.path.basename(path) if path else 'No photo attached'

    def saveobs(self):
        if not self.ol.text.strip() or not self.ox.text.strip():
            return msg('Required', 'Location and observation are required.')
        try:
            i = self.db.add('observations', {
                'date': self.od.text.strip(), 'time': self.oti.text.strip(), 'location': self.ol.text.strip(),
                'responsible': self.orp.text.strip(), 'designation': self.odg.text.strip(),
                'department': self.odept.text, 'type': self.ot.text, 'category': self.oc.text,
                'observation': self.ox.text.strip(), 'action': self.oa.text.strip(),
                'status': self.os.text, 'observed_by': self.ob.text.strip(), 'observer_id': self.obi.text.strip(),
                'observer_designation': self.obd.text.strip(), 'evidence': self.oe.text.strip(),
                'photo_path': self.photo_path,
                'created_at': now()
            })
            self.selected_observations = {}
            msg('Saved', 'Observation #%d saved successfully.\n\nOpen the Observation Register to select it and draft the SOP card.' % i)
            self.refresh()
        except Exception as e:
            msg('Save Error', str(e))

    def observation_register(self):
        rows = self.db.observation_rows()
        self.selected_observations = {}
        self.obs_checkboxes = {}
        root = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(7))
        root.add_widget(L('OBSERVATION REGISTER', 16, NAVY, True, 34))
        root.add_widget(L('Select one or more observations, then press DRAFT SOP CARD.', 10, MUTED, False, 28))

        # Fixed-width horizontal table so the register remains readable on a phone.
        widths = [45, 50, 72, 80, 90, 145, 155, 240, 72]
        headers = ['SEL','ID','DATE','TIME','LOCATION','TYPE','CATEGORY','OBSERVATION','STATUS']
        hs = ScrollView(do_scroll_x=True, do_scroll_y=False, size_hint_y=None, height=dp(44), bar_width=dp(4))
        hg = GridLayout(cols=len(headers), size_hint=(None, None), height=dp(42), spacing=dp(1))
        for text, width in zip(headers, widths):
            hg.add_widget(TableCell(text, True, width))
        hg.width = dp(sum(widths) + len(widths)-1)
        hs.add_widget(hg)
        root.add_widget(hs)

        vs = ScrollView(do_scroll_x=True, do_scroll_y=True, bar_width=dp(4))
        vg = GridLayout(cols=len(headers), size_hint=(None, None), spacing=dp(1))
        vg.bind(minimum_height=vg.setter('height'))
        vg.width = dp(sum(widths) + len(widths)-1)
        for r in rows:
            cb = CheckBox(size_hint=(None, None), size=(dp(45), dp(46)))
            self.obs_checkboxes[int(r['id'])] = cb
            cb.bind(active=lambda obj, val, rid=int(r['id']): self.toggle_observation(rid, val))
            cell = BoxLayout(size_hint=(None, None), size=(dp(45), dp(46)))
            cell.add_widget(cb)
            vg.add_widget(cell)
            vals = [r['id'], r['date'], r['time'] if 'time' in r.keys() else '', r['location'], r['type'], r['category'], r['observation'], r['status']]
            for v, width in zip(vals, widths[1:]):
                vg.add_widget(TableCell(v or '-', False, width))
        if not rows:
            vg.add_widget(TableCell('No observations found.', False, sum(widths)))
        vs.add_widget(vg)
        root.add_widget(vs)

        controls = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(195))
        for text, col, fn in [
            ('SELECT ALL', TEAL, lambda _: self.select_all_observations(rows)),
            ('CLEAR SELECTION', ORANGE, lambda _: self.clear_observation_selection()),
            ('DRAFT SOP CARD', BLUE, lambda _: self.draft_sop_cards()),
            ('EXPORT PDF REGISTER', RED, lambda _: self.export_observation_register_pdf()),
            ('EXPORT WORD REGISTER', NAVY, lambda _: self.export_observation_register_word()),
            ('EXPORT EXCEL REGISTER', GREEN, lambda _: self.export_observation_register_excel()),
            ('CLOSE REGISTER', NAVY, lambda _: self.close_observation_register()),
        ]:
            bb = B(text, col, 44, 8)
            bb.bind(on_release=fn)
            controls.add_widget(bb)
        root.add_widget(controls)
        p = Popup(title='Observation Register', content=root, size_hint=(.98, .94), auto_dismiss=False)
        p.open()
        self.obs_register_popup = p

    def close_observation_register(self):
        p = getattr(self, 'obs_register_popup', None)
        if p:
            p.dismiss()

    def toggle_observation(self, rid, active):
        if active:
            self.selected_observations[int(rid)] = True
        else:
            self.selected_observations.pop(int(rid), None)

    def select_all_observations(self, rows):
        self.selected_observations = {int(r['id']): True for r in rows}
        for rid, cb in getattr(self, 'obs_checkboxes', {}).items():
            cb.active = rid in self.selected_observations

    def clear_observation_selection(self):
        self.selected_observations = {}
        for cb in getattr(self, 'obs_checkboxes', {}).values():
            cb.active = False

    def selected_observation_rows(self):
        ids = list(self.selected_observations.keys())
        if not ids:
            return []
        placeholders = ','.join('?' * len(ids))
        return self.db.c.execute(
            'select * from observations where id in (%s) order by id' % placeholders, ids
        ).fetchall()

    def draft_sop_cards(self):
        rows = self.selected_observation_rows()
        if not rows:
            return msg('SOP Card', 'Select one or more observations first.')
        self.sop_rows = rows

        root = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(7))
        root.add_widget(L('SOP SAFETY OBSERVATION CARD - DRAFT', 16, NAVY, True, 34))
        root.add_widget(L('%d observation(s) selected. Each observation = one card page.' % len(rows), 10, MUTED, False, 26))

        # Preview the first selected card inside the application.
        r = rows[0]
        preview_scroll = ScrollView(bar_width=dp(5))
        card = Card(orientation='vertical', padding=dp(12), spacing=dp(4), size_hint_y=None, height=dp(900))
        logo = self.db.setting('logo_path')
        if logo and os.path.isfile(logo):
            img = Image(source=logo, size_hint_y=None, height=dp(70), allow_stretch=True, keep_ratio=True)
            card.add_widget(img)
        else:
            card.add_widget(L('', 10, TEXT, False, 45))

        company = self.db.setting('company_name')
        project = self.db.setting('project_name')
        card.add_widget(L('SAFETY OBSERVATION CARD', 19, NAVY, True, 38))
        card.add_widget(L(company, 12, TEXT, True, 28))
        card.add_widget(L(project, 11, TEXT, True, 34))
        card.add_widget(L('PERSON INFORMATION', 13, NAVY, True, 30))
        card.add_widget(L('Department: %s    |    Location: %s' % (r['department'] or '', r['location'] or ''), 10, TEXT, False, 28))
        card.add_widget(L('In-Charge: %s    |    Designation: %s' % (r['responsible'] or '', r['designation'] or ''), 10, TEXT, False, 32))
        card.add_widget(L('Date: %s    |    Time: %s' % (r['date'] or '', (r['time'] if 'time' in r.keys() else '') or ''), 10, TEXT, False, 28))

        card.add_widget(L('TYPE OF OBSERVATION', 13, NAVY, True, 30))
        for item in OBS_TYPES:
            card.add_widget(L(('[X] ' if r['type'] == item else '[ ] ') + item, 10, TEXT, False, 25))

        card.add_widget(L('DESCRIPTION OF THE OBSERVATION', 13, NAVY, True, 30))
        d = L(r['observation'] or '', 10, TEXT, False, 100)
        d.size_hint_y = None
        d.text_size = (None, None)
        d.bind(texture_size=lambda o, v: setattr(o, 'height', max(dp(80), v[1]+dp(10))))
        card.add_widget(d)

        card.add_widget(L('IMMEDIATE CORRECTIVE ACTION TAKEN (IF ANY)', 13, NAVY, True, 34))
        a = L(r['action'] or '', 10, TEXT, False, 90)
        a.size_hint_y = None
        a.bind(texture_size=lambda o, v: setattr(o, 'height', max(dp(70), v[1]+dp(10))))
        card.add_widget(a)

        card.add_widget(L('OBSERVATION STATUS', 13, NAVY, True, 30))
        card.add_widget(L('%s Open    %s Closed    %s STOP Work' % (
            '[X]' if r['status'] == 'Open' else '[ ]',
            '[X]' if r['status'] == 'Closed' else '[ ]',
            '[X]' if r['status'] == 'STOP Work' else '[ ]'), 10, TEXT, False, 28))

        card.add_widget(L('OBSERVATION CATEGORIES', 13, NAVY, True, 30))
        for item in OBS_CATEGORIES:
            card.add_widget(L(('[X] ' if r['category'] == item else '[ ] ') + item, 9, TEXT, False, 22))

        card.add_widget(L("OBSERVER'S INFORMATION", 13, NAVY, True, 30))
        card.add_widget(L('Name: %s    |    Emp.#: %s' % (r['observed_by'] or '', r['observer_id'] or ''), 10, TEXT, False, 28))
        card.add_widget(L('Designation: %s' % (r['observer_designation'] or ''), 10, TEXT, False, 28))
        card.add_widget(L('Signature: ________________________________', 10, TEXT, False, 32))
        preview_scroll.add_widget(card)
        root.add_widget(preview_scroll)

        actions = GridLayout(cols=2, spacing=dp(5), size_hint_y=None, height=dp(96))
        save = B('SAVE SOP CARD PDF', BLUE, 44, 9)
        close = B('CLOSE', NAVY, 44, 9)
        actions.add_widget(save); actions.add_widget(close)
        root.add_widget(actions)
        p = Popup(title='SOP Card Draft', content=root, size_hint=(.98, .96), auto_dismiss=False)
        close.bind(on_release=p.dismiss)
        save.bind(on_release=lambda _: self.save_sop_draft(rows, p))
        p.open()
        self.sop_draft_popup = p

    def save_sop_draft(self, rows, popup=None):
        # Always rebuild from the database so the latest Settings logo/company/project are used.
        fresh = self.selected_observation_rows()
        if fresh:
            rows = fresh
        self.export_sop_cards_pdf(rows)
        if popup:
            popup.dismiss()

    def sop_page(self, r, page_no, total, logo_path):
        # One selected observation = exactly one PDF page.
        # The supplied two-sided card is condensed into one printable A4 page.
        W, H = 595, 842
        c = ''
        c += '0.8 w\n32 30 m 563 30 l 563 812 l 32 812 l 32 30 l S\n'
        company = self.db.setting('company_name')
        project = self.db.setting('project_name')
        c += pdf_text(205, 806, 'Safety Observation Card', 15)
        c += pdf_text(55, 784, company or ' ', 10)
        c += pdf_text(55, 766, project or ' ', 9)
        if logo_path and os.path.isfile(logo_path):
            c += 'q 485 750 55 55 cm /Im1 Do Q\n'

        # Person information
        c += pdf_text(55, 735, 'Person Information', 10)
        c += pdf_line(55, 731, 160, 731)
        department = r['department'] if 'department' in r.keys() else ''
        c += pdf_text(60, 710, ('[X]' if department == 'CIVIL' else '[ ]') + ' CIVIL', 8)
        c += pdf_text(150, 710, ('[X]' if department == 'MECH.' else '[ ]') + ' MECH.', 8)
        c += pdf_text(245, 710, 'Location:', 8)
        c += pdf_text(295, 710, r['location'] or '', 8)
        c += pdf_text(60, 690, 'In-Charge:', 8)
        c += pdf_text(120, 690, r['responsible'] or '', 8)
        c += pdf_text(300, 690, 'Designation:', 8)
        c += pdf_text(370, 690, r['designation'] or '', 8)
        c += pdf_text(60, 670, 'Date:', 8)
        c += pdf_text(100, 670, r['date'] or '', 8)
        c += pdf_text(250, 670, 'Time:', 8)
        c += pdf_text(285, 670, (r['time'] if 'time' in r.keys() else '') or '', 8)

        # Type
        c += pdf_text(55, 646, 'Type of Observation', 10)
        ty = 626
        for key in OBS_TYPES:
            mark = '[X]' if r['type'] == key else '[ ]'
            c += pdf_text(60, ty, mark + ' ' + key, 7)
            ty -= 18

        # Description and action
        c += pdf_text(55, 548, 'Description of the Observation', 10)
        desc_lines = self.wrap_text(r['observation'] or '', 88)[:4]
        yy = 530
        for line in desc_lines:
            c += pdf_text(60, yy, line, 7)
            yy -= 14
        for off in (8, 26, 44, 62):
            c += pdf_line(55, 522-off, 540, 522-off)

        c += pdf_text(55, 438, 'Immediate Corrective Action Taken (if any)', 10)
        act_lines = self.wrap_text(r['action'] or '', 88)[:3]
        yy = 420
        for line in act_lines:
            c += pdf_text(60, yy, line, 7)
            yy -= 14
        for off in (8, 26, 44):
            c += pdf_line(55, 412-off, 540, 412-off)

        c += pdf_text(55, 340, 'Observation Status', 10)
        status = r['status'] or ''
        c += pdf_text(65, 320, ('[X]' if status == 'Open' else '[ ]') + ' Open', 8)
        c += pdf_text(190, 320, ('[X]' if status == 'Closed' else '[ ]') + ' Closed', 8)
        c += pdf_text(330, 320, ('[X]' if status == 'STOP Work' else '[ ]') + ' STOP Work', 8)

        # Categories: all supplied card categories, two columns.
        c += pdf_text(55, 295, 'Observation Categories', 10)
        left = OBS_CATEGORIES[:14]
        right = OBS_CATEGORIES[14:]
        y1 = 275
        for item in left:
            mark = '[X]' if r['category'] == item else '[ ]'
            c += pdf_text(58, y1, mark + ' ' + item, 6)
            y1 -= 16
        y2 = 275
        for item in right:
            mark = '[X]' if r['category'] == item else '[ ]'
            c += pdf_text(305, y2, mark + ' ' + item, 6)
            y2 -= 16

        # Observer information
        c += pdf_text(55, 54, "Observer's Information", 9)
        c += pdf_text(60, 38, 'Name: ' + (r['observed_by'] or ''), 7)
        observer_id = r['observer_id'] if 'observer_id' in r.keys() else ''
        observer_desig = r['observer_designation'] if 'observer_designation' in r.keys() else ''
        c += pdf_text(245, 38, 'Emp.#: ' + (observer_id or ''), 7)
        c += pdf_text(365, 38, 'Designation: ' + (observer_desig or r['designation'] or ''), 7)
        c += pdf_text(60, 18, 'Signature: ____________________________', 7)
        c += pdf_text(350, 18, 'SAFETY FIRST, THINK SAFE, BE SAFE & SAVE ENVIRONMENT', 5)
        return c

    def export_sop_cards_pdf(self, rows):
        logo = self.db.setting('logo_path')
        pages = [self.sop_page(r, i + 1, len(rows), logo) for i, r in enumerate(rows)]
        name = 'SOP_Safety_Observation_Cards_%s.pdf' % datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.export_dir, name)
        build_pdf(pages, path, logo)
        self.request_save_file(path, name, 'application/pdf')

    # ---------- Observation exports ----------
    def observation_export_data(self):
        rows = self.db.observation_rows()
        keys = ['id','date','time','location','responsible','designation','department','type','category','observation','action','status','observed_by','observer_id','observer_designation','evidence','created_at']
        return rows, keys

    def export_observation_register_pdf(self):
        rows, keys = self.observation_export_data()
        if not rows:
            return msg('Export', 'No observations available.')
        pages = []
        lines_per_page = 45
        header = 'OBSERVATION REGISTER | %s | %s' % (self.db.setting('company_name'), self.db.setting('project_name'))
        for start in range(0, len(rows), lines_per_page):
            c = pdf_text(30, 810, header[:100], 11)
            c += pdf_text(30, 792, 'ID | DATE | LOCATION | TYPE | CATEGORY | OBSERVATION | STATUS', 7)
            y = 775
            for r in rows[start:start+lines_per_page]:
                text = '%s | %s | %s | %s | %s | %s | %s' % (
                    r['id'], r['date'], r['location'], r['type'], r['category'], r['observation'], r['status']
                )
                # Keep each line short enough for a PDF page.
                for line in self.wrap_text(text, 120)[:3]:
                    c += pdf_text(30, y, line, 6)
                    y -= 11
                y -= 3
            pages.append(c)
        name = 'Observation_Register_%s.pdf' % datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.export_dir, name)
        build_pdf(pages, path)
        self.request_save_file(path, name, 'application/pdf')

    def wrap_text(self, text, width):
        words = str(text or '').split()
        lines = []
        line = ''
        for w in words:
            if len(line) + len(w) + 1 > width and line:
                lines.append(line)
                line = w
            else:
                line = (line + ' ' + w).strip()
        if line:
            lines.append(line)
        return lines or ['']

    def rtf_escape(self, s):
        return str(s or '').replace('\\', '\\\\').replace('{', '\\{').replace('}', '\\}').replace('\n', '\\line ')

    def rtf_logo(self, path):
        if not path or not os.path.isfile(path):
            return ''
        ext = os.path.splitext(path)[1].lower()
        if ext not in ('.png', '.jpg', '.jpeg'):
            return ''
        try:
            data = open(path, 'rb').read()
            hexdata = data.hex()
            control = '\\pngblip' if ext == '.png' else '\\jpegblip'
            return '{\\pict%s\\picwgoal2400\\pichgoal1400\n%s}' % (control, hexdata)
        except Exception:
            return ''

    def export_observation_register_word(self):
        rows, keys = self.observation_export_data()
        if not rows:
            return msg('Export', 'No observations available.')
        # RTF content saved as .doc so Microsoft Word can open it directly.
        widths = [500, 900, 700, 1300, 1450, 1300, 850, 1650, 1650, 4200, 1200]
        headers = ['ID','DATE','TIME','LOCATION','RESPONSIBLE','DESIGNATION','DEPT.','TYPE','CATEGORY','OBSERVATION','STATUS']
        rtf = ['{\\rtf1\\ansi\\deff0', '{\\fonttbl{\\f0 Arial;}}', '\\landscape\\paperw16840\\paperh11900']
        rtf.append(self.rtf_logo(self.db.setting('logo_path')))
        rtf.append('\\fs24\\b %s\\b0\\line ' % self.rtf_escape(self.db.setting('company_name')))
        rtf.append('\\fs22\\b %s\\b0\\line\\line ' % self.rtf_escape(self.db.setting('project_name')))
        rtf.append('\\fs20\\b OBSERVATION REGISTER\\b0\\line ')
        for r in rows:
            rtf.append('\\trowd\\trrh-2880')  # 2 inches = 2880 twips
            pos = 0
            vals = [r['id'], r['date'], r['time'], r['location'], r['responsible'], r['designation'], r['department'], r['type'], r['category'], r['observation'], r['status']]
            for w, v in zip(widths, vals):
                pos += w
                rtf.append('\\cellx%d' % pos)
            for v in vals:
                rtf.append('\\pard\\intbl\\fs18\\b0 %s\\cell' % self.rtf_escape(v))
            rtf.append('\\row')
        rtf.append('}')
        name = 'Observation_Register_%s.doc' % datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.export_dir, name)
        with open(path, 'w', encoding='latin-1', errors='replace') as f:
            f.write(''.join(rtf))
        self.request_save_file(path, name, 'application/msword')

    def export_observation_register_excel(self):
        rows, keys = self.observation_export_data()
        if not rows:
            return msg('Export', 'No observations available.')
        logo_html = ''
        logo = self.db.setting('logo_path')
        if logo and os.path.isfile(logo):
            ext = os.path.splitext(logo)[1].lower()
            if ext in ('.png', '.jpg', '.jpeg'):
                mime = 'image/png' if ext == '.png' else 'image/jpeg'
                try:
                    data = base64.b64encode(open(logo, 'rb').read()).decode('ascii')
                    logo_html = '<img style="max-height:90px;max-width:220px" src="data:%s;base64,%s">' % (mime, data)
                except Exception:
                    logo_html = ''
        headers = ['ID','DATE','TIME','LOCATION','RESPONSIBLE','DESIGNATION','DEPT.','TYPE','CATEGORY','OBSERVATION','ACTION','STATUS','OBSERVED BY','EMP.#','OBSERVER DESIGNATION','EVIDENCE','CREATED AT']
        html = ['<html><head><meta charset="utf-8"><style>@page{size:landscape;}body{font-family:Arial;font-size:10pt;}table{border-collapse:collapse;width:100%%;}th,td{border:1px solid #777;padding:5px;vertical-align:top;}th{background:#17243b;color:white;}tr{height:144pt;}</style></head><body>']
        html.append(logo_html)
        html.append('<h2>%s</h2><h3>%s</h3><h3>Observation Register</h3><table><tr>%s</tr>' % (
            self.html_escape(self.db.setting('company_name')),
            self.html_escape(self.db.setting('project_name')),
            ''.join('<th>%s</th>' % h for h in headers)
        ))
        for r in rows:
            html.append('<tr>%s</tr>' % ''.join('<td>%s</td>' % self.html_escape(r[k]) for k in ['id','date','time','location','responsible','designation','department','type','category','observation','action','status','observed_by','observer_id','observer_designation','evidence','created_at']))
        html.append('</table></body></html>')
        name = 'Observation_Register_%s.xls' % datetime.now().strftime('%Y%m%d_%H%M%S')
        path = os.path.join(self.export_dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(''.join(html))
        self.request_save_file(path, name, 'application/vnd.ms-excel')

    def html_escape(self, v):
        s = str(v if v is not None else '')
        return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

    # ---------- Incidents ----------
    def incidents(self):
        s, g = self.form()
        g.add_widget(L('INCIDENT / ACCIDENT INVESTIGATION', 16, NAVY, True, 30))
        g.add_widget(L('Includes ICAM, RCA, 5-Why, Fishbone and Bow-Tie.', 11, MUTED, False, 30))
        fields = [('idate','Date'),('itime','Time'),('iloc','Location *'),('ipro','Project / Area'),('iact','Activity'),('ititle','Incident Title *')]
        for a, h in fields:
            setattr(self, a, I(h)); g.add_widget(getattr(self, a))
        self.idate.text = today()
        self.ic = Spinner(text='Near Miss', values=['Near Miss','First Aid','Medical Treatment','Lost Time Injury','Fatality','Property Damage','Environmental','Fire','Vehicle','Process Safety','Security','Other'], size_hint_y=None, height=44)
        self.isv = Spinner(text='Medium', values=['Low','Medium','High','Critical'], size_hint_y=None, height=44)
        g.add_widget(self.ic); g.add_widget(self.isv)
        labels = [('ides','Detailed Incident Description',120),('icon','Actual Consequence',70),('ipot','Potential Consequence',70),('ipeo','Persons Involved / Roles',80),('iinj','Injury / Illness Details',80),('idam','Property / Equipment Damage',70),('ienv','Environmental Impact',70),('iwit','Witnesses / Statements',80),('iimm','Immediate Action / Containment',90),('ieve','Evidence / Photos / Documents / File References',80),('ilead','Investigation Leader',44),('iteam','Investigation Team',60),('iscope','Investigation Scope / Terms',80),('itimeL','Sequence / Timeline',110),('istat','Statements / Evidence Findings',100)]
        for a, h, ht in labels:
            setattr(self, a, I(h, ht, ht > 60)); g.add_widget(getattr(self, a))
        g.add_widget(L('ICAM ANALYSIS', 13, RED, True, 28))
        for a,h,ht in [('icam_event','Event / Incident',90),('icam_ind','Individual / Team Actions',90),('icam_task','Task / Environmental Conditions',90),('icam_org','Organisational Factors',90),('icam_def','Absent / Failed Defences and Barriers',100),('icam_act','ICAM Actions / Defence Improvements',100)]:
            setattr(self,a,I(h,ht,True));g.add_widget(getattr(self,a))
        g.add_widget(L('ROOT CAUSE ANALYSIS',13,PURPLE,True,28))
        self.rcam=Spinner(text='5-Why',values=['5-Why','Fishbone / Ishikawa','Bow-Tie','ICAM','Root Cause Tree','Other'],size_hint_y=None,height=44);g.add_widget(self.rcam)
        for a,h,ht in [('direct','Direct / Immediate Cause',80),('under','Underlying Cause',80),('root','Root Cause',100),('contrib','Contributing Factors',90),('why','5-Why Analysis',120),('fish','Fishbone: People / Method / Machine / Material / Environment / Management / Measurement',130),('bow','Bow-Tie: Threats / Top Event / Preventive Barriers / Consequences / Mitigating Barriers',130)]:
            setattr(self,a,I(h,ht,True));g.add_widget(getattr(self,a))
        g.add_widget(L('ACTION & CLOSEOUT',13,GREEN,True,28))
        for a,h,ht in [('ca','Corrective Actions',100),('pa','Preventive Actions',100),('sys','System / Management Improvement',90),('resp','Responsible Person',44),('target','Target Date',44)]:
            setattr(self,a,I(h,ht,ht>60));g.add_widget(getattr(self,a))
        self.pri=Spinner(text='Medium',values=['Low','Medium','High','Critical'],size_hint_y=None,height=44);self.ist=Spinner(text='Open',values=['Open','Investigation','Action In Progress','Closed'],size_hint_y=None,height=44);g.add_widget(self.pri);g.add_widget(self.ist);self.ver=I('Verification / Effectiveness Check',90,True);self.close=I('Closeout Details',90,True);g.add_widget(self.ver);g.add_widget(self.close)
        b=B('SAVE COMPLETE INVESTIGATION',RED,48);b.bind(on_release=lambda _:self.saveinc());g.add_widget(b);b=B('VIEW INCIDENT REGISTER',NAVY,42);b.bind(on_release=lambda _:self.view('incidents'));g.add_widget(b)
        return self.page('Incident Investigation',s)

    def saveinc(self):
        if not self.iloc.text.strip() or not self.ititle.text.strip(): return msg('Required','Location and Incident Title are required.')
        def v(a): return getattr(self,a).text
        d={'date':v('idate'),'time':v('itime'),'location':v('iloc'),'project':v('ipro'),'activity':v('iact'),'classification':self.ic.text,'severity':self.isv.text,'title':v('ititle'),'description':v('ides'),'consequence':v('icon'),'potential_consequence':v('ipot'),'people':v('ipeo'),'injury':v('iinj'),'damage':v('idam'),'environment':v('ienv'),'witnesses':v('iwit'),'immediate':v('iimm'),'evidence':v('ieve'),'investigator':v('ilead'),'team':v('iteam'),'scope':v('iscope'),'timeline':v('itimeL'),'statements':v('istat'),'icam_event':v('icam_event'),'icam_individual':v('icam_ind'),'icam_task':v('icam_task'),'icam_org':v('icam_org'),'icam_defences':v('icam_def'),'icam_actions':v('icam_act'),'rca_method':self.rcam.text,'direct_cause':v('direct'),'underlying_cause':v('under'),'root_cause':v('root'),'contributing':v('contrib'),'five_whys':v('why'),'fishbone':v('fish'),'bowtie':v('bow'),'corrective':v('ca'),'preventive':v('pa'),'system_action':v('sys'),'responsible':v('resp'),'target':v('target'),'priority':self.pri.text,'status':self.ist.text,'verification':v('ver'),'closeout':v('close'),'created_at':now()}
        try:
            i=self.db.add('incidents',d);msg('Saved','Complete incident investigation #%d saved.'%i);self.refresh()
        except Exception as e: msg('Save Error',str(e))

    # ---------- Inspections ----------
    def inspections(self):
        s,g=self.form();g.add_widget(L('INSPECTION MANAGEMENT',16,NAVY,True,30));self.nd=I('Date');self.nd.text=today()
        ws=[self.nd,I('Time'),I('Location *'),I('Inspection Type'),I('Inspector'),I('Activity / Work Area'),I('Checklist / Areas Checked',100,True),I('Unsafe Acts',80,True),I('Unsafe Conditions',80,True),I('Good Practices',80,True),I('PPE',65,True),I('Excavation',65,True),I('Work at Height',65,True),I('Lifting',65,True),I('Scaffolding',65,True),I('Electrical',65,True),I('Confined Space',65,True),I('Hot Work',65,True),I('Fire Safety',65,True),I('Housekeeping',65,True),I('Vehicle / Plant',65,True),I('Environmental',65,True),I('Emergency Preparedness',65,True),I('Findings',100,True),I('Actions Required',100,True),I('Responsible Person'),I('Target Date')]
        self.nw=ws
        for w in ws:g.add_widget(w)
        self.ns=Spinner(text='Open',values=['Open','Closed'],size_hint_y=None,height=44);self.ne=I('Evidence / Photo / File Reference',70,True);g.add_widget(self.ns);g.add_widget(self.ne);b=B('SAVE INSPECTION',TEAL,46);b.bind(on_release=lambda _:self.saveinsp());g.add_widget(b);b=B('VIEW INSPECTIONS',NAVY,42);b.bind(on_release=lambda _:self.view('inspections'));g.add_widget(b);return self.page('Inspections',s)

    def saveinsp(self):
        w=self.nw;keys=['date','time','location','inspection_type','inspector','activity','checklist','unsafe_acts','unsafe_conditions','good_practices','ppe','excavation','wah','lifting','scaffolding','electrical','confined_space','hot_work','fire','housekeeping','vehicle','environment','emergency','findings','actions','responsible','target_date'];d={k:w[i].text for i,k in enumerate(keys)};d.update(status=self.ns.text,evidence=self.ne.text,created_at=now());
        try:i=self.db.add('inspections',d);msg('Saved','Inspection #%d saved.'%i);self.refresh()
        except Exception as e:msg('Save Error',str(e))

    # ---------- Audits ----------
    def audits(self):
        s,g=self.form();g.add_widget(L('HSE AUDIT MANAGEMENT',16,NAVY,True,30));self.aw=[I('Date'),I('Location *'),I('Audit Type'),I('Auditor / Team'),I('Scope / Standard',80,True),I('Findings / Nonconformities',110,True),I('Good Practices / Strengths',80,True),I('Corrective Actions',100,True),I('Responsible Person'),I('Target Date')];self.aw[0].text=today()
        for w in self.aw:g.add_widget(w)
        self.ast=Spinner(text='Open',values=['Open','Closed'],size_hint_y=None,height=44);self.aev=I('Evidence / File Reference',70,True);g.add_widget(self.ast);g.add_widget(self.aev);b=B('SAVE AUDIT',GREEN,46);b.bind(on_release=lambda _:self.saveaudit());g.add_widget(b);b=B('VIEW AUDITS',NAVY,42);b.bind(on_release=lambda _:self.view('audits'));g.add_widget(b);return self.page('Audits',s)

    def saveaudit(self):
        keys=['date','location','audit_type','auditor','scope','findings','good_practices','actions','responsible','target'];d={k:self.aw[i].text for i,k in enumerate(keys)};d.update(status=self.ast.text,evidence=self.aev.text,created_at=now());
        try:i=self.db.add('audits',d);msg('Saved','Audit #%d saved.'%i);self.refresh()
        except Exception as e:msg('Save Error',str(e))

    # ---------- CAPA ----------
    def capa(self):
        s,g=self.form();g.add_widget(L('CAPA MANAGEMENT',16,NAVY,True,30));self.cw=[I('Date'),I('Source'),I('Location'),I('Finding *',100,True),I('Root Cause',90,True),I('Corrective Action',100,True),I('Preventive Action',100,True),I('Responsible Person'),I('Target Date')];self.cw[0].text=today()
        for w in self.cw:g.add_widget(w)
        self.cp=Spinner(text='Medium',values=['Low','Medium','High','Critical'],size_hint_y=None,height=44);self.cs=Spinner(text='Open',values=['Open','In Progress','Closed','Overdue'],size_hint_y=None,height=44);self.cv=I('Verification / Effectiveness',80,True);self.cc=I('Closeout',80,True);self.ce=I('Closeout Evidence / File Reference',70,True);g.add_widget(self.cp);g.add_widget(self.cs);g.add_widget(self.cv);g.add_widget(self.cc);g.add_widget(self.ce);b=B('SAVE CAPA',PURPLE,46);b.bind(on_release=lambda _:self.savecapa());g.add_widget(b);b=B('VIEW CAPA',NAVY,42);b.bind(on_release=lambda _:self.view('capa'));g.add_widget(b);b=B('EXPORT CAPA CSV',TEAL,42);b.bind(on_release=lambda _:self.export('capa'));g.add_widget(b);return self.page('CAPA',s)

    def savecapa(self):
        if not self.cw[3].text.strip():return msg('Required','Finding is required.')
        keys=['date','source','location','finding','root_cause','corrective','preventive','responsible','target'];d={k:self.cw[i].text for i,k in enumerate(keys)};d.update(priority=self.cp.text,status=self.cs.text,verification=self.cv.text,closeout=self.cc.text,evidence=self.ce.text,created_at=now());
        try:i=self.db.add('capa',d);msg('Saved','CAPA #%d saved.'%i);self.refresh()
        except Exception as e:msg('Save Error',str(e))

    # ---------- Files ----------
    def files(self):
        s,g=self.form();g.add_widget(L('FILES & EVIDENCE',16,NAVY,True,30));self.fm=Spinner(text='Incident',values=['Observation','Incident','Inspection','Audit','CAPA'],size_hint_y=None,height=44);self.fr=I('Record ID *');self.fp=I('File path / photo / document reference *',75,True);self.fd=I('Description')
        for w in [self.fm,self.fr,self.fp,self.fd]:g.add_widget(w)
        b=B('SAVE FILE REFERENCE',ORANGE,46);b.bind(on_release=lambda _:self.savefile());g.add_widget(b);b=B('VIEW FILE REGISTER',NAVY,42);b.bind(on_release=lambda _:self.viewfiles());g.add_widget(b);return self.page('Files & Evidence',s)

    def savefile(self):
        try:i=int(self.fr.text.strip())
        except:return msg('Invalid','Record ID must be a number.')
        if not self.fp.text.strip():return msg('Required','File reference is required.')
        try:self.db.add('files',{'module':self.fm.text,'record_id':i,'path':self.fp.text,'description':self.fd.text,'created_at':now()});msg('Saved','File reference saved.')
        except Exception as e:msg('Save Error',str(e))

    def viewfiles(self):
        r=self.db.c.execute('select id,module,record_id,path,description,created_at from files order by id desc').fetchall();msg('FILE REGISTER','\n\n----------------\n\n'.join('ID: %s\nModule: %s\nRecord: %s\nFile: %s\nDescription: %s\n%s'%tuple(x) for x in r) if r else 'No file references.')

    def view(self,t):
        r=self.db.rows(t);msg(t.upper()+' REGISTER','\n\n----------------\n\n'.join('\n'.join('%s: %s'%(i+1,v if v not in (None,'') else '-') for i,v in enumerate(x)) for x in r) if r else 'No records found.')

    def export(self,t):
        r=self.db.rows(t)
        if not r:return msg('Export','No records available.')
        p=os.path.join(self.export_dir,t+'_register_'+datetime.now().strftime('%Y%m%d_%H%M%S')+'.csv')
        with open(p,'w',newline='',encoding='utf-8-sig') as f:
            csv.writer(f).writerows([list(x) for x in r])
        self.request_save_file(p, os.path.basename(p), 'text/csv')

    # ---------- Settings ----------
    def settings(self):
        s,g=self.form()
        g.add_widget(L('APPLICATION SETTINGS',16,NAVY,True,30))
        g.add_widget(L('Company and project information below is used automatically on exported reports and SOP Safety Observation Cards.',11,MUTED,False,55))
        self.set_company=I('Company Name')
        self.set_project=I('Project Name')
        self.set_logo=I('Company Logo Path / Local File',70,True)
        self.logo_preview=L('No logo selected',10,MUTED,False,50)
        self.set_company.text=self.db.setting('company_name')
        self.set_project.text=self.db.setting('project_name')
        self.set_logo.text=self.db.setting('logo_path')
        for w in [self.set_company,self.set_project,self.set_logo]:g.add_widget(w)
        lb=B('SELECT COMPANY LOGO FROM GALLERY',TEAL,44,9)
        lb.bind(on_release=lambda _: self.select_gallery_image(self.settings_logo_selected))
        g.add_widget(lb);g.add_widget(self.logo_preview)
        sb=B('SAVE SETTINGS',BLUE,46);sb.bind(on_release=lambda _:self.save_settings());g.add_widget(sb)
        g.add_widget(L('SOP CARD HEADER',13,NAVY,True,30))
        g.add_widget(L('The card does not contain the Medgulf logo or Medgulf project wording. It uses the logo, company name and project name saved here. If blank, those areas remain blank.',11,MUTED,False,75))
        return self.page('Settings',s)

    def settings_logo_selected(self, path):
        self.set_logo.text = path or ''
        self.logo_preview.text = os.path.basename(path) if path else 'No logo selected'
        self.db.set_setting('logo_path', path or '')

    def save_settings(self):
        self.db.set_setting('company_name', self.set_company.text.strip())
        self.db.set_setting('project_name', self.set_project.text.strip())
        self.db.set_setting('logo_path', self.set_logo.text.strip())
        msg('Settings Saved', 'Company, project and logo settings have been saved.\n\nNew exports and SOP cards will use these settings.')

    def on_stop(self):
        try:
            if self._activity_bound and self._android_activity:
                self._android_activity.unbind(on_activity_result=self.on_activity_result)
        except Exception:
            pass
        self.db.c.close()


if __name__ == '__main__':
    AppHSE().run()