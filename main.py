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
from kivy.uix.screenmanager import ScreenManager, Screen


APP_NAME = "HSE Management System"


# ============================================================
# GENERAL HELPERS
# ============================================================

def current_date():
    return datetime.now().strftime("%Y-%m-%d")


def current_datetime():
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


def make_label(text="", size=14, bold=False, height=40):
    widget = Label(
        text=str(text),
        font_size=dp(size),
        bold=bold,
        size_hint_y=None,
        height=dp(height),
        halign="left",
        valign="middle",
    )

    widget.bind(
        width=lambda instance, value: setattr(
            instance,
            "text_size",
            (max(0, value - dp(5)), None),
        )
    )

    return widget


def make_input(hint="", multiline=False, height=45):
    return TextInput(
        hint_text=hint,
        multiline=multiline,
        size_hint_y=None,
        height=dp(height),
        padding=[dp(10), dp(8)],
    )


def make_button(text, height=50):
    return Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        font_size=dp(14),
    )


def show_message(title, message):
    outer = BoxLayout(
        orientation="vertical",
        spacing=dp(10),
        padding=dp(10),
    )

    scroll = ScrollView()

    label = Label(
        text=str(message),
        font_size=dp(14),
        size_hint_y=None,
        halign="left",
        valign="top",
    )

    label.bind(
        width=lambda instance, value: setattr(
            instance,
            "text_size",
            (max(0, value - dp(15)), None),
        )
    )

    label.texture_update()

    label.height = max(
        dp(120),
        label.texture_size[1] + dp(20),
    )

    scroll.add_widget(label)

    close_button = Button(
        text="Close",
        size_hint_y=None,
        height=dp(45),
    )

    outer.add_widget(scroll)
    outer.add_widget(close_button)

    popup = Popup(
        title=title,
        content=outer,
        size_hint=(0.92, 0.78),
        auto_dismiss=False,
    )

    close_button.bind(
        on_release=popup.dismiss
    )

    popup.open()


# ============================================================
# RTF EXPORT
# ============================================================

def rtf_escape(value):
    text = str(value or "")

    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{")
    text = text.replace("}", "\\}")

    result = []

    for char in text:
        number = ord(char)

        if number > 127:
            if number > 32767:
                number -= 65536

            result.append("\\u{}?".format(number))
        else:
            result.append(char)

    return "".join(result)


def create_rtf_file(filename, title, sections):
    lines = [
        r"{\rtf1\ansi\deff0",
        r"{\fonttbl{\f0 Arial;}}",
        r"\fs28\b " + rtf_escape(title) + r"\b0\par",
        r"\fs20",
    ]

    for heading, value in sections:
        lines.append(
            r"\b "
            + rtf_escape(heading)
            + r":\b0 "
            + rtf_escape(value)
            + r"\par"
        )

    lines.append("}")

    with open(filename, "w", encoding="utf-8") as file:
        file.write("\n".join(lines))


# ============================================================
# SIMPLE PURE PYTHON PDF EXPORT
# ============================================================

def pdf_escape(value):
    text = str(value or "")

    text = text.encode(
        "latin-1",
        errors="replace",
    ).decode("latin-1")

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

    lines = [str(title)]

    for heading, value in sections:
        value = str(value or "")

        wrapped = textwrap.wrap(
            value,
            width=82,
            break_long_words=True,
            break_on_hyphens=False,
        )

        if not wrapped:
            wrapped = [""]

        first = True

        for part in wrapped:
            if first:
                lines.append(
                    "{}: {}".format(
                        heading,
                        part,
                    )
                )
                first = False
            else:
                lines.append(
                    "    {}".format(part)
                )

    max_lines = 48
    pages = []
    current_page = []

    for line in lines:
        if len(current_page) >= max_lines:
            pages.append(current_page)
            current_page = []

        current_page.append(line)

    if current_page:
        pages.append(current_page)

    if not pages:
        pages = [[""]]

    objects = []

    # Object 1 - Catalog
    objects.append(
        "<< /Type /Catalog /Pages 2 0 R >>"
    )

    page_object_ids = []
    next_object_id = 3

    for _ in pages:
        page_object_ids.append(next_object_id)
        next_object_id += 2

    # Object 2 - Pages
    kids = " ".join(
        "{} 0 R".format(object_id)
        for object_id in page_object_ids
    )

    objects.append(
        "<< /Type /Pages /Kids [{}] /Count {} >>".format(
            kids,
            len(pages),
        )
    )

    # Font object
    font_object_id = next_object_id

    objects.append(
        "<< /Type /Font "
        "/Subtype /Type1 "
        "/BaseFont /Helvetica >>"
    )

    # Page objects
    for index, page_lines in enumerate(pages):
        page_object_id = page_object_ids[index]
        content_object_id = page_object_id + 1

        commands = [
            "BT",
            "/F1 {} Tf".format(font_size),
            "1 0 0 1 {} {} Tm".format(
                margin,
                page_height - margin,
            ),
        ]

        for line_index, line in enumerate(page_lines):
            if line_index > 0:
                commands.append(
                    "0 -{} Td".format(line_height)
                )

            commands.append(
                "({}) Tj".format(
                    pdf_escape(line)
                )
            )

        commands.append("ET")

        stream = "\n".join(commands)

        page_object = (
            "<< /Type /Page "
            "/Parent 2 0 R "
            "/MediaBox [0 0 {} {}] "
            "/Resources << "
            "/Font << /F1 {} 0 R >> "
            ">> "
            "/Contents {} 0 R >>"
        ).format(
            page_width,
            page_height,
            font_object_id,
            content_object_id,
        )

        content_object = (
            "<< /Length {} >>\n"
            "stream\n"
            "{}\n"
            "endstream"
        ).format(
            len(
                stream.encode(
                    "latin-1",
                    errors="replace",
                )
            ),
            stream,
        )

        objects.append(page_object)
        objects.append(content_object)

    pdf = bytearray()

    pdf.extend(b"%PDF-1.4\n")
    pdf.extend(b"%\xe2\xe3\xcf\xd3\n")

    offsets = [0]

    for object_number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))

        pdf.extend(
            "{} 0 obj\n".format(
                object_number
            ).encode("ascii")
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

    pdf.extend(
        b"0000000000 65535 f \n"
    )

    for offset in offsets[1:]:
        pdf.extend(
            "{:010d} 00000 n \n".format(
                offset
            ).encode("ascii")
        )

    trailer = (
        "trailer\n"
        "<< /Size {} /Root 1 0 R >>\n"
        "startxref\n"
        "{}\n"
        "%%EOF\n"
    ).format(
        len(objects) + 1,
        xref_position,
    )

    pdf.extend(
        trailer.encode("ascii")
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
                evidence TEXT,
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

        # Add evidence column to an older database
        try:
            cursor.execute(
                "ALTER TABLE observations "
                "ADD COLUMN evidence TEXT"
            )
        except sqlite3.OperationalError:
            pass

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
                evidence,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                data["evidence"],
                current_datetime(),
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
                current_datetime(),
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
                current_datetime(),
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
                current_datetime(),
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

    def count_where(self, table, field, value):
        allowed_tables = {
            "observations",
            "incidents",
            "audits",
            "capa",
        }

        allowed_fields = {
            "status",
        }

        if table not in allowed_tables:
            return 0

        if field not in allowed_fields:
            return 0

        cursor = self.connection.cursor()

        cursor.execute(
            "SELECT COUNT(*) FROM {} WHERE {} = ?".format(
                table,
                field,
            ),
            (value,),
        )

        row = cursor.fetchone()

        return row[0] if row else 0

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
                observed_by,
                evidence
            FROM observations
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()

    def get_incidents(self):
        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                date,
                location,
                incident_type,
                description,
                immediate_action,
                root_cause,
                corrective_action,
                status
            FROM incidents
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()

    def get_audits(self):
        cursor = self.connection.cursor()

        cursor.execute(
            """
            SELECT
                id,
                date,
                location,
                audit_type,
                auditor,
                findings,
                corrective_action,
                status
            FROM audits
            ORDER BY id DESC
            """
        )

        return cursor.fetchall()

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

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass


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

        database_path = os.path.join(
            self.app_folder,
            "hse_management.db",
        )

        self.db = Database(database_path)

        # ----------------------------------------------------
        # SCREEN MANAGER
        # ----------------------------------------------------

        self.sm = ScreenManager()

        self.dashboard_screen = Screen(
            name="dashboard"
        )

        self.observation_screen = Screen(
            name="observations"
        )

        self.incident_screen = Screen(
            name="incidents"
        )

        self.audit_screen = Screen(
            name="audits"
        )

        self.capa_screen = Screen(
            name="capa"
        )

        # ----------------------------------------------------
        # BUILD SCREENS
        # ----------------------------------------------------

        self.dashboard_screen.add_widget(
            self.build_dashboard()
        )

        self.observation_screen.add_widget(
            self.build_observations()
        )

        self.incident_screen.add_widget(
            self.build_incidents()
        )

        self.audit_screen.add_widget(
            self.build_audits()
        )

        self.capa_screen.add_widget(
            self.build_capa()
        )

        self.sm.add_widget(
            self.dashboard_screen
        )

        self.sm.add_widget(
            self.observation_screen
        )

        self.sm.add_widget(
            self.incident_screen
        )

        self.sm.add_widget(
            self.audit_screen
        )

        self.sm.add_widget(
            self.capa_screen
        )

        return self.sm

    # ========================================================
    # NAVIGATION
    # ========================================================

    def go_to(self, screen_name):
        if self.sm.has_screen(screen_name):
            self.sm.current = screen_name

            if screen_name == "dashboard":
                self.refresh_dashboard()

    def make_navigation(self):
        nav = BoxLayout(
            orientation="horizontal",
            size_hint_y=None,
            height=dp(58),
            spacing=dp(2),
            padding=[dp(2), dp(3)],
        )

        buttons = [
            ("Dashboard", "dashboard"),
            ("Observations", "observations"),
            ("Incidents", "incidents"),
            ("Audits", "audits"),
            ("CAPA", "capa"),
        ]

        for text, screen_name in buttons:
            button = Button(
                text=text,
                font_size=dp(11),
                size_hint_x=1,
            )

            button.bind(
                on_release=lambda instance,
                name=screen_name: self.go_to(name)
            )

            nav.add_widget(button)

        return nav

    def make_screen_layout(
        self,
        title,
        content,
    ):
        root = BoxLayout(
            orientation="vertical",
        )

        # Top title bar
        header = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(65),
            padding=[
                dp(12),
                dp(5),
            ],
        )

        header.add_widget(
            make_label(
                title,
                size=19,
                bold=True,
                height=55,
            )
        )

        root.add_widget(header)

        # Main content
        root.add_widget(content)

        # Always-visible navigation
        root.add_widget(
            self.make_navigation()
        )

        return root

    # ========================================================
    # DASHBOARD
    # ========================================================

    def build_dashboard(self):
        content = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10),
        )

        content.add_widget(
            make_label(
                "HSE MANAGEMENT SYSTEM",
                size=21,
                bold=True,
                height=45,
            )
        )

        content.add_widget(
            make_label(
                "Live HSE Dashboard",
                size=15,
                height=35,
            )
        )

        self.dashboard_grid = GridLayout(
            cols=2,
            spacing=dp(8),
            size_hint_y=None,
        )

        self.dashboard_grid.bind(
            minimum_height=
            self.dashboard_grid.setter("height")
        )

        scroll = ScrollView()

        scroll.add_widget(
            self.dashboard_grid
        )

        content.add_widget(scroll)

        refresh = make_button(
            "REFRESH DASHBOARD",
            52,
        )

        refresh.bind(
            on_release=lambda *_:
            self.refresh_dashboard()
        )

        content.add_widget(refresh)

        return self.make_screen_layout(
            "Dashboard",
            content,
        )

    def refresh_dashboard(self):
        if not hasattr(
            self,
            "dashboard_grid",
        ):
            return

        self.dashboard_grid.clear_widgets()

        observation_count = self.db.count(
            "observations"
        )

        incident_count = self.db.count(
            "incidents"
        )

        audit_count = self.db.count(
            "audits"
        )

        capa_count = self.db.count(
            "capa"
        )

        observation_open = self.db.count_where(
            "observations",
            "status",
            "Open",
        )

        observation_closed = self.db.count_where(
            "observations",
            "status",
            "Closed",
        )

        incident_open = self.db.count_where(
            "incidents",
            "status",
            "Open",
        )

        incident_closed = self.db.count_where(
            "incidents",
            "status",
            "Closed",
        )

        audit_open = self.db.count_where(
            "audits",
            "status",
            "Open",
        )

        audit_closed = self.db.count_where(
            "audits",
            "status",
            "Closed",
        )

        capa_open = self.db.count_where(
            "capa",
            "status",
            "Open",
        )

        capa_closed = self.db.count_where(
            "capa",
            "status",
            "Closed",
        )

        cards = [
            (
                "OBSERVATIONS",
                observation_count,
                "Open: {}\nClosed: {}".format(
                    observation_open,
                    observation_closed,
                ),
                "observations",
            ),
            (
                "INCIDENTS",
                incident_count,
                "Open: {}\nClosed: {}".format(
                    incident_open,
                    incident_closed,
                ),
                "incidents",
            ),
            (
                "AUDITS",
                audit_count,
                "Open: {}\nClosed: {}".format(
                    audit_open,
                    audit_closed,
                ),
                "audits",
            ),
            (
                "CAPA",
                capa_count,
                "Open: {}\nClosed: {}".format(
                    capa_open,
                    capa_closed,
                ),
                "capa",
            ),
        ]

        for title, number, detail, screen_name in cards:
            button = Button(
                size_hint_y=None,
                height=dp(145),
                background_normal="",
            )

            layout = BoxLayout(
                orientation="vertical",
                padding=dp(8),
                spacing=dp(2),
            )

            layout.add_widget(
                make_label(
                    title,
                    size=15,
                    bold=True,
                    height=35,
                )
            )

            layout.add_widget(
                make_label(
                    str(number),
                    size=28,
                    bold=True,
                    height=50,
                )
            )

            layout.add_widget(
                make_label(
                    detail,
                    size=12,
                    height=45,
                )
            )

            button.add_widget(layout)

            button.bind(
                on_release=lambda instance,
                name=screen_name:
                self.go_to(name)
            )

            self.dashboard_grid.add_widget(
                button
            )

    # ========================================================
    # OBSERVATIONS
    # ========================================================

    def build_observations(self):
        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=
            layout.setter("height")
        )

        layout.add_widget(
            make_label(
                "HSE INSPECTION / OBSERVATION",
                size=20,
                bold=True,
                height=50,
            )
        )

        self.obs_date = make_input("Date")
        self.obs_date.text = current_date()
        layout.add_widget(self.obs_date)

        self.obs_location = make_input(
            "Location *"
        )
        layout.add_widget(self.obs_location)

        self.obs_responsible = make_input(
            "Responsible Person"
        )
        layout.add_widget(self.obs_responsible)

        self.obs_responsible_designation = make_input(
            "Responsible Person Designation"
        )
        layout.add_widget(
            self.obs_responsible_designation
        )

        layout.add_widget(
            make_label(
                "Observation Type",
                bold=True,
                height=30,
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
            "Observation / Description *",
            multiline=True,
            height=120,
        )
        layout.add_widget(self.obs_text)

        self.obs_action = make_input(
            "Corrective Action / Action Required",
            multiline=True,
            height=120,
        )
        layout.add_widget(self.obs_action)

        layout.add_widget(
            make_label(
                "Status",
                bold=True,
                height=30,
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
                height=30,
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

        layout.add_widget(self.obs_category)

        self.obs_observed_by = make_input(
            "Observed By"
        )
        layout.add_widget(self.obs_observed_by)

        self.obs_observed_designation = make_input(
            "Observed By Designation"
        )
        layout.add_widget(
            self.obs_observed_designation
        )

        self.obs_observed_id = make_input(
            "Observed By ID Number"
        )
        layout.add_widget(
            self.obs_observed_id
        )

        self.obs_evidence = make_input(
            "Evidence / Photo Reference "
            "(optional)",
            multiline=True,
            height=70,
        )
        layout.add_widget(self.obs_evidence)

        save = make_button(
            "SAVE OBSERVATION",
            55,
        )

        save.bind(
            on_release=lambda *_:
            self.save_observation()
        )

        layout.add_widget(save)

        clear = make_button(
            "CLEAR FORM",
            48,
        )

        clear.bind(
            on_release=lambda *_:
            self.clear_observation()
        )

        layout.add_widget(clear)

        view = make_button(
            "VIEW SAVED OBSERVATIONS",
            50,
        )

        view.bind(
            on_release=lambda *_:
            self.view_observations()
        )

        layout.add_widget(view)

        scroll.add_widget(layout)

        return self.make_screen_layout(
            "Observations",
            scroll,
        )

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
            "date": self.obs_date.text.strip(),
            "location": self.obs_location.text.strip(),
            "responsible_person":
                self.obs_responsible.text.strip(),
            "responsible_designation":
                self.obs_responsible_designation.text.strip(),
            "observation_type":
                self.obs_type.text,
            "observation":
                self.obs_text.text.strip(),
            "corrective_action":
                self.obs_action.text.strip(),
            "status":
                self.obs_status.text,
            "hse_category":
                self.obs_category.text,
            "observed_by":
                self.obs_observed_by.text.strip(),
            "observed_by_designation":
                self.obs_observed_designation.text.strip(),
            "observed_by_id":
                self.obs_observed_id.text.strip(),
            "evidence":
                self.obs_evidence.text.strip(),
        }

        record_id = self.db.add_observation(
            data
        )

        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        base_name = (
            "Observation_{}_{}".format(
                record_id,
                timestamp,
            )
        )

        rtf_path = os.path.join(
            self.app_folder,
            base_name + ".rtf",
        )

        pdf_path = os.path.join(
            self.app_folder,
            base_name + ".pdf",
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
            ("Status", data["status"]),
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
            (
                "Evidence / Photo Reference",
                data["evidence"],
            ),
        ]

        export_error = ""

        try:
            create_rtf_file(
                rtf_path,
                "HSE Observation Report",
                sections,
            )

            create_pdf_file(
                pdf_path,
                "HSE Observation Report",
                sections,
            )

        except Exception as error:
            export_error = str(error)

        self.clear_observation()
        self.refresh_dashboard()

        if export_error:
            show_message(
                "Observation Saved",
                "Observation saved successfully.\n\n"
                "Record ID: {}\n\n"
                "Export error:\n{}".format(
                    record_id,
                    export_error,
                ),
            )
        else:
            show_message(
                "Observation Saved",
                "Observation saved successfully.\n\n"
                "Record ID: {}\n\n"
                "PDF created.\n"
                "RTF created.",
            )

    def clear_observation(self):
        self.obs_location.text = ""
        self.obs_responsible.text = ""
        self.obs_responsible_designation.text = ""
        self.obs_text.text = ""
        self.obs_action.text = ""
        self.obs_observed_by.text = ""
        self.obs_observed_designation.text = ""
        self.obs_observed_id.text = ""
        self.obs_evidence.text = ""

        self.obs_date.text = current_date()
        self.obs_type.text = "Unsafe Condition"
        self.obs_status.text = "Open"
        self.obs_category.text = "PPE"

    def view_observations(self):
        rows = self.db.get_observations()

        if not rows:
            show_message(
                "Observations",
                "No observations recorded.",
            )
            return

        output = []

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
                evidence,
            ) = row

            output.append(
                "ID: {}\n"
                "Date: {}\n"
                "Location: {}\n"
                "Type: {}\n"
                "Category: {}\n"
                "Observation: {}\n"
                "Action: {}\n"
                "Status: {}\n"
                "Observed By: {}\n"
                "Evidence: {}\n"
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
                    evidence or "",
                )
            )

        show_message(
            "Saved Observations",
            "\n".join(output),
        )

    # ========================================================
    # INCIDENTS
    # ========================================================

    def build_incidents(self):
        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=
            layout.setter("height")
        )

        layout.add_widget(
            make_label(
                "ACCIDENT / INCIDENT INVESTIGATION",
                size=20,
                bold=True,
                height=50,
            )
        )

        self.inc_date = make_input("Date")
        self.inc_date.text = current_date()
        layout.add_widget(self.inc_date)

        self.inc_location = make_input(
            "Location *"
        )
        layout.add_widget(self.inc_location)

        layout.add_widget(
            make_label(
                "Incident Classification",
                bold=True,
                height=30,
            )
        )

        self.inc_type = Spinner(
            text="Near Miss",
            values=[
                "Near Miss",
                "First Aid",
                "Medical Treatment",
                "Lost Time Injury",
                "Property Damage",
                "Environmental",
                "Fire",
                "Vehicle Incident",
                "Other",
            ],
            size_hint_y=None,
            height=45,
        )

        layout.add_widget(self.inc_type)

        self.inc_description = make_input(
            "Incident Description *",
            multiline=True,
            height=130,
        )
        layout.add_widget(self.inc_description)

        self.inc_immediate = make_input(
            "Immediate Action",
            multiline=True,
            height=110,
        )
        layout.add_widget(self.inc_immediate)

        self.inc_root = make_input(
            "Root Cause",
            multiline=True,
            height=110,
        )
        layout.add_widget(self.inc_root)

        self.inc_action = make_input(
            "Corrective Action",
            multiline=True,
            height=110,
        )
        layout.add_widget(self.inc_action)

        layout.add_widget(
            make_label(
                "Status",
                bold=True,
                height=30,
            )
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

        layout.add_widget(self.inc_status)

        save = make_button(
            "SAVE INCIDENT",
            55,
        )

        save.bind(
            on_release=lambda *_:
            self.save_incident()
        )

        layout.add_widget(save)

        clear = make_button(
            "CLEAR FORM",
            48,
        )

        clear.bind(
            on_release=lambda *_:
            self.clear_incident()
        )

        layout.add_widget(clear)

        view = make_button(
            "VIEW SAVED INCIDENTS",
            50,
        )

        view.bind(
            on_release=lambda *_:
            self.view_incidents()
        )

        layout.add_widget(view)

        scroll.add_widget(layout)

        return self.make_screen_layout(
            "Incidents",
            scroll,
        )

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
            "date": self.inc_date.text.strip(),
            "location": self.inc_location.text.strip(),
            "incident_type": self.inc_type.text,
            "description":
                self.inc_description.text.strip(),
            "immediate_action":
                self.inc_immediate.text.strip(),
            "root_cause":
                self.inc_root.text.strip(),
            "corrective_action":
                self.inc_action.text.strip(),
            "status":
                self.inc_status.text,
        }

        record_id = self.db.add_incident(
            data
        )

        self.clear_incident()
        self.refresh_dashboard()

        show_message(
            "Incident Saved",
            "Incident saved successfully.\n\n"
            "Record ID: {}".format(
                record_id
            ),
        )

    def clear_incident(self):
        self.inc_date.text = current_date()
        self.inc_location.text = ""
        self.inc_description.text = ""
        self.inc_immediate.text = ""
        self.inc_root.text = ""
        self.inc_action.text = ""
        self.inc_type.text = "Near Miss"
        self.inc_status.text = "Open"

    def view_incidents(self):
        rows = self.db.get_incidents()

        if not rows:
            show_message(
                "Incidents",
                "No incidents recorded.",
            )
            return

        output = []

        for row in rows:
            (
                record_id,
                date,
                location,
                incident_type,
                description,
                immediate_action,
                root_cause,
                corrective_action,
                status,
            ) = row

            output.append(
                "ID: {}\n"
                "Date: {}\n"
                "Location: {}\n"
                "Classification: {}\n"
                "Description: {}\n"
                "Immediate Action: {}\n"
                "Root Cause: {}\n"
                "Corrective Action: {}\n"
                "Status: {}\n"
                "------------------------------".format(
                    record_id,
                    date,
                    location,
                    incident_type,
                    description,
                    immediate_action,
                    root_cause,
                    corrective_action,
                    status,
                )
            )

        show_message(
            "Saved Incidents",
            "\n".join(output),
        )

    # ========================================================
    # AUDITS
    # ========================================================

    def build_audits(self):
        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=
            layout.setter("height")
        )

        layout.add_widget(
            make_label(
                "HSE AUDIT REGISTER",
                size=20,
                bold=True,
                height=50,
            )
        )

        self.audit_date = make_input("Date")
        self.audit_date.text = current_date()
        layout.add_widget(self.audit_date)

        self.audit_location = make_input(
            "Location *"
        )
        layout.add_widget(self.audit_location)

        self.audit_type = make_input(
            "Audit Type"
        )
        layout.add_widget(self.audit_type)

        self.audit_auditor = make_input(
            "Auditor"
        )
        layout.add_widget(self.audit_auditor)

        self.audit_findings = make_input(
            "Findings",
            multiline=True,
            height=130,
        )
        layout.add_widget(self.audit_findings)

        self.audit_action = make_input(
            "Corrective Action",
            multiline=True,
            height=110,
        )
        layout.add_widget(self.audit_action)

        layout.add_widget(
            make_label(
                "Status",
                bold=True,
                height=30,
            )
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

        layout.add_widget(self.audit_status)

        save = make_button(
            "SAVE AUDIT",
            55,
        )

        save.bind(
            on_release=lambda *_:
            self.save_audit()
        )

        layout.add_widget(save)

        clear = make_button(
            "CLEAR FORM",
            48,
        )

        clear.bind(
            on_release=lambda *_:
            self.clear_audit()
        )

        layout.add_widget(clear)

        view = make_button(
            "VIEW SAVED AUDITS",
            50,
        )

        view.bind(
            on_release=lambda *_:
            self.view_audits()
        )

        layout.add_widget(view)

        scroll.add_widget(layout)

        return self.make_screen_layout(
            "Audits",
            scroll,
        )

    def save_audit(self):
        if not self.audit_location.text.strip():
            show_message(
                "Required",
                "Please enter the audit location.",
            )
            return

        data = {
            "date": self.audit_date.text.strip(),
            "location":
                self.audit_location.text.strip(),
            "audit_type":
                self.audit_type.text.strip(),
            "auditor":
                self.audit_auditor.text.strip(),
            "findings":
                self.audit_findings.text.strip(),
            "corrective_action":
                self.audit_action.text.strip(),
            "status":
                self.audit_status.text,
        }

        record_id = self.db.add_audit(
            data
        )

        self.clear_audit()
        self.refresh_dashboard()

        show_message(
            "Audit Saved",
            "Audit saved successfully.\n\n"
            "Record ID: {}".format(
                record_id
            ),
        )

    def clear_audit(self):
        self.audit_date.text = current_date()
        self.audit_location.text = ""
        self.audit_type.text = ""
        self.audit_auditor.text = ""
        self.audit_findings.text = ""
        self.audit_action.text = ""
        self.audit_status.text = "Open"

    def view_audits(self):
        rows = self.db.get_audits()

        if not rows:
            show_message(
                "Audits",
                "No audits recorded.",
            )
            return

        output = []

        for row in rows:
            (
                record_id,
                date,
                location,
                audit_type,
                auditor,
                findings,
                corrective_action,
                status,
            ) = row

            output.append(
                "ID: {}\n"
                "Date: {}\n"
                "Location: {}\n"
                "Audit Type: {}\n"
                "Auditor: {}\n"
                "Findings: {}\n"
                "Corrective Action: {}\n"
                "Status: {}\n"
                "------------------------------".format(
                    record_id,
                    date,
                    location,
                    audit_type,
                    auditor,
                    findings,
                    corrective_action,
                    status,
                )
            )

        show_message(
            "Saved Audits",
            "\n".join(output),
        )

    # ========================================================
    # CAPA
    # ========================================================

    def build_capa(self):
        scroll = ScrollView()

        layout = GridLayout(
            cols=1,
            spacing=dp(8),
            padding=dp(12),
            size_hint_y=None,
        )

        layout.bind(
            minimum_height=
            layout.setter("height")
        )

        layout.add_widget(
            make_label(
                "CAPA REGISTER",
                size=20,
                bold=True,
                height=50,
            )
        )

        self.capa_date = make_input("Date")
        self.capa_date.text = current_date()
        layout.add_widget(self.capa_date)

        self.capa_source = make_input(
            "Source"
        )
        layout.add_widget(self.capa_source)

        self.capa_location = make_input(
            "Location"
        )
        layout.add_widget(self.capa_location)

        self.capa_finding = make_input(
            "Finding *",
            multiline=True,
            height=110,
        )
        layout.add_widget(self.capa_finding)

        self.capa_action = make_input(
            "Corrective / Preventive Action",
            multiline=True,
            height=110,
        )
        layout.add_widget(self.capa_action)

        self.capa_responsible = make_input(
            "Responsible Person"
        )
        layout.add_widget(self.capa_responsible)

        self.capa_target = make_input(
            "Target Date"
        )
        layout.add_widget(self.capa_target)

        layout.add_widget(
            make_label(
                "Status",
                bold=True,
                height=30,
            )
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

        layout.add_widget(self.capa_status)

        self.capa_closeout = make_input(
            "Closeout Date"
        )
        layout.add_widget(self.capa_closeout)

        save = make_button(
            "SAVE CAPA",
            55,
        )

        save.bind(
            on_release=lambda *_:
            self.save_capa()
        )

        layout.add_widget(save)

        clear = make_button(
            "CLEAR FORM",
            48,
        )

        clear.bind(
            on_release=lambda *_:
            self.clear_capa()
        )

        layout.add_widget(clear)

        export = make_button(
            "EXPORT CAPA TO CSV",
            55,
        )

        export.bind(
            on_release=lambda *_:
            self.export_capa_csv()
        )

        layout.add_widget(export)

        view = make_button(
            "VIEW CAPA REGISTER",
            50,
        )

        view.bind(
            on_release=lambda *_:
            self.view_capa()
        )

        layout.add_widget(view)

        layout.add_widget(
            make_label(
                "CSV export can be opened in "
                "Microsoft Excel or Google Sheets.",
                size=13,
                height=55,
            )
        )

        scroll.add_widget(layout)

        return self.make_screen_layout(
            "CAPA",
            scroll,
        )

    def save_capa(self):
        if not self.capa_finding.text.strip():
            show_message(
                "Required",
                "Please enter the finding.",
            )
            return

        data = {
            "date":
                self.capa_date.text.strip(),
            "source":
                self.capa_source.text.strip(),
            "location":
                self.capa_location.text.strip(),
            "finding":
                self.capa_finding.text.strip(),
            "action":
                self.capa_action.text.strip(),
            "responsible_person":
                self.capa_responsible.text.strip(),
            "target_date":
                self.capa_target.text.strip(),
            "status":
                self.capa_status.text,
            "closeout_date":
                self.capa_closeout.text.strip(),
        }

        record_id = self.db.add_capa(
            data
        )

        self.clear_capa()
        self.refresh_dashboard()

        show_message(
            "CAPA Saved",
            "CAPA saved successfully.\n\n"
            "Record ID: {}".format(
                record_id
            ),
        )

    def clear_capa(self):
        self.capa_date.text = current_date()
        self.capa_source.text = ""
        self.capa_location.text = ""
        self.capa_finding.text = ""
        self.capa_action.text = ""
        self.capa_responsible.text = ""
        self.capa_target.text = ""
        self.capa_closeout.text = ""
        self.capa_status.text = "Open"

    def export_capa_csv(self):
        rows = self.db.get_capa()

        if not rows:
            show_message(
                "Export",
                "No CAPA records available.",
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
                "CSV file created successfully.",
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

        output = []

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
                closeout_date,
            ) = row

            output.append(
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
                    closeout_date,
                )
            )

        show_message(
            "CAPA Register",
            "\n".join(output),
        )

    # ========================================================
    # APPLICATION CLOSE
    # ========================================================

    def on_stop(self):
        try:
            self.db.close()
        except Exception:
            pass


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    HSEManagementApp().run()