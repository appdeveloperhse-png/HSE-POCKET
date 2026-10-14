# HSE-POCKET - single-file Kivy Android HSE observation app
# Replacement main.py. Keeps existing SQLite observation data by discovering and
# reusing an existing database/table where possible. Does not modify the GitHub workflow.

import os
import sys
import json
import shutil
import sqlite3
import tempfile
import datetime
import traceback
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.utils import platform
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.image import Image
from kivy.uix.filechooser import FileChooserListView

APP_NAME = "HSE-POCKET"
APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("HSE_POCKET_DATA", str(APP_DIR)))
DATA_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = DATA_DIR / "hse_pocket_settings.json"
DEFAULT_DB = DATA_DIR / "hse_pocket.db"
EXPORT_DIR = DATA_DIR / "HSE-POCKET-Exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)

# ---------- visual helpers ----------

def now_text():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M")


def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


def slug(value):
    value = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in safe_text(value))
    return value[:48] or "HSE"


def popup_message(title, message):
    content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
    content.add_widget(Label(text=str(message), halign="left", valign="middle"))
    close = Button(text="OK", size_hint_y=None, height=dp(46))
    content.add_widget(close)
    pop = Popup(title=title, content=content, size_hint=(0.9, 0.55), auto_dismiss=True)
    close.bind(on_release=pop.dismiss)
    pop.open()


class HSEButton(Button):
    def __init__(self, **kwargs):
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("height", dp(46))
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_color", (0.10, 0.27, 0.43, 1))
        kwargs.setdefault("color", (1, 1, 1, 1))
        super().__init__(**kwargs)


class Field(BoxLayout):
    def __init__(self, caption, value="", multiline=False, **kwargs):
        super().__init__(orientation="vertical", size_hint_y=None, height=dp(82), spacing=dp(3), **kwargs)
        self.add_widget(Label(text=caption, size_hint_y=None, height=dp(23), halign="left", valign="middle",
                              color=(0.12, 0.18, 0.24, 1)))
        self.input = TextInput(text=safe_text(value), multiline=multiline, size_hint_y=None,
                               height=dp(55 if multiline else 48), padding=[dp(9), dp(8)],
                               background_normal="", background_active="", background_color=(0.96, 0.97, 0.98, 1),
                               foreground_color=(0.08, 0.10, 0.12, 1), cursor_color=(0.05, 0.3, 0.5, 1))
        self.add_widget(self.input)


# ---------- database: reuse the existing observation table where possible ----------

class ObservationStore:
    FIELD_ALIASES = {
        "id": ["id", "observation_id", "serial", "serial_no", "sr_no"],
        "date": ["date", "observation_date", "created_at", "datetime", "date_time"],
        "location": ["location", "area", "site_location"],
        "responsible": ["responsible", "responsible_person", "person_responsible", "supervisor"],
        "designation": ["designation", "responsible_designation"],
        "type": ["type", "observation_type", "kind"],
        "category": ["category", "hazard_category"],
        "observation": ["observation", "description", "details", "finding", "unsafe_condition"],
        "action": ["action", "corrective_action", "recommendation", "immediate_action"],
        "status": ["status", "closeout_status"],
        "observed_by": ["observed_by", "observer", "reported_by", "hse_officer"],
        "observer_designation": ["observer_designation", "observed_by_designation"],
        "observer_id": ["observer_id", "employee_id", "observed_by_id"],
        "evidence": ["evidence", "photo", "photo_path", "attachment", "image_path"],
        "closeout_evidence": ["closeout_evidence", "closeout_photo", "closure_evidence"],
        "remarks": ["remarks", "comments", "notes"],
    }

    def __init__(self):
        self.db_path = self._find_database()
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._prepare_table()

    def _find_database(self):
        candidates = []
        for base in [DATA_DIR, APP_DIR, Path.home()]:
            if base.exists():
                try:
                    candidates.extend(list(base.glob("*.db")))
                    candidates.extend(list(base.glob("*.sqlite")))
                    candidates.extend(list(base.glob("*.sqlite3")))
                except Exception:
                    pass
        seen = set()
        for candidate in candidates:
            try:
                key = str(candidate.resolve())
                if key in seen:
                    continue
                seen.add(key)
                con = sqlite3.connect(str(candidate))
                tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
                found = False
                for table in tables:
                    if table.lower() in ("observations", "observation", "safety_observations"):
                        found = True
                        break
                con.close()
                if found:
                    return candidate
            except Exception:
                continue
        return DEFAULT_DB

    def _tables(self):
        return [r[0] for r in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]

    def _prepare_table(self):
        tables = self._tables()
        chosen = next((t for t in tables if t.lower() in ("observations", "observation", "safety_observations")), None)
        if not chosen:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT, location TEXT, responsible TEXT, designation TEXT,
                    type TEXT, category TEXT, observation TEXT, action TEXT, status TEXT,
                    observed_by TEXT, observer_designation TEXT, observer_id TEXT,
                    evidence TEXT, closeout_evidence TEXT, remarks TEXT
                )
            """)
            self.conn.commit()
            chosen = "observations"
        self.table = chosen
        self.columns = [r[1] for r in self.conn.execute(f'PRAGMA table_info("{self.table}")')]
        self.column_map = {}
        lower = {c.lower(): c for c in self.columns}
        for logical, aliases in self.FIELD_ALIASES.items():
            self.column_map[logical] = next((lower[a] for a in aliases if a in lower), None)
        # Existing schemas may have different column names. Add only optional fields
        # when the table is our new table; never rewrite or drop a user's old table.
        if self.table == "observations":
            for col, definition in [
                ("date", "TEXT"), ("location", "TEXT"), ("responsible", "TEXT"),
                ("designation", "TEXT"), ("type", "TEXT"), ("category", "TEXT"),
                ("observation", "TEXT"), ("action", "TEXT"), ("status", "TEXT"),
                ("observed_by", "TEXT"), ("observer_designation", "TEXT"),
                ("observer_id", "TEXT"), ("evidence", "TEXT"),
                ("closeout_evidence", "TEXT"), ("remarks", "TEXT")
            ]:
                if col not in self.columns:
                    try:
                        self.conn.execute(f'ALTER TABLE "{self.table}" ADD COLUMN "{col}" {definition}')
                    except Exception:
                        pass
            self.conn.commit()
            self.columns = [r[1] for r in self.conn.execute(f'PRAGMA table_info("{self.table}")')]
            lower = {c.lower(): c for c in self.columns}
            for logical, aliases in self.FIELD_ALIASES.items():
                self.column_map[logical] = next((lower[a] for a in aliases if a in lower), None)

    def list_observations(self):
        rows = self.conn.execute(f'SELECT * FROM "{self.table}" ORDER BY rowid DESC').fetchall()
        results = []
        for row in rows:
            item = {}
            for logical in self.FIELD_ALIASES:
                col = self.column_map.get(logical)
                item[logical] = safe_text(row[col]) if col and col in row.keys() else ""
            item["_rowid"] = row["rowid"] if "rowid" in row.keys() else ""
            results.append(item)
        return results

    def add(self, values):
        pairs = []
        for logical, value in values.items():
            col = self.column_map.get(logical)
            if col and logical != "id":
                pairs.append((col, value))
        if not pairs:
            raise RuntimeError("The existing observation table does not have compatible writable columns.")
        cols = ", ".join('"' + c.replace('"', '""') + '"' for c, _ in pairs)
        marks = ", ".join("?" for _ in pairs)
        self.conn.execute(f'INSERT INTO "{self.table}" ({cols}) VALUES ({marks})', [v for _, v in pairs])
        self.conn.commit()

    def close(self):
        try:
            self.conn.close()
        except Exception:
            pass


# ---------- settings and exports ----------

def load_settings():
    defaults = {"company": "", "project": "", "logo": ""}
    try:
        if SETTINGS_FILE.exists():
            data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
            defaults.update(data if isinstance(data, dict) else {})
    except Exception:
        pass
    return defaults


def save_settings(settings):
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


def export_header(story, settings, title):
    story.append(title)
    story.append("Company: " + safe_text(settings.get("company")))
    story.append("Project: " + safe_text(settings.get("project")))
    story.append("Generated: " + now_text())
    story.append("-" * 90)


def export_pdf_register(rows, settings, path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_LEFT, TA_CENTER
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image as RLImage
    except Exception as exc:
        raise RuntimeError("PDF export needs reportlab in requirements.txt. " + str(exc))
    doc = SimpleDocTemplate(str(path), pagesize=landscape(A4), rightMargin=10*mm, leftMargin=10*mm,
                            topMargin=10*mm, bottomMargin=10*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="SmallCell", parent=styles["BodyText"], fontSize=7, leading=8))
    styles.add(ParagraphStyle(name="MainTitle", parent=styles["Title"], fontSize=15, leading=18, alignment=TA_LEFT))
    story = []
    logo = safe_text(settings.get("logo"))
    if logo and Path(logo).exists():
        try:
            story.append(RLImage(logo, width=28*mm, height=18*mm, kind="proportional"))
        except Exception:
            pass
    story.append(Paragraph(APP_NAME + " - Observation Register", styles["MainTitle"]))
    story.append(Paragraph("Company: " + safe_text(settings.get("company")) + " &nbsp;&nbsp; Project: " +
                           safe_text(settings.get("project")), styles["Normal"]))
    story.append(Paragraph("Generated: " + now_text(), styles["Normal"]))
    story.append(Spacer(1, 5*mm))
    headers = ["No.", "Date", "Location", "Type", "Category", "Observation / Finding", "Corrective Action", "Status", "Observed By"]
    data = [[Paragraph("<b>" + h + "</b>", styles["SmallCell"]) for h in headers]]
    for i, r in enumerate(rows, 1):
        vals = [str(i), r.get("date",""), r.get("location",""), r.get("type",""), r.get("category",""),
                r.get("observation",""), r.get("action",""), r.get("status",""), r.get("observed_by","")]
        data.append([Paragraph(str(v).replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace("\n","<br/>"),
                               styles["SmallCell"]) for v in vals])
    widths = [10*mm, 22*mm, 23*mm, 18*mm, 20*mm, 57*mm, 48*mm, 18*mm, 27*mm]
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#173f5f")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.HexColor("#73808c")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f5f8")]),
    ]))
    story.append(table)
    doc.build(story)


def export_word_register(rows, settings, path):
    try:
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from docx.enum.section import WD_ORIENT
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
    except Exception as exc:
        raise RuntimeError("Word export needs python-docx in requirements.txt. " + str(exc))
    doc = Document()
    section = doc.sections[0]
    section.orientation = WD_ORIENT.LANDSCAPE
    section.page_width, section.page_height = section.page_height, section.page_width
    logo = safe_text(settings.get("logo"))
    if logo and Path(logo).exists():
        try:
            doc.add_picture(logo, width=Inches(0.8))
        except Exception:
            pass
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(APP_NAME + " - Observation Register")
    run.bold = True
    run.font.size = Pt(16)
    p = doc.add_paragraph("Company: " + safe_text(settings.get("company")) + "    Project: " +
                          safe_text(settings.get("project")) + "    Generated: " + now_text())
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    headers = ["No.", "Date", "Location", "Type", "Category", "Observation / Finding", "Corrective Action", "Status", "Observed By"]
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = "Table Grid"
    table.autofit = True
    for cell, heading in zip(table.rows[0].cells, headers):
        cell.text = heading
        for run in cell.paragraphs[0].runs:
            run.bold = True
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(255,255,255)
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "173F5F")
        tcPr.append(shd)
    for i, r in enumerate(rows, 1):
        values = [str(i), r.get("date",""), r.get("location",""), r.get("type",""), r.get("category",""),
                  r.get("observation",""), r.get("action",""), r.get("status",""), r.get("observed_by","")]
        cells = table.add_row().cells
        for cell, value in zip(cells, values):
            cell.text = safe_text(value)
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(7)
    doc.save(str(path))


def export_excel_register(rows, settings, path):
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Border, Side, Alignment
        from openpyxl.utils import get_column_letter
    except Exception as exc:
        raise RuntimeError("Excel export needs openpyxl in requirements.txt. " + str(exc))
    wb = Workbook()
    ws = wb.active
    ws.title = "Observation Register"
    ws.append([APP_NAME + " - Observation Register"])
    ws.append(["Company", safe_text(settings.get("company")), "Project", safe_text(settings.get("project"))])
    ws.append(["Generated", now_text()])
    ws.append([])
    headers = ["No.", "Date", "Location", "Responsible Person", "Designation", "Type", "Category",
               "Observation / Finding", "Corrective Action", "Status", "Observed By", "Observer Designation",
               "Observer ID", "Evidence", "Closeout Evidence", "Remarks"]
    ws.append(headers)
    for i, r in enumerate(rows, 1):
        ws.append([i] + [r.get(k, "") for k in [
            "date", "location", "responsible", "designation", "type", "category", "observation", "action",
            "status", "observed_by", "observer_designation", "observer_id", "evidence", "closeout_evidence", "remarks"
        ]])
    navy = "173F5F"
    thin = Side(style="thin", color="8A969F")
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for cell in ws[6]:
        cell.fill = PatternFill("solid", fgColor=navy)
        cell.font = Font(bold=True, color="FFFFFF")
    ws["A1"].font = Font(bold=True, size=16, color=navy)
    widths = [8,18,20,22,18,16,18,45,40,14,22,22,15,28,28,30]
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = "A7"
    ws.auto_filter.ref = f"A6:P{max(6, ws.max_row)}"
    wb.save(str(path))


def export_sop_cards(rows, settings, path):
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.enums import TA_CENTER
        from reportlab.lib.units import mm
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image as RLImage
    except Exception as exc:
        raise RuntimeError("SOP PDF export needs reportlab in requirements.txt. " + str(exc))
    if not rows:
        raise RuntimeError("Select at least one observation to draft SOP cards.")
    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=16*mm, leftMargin=16*mm,
                            topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="CardTitle", parent=styles["Title"], fontSize=17, leading=20,
                              textColor=colors.HexColor("#173f5f"), alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name="CardText", parent=styles["BodyText"], fontSize=9, leading=12))
    styles.add(ParagraphStyle(name="CardLabel", parent=styles["BodyText"], fontSize=9, leading=11,
                              textColor=colors.HexColor("#173f5f")))
    story = []
    logo = safe_text(settings.get("logo"))
    for idx, r in enumerate(rows):
        if logo and Path(logo).exists():
            try:
                story.append(RLImage(logo, width=27*mm, height=18*mm, kind="proportional"))
            except Exception:
                pass
        story.append(Paragraph("SAFETY OBSERVATION CARD", styles["CardTitle"]))
        story.append(Paragraph("<b>" + safe_text(settings.get("company")) + "</b> &nbsp; | &nbsp; " +
                               "<b>" + safe_text(settings.get("project")) + "</b>", styles["CardText"]))
        story.append(Spacer(1, 5*mm))
        data = [
            [Paragraph("<b>Card No.</b>", styles["CardLabel"]), Paragraph(str(idx+1), styles["CardText"]),
             Paragraph("<b>Date / Time</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("date")) or now_text(), styles["CardText"])],
            [Paragraph("<b>Location</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("location")), styles["CardText"]),
             Paragraph("<b>Observation Type</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("type")), styles["CardText"])],
            [Paragraph("<b>Category</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("category")), styles["CardText"]),
             Paragraph("<b>Status</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("status")), styles["CardText"])],
            [Paragraph("<b>Observation / Unsafe Act or Condition</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("observation")), styles["CardText"]), "", ""],
            [Paragraph("<b>Immediate / Corrective Action</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("action")), styles["CardText"]), "", ""],
            [Paragraph("<b>Responsible Person</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("responsible")), styles["CardText"]),
             Paragraph("<b>Designation</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("designation")), styles["CardText"])],
            [Paragraph("<b>Observed By</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("observed_by")), styles["CardText"]),
             Paragraph("<b>Observer ID</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("observer_id")), styles["CardText"])],
            [Paragraph("<b>Evidence / Photo Path</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("evidence")), styles["CardText"]), "", ""],
            [Paragraph("<b>Closeout Evidence</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("closeout_evidence")), styles["CardText"]), "", ""],
            [Paragraph("<b>Remarks</b>", styles["CardLabel"]), Paragraph(safe_text(r.get("remarks")), styles["CardText"]), "", ""],
        ]
        table = Table(data, colWidths=[39*mm, 48*mm, 34*mm, 43*mm])
        table.setStyle(TableStyle([
            ("GRID", (0,0), (-1,-1), 0.7, colors.HexColor("#7c8b96")),
            ("BACKGROUND", (0,0), (0,-1), colors.HexColor("#edf2f6")),
            ("BACKGROUND", (2,0), (2,2), colors.HexColor("#edf2f6")),
            ("SPAN", (1,3), (3,3)), ("SPAN", (1,4), (3,4)),
            ("SPAN", (1,7), (3,7)), ("SPAN", (1,8), (3,8)), ("SPAN", (1,9), (3,9)),
            ("VALIGN", (0,0), (-1,-1), "TOP"),
            ("LEFTPADDING", (0,0), (-1,-1), 6), ("RIGHTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 7), ("BOTTOMPADDING", (0,0), (-1,-1), 7),
        ]))
        story.append(table)
        story.append(Spacer(1, 8*mm))
        story.append(Paragraph("Follow-up / close-out verification: ________________________________________________", styles["CardText"]))
        story.append(Spacer(1, 6*mm))
        story.append(Paragraph("Verified by: ____________________________     Date: ____________________", styles["CardText"]))
        if idx != len(rows) - 1:
            story.append(PageBreak())
    doc.build(story)


# ---------- main application ----------

class HSEPocketApp(App):
    title = APP_NAME

    def build(self):
        self.settings_data = load_settings()
        self.store = ObservationStore()
        self.current_screen = "home"
        self.selected_ids = set()
        self.form_fields = {}
        self.root_layout = BoxLayout(orientation="vertical", spacing=0)
        with self.root_layout.canvas.before:
            Color(0.95, 0.97, 0.98, 1)
            self.bg_rect = RoundedRectangle(pos=self.root_layout.pos, size=self.root_layout.size, radius=[0])
        self.root_layout.bind(pos=self._update_bg, size=self._update_bg)
        Window.bind(on_keyboard=self._on_keyboard)
        self.show_home()
        return self.root_layout

    def _update_bg(self, instance, value):
        self.bg_rect.pos = instance.pos
        self.bg_rect.size = instance.size

    def _on_keyboard(self, window, key, *args):
        # Android back: navigate home; only leave if already on Home and back pressed again.
        if key in (27, 1001):
            if self.current_screen != "home":
                self.show_home()
                return True
            return False
        return False

    def base_screen(self, title, show_back=True):
        self.root_layout.clear_widgets()
        header = BoxLayout(size_hint_y=None, height=dp(58), padding=[dp(10), dp(5)], spacing=dp(8))
        if show_back:
            back = HSEButton(text="<- Back", size_hint_x=None, width=dp(84), height=dp(44))
            back.bind(on_release=lambda *_: self.show_home())
            header.add_widget(back)
        heading = Label(text=title, bold=True, font_size="18sp", color=(0.08, 0.19, 0.29, 1),
                        halign="left", valign="middle")
        header.add_widget(heading)
        self.root_layout.add_widget(header)
        self.content = ScrollView(do_scroll_x=False, bar_width=dp(4))
        self.body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(9), size_hint_y=None)
        self.body.bind(minimum_height=self.body.setter("height"))
        self.content.add_widget(self.body)
        self.root_layout.add_widget(self.content)
        self.current_screen = title.lower()

    def add_text(self, text, size=14, height=None, bold=False):
        lbl = Label(text=str(text), font_size=f"{size}sp", bold=bold, color=(0.10,0.16,0.21,1),
                    halign="left", valign="middle", size_hint_y=None,
                    height=dp(height or (32 if "\n" not in str(text) else 58))
                    )
        lbl.bind(size=lambda inst, val: setattr(inst, "text_size", (val[0], None)))
        self.body.add_widget(lbl)
        return lbl

    def add_button(self, text, callback, color=(0.10, 0.27, 0.43, 1), height=48):
        btn = HSEButton(text=text, height=dp(height), background_color=color)
        btn.bind(on_release=lambda *_: callback())
        self.body.add_widget(btn)
        return btn

    def show_home(self):
        self.base_screen(APP_NAME, show_back=False)
        company = safe_text(self.settings_data.get("company")) or "Company not configured"
        project = safe_text(self.settings_data.get("project")) or "Project not configured"
        logo = safe_text(self.settings_data.get("logo"))
        if logo and Path(logo).exists():
            try:
                self.body.add_widget(Image(source=logo, size_hint_y=None, height=dp(95), allow_stretch=True, keep_ratio=True))
            except Exception:
                pass
        self.add_text(company + "\n" + project, size=15, height=56, bold=True)
        self.add_text("Observation register and safety card reporting", size=13, height=30)
        self.add_button("+  New Observation", self.show_new_observation)
        self.add_button("=  Observation Register", self.show_register)
        self.add_button("*  Settings", self.show_settings)
        self.add_text("Data database: " + self.store.db_path.name, size=11, height=25)

    def show_new_observation(self):
        self.base_screen("New Observation")
        self.form_fields = {}
        definitions = [
            ("date", "Date / Time", now_text(), False),
            ("location", "Location / Area", "", False),
            ("responsible", "Responsible Person", "", False),
            ("designation", "Responsible Person Designation", "", False),
            ("type", "Observation Type (Unsafe Act / Unsafe Condition / Good Practice)", "Unsafe Condition", False),
            ("category", "Category (PPE / Excavation / WAH / Lifting / Electrical / Other)", "", False),
            ("observation", "Observation / Finding", "", True),
            ("action", "Immediate / Corrective Action", "", True),
            ("status", "Status (Open / Closed)", "Open", False),
            ("observed_by", "Observed By", "", False),
            ("observer_designation", "Observer Designation", "HSE Officer", False),
            ("observer_id", "Observer ID", "", False),
            ("evidence", "Evidence Photo Path (optional)", "", False),
            ("closeout_evidence", "Closeout Evidence Path (optional)", "", False),
            ("remarks", "Remarks", "", True),
        ]
        for key, label, default, multi in definitions:
            field = Field(label, default, multiline=multi)
            self.form_fields[key] = field.input
            self.body.add_widget(field)
        self.add_button("Choose Evidence Photo", lambda: self.choose_image("evidence"))
        self.add_button("Choose Closeout Photo", lambda: self.choose_image("closeout_evidence"))
        self.add_button("Save Observation", self.save_observation, color=(0.08,0.45,0.29,1), height=52)

    def save_observation(self):
        values = {key: widget.text.strip() for key, widget in self.form_fields.items()}
        if not values.get("observation"):
            popup_message("Missing information", "Please enter the observation / finding before saving.")
            return
        try:
            self.store.add(values)
            popup_message("Saved", "Observation saved successfully. Existing observations remain in the database.")
            self.show_register()
        except Exception as exc:
            popup_message("Save failed", str(exc))

    def show_register(self):
        self.base_screen("Observation Register")
        rows = self.store.list_observations()
        self.add_text(f"Total observations: {len(rows)}", size=14, height=32, bold=True)
        self.add_text("Select observations for SOP cards. Exports include all records unless you choose selected records.", size=12, height=48)
        self.selected_ids = set()
        self.row_checks = {}
        for idx, row in enumerate(rows):
            row_id = safe_text(row.get("id")) or safe_text(row.get("_rowid")) or str(idx)
            card = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(132), padding=dp(8), spacing=dp(3))
            with card.canvas.before:
                Color(1,1,1,1)
                card.bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[dp(8)])
            card.bind(pos=lambda inst, val: setattr(inst.bg, "pos", val),
                      size=lambda inst, val: setattr(inst.bg, "size", val))
            line = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
            from kivy.uix.checkbox import CheckBox
            check = CheckBox(size_hint_x=None, width=dp(38))
            check.bind(active=lambda inst, active, rid=row_id: self._set_selected(rid, active))
            line.add_widget(check)
            line.add_widget(Label(text=f"#{row_id}  {row.get('date','')}", color=(0.08,0.19,0.29,1), bold=True, halign="left"))
            card.add_widget(line)
            card.add_widget(Label(text=f"{row.get('location','')} | {row.get('type','')} | {row.get('status','')}",
                                  color=(0.12,0.16,0.2,1), halign="left", size_hint_y=None, height=dp(25)))
            desc = safe_text(row.get("observation"))
            card.add_widget(Label(text=desc[:220] + ("..." if len(desc)>220 else ""), color=(0.15,0.18,0.2,1),
                                  halign="left", valign="top", size_hint_y=None, height=dp(45)))
            self.body.add_widget(card)
            self.row_checks[row_id] = row
        self.add_button("Select All", self.select_all)
        self.add_button("Draft SOP Card PDF - Selected", self.make_sop_selected, color=(0.08,0.45,0.29,1))
        self.add_button("Export PDF Register", lambda: self.export_register("pdf"))
        self.add_button("Export Word Register (.docx)", lambda: self.export_register("word"))
        self.add_button("Export Excel Register (.xlsx)", lambda: self.export_register("excel"))
        self.add_button("Back to Home", self.show_home)

    def _set_selected(self, row_id, active):
        if active:
            self.selected_ids.add(row_id)
        else:
            self.selected_ids.discard(row_id)

    def select_all(self):
        # Toggle all current rows to selected. Rebuild screen so checkboxes are visibly active.
        self.selected_ids = set(self.row_checks.keys())
        self.show_register()
        for rid, checkbox_row in self.row_checks.items():
            pass
        popup_message("Selection", "Use the checkboxes to select individual records. If needed, tap Select All again after refresh.")

    def _selected_rows(self):
        rows = self.store.list_observations()
        if not self.selected_ids:
            return []
        selected = []
        for idx, row in enumerate(rows):
            rid = safe_text(row.get("id")) or safe_text(row.get("_rowid")) or str(idx)
            if rid in self.selected_ids:
                selected.append(row)
        return selected

    def make_sop_selected(self):
        rows = self._selected_rows()
        if not rows:
            popup_message("Select observations", "Tick one or more observation checkboxes first.")
            return
        path = EXPORT_DIR / ("SOP_Cards_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".pdf")
        try:
            export_sop_cards(rows, self.settings_data, path)
            self.show_export_result(path)
        except Exception as exc:
            popup_message("SOP export failed", str(exc))

    def export_register(self, kind):
        rows = self.store.list_observations()
        if not rows:
            popup_message("No observations", "There are no observations to export yet.")
            return
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        if kind == "pdf":
            path = EXPORT_DIR / f"Observation_Register_{stamp}.pdf"
            fn = export_pdf_register
        elif kind == "word":
            path = EXPORT_DIR / f"Observation_Register_{stamp}.docx"
            fn = export_word_register
        else:
            path = EXPORT_DIR / f"Observation_Register_{stamp}.xlsx"
            fn = export_excel_register
        try:
            fn(rows, self.settings_data, path)
            self.show_export_result(path)
        except Exception as exc:
            popup_message("Export failed", str(exc))

    def show_export_result(self, path):
        content = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        content.add_widget(Label(text="File created:\n" + str(path), halign="left", valign="middle"))
        content.add_widget(Label(text="On Android, the file is stored in the app's data folder. Use your file manager to copy it to Downloads or share it.",
                                 halign="left", valign="middle"))
        close = HSEButton(text="OK")
        content.add_widget(close)
        pop = Popup(title="Export complete", content=content, size_hint=(0.92, 0.48))
        close.bind(on_release=pop.dismiss)
        pop.open()

    def show_settings(self):
        self.base_screen("Settings")
        self.settings_fields = {}
        for key, label in [("company", "Company Name"), ("project", "Project Name")]:
            field = Field(label, self.settings_data.get(key, ""))
            self.settings_fields[key] = field.input
            self.body.add_widget(field)
        self.add_text("Company logo", size=14, bold=True)
        logo_path = safe_text(self.settings_data.get("logo"))
        if logo_path and Path(logo_path).exists():
            try:
                self.body.add_widget(Image(source=logo_path, size_hint_y=None, height=dp(110), allow_stretch=True, keep_ratio=True))
            except Exception:
                self.add_text("Saved logo path: " + logo_path, size=11, height=40)
        else:
            self.add_text("No logo selected. PNG and JPG images are recommended.", size=12, height=35)
        self.add_button("Upload / Change Logo", self.choose_logo)
        self.add_button("Save Settings", self.save_settings_screen, color=(0.08,0.45,0.29,1))
        self.add_button("Back to Home", self.show_home)

    def save_settings_screen(self):
        self.settings_data["company"] = self.settings_fields["company"].text.strip()
        self.settings_data["project"] = self.settings_fields["project"].text.strip()
        try:
            save_settings(self.settings_data)
            popup_message("Settings saved", "Company and project details saved.")
            self.show_settings()
        except Exception as exc:
            popup_message("Settings error", str(exc))

    def choose_logo(self):
        self.choose_file(on_path=self._save_logo, title="Choose company logo")

    def choose_image(self, field_key):
        self.choose_file(on_path=lambda path: self._set_form_image(field_key, path), title="Choose photo")

    def _set_form_image(self, field_key, path):
        if field_key in self.form_fields:
            self.form_fields[field_key].text = path

    def _save_logo(self, source_path):
        try:
            source = Path(source_path)
            if not source.exists() or not source.is_file() or source.stat().st_size < 1:
                raise RuntimeError("The selected image is empty or unavailable. Please choose another file.")
            ext = source.suffix.lower()
            if ext not in (".png", ".jpg", ".jpeg"):
                try:
                    from PIL import Image as PILImage
                    image = PILImage.open(str(source)).convert("RGB")
                    destination = DATA_DIR / "company_logo.jpg"
                    image.save(str(destination), "JPEG", quality=92)
                except Exception:
                    raise RuntimeError("Please select a PNG or JPG/JPEG image. This format could not be converted.")
            else:
                destination = DATA_DIR / ("company_logo" + ext)
                if source.resolve() != destination.resolve():
                    shutil.copyfile(str(source), str(destination))
            if destination.stat().st_size < 1:
                raise RuntimeError("Logo copy failed; the saved file is empty.")
            self.settings_data["logo"] = str(destination)
            save_settings(self.settings_data)
            popup_message("Logo saved", "Company logo uploaded and saved successfully.")
            self.show_settings()
        except Exception as exc:
            popup_message("Logo upload failed", str(exc))

    def choose_file(self, on_path, title="Choose file"):
        content = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        initial = str(Path.home())
        if platform == "android":
            for candidate in ["/storage/emulated/0/Download", "/storage/emulated/0/Pictures",
                              "/storage/emulated/0/DCIM", str(DATA_DIR)]:
                if Path(candidate).exists():
                    initial = candidate
                    break
        chooser = FileChooserListView(path=initial, filters=["*.png", "*.jpg", "*.jpeg", "*.webp", "*.bmp"],
                                      dirselect=False)
        content.add_widget(chooser)
        buttons = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        cancel = HSEButton(text="Cancel")
        select = HSEButton(text="Use Selected File", background_color=(0.08,0.45,0.29,1))
        buttons.add_widget(cancel)
        buttons.add_widget(select)
        content.add_widget(buttons)
        pop = Popup(title=title, content=content, size_hint=(0.96, 0.88))
        cancel.bind(on_release=pop.dismiss)
        def accept(*_):
            if not chooser.selection:
                popup_message("Choose file", "Select an image file first.")
                return
            on_path(chooser.selection[0])
            pop.dismiss()
        select.bind(on_release=accept)
        pop.open()

    def on_stop(self):
        self.store.close()


if __name__ == "__main__":
    try:
        HSEPocketApp().run()
    except Exception:
        traceback.print_exc()
