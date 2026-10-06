__version__ = "1.0.0"

import os
import sqlite3
from datetime import datetime

from kivy.app import App
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.tabbedpanel import TabbedPanel
from kivy.uix.tabbedpanel import TabbedPanelHeader
from kivy.uix.textinput import TextInput

import openpyxl


# ============================================================
# APPLICATION PATHS
# ============================================================

def get_app_directory():

    app = App.get_running_app()

    if app:
        base = app.user_data_dir
    else:
        base = os.path.expanduser("~")

    folder = os.path.join(
        base,
        "HSE_Management"
    )

    os.makedirs(folder, exist_ok=True)

    return folder


APP_DIR = get_app_directory()

DB_NAME = os.path.join(
    APP_DIR,
    "hse_management.db"
)

EXPORT_DIR = os.path.join(
    APP_DIR,
    "exports"
)

os.makedirs(
    EXPORT_DIR,
    exist_ok=True
)


# ============================================================
# DATABASE
# ============================================================

def get_connection():

    return sqlite3.connect(DB_NAME)


def init_db():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT,
            category TEXT,
            obs_type TEXT,
            priority TEXT,
            description TEXT,
            action TEXT,
            target_date TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incidents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT,
            title TEXT,
            date_time TEXT,
            location TEXT,
            rca_method TEXT,
            rca_details TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            doc_no TEXT,
            audit_type TEXT,
            iso_standard TEXT,
            finding_type TEXT,
            details TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS capa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            action_item TEXT,
            assignee TEXT,
            target_date TEXT,
            status TEXT,
            created_at TEXT
        )
    """)

    conn.commit()

    conn.close()


# ============================================================
# GENERAL HELPERS
# ============================================================

def timestamp():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def document_number(prefix):

    return "{}-{}".format(
        prefix,
        datetime.now().strftime(
            "%Y%m%d%H%M%S"
        )
    )


def safe_filename(value):

    characters = '<>:"/\\|?*'

    for char in characters:
        value = value.replace(
            char,
            "_"
        )

    return value


def clean_pdf_text(text):

    if text is None:
        return ""

    text = str(text)

    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u00a0": " ",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    result = ""

    for char in text:

        if ord(char) < 128:
            result += char
        else:
            result += "?"

    return result


# ============================================================
# RTF / WORD-COMPATIBLE EXPORT
# ============================================================

def rtf_escape(text):

    if text is None:
        return ""

    text = str(text)

    result = ""

    for char in text:

        code = ord(char)

        if char == "\\":
            result += r"\\"

        elif char == "{":
            result += r"\{"

        elif char == "}":
            result += r"\}"

        elif char == "\n":
            result += r"\line "

        elif code < 128:
            result += char

        else:

            if code > 32767:
                code -= 65536

            result += r"\u{}?".format(code)

    return result


def export_stop_card_rtf(
    doc_no,
    category,
    obs_type,
    priority,
    description,
    action
):

    filename = safe_filename(
        "STOP_Card_{}.rtf".format(
            doc_no
        )
    )

    path = os.path.join(
        EXPORT_DIR,
        filename
    )

    content = []

    content.append(
        r"{\rtf1\ansi\deff0"
    )

    content.append(
        r"{\fonttbl{\f0 Arial;}}"
    )

    content.append(
        r"\fs32\b HSE OBSERVATION & STOP CARD\b0\fs20\par"
    )

    content.append(
        r"\par"
    )

    content.append(
        r"\b Document No:\b0 "
        + rtf_escape(doc_no)
        + r"\par"
    )

    content.append(
        r"\b Category:\b0 "
        + rtf_escape(category)
        + r"\par"
    )

    content.append(
        r"\b Observation Type:\b0 "
        + rtf_escape(obs_type)
        + r"\par"
    )

    content.append(
        r"\b Priority:\b0 "
        + rtf_escape(priority)
        + r"\par"
    )

    content.append(
        r"\par\b Observation\b0\par"
    )

    content.append(
        rtf_escape(description)
        + r"\par"
    )

    content.append(
        r"\par\b Corrective Action\b0\par"
    )

    content.append(
        rtf_escape(action)
        + r"\par"
    )

    content.append(
        r"\par"
        r"\b Generated:\b0 "
        + rtf_escape(timestamp())
        + r"\par"
    )

    content.append("}")

    with open(
        path,
        "w",
        encoding="utf-8"
    ) as file:

        file.write(
            "\n".join(content)
        )

    return path


# ============================================================
# PURE PYTHON PDF EXPORT
# ============================================================

def pdf_escape(text):

    text = clean_pdf_text(text)

    text = text.replace(
        "\\",
        "\\\\"
    )

    text = text.replace(
        "(",
        "\\("
    )

    text = text.replace(
        ")",
        "\\)"
    )

    return text


def wrap_text(text, max_chars=95):

    text = clean_pdf_text(text)

    if not text:
        return [""]

    result = []

    paragraphs = text.split(
        "\n"
    )

    for paragraph in paragraphs:

        words = paragraph.split()

        if not words:
            result.append("")
            continue

        current = ""

        for word in words:

            if not current:

                current = word

            elif len(current) + 1 + len(word) <= max_chars:

                current += " " + word

            else:

                result.append(current)

                current = word

        if current:
            result.append(current)

    return result


def create_pdf_file(
    path,
    title,
    lines
):

    page_width = 595
    page_height = 842

    left = 40
    top = 800
    line_height = 16

    max_lines = 45

    pages = []

    current_page = []

    for line in lines:

        wrapped = wrap_text(
            line
        )

        for wrapped_line in wrapped:

            if len(current_page) >= max_lines:

                pages.append(
                    current_page
                )

                current_page = []

            current_page.append(
                wrapped_line
            )

    if current_page:

        pages.append(
            current_page
        )

    if not pages:

        pages = [[""]]

    objects = []

    # Catalog
    objects.append(
        b"<< /Type /Catalog /Pages 2 0 R >>"
    )

    # Pages object
    page_numbers = []

    for index in range(
        len(pages)
    ):
        page_numbers.append(
            4 + index * 2
        )

    kids = " ".join(
        "{} 0 R".format(number)
        for number in page_numbers
    )

    objects.append(
        "<< /Type /Pages /Kids [{}] /Count {} >>".format(
            kids,
            len(pages)
        ).encode("latin-1")
    )

    font_object_number = 3

    objects.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )

    for index, page_lines in enumerate(pages):

        page_object_number = 4 + index * 2

        content_object_number = 5 + index * 2

        commands = []

        commands.append(
            "BT"
        )

        commands.append(
            "/F1 16 Tf"
        )

        commands.append(
            "{} {} Td".format(
                left,
                top
            )
        )

        commands.append(
            "({}) Tj".format(
                pdf_escape(title)
            )
        )

        commands.append(
            "0 -28 Td"
        )

        commands.append(
            "/F1 10 Tf"
        )

        for line in page_lines:

            commands.append(
                "({}) Tj".format(
                    pdf_escape(line)
                )
            )

            commands.append(
                "0 -{} Td".format(
                    line_height
                )
            )

        commands.append(
            "ET"
        )

        stream = "\n".join(
            commands
        ).encode(
            "latin-1",
            errors="replace"
        )

        page_object = (
            "<< /Type /Page "
            "/Parent 2 0 R "
            "/MediaBox [0 0 595 842] "
            "/Resources << /Font << /F1 3 0 R >> >> "
            "/Contents {} 0 R >>"
        ).format(
            content_object_number
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
