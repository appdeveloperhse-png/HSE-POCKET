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
            findings,actions,responsible,target,status,evidence,created_at)''')
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
        Window.clearcolor = BG
        self.dir = os.path.join(self.user_data_dir, 'HSE_POCKET')
        self.export_dir = os.path.join(self.dir, 'Exports')
        self.photo_dir = os.path.join(self.dir, 'Photos')
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(self.export_dir, exist_ok=True)
        os.makedirs(self.photo_dir, exist_ok=True)
        self.db = DB(os.path.join(self.dir, 'hse_pocket.db'))
        self.sm = ScreenManager()
        self.selected_observations = {}
        self.gallery_callback = None
        self.pending_export = None
        self._android_activity = None
        self.setup_android_activity()

        for n, f in [
            ('home', self.home), ('observations', self.observations),
            ('incidents', self.incidents), ('inspections', self.inspections),
            ('audits', self.audits), ('capa', self.capa), ('files', self.files),
            ('settings', self.settings)
        ]:
            s = Screen(name=n)
            s.add_widget(f())
            self.sm.add_widget(s)
        return self.sm

    def setup_android_activity(self):
        try:
            from android import activity
            self._android_activity = activity
            activity.bind(on_activity_result=self.on_activity_result)
        except Exception:
            self._android_activity = None

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
        if not self._android_activity:
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
        if not self._android_activity:
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
        self.sm.current = n
        if n == 'home':
            self.refresh()

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
                'department': self.odept.text, 'type': self.ot.text, 'category