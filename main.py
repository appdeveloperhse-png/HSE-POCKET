import os
import csv
import sqlite3
import textwrap
from datetime import datetime

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.tabbedpanel import TabbedPanelItem


# ============================================================
# APPLICATION DIRECTORIES
# ============================================================

APP_NAME = "HSE Management System"


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def now_string():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def safe_filename(value):
    value = str(value or "file")
    result = ""

    for char in value:
        if char.isalnum() or char in ("-", "_"):
            result += char
        else:
            result += "_"

    return result[:80]


def make_label(text="", size=14, bold=False, height=None):
    label = Label(
        text=str(text),
        font_size=dp(size),
        bold=bold,
        halign="left",
        valign="middle",
        size_hint_y=None,
    )

    if height is None:
        label.height = dp(40)
    else:
        label.height = dp(height)

    label.text_size = (None, None)

    return label


def make_input(hint="", multiline=False, height=45):
    field = TextInput(
        hint_text=hint,
        multiline=multiline,
        size_hint_y=None,
        height=dp(height),
        padding=[dp(10), dp(8)],
    )
    return field


def show_message(title, message):
    content = BoxLayout(
        orientation="vertical",
        spacing=dp(10),
        padding=dp(10),
    )

    scroll = ScrollView()

    label = Label(
        text=str(message),
        font_size=dp(14),
        halign="left",
        valign="top",
        size_hint_y=None,
    )

    label.bind(
        width=lambda instance, value: setattr(
            instance,
            "text_size",
            (value - dp(10), None),
        )
    )

    label.texture_update()
    label.height = max(dp(100), label.texture_size[1] + dp(20))

    scroll.add_widget(label)

    close_button = Button(
        text="Close",
        size_hint_y=None,
        height=dp(45),
    )

    content.add_widget(scroll)
    content.add_widget(close_button)

    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.92, 0.75),
        auto_dismiss=False,
    )

    close_button.bind(on_release=popup.dismiss)

    popup.open()


# ============================================================
# SIMPLE RTF EXPORT
# ============================================================

def rtf_escape(text):
    text = str(text or "")

    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")

    result = []

    for char in text:
        code = ord(char)

        if code > 127:
            if code > 32767:
                code -= 65536

            result.append("\\u{}?".format(code))
        else:
            result.append(char)

    return "".join(result)


def create_rtf_file(filename, title, sections):
    lines = []

    lines.append(r"{\rtf1\ansi\deff0")
    lines.append(r"{\fonttbl{\f0 Arial;}}")
    lines.append(r"\fs28\b " + rtf_escape(title) + r"\b0\par")
    lines.append(r"\fs20")

    for heading, value in sections:
        lines.append(
            r"\b " + rtf_escape(heading) + r":\b0 "
            + rtf_escape(value)
            + r"\par"
        )

    lines.append("}")

    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


# ============================================================
# SIMPLE PDF EXPORT
# ============================================================

def pdf_escape(text):
    text = str(text or "")

    text = text.replace("\\", "\\\\")
    text = text.replace("(", "\\(")
    text = text.replace(")", "\\)")

    return text


def create_pdf_file(filename, title, sections):
    page_width = 595
    page_height = 842

    margin = 45
    font_size = 10
    line_height = 15

    lines = []

    lines.append(title)

    for heading, value in sections:
        value = str(value or "")

        wrapped = textwrap.wrap(
            value,
            width=82,
            replace_whitespace=False,
        )

        if not wrapped:
            wrapped = [""]

        first = True

        for part in wrapped:
            if first:
                lines.append("{}: {}".format(heading, part))
                first = False
            else:
                lines.append("    {}".format(part))

    pages = []

    current = []

    max_lines = 48

    for line in lines:
        if len(current) >= max_lines:
            pages.append(current)
            current = []

        current.append(line)

    if current:
        pages.append(current)

    objects = []

    # Object 1: Catalog
    objects.append(
        "<< /Type /Catalog /Pages 2 0 R >>"
    )

    # Object 2: Pages
    page_ids = []

    next_id = 3

    for _ in pages:
        page_ids.append(next_id)
        next_id += 2

    kids = " ".join(
        "{} 0 R".format(page_id)
        for page_id in page_ids
    )

    objects.append(
        "<< /Type /Pages /Kids [{}] /Count {} >>".format(
            kids,
            len(pages),
        )
    )

    font_object_id = next_id

    objects.append(
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )

    next_id += 1

    for index, page_lines in enumerate(pages):
        page_object_id = page_ids[index]
        content_object_id = page_object_id + 1

        stream_parts = []

        stream_parts.append(
            "BT /F1 {} Tf {} {} Td".format(
                font_size,
                margin,
                page_height - margin,
            )
        )

        first_line = True

        for line in page_lines:
            if not first_line:
                stream_parts.append(
                    "0 -{} Td".format(line_height)
                )

            stream_parts.append(
                "({}) Tj".format(
                    pdf_escape(line)
                )
            )

            first_line = False

        stream_parts.append("ET")

        stream = "\n".join(stream_parts)

        objects.append(
            "<< /Type /Page "
            "/Parent 2 0 R "
            "/MediaBox [0 0 {} {}] "
            "/Resources << /Font << /F1 {} 0 R >> >> "
            "/Contents {} 0 R >>".format(
                page_width,
                page_height,
                font_object_id,
                content_object_id,
            )
        )

        objects.append(
            "<< /Length {} >>\nstream\n{}\nendstream".format(
                len(stream.encode("latin-1", errors="replace")),
                stream,
            )
        )

    pdf = bytearray()
    pdf.extend(b"%PDF-1.4\n")
    pdf.extend(b"%\xe2\xe3\xcf\xd3\n")

    offsets = [0]

    for object_number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))

        pdf.extend(
            "{} 0 obj\n".format(object_number).encode(
                "ascii"
            )
        )

        pdf.extend(
            obj.encode(
                "latin-1",
                errors="replace",
            )
        )

        pdf.extend(b"\nendobj\n")

    xref_position = len(pdf)

    pdf.extend(
        "xref\n0 {}\n".format(
            len(objects) + 1
        ).encode("ascii")
    )

    pdf.extend(b"0000000000 65535 f \n")

    for offset in offsets[1:]:
        pdf.extend(
            "{:010d} 00000 n \n".format(
                offset
            ).encode("ascii")
        )

    pdf.extend(
        "trailer\n"
        "<< /Size {} /Root 1 0 R >>\n"
        "startxref\n"
        "{}\n"
        "%%EOF".format(
            len(objects) + 1,
            xref_position,
        ).encode("ascii")
    )

    with open(filename, "wb") as file:
        file.write(pdf)


# ============================================================
# DATABASE
# ============================================================

class Database:

    def __init__(self, database_path):
        self.database_path = database_path

        self.connection = sqlite3.connect(
            self.database_path
        )

        self.create_tables()

    def create_tables(self):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                location TEXT,
                responsible_person TEXT,
                responsible_designation TEXT,
                observation_type TEXT,
                observation TEXT,
                corrective_action TEXT,
                status TEXT,
                hse_category TEXT,
                observed_by TEXT,
                observed_by_designation TEXT,
                observed_by_id TEXT,
                created_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                location TEXT,
                incident_type TEXT,
                description TEXT,
                immediate_action TEXT,
                root_cause TEXT,
                corrective_action TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                location TEXT,
                audit_type TEXT,
                auditor TEXT,
                findings TEXT,
                corrective_action TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS capa (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                source TEXT,
                location TEXT,
                finding TEXT,
                action TEXT,
                responsible_person TEXT,
                target_date TEXT,
                status TEXT,
                closeout_date TEXT,
                created_at TEXT
            )
            """
        )

        self.connection.commit()

    def add_observation(self, data):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO observations (
                date,
                location,
                responsible_person,
                responsible_designation,
                observation_type,
                observation,
                corrective_action,
                status,
                hse_category,
                observed_by,
                observed_by_designation,
                observed_by_id,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"],
                data["location"],
                data["responsible_person"],
                data["responsible_designation"],
                data["observation_type"],
                data["observation"],
                data["corrective_action"],
                data["status"],
                data["hse_category"],
                data["observed_by"],
                data["observed_by_designation"],
                data["observed_by_id"],
                now_string(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def add_incident(self, data):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO incidents (
                date,
                location,
                incident_type,
                description,
                immediate_action,
                root_cause,
                corrective_action,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"],
                data["location"],
                data["incident_type"],
                data["description"],
                data["immediate_action"],
                data["root_cause"],
                data["corrective_action"],
                data["status"],
                now_string(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def add_audit(self, data):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO audits (
                date,
                location,
                audit_type,
                auditor,
                findings,
                corrective_action,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"],
                data["location"],
                data["audit_type"],
                data["auditor"],
                data["findings"],
                data["corrective_action"],
                data["status"],
                now_string(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def add_capa(self, data):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            INSERT INTO capa (
                date,
                source,
                location,
                finding,
                action,
                responsible_person,
                target_date,
                status,
                closeout_date,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["date"],
                data["source"],
                data["location"],
                data["finding"],
                data["action"],
                data["responsible_person"],
                data["target_date"],
                data["status"],
                data["closeout_date"],
                now_string(),
            ),
        )

        self.connection.commit()

        return cursor.lastrowid

    def count(self, table):

        allowed = {
            "observations",
            "incidents",
            "audits",
            "capa",
        }

        if table not in allowed:
            return 0

        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM {}".format(table)
        )

        row = cursor.fetchone()

        return row[0] if row else 0

    def get_capa(self):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                date,
                source,
                location,
                finding,
                action,
                responsible_person,
                target_date,
                status,
                closeout_date
            FROM capa
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()

    def get_observations(self):

        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                date,
                location,
                observation_type,
                observation,
                corrective_action,
                status,
                hse_category,
                observed_by
            FROM observations
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()

    def close(self):
        self.connection.close()


# ============================================================
# MAIN APPLICATION
# ============================================================

class HSEManagementApp(App):

    def build(self):

        self.title = APP_NAME

        self.app_folder = os.path.join(
            self.user_data_dir,
            "HSE_Management",
        )

        os.makedirs(
            self.app_folder,
            exist_ok=True,
        )

        database_file = os.path.join(
            self.app_folder,
            "hse_management.db",
        )

        self.db = Database(database_file)

        self.root_panel = TabbedPanel(
            do_default_tab=False,
            tab_width=dp(120),
        )

        self.dashboard_tab = TabbedPanelItem(
            text="Dashboard"
        )

        self.observation_tab = TabbedPanelItem(
            text="Observations"
        )

        self.incident_tab = TabbedPanelItem(
            text="Incidents"
        )

        self.audit_tab = TabbedPanelItem(
            text="Audits"
        )

        self.capa_tab = TabbedPanelItem(
            text="CAPA"
        )

        self.dashboard_tab.add_widget(
            self.build_dashboard()
        )

        self.observation_tab.add_widget(
            self.build_observation_screen()
        )

        self.incident_tab.add_widget(
            self.build_incident_screen()
        )

        self.audit_tab.add_widget(
            self.build_audit_screen()
        )

        self.capa_tab.add_widget(
            self.build_capa_screen()
        )

        self.root_panel.add_widget(
            self.dashboard_tab
        )

        self.root_panel.add_widget(
            self.observation_tab
        )

        self.root_panel.add_widget(
            self.incident_tab
        )

        self.root_panel.add_widget(
            self.audit_tab
        )

        self.root_panel.add_widget(
            self.capa_tab
        )

        return self.root_panel

    # ========================================================
    # DASHBOARD
    # ========================================================

    def build_dashboard(self):

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(12),
        )

        title = make_label(
            "HSE MANAGEMENT SYSTEM",
            size=22,
            bold=True,
            height=60,
        )

        layout.add_widget(title)

        subtitle = make_label(
            "Safety Dashboard",
            size=16,
            height=40,
        )

        layout.add_widget(subtitle)

        self.dashboard_counts = GridLayout(
            cols=2,
            spacing=dp(10),
            size_hint_y=None,
        )

        self.dashboard_counts.bind(
            minimum_height=self.dashboard_counts.setter(
                "height"
            )
        )

        layout.add_widget(
            self.dashboard_counts
        )

        refresh = Button(
            text="Refresh Dashboard",
            size_hint_y=None,
            height=dp(50),
        )

        refresh.bind(
            on_release=lambda *_:
            self.refresh_dashboard()
        )

        layout.add_widget(refresh)

        info = make_label(
            "Use the tabs below to record observations, "
            "incidents, audits and CAPA actions.",
            size=14,
            height=70,
        )

        layout.add_widget(info)

        self.refresh_dashboard()

        return layout

    def refresh_dashboard(self):

        self.dashboard_counts.clear_widgets()

        records = [
            (
                "Observations",
                self.db.count("observations"),
            ),
            (
                "Incidents",
                self.db.count("incidents"),
            ),
            (
                "Audits",
                self.db.count("audits"),
            ),
            (
                "CAPA",
                self.db.count("capa"),
            ),
        ]

        for name, count in records:

            box = BoxLayout(
                orientation="vertical",
                size_hint_y=None,
                height=dp(100),
                padding=dp(10),
            )

            box.add_widget(
                make_label(
                    name,
                    size=16,
                    bold=True,
                    height=40,
                )
            )

            box.add_widget(
                make_label(
                    str(count),
                    size=28,
                    bold=True,
                    height=50,
                )
            )

            self.dashboard_counts.add_widget(
                box
            )

    # ========================================================
    # OBSERVATIONS
    # ========================================================

    def build_observation_screen(self):

        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=layout.setter(
                "height"
            )
        )

        layout.add_widget(
            make_label(
                "HSE INSPECTION / OBSERVATION",
                size=20,
                bold=True,
                height=55,
            )
        )

        self.obs_date = make_input(
            "Date",
            height=45,
        )

        self.obs_date.text = datetime.now().strftime(
            "%Y-%m-%d"
        )

        layout.add_widget(self.obs_date)

        self.obs_location = make_input(
            "Location",
        )

        layout.add_widget(self.obs_location)

        self.obs_responsible = make_input(
            "Responsible Person",
        )

        layout.add_widget(self.obs_responsible)

        self.obs_responsible_designation = make_input(
            "Responsible Person Designation",
        )

        layout.add_widget(
            self.obs_responsible_designation
        )

        layout.add_widget(
            make_label(
                "Observation Type",
                bold=True,
                height=32,
            )
        )

        self.obs_type = Spinner(
            text="Unsafe Condition",
            values=[
                "Unsafe Act",
                "Unsafe Condition",
                "Good Observation",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(self.obs_type)

        self.obs_text = make_input(
            "Observation",
            multiline=True,
            height=110,
        )

        layout.add_widget(self.obs_text)

        self.obs_action = make_input(
            "Corrective Action",
            multiline=True,
            height=110,
        )

        layout.add_widget(self.obs_action)

        layout.add_widget(
            make_label(
                "Status",
                bold=True,
                height=32,
            )
        )

        self.obs_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(self.obs_status)

        layout.add_widget(
            make_label(
                "HSE Category",
                bold=True,
                height=32,
            )
        )

        self.obs_category = Spinner(
            text="PPE",
            values=[
                "PPE",
                "Excavation",
                "Work at Height",
                "Lifting",
                "Electrical Hazard",
                "Confined Space",
                "Hot Work",
                "Fire Safety",
                "Scaffolding",
                "Housekeeping",
                "Slip / Trip / Fall",
                "Chemical Safety",
                "Vehicle Safety",
                "Plant & Equipment",
                "Environmental",
                "Emergency Preparedness",
                "Material Management",
                "Other",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(
            self.obs_category
        )

        self.obs_observed_by = make_input(
            "Observed By",
        )

        layout.add_widget(
            self.obs_observed_by
        )

        self.obs_observed_designation = make_input(
            "Observed By Designation",
        )

        layout.add_widget(
            self.obs_observed_designation
        )

        self.obs_observed_id = make_input(
            "Observed By ID Number",
        )

        layout.add_widget(
            self.obs_observed_id
        )

        button = Button(
            text="SAVE OBSERVATION",
            size_hint_y=None,
            height=dp(55),
        )

        button.bind(
            on_release=lambda *_:
            self.save_observation()
        )

        layout.add_widget(button)

        export_button = Button(
            text="View Saved Observations",
            size_hint_y=None,
            height=dp(50),
        )

        export_button.bind(
            on_release=lambda *_:
            self.view_observations()
        )

        layout.add_widget(export_button)

        scroll.add_widget(layout)

        return scroll

    def save_observation(self):

        if not self.obs_location.text.strip():
            show_message(
                "Required",
                "Please enter the location.",
            )
            return

        if not self.obs_text.text.strip():
            show_message(
                "Required",
                "Please enter the observation.",
            )
            return

        data = {
            "date": self.obs_date.text,
            "location": self.obs_location.text,
            "responsible_person":
                self.obs_responsible.text,
            "responsible_designation":
                self.obs_responsible_designation.text,
            "observation_type":
                self.obs_type.text,
            "observation":
                self.obs_text.text,
            "corrective_action":
                self.obs_action.text,
            "status":
                self.obs_status.text,
            "hse_category":
                self.obs_category.text,
            "observed_by":
                self.obs_observed_by.text,
            "observed_by_designation":
                self.obs_observed_designation.text,
            "observed_by_id":
                self.obs_observed_id.text,
        }

        record_id = self.db.add_observation(
            data
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename_base = (
            "Observation_{}_{}".format(
                record_id,
                timestamp,
            )
        )

        rtf_file = os.path.join(
            self.app_folder,
            filename_base + ".rtf",
        )

        pdf_file = os.path.join(
            self.app_folder,
            filename_base + ".pdf",
        )

        sections = [
            ("Record ID", record_id),
            ("Date", data["date"]),
            ("Location", data["location"]),
            (
                "Responsible Person",
                data["responsible_person"],
            ),
            (
                "Responsible Designation",
                data["responsible_designation"],
            ),
            (
                "Observation Type",
                data["observation_type"],
            ),
            (
                "HSE Category",
                data["hse_category"],
            ),
            (
                "Observation",
                data["observation"],
            ),
            (
                "Corrective Action",
                data["corrective_action"],
            ),
            (
                "Status",
                data["status"],
            ),
            (
                "Observed By",
                data["observed_by"],
            ),
            (
                "Observed By Designation",
                data["observed_by_designation"],
            ),
            (
                "Observed By ID",
                data["observed_by_id"],
            ),
        ]

        try:
            create_rtf_file(
                rtf_file,
                "HSE Observation Report",
                sections,
            )

            create_pdf_file(
                pdf_file,
                "HSE Observation Report",
                sections,
            )

            self.clear_observation_form()

            self.refresh_dashboard()

            show_message(
                "Saved",
                "Observation saved successfully.\n\n"
                "Record ID: {}\n\n"
                "RTF:\n{}\n\n"
                "PDF:\n{}".format(
                    record_id,
                    rtf_file,
                    pdf_file,
                ),
            )

        except Exception as error:

            show_message(
                "Saved With Export Error",
                "Observation was saved.\n\n"
                "Record ID: {}\n\n"
                "Export error:\n{}".format(
                    record_id,
                    error,
                ),
            )

    def clear_observation_form(self):

        self.obs_location.text = ""
        self.obs_responsible.text = ""
        self.obs_responsible_designation.text = ""
        self.obs_text.text = ""
        self.obs_action.text = ""
        self.obs_observed_by.text = ""
        self.obs_observed_designation.text = ""
        self.obs_observed_id.text = ""

    def view_observations(self):

        rows = self.db.get_observations()

        if not rows:

            show_message(
                "Observations",
                "No observations recorded.",
            )

            return

        text = []

        for row in rows:

            (
                record_id,
                date,
                location,
                observation_type,
                observation,
                corrective_action,
                status,
                category,
                observed_by,
            ) = row

            text.append(
                "ID: {}\n"
                "Date: {}\n"
                "Location: {}\n"
                "Type: {}\n"
                "Category: {}\n"
                "Observation: {}\n"
                "Action: {}\n"
                "Status: {}\n"
                "Observed By: {}\n"
                "------------------------------".format(
                    record_id,
                    date,
                    location,
                    observation_type,
                    category,
                    observation,
                    corrective_action,
                    status,
                    observed_by,
                )
            )

        show_message(
            "Saved Observations",
            "\n".join(text),
        )

    # ========================================================
    # INCIDENTS
    # ========================================================

    def build_incident_screen(self):

        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=layout.setter(
                "height"
            )
        )

        layout.add_widget(
            make_label(
                "INCIDENT INVESTIGATION",
                size=20,
                bold=True,
                height=55,
            )
        )

        self.inc_date = make_input(
            "Date",
        )

        self.inc_date.text = datetime.now().strftime(
            "%Y-%m-%d"
        )

        layout.add_widget(self.inc_date)

        self.inc_location = make_input(
            "Location",
        )

        layout.add_widget(self.inc_location)

        layout.add_widget(
            make_label(
                "Incident Type",
                bold=True,
                height=32,
            )
        )

        self.inc_type = Spinner(
            text="Near Miss",
            values=[
                "Near Miss",
                "First Aid",
                "Medical Treatment",
                "Property Damage",
                "Environmental",
                "Lost Time Injury",
                "Fire",
                "Vehicle Incident",
                "Other",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(self.inc_type)

        self.inc_description = make_input(
            "Incident Description",
            multiline=True,
            height=120,
        )

        layout.add_widget(
            self.inc_description
        )

        self.inc_immediate = make_input(
            "Immediate Action",
            multiline=True,
            height=100,
        )

        layout.add_widget(
            self.inc_immediate
        )

        self.inc_root = make_input(
            "Root Cause",
            multiline=True,
            height=100,
        )

        layout.add_widget(
            self.inc_root
        )

        self.inc_action = make_input(
            "Corrective Action",
            multiline=True,
            height=100,
        )

        layout.add_widget(
            self.inc_action
        )

        self.inc_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(
            self.inc_status
        )

        button = Button(
            text="SAVE INCIDENT",
            size_hint_y=None,
            height=dp(55),
        )

        button.bind(
            on_release=lambda *_:
            self.save_incident()
        )

        layout.add_widget(button)

        scroll.add_widget(layout)

        return scroll

    def save_incident(self):

        if not self.inc_location.text.strip():
            show_message(
                "Required",
                "Please enter the location.",
            )
            return

        if not self.inc_description.text.strip():
            show_message(
                "Required",
                "Please enter the incident description.",
            )
            return

        data = {
            "date": self.inc_date.text,
            "location": self.inc_location.text,
            "incident_type": self.inc_type.text,
            "description": self.inc_description.text,
            "immediate_action":
                self.inc_immediate.text,
            "root_cause":
                self.inc_root.text,
            "corrective_action":
                self.inc_action.text,
            "status":
                self.inc_status.text,
        }

        record_id = self.db.add_incident(
            data
        )

        self.inc_location.text = ""
        self.inc_description.text = ""
        self.inc_immediate.text = ""
        self.inc_root.text = ""
        self.inc_action.text = ""

        self.refresh_dashboard()

        show_message(
            "Saved",
            "Incident saved successfully.\n\n"
            "Record ID: {}".format(
                record_id
            ),
        )

    # ========================================================
    # AUDITS
    # ========================================================

    def build_audit_screen(self):

        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=layout.setter(
                "height"
            )
        )

        layout.add_widget(
            make_label(
                "HSE AUDIT REGISTER",
                size=20,
                bold=True,
                height=55,
            )
        )

        self.audit_date = make_input(
            "Date",
        )

        self.audit_date.text = datetime.now().strftime(
            "%Y-%m-%d"
        )

        layout.add_widget(
            self.audit_date
        )

        self.audit_location = make_input(
            "Location",
        )

        layout.add_widget(
            self.audit_location
        )

        self.audit_type = make_input(
            "Audit Type",
        )

        layout.add_widget(
            self.audit_type
        )

        self.audit_auditor = make_input(
            "Auditor",
        )

        layout.add_widget(
            self.audit_auditor
        )

        self.audit_findings = make_input(
            "Findings",
            multiline=True,
            height=120,
        )

        layout.add_widget(
            self.audit_findings
        )

        self.audit_action = make_input(
            "Corrective Action",
            multiline=True,
            height=100,
        )

        layout.add_widget(
            self.audit_action
        )

        self.audit_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(
            self.audit_status
        )

        button = Button(
            text="SAVE AUDIT",
            size_hint_y=None,
            height=dp(55),
        )

        button.bind(
            on_release=lambda *_:
            self.save_audit()
        )

        layout.add_widget(button)

        scroll.add_widget(layout)

        return scroll

    def save_audit(self):

        if not self.audit_location.text.strip():
            show_message(
                "Required",
                "Please enter the audit location.",
            )
            return

        data = {
            "date": self.audit_date.text,
            "location": self.audit_location.text,
            "audit_type": self.audit_type.text,
            "auditor": self.audit_auditor.text,
            "findings": self.audit_findings.text,
            "corrective_action":
                self.audit_action.text,
            "status": self.audit_status.text,
        }

        record_id = self.db.add_audit(
            data
        )

        self.audit_location.text = ""
        self.audit_type.text = ""
        self.audit_auditor.text = ""
        self.audit_findings.text = ""
        self.audit_action.text = ""

        self.refresh_dashboard()

        show_message(
            "Saved",
            "Audit saved successfully.\n\n"
            "Record ID: {}".format(
                record_id
            ),
        )

    # ========================================================
    # CAPA
    # ========================================================

    def build_capa_screen(self):

        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=layout.setter(
                "height"
            )
        )

        layout.add_widget(
            make_label(
                "CAPA REGISTER",
                size=20,
                bold=True,
                height=55,
            )
        )

        self.capa_date = make_input(
            "Date",
        )

        self.capa_date.text = datetime.now().strftime(
            "%Y-%m-%d"
        )

        layout.add_widget(
            self.capa_date
        )

        self.capa_source = make_input(
            "Source",
        )

        layout.add_widget(
            self.capa_source
        )

        self.capa_location = make_input(
            "Location",
        )

        layout.add_widget(
            self.capa_location
        )

        self.capa_finding = make_input(
            "Finding",
            multiline=True,
            height=100,
        )

        layout.add_widget(
            self.capa_finding
        )

        self.capa_action = make_input(
            "Corrective / Preventive Action",
            multiline=True,
            height=100,
        )

        layout.add_widget(
            self.capa_action
        )

        self.capa_responsible = make_input(
            "Responsible Person",
        )

        layout.add_widget(
            self.capa_responsible
        )

        self.capa_target = make_input(
            "Target Date",
        )

        layout.add_widget(
            self.capa_target
        )

        self.capa_status = Spinner(
            text="Open",
            values=[
                "Open",
                "In Progress",
                "Closed",
                "Overdue",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(
            self.capa_status
        )

        self.capa_closeout = make_input(
            "Closeout Date",
        )

        layout.add_widget(
            self.capa_closeout
        )

        save_button = Button(
            text="SAVE CAPA",
            size_hint_y=None,
            height=dp(55),
        )

        save_button.bind(
            on_release=lambda *_:
            self.save_capa()
        )

        layout.add_widget(
            save_button
        )

        export_button = Button(
            text="EXPORT CAPA TO CSV / EXCEL",
            size_hint_y=None,
            height=dp(55),
        )

        export_button.bind(
            on_release=lambda *_:
            self.export_capa_csv()
        )

        layout.add_widget(
            export_button
        )

        view_button = Button(
            text="VIEW CAPA REGISTER",
            size_hint_y=None,
            height=dp(50),
        )

        view_button.bind(
            on_release=lambda *_:
            self.view_capa()
        )

        layout.add_widget(
            view_button
        )

        note = make_label(
            "CSV files can be opened directly in "
            "Microsoft Excel or Google Sheets.",
            size=13,
            height=60,
        )

        layout.add_widget(note)

        scroll.add_widget(layout)

        return scroll

    def save_capa(self):

        if not self.capa_finding.text.strip():
            show_message(
                "Required",
                "Please enter the finding.",
            )
            return

        data = {
            "date": self.capa_date.text,
            "source": self.capa_source.text,
            "location": self.capa_location.text,
            "finding": self.capa_finding.text,
            "action": self.capa_action.text,
            "responsible_person":
                self.capa_responsible.text,
            "target_date": self.capa_target.text,
            "status": self.capa_status.text,
            "closeout_date":
                self.capa_closeout.text,
        }

        record_id = self.db.add_capa(
            data
        )

        self.capa_source.text = ""
        self.capa_location.text = ""
        self.capa_finding.text = ""
        self.capa_action.text = ""
        self.capa_responsible.text = ""
        self.capa_target.text = ""
        self.capa_closeout.text = ""

        self.refresh_dashboard()

        show_message(
            "Saved",
            "CAPA saved successfully.\n\n"
            "Record ID: {}".format(
                record_id
            ),
        )

    def export_capa_csv(self):

        rows = self.db.get_capa()

        if not rows:
            show_message(
                "Export",
                "There are no CAPA records to export.",
            )
            return

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        filename = os.path.join(
            self.app_folder,
            "CAPA_Register_{}.csv".format(
                timestamp
            ),
        )

        headers = [
            "ID",
            "Date",
            "Source",
            "Location",
            "Finding",
            "Action",
            "Responsible Person",
            "Target Date",
            "Status",
            "Closeout Date",
        ]

        try:

            with open(
                filename,
                "w",
                newline="",
                encoding="utf-8-sig",
            ) as file:

                writer = csv.writer(file)

                writer.writerow(headers)

                for row in rows:
                    writer.writerow(row)

            show_message(
                "Export Complete",
                "CAPA register exported successfully.\n\n"
                "CSV file:\n{}".format(
                    filename
                ),
            )

        except Exception as error:

            show_message(
                "Export Error",
                str(error),
            )

    def view_capa(self):

        rows = self.db.get_capa()

        if not rows:

            show_message(
                "CAPA",
                "No CAPA records available.",
            )

            return

        text = []

        for row in rows:

            (
                record_id,
                date,
                source,
                location,
                finding,
                action,
                responsible,
                target_date,
                status,
                closeout,
            ) = row

            text.append(
                "ID: {}\n"
                "Date: {}\n"
                "Source: {}\n"
                "Location: {}\n"
                "Finding: {}\n"
                "Action: {}\n"
                "Responsible: {}\n"
                "Target Date: {}\n"
                "Status: {}\n"
                "Closeout Date: {}\n"
                "------------------------------".format(
                    record_id,
                    date,
                    source,
                    location,
                    finding,
                    action,
                    responsible,
                    target_date,
                    status,
                    closeout,
                )
            )

        show_message(
            "CAPA Register",
            "\n".join(text),
        )

    # ========================================================
    # APPLICATION STOP
    # ========================================================

    def on_stop(self):

        try:
            self.db.close()
        except Exception:
            pass


# ============================================================
# START APPLICATION
# ============================================================

if __name__ == "__main__":
    HSEManagementApp().run()    content_object_number
        ).encode(
            "latin-1"
        )

        content_object = (
            "<< /Length {} >>\n"
            "stream\n"
        ).format(
            len(stream)
        ).encode(
            "latin-1"
        ) + stream + b"\nendstream"

        objects.append(
            page_object
        )

        objects.append(
            content_object
        )

    pdf = bytearray()

    pdf.extend(
        b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    )

    offsets = [0]

    for number, obj in enumerate(
        objects,
        start=1
    ):

        offsets.append(
            len(pdf)
        )

        pdf.extend(
            "{} 0 obj\n".format(
                number
            ).encode(
                "latin-1"
            )
        )

        pdf.extend(obj)

        pdf.extend(
            b"\nendobj\n"
        )

    xref_position = len(pdf)

    pdf.extend(
        "xref\n0 {}\n".format(
            len(objects) + 1
        ).encode(
            "latin-1"
        )
    )

    pdf.extend(
        b"0000000000 65535 f \n"
    )

    for offset in offsets[1:]:

        pdf.extend(
            "{:010d} 00000 n \n".format(
                offset
            ).encode(
                "latin-1"
            )
        )

    pdf.extend(
        "trailer\n<< /Size {} /Root 1 0 R >>\n".format(
            len(objects) + 1
        ).encode(
            "latin-1"
        )
    )

    pdf.extend(
        b"startxref\n"
    )

    pdf.extend(
        "{}\n".format(
            xref_position
        ).encode(
            "latin-1"
        )
    )

    pdf.extend(
        b"%%EOF"
    )

    with open(
        path,
        "wb"
    ) as file:

        file.write(pdf)


def export_stop_card_pdf(
    doc_no,
    category,
    obs_type,
    priority,
    description,
    action
):

    filename = safe_filename(
        "STOP_Card_{}.pdf".format(
            doc_no
        )
    )

    path = os.path.join(
        EXPORT_DIR,
        filename
    )

    lines = [
        "Document No: {}".format(
            doc_no
        ),
        "Category: {}".format(
            category
        ),
        "Observation Type: {}".format(
            obs_type
        ),
        "Priority: {}".format(
            priority
        ),
        "",
        "OBSERVATION",
        description,
        "",
        "CORRECTIVE ACTION",
        action,
        "",
        "Generated: {}".format(
            timestamp()
        )
    ]

    create_pdf_file(
        path,
        "HSE OBSERVATION & STOP CARD",
        lines
    )

    return path


# ============================================================
# EXCEL EXPORT
# ============================================================

def export_capa_excel():

    filename = "CAPA_Register.xlsx"

    path = os.path.join(
        EXPORT_DIR,
        filename
    )

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id,
            source,
            action_item,
            assignee,
            target_date,
            status,
            created_at
        FROM capa
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    workbook = openpyxl.Workbook()

    sheet = workbook.active

    sheet.title = "CAPA Register"

    sheet.append([
        "ID",
        "Source",
        "Action Item",
        "Assignee",
        "Target Date",
        "Status",
        "Created At"
    ])

    for row in rows:

        sheet.append(
            list(row)
        )

    sheet.freeze_panes = "A2"

    # Basic column widths
    widths = {
        "A": 10,
        "B": 22,
        "C": 45,
        "D": 25,
        "E": 18,
        "F": 15,
        "G": 22
    }

    for column, width in widths.items():

        sheet.column_dimensions[
            column
        ].width = width

    workbook.save(
        path
    )

    return path


# ============================================================
# MAIN APPLICATION
# ============================================================

class HSEApp(App):

    def build(self):

        self.title = "HSE Management System"

        Window.softinput_mode = "below_target"

        init_db()

        main_layout = BoxLayout(
            orientation="vertical"
        )

        header = Label(
            text="HSE MANAGEMENT SYSTEM",
            size_hint_y=None,
            height=dp(55),
            font_size="18sp",
            bold=True
        )

        main_layout.add_widget(
            header
        )

        self.tabs = TabbedPanel(
            do_default_tab=False,
            tab_width=dp(130)
        )

        # Dashboard

        dashboard_tab = TabbedPanelHeader(
            text="Dashboard"
        )

        dashboard_tab.content = (
            self.create_dashboard()
        )

        self.tabs.add_widget(
            dashboard_tab
        )

        # Observations

        observation_tab = TabbedPanelHeader(
            text="Observations"
        )

        observation_tab.content = (
            self.create_observation_view()
        )

        self.tabs.add_widget(
            observation_tab
        )

        # Incidents

        incident_tab = TabbedPanelHeader(
            text="Incidents"
        )

        incident_tab.content = (
            self.create_incident_view()
        )

        self.tabs.add_widget(
            incident_tab
        )

        # Audits

        audit_tab = TabbedPanelHeader(
            text="Audits"
        )

        audit_tab.content = (
            self.create_audit_view()
        )

        self.tabs.add_widget(
            audit_tab
        )

        # CAPA

        capa_tab = TabbedPanelHeader(
            text="CAPA"
        )

        capa_tab.content = (
            self.create_capa_view()
        )

        self.tabs.add_widget(
            capa_tab
        )

        main_layout.add_widget(
            self.tabs
        )

        return main_layout


# ============================================================
# DASHBOARD
# ============================================================

    def create_dashboard(self):

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(12)
        )

        self.dashboard_label = Label(
            text="Loading...",
            font_size="17sp"
        )

        layout.add_widget(
            self.dashboard_label
        )

        refresh = Button(
            text="Refresh Dashboard",
            size_hint_y=None,
            height=dp(50)
        )

        refresh.bind(
            on_release=lambda x:
            self.refresh_dashboard()
        )

        layout.add_widget(
            refresh
        )

        self.refresh_dashboard()

        return layout


    def refresh_dashboard(self):

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM observations"
        )

        observations = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM incidents"
        )

        incidents = cursor.fetchone()[0]

        cursor.execute(
            "SELECT COUNT(*) FROM audits"
        )

        audits = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*)
            FROM capa
            WHERE status != 'Closed'
        """)

        open_capa = cursor.fetchone()[0]

        conn.close()

        self.dashboard_label.text = (
            "Observations / STOP Cards: {}\n\n"
            "Incidents: {}\n\n"
            "Audit Findings: {}\n\n"
            "Open CAPA: {}".format(
                observations,
                incidents,
                audits,
                open_capa
            )
        )


# ============================================================
# OBSERVATION
# ============================================================

    def create_observation_view(self):

        scroll = ScrollView()

        grid = GridLayout(
            cols=2,
            spacing=dp(8),
            padding=dp(10),
            size_hint_y=None
        )

        grid.bind(
            minimum_height=grid.setter(
                "height"
            )
        )

        def label(text):

            return Label(
                text=text,
                size_hint_y=None,
                height=dp(45)
            )

        grid.add_widget(
            label("Category")
        )

        self.obs_cat = Spinner(
            text="PPE",
            values=[
                "PPE",
                "Work at Height",
                "Excavation",
                "Lifting",
                "Electrical",
                "Confined Space",
                "Hot Work",
                "Vehicle Safety",
                "Scaffolding",
                "Housekeeping",
                "Environmental",
                "Other"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.obs_cat
        )

        grid.add_widget(
            label("Observation Type")
        )

        self.obs_type = Spinner(
            text="Unsafe Condition",
            values=[
                "Unsafe Act",
                "Unsafe Condition",
                "Good Practice",
                "Near Miss",
                "Environmental"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.obs_type
        )

        grid.add_widget(
            label("Priority")
        )

        self.obs_priority = Spinner(
            text="Medium",
            values=[
                "Low",
                "Medium",
                "High",
                "Critical"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.obs_priority
        )

        grid.add_widget(
            label("Observation")
        )

        self.obs_desc = TextInput(
            multiline=True,
            size_hint_y=None,
            height=dp(120)
        )

        grid.add_widget(
            self.obs_desc
        )

        grid.add_widget(
            label("Corrective Action")
        )

        self.obs_action = TextInput(
            multiline=True,
            size_hint_y=None,
            height=dp(120)
        )

        grid.add_widget(
            self.obs_action
        )

        save = Button(
            text="SAVE + GENERATE REPORTS",
            size_hint_y=None,
            height=dp(55)
        )

        save.bind(
            on_release=self.save_observation
        )

        grid.add_widget(
            save
        )

        grid.add_widget(
            Label(text="")
        )

        scroll.add_widget(
            grid
        )

        return scroll


    def save_observation(self, instance):

        if not self.obs_desc.text.strip():

            self.show_popup(
                "Required",
                "Please enter the observation."
            )

            return

        doc_no = document_number(
            "HSE-OBS"
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO observations (
                doc_no,
                category,
                obs_type,
                priority,
                description,
                action,
                target_date,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            doc_no,
            self.obs_cat.text,
            self.obs_type.text,
            self.obs_priority.text,
            self.obs_desc.text,
            self.obs_action.text,
            "30 Days",
            "Open",
            timestamp()
        ))

        cursor.execute("""
            INSERT INTO capa (
                source,
                action_item,
                assignee,
                target_date,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doc_no,
            self.obs_action.text,
            "HSE Supervisor",
            "30 Days",
            "Open",
            timestamp()
        ))

        conn.commit()

        conn.close()

        try:

            rtf = export_stop_card_rtf(
                doc_no,
                self.obs_cat.text,
                self.obs_type.text,
                self.obs_priority.text,
                self.obs_desc.text,
                self.obs_action.text
            )

            pdf = export_stop_card_pdf(
                doc_no,
                self.obs_cat.text,
                self.obs_type.text,
                self.obs_priority.text,
                self.obs_desc.text,
                self.obs_action.text
            )

            self.refresh_dashboard()

            self.show_popup(
                "Saved",
                "Observation saved successfully.\n\n"
                "Word-compatible RTF:\n{}\n\n"
                "PDF:\n{}".format(
                    rtf,
                    pdf
                )
            )

        except Exception as error:

            self.refresh_dashboard()

            self.show_popup(
                "Saved - Export Error",
                "Observation was saved successfully.\n\n"
                "Report generation error:\n{}".format(
                    error
                )
            )


# ============================================================
# INCIDENT
# ============================================================

    def create_incident_view(self):

        scroll = ScrollView()

        grid = GridLayout(
            cols=2,
            spacing=dp(8),
            padding=dp(10),
            size_hint_y=None
        )

        grid.bind(
            minimum_height=grid.setter(
                "height"
            )
        )

        grid.add_widget(
            Label(
                text="Incident Title",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.inc_title = TextInput(
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.inc_title
        )

        grid.add_widget(
            Label(
                text="Location",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.inc_loc = TextInput(
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.inc_loc
        )

        grid.add_widget(
            Label(
                text="RCA Method",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.inc_rca_method = Spinner(
            text="5-Why Analysis",
            values=[
                "5-Why Analysis",
                "Fishbone / Ishikawa",
                "ICAM Method"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.inc_rca_method
        )

        grid.add_widget(
            Label(
                text="RCA Details",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.inc_rca_details = TextInput(
            multiline=True,
            size_hint_y=None,
            height=dp(160)
        )

        grid.add_widget(
            self.inc_rca_details
        )

        save = Button(
            text="SAVE INCIDENT",
            size_hint_y=None,
            height=dp(55)
        )

        save.bind(
            on_release=self.save_incident
        )

        grid.add_widget(
            save
        )

        grid.add_widget(
            Label(text="")
        )

        scroll.add_widget(
            grid
        )

        return scroll


    def save_incident(self, instance):

        if not self.inc_title.text.strip():

            self.show_popup(
                "Required",
                "Enter incident title."
            )

            return

        doc_no = document_number(
            "HSE-INC"
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO incidents (
                doc_no,
                title,
                date_time,
                location,
                rca_method,
                rca_details
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doc_no,
            self.inc_title.text,
            timestamp(),
            self.inc_loc.text,
            self.inc_rca_method.text,
            self.inc_rca_details.text
        ))

        conn.commit()

        conn.close()

        self.refresh_dashboard()

        self.show_popup(
            "Saved",
            "Incident recorded.\n\n{}".format(
                doc_no
            )
        )


# ============================================================
# AUDIT
# ============================================================

    def create_audit_view(self):

        scroll = ScrollView()

        grid = GridLayout(
            cols=2,
            spacing=dp(8),
            padding=dp(10),
            size_hint_y=None
        )

        grid.bind(
            minimum_height=grid.setter(
                "height"
            )
        )

        grid.add_widget(
            Label(
                text="Audit Type",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.audit_type = Spinner(
            text="Internal Audit",
            values=[
                "Internal Audit",
                "External Audit",
                "Certification",
                "Surveillance"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.audit_type
        )

        grid.add_widget(
            Label(
                text="ISO Standard",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.audit_iso = Spinner(
            text="ISO 45001",
            values=[
                "ISO 45001",
                "ISO 14001"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.audit_iso
        )

        grid.add_widget(
            Label(
                text="Finding",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.audit_finding = Spinner(
            text="Minor Nonconformity",
            values=[
                "Major Nonconformity",
                "Minor Nonconformity",
                "OFI",
                "Conformity"
            ],
            size_hint_y=None,
            height=dp(45)
        )

        grid.add_widget(
            self.audit_finding
        )

        grid.add_widget(
            Label(
                text="Finding Details",
                size_hint_y=None,
                height=dp(45)
            )
        )

        self.audit_details = TextInput(
            multiline=True,
            size_hint_y=None,
            height=dp(150)
        )

        grid.add_widget(
            self.audit_details
        )

        save = Button(
            text="SAVE AUDIT FINDING",
            size_hint_y=None,
            height=dp(55)
        )

        save.bind(
            on_release=self.save_audit
        )

        grid.add_widget(
            save
        )

        grid.add_widget(
            Label(text="")
        )

        scroll.add_widget(
            grid
        )

        return scroll


    def save_audit(self, instance):

        doc_no = document_number(
            "HSE-AUD"
        )

        conn = get_connection()

        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO audits (
                doc_no,
                audit_type,
                iso_standard,
                finding_type,
                details,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            doc_no,
            self.audit_type.text,
            self.audit_iso.text,
            self.audit_finding.text,
            self.audit_details.text,
            timestamp()
        ))

        conn.commit()

        conn.close()

        self.refresh_dashboard()

        self.show_popup(
            "Saved",
            "Audit finding recorded.\n\n{}".format(
                doc_no
            )
        )


# ============================================================
# CAPA
# ============================================================

    def create_capa_view(self):

        layout = BoxLayout(
            orientation="vertical",
            padding=dp(15),
            spacing=dp(12)
        )

        info = Label(
            text=(
                "CAPA Register\n\n"
                "Observation corrective actions are "
                "automatically added here."
            ),
            font_size="16sp"
        )

        layout.add_widget(
            info
        )

        export = Button(
            text="EXPORT CAPA TO EXCEL",
            size_hint_y=None,
            height=dp(55)
        )

        export.bind(
            on_release=self.export_excel
        )

        layout.add_widget(
            export
        )

        return layout


    def export_excel(self, instance):

        try:

            path = export_capa_excel()

            self.show_popup(
                "Export Complete",
                "Excel file created:\n\n{}".format(
                    path
                )
            )

        except Exception as error:

            self.show_popup(
                "Export Error",
                str(error)
            )


# ============================================================
# POPUP
# ============================================================

    def show_popup(
        self,
        title,
        message
    ):

        content = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(10)
        )

        text = Label(
            text=message
        )

        close = Button(
            text="OK",
            size_hint_y=None,
            height=dp(50)
        )

        content.add_widget(
            text
        )

        content.add_widget(
            close
        )

        popup = Popup(
            title=title,
            content=content,
            size_hint=(0.9, 0.55)
        )

        close.bind(
            on_release=popup.dismiss
        )

        popup.open()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    HSEApp().run()
