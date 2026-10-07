# ============================================================
# HSE-POCKET
# Complete Kivy HSE Management System
# ============================================================

import os
import csv
import base64
import sqlite3
import html
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
from kivy.uix.image import Image


APP_NAME = "HSE-POCKET"

NAVY = (0.04, 0.10, 0.17, 1)
BLUE = (0.06, 0.32, 0.62, 1)
RED = (0.75, 0.10, 0.10, 1)
GREEN = (0.08, 0.50, 0.28, 1)
TEAL = (0.03, 0.46, 0.45, 1)
PURPLE = (0.40, 0.22, 0.60, 1)
ORANGE = (0.86, 0.45, 0.06, 1)

BG = (0.94, 0.95, 0.97, 1)
WHITE = (1, 1, 1, 1)
TEXT = (0.10, 0.13, 0.17, 1)
MUTED = (0.40, 0.44, 0.49, 1)


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def today():
    return datetime.now().strftime("%Y-%m-%d")


def make_label(text="", size=13, color=TEXT,
               bold=False, height=34):

    x = Label(
        text=str(text),
        size_hint_y=None,
        height=dp(height),
        font_size=dp(size),
        color=color,
        bold=bold,
        halign="left",
        valign="middle"
    )

    x.bind(
        width=lambda obj, value:
        setattr(
            obj,
            "text_size",
            (max(1, value - dp(6)), None)
        )
    )

    return x


def make_input(hint="", height=44, multiline=False):

    return TextInput(
        hint_text=hint,
        size_hint_y=None,
        height=dp(height),
        multiline=multiline,
        font_size=dp(13),
        padding=[dp(10), dp(9)],
        background_normal="",
        background_active="",
        background_color=WHITE,
        foreground_color=TEXT,
        hint_text_color=MUTED
    )


def make_button(text, color=BLUE, height=44, size=10):

    return Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_down="",
        background_color=color,
        color=WHITE,
        bold=True,
        font_size=dp(size)
    )


def show_message(title, message):

    box = BoxLayout(
        orientation="vertical",
        padding=dp(10),
        spacing=dp(8)
    )

    scroll = ScrollView()

    label = make_label(
        message,
        13,
        TEXT,
        False,
        100
    )

    label.size_hint_y = None

    label.bind(
        texture_size=lambda obj, value:
        setattr(
            obj,
            "height",
            max(dp(100), value[1] + dp(20))
        )
    )

    scroll.add_widget(label)
    box.add_widget(scroll)

    close_button = make_button(
        "CLOSE",
        NAVY,
        44
    )

    box.add_widget(close_button)

    popup = Popup(
        title=title,
        content=box,
        size_hint=(0.95, 0.82),
        auto_dismiss=False
    )

    close_button.bind(
        on_release=popup.dismiss
    )

    popup.open()


class Card(BoxLayout):

    def __init__(self, bg=WHITE, **kwargs):

        super().__init__(**kwargs)

        with self.canvas.before:

            self.card_color = Color(*bg)

            self.rectangle = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )

        self.bind(
            pos=self.update_card,
            size=self.update_card
        )

    def update_card(self, *args):

        self.rectangle.pos = self.pos
        self.rectangle.size = self.size


# ============================================================
# DATABASE
# ============================================================

class Database:

    def __init__(self, path):

        self.connection = sqlite3.connect(path)

        self.connection.execute(
            "PRAGMA foreign_keys=ON"
        )

        self.create_tables()

    def create_tables(self):

        c = self.connection

        c.execute("""
        CREATE TABLE IF NOT EXISTS settings(
            id INTEGER PRIMARY KEY,
            project_name TEXT,
            company_name TEXT,
            logo_path TEXT,
            updated_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS observations(
            id INTEGER PRIMARY KEY,
            date TEXT,
            location TEXT,
            responsible TEXT,
            designation TEXT,
            type TEXT,
            category TEXT,
            observation TEXT,
            action TEXT,
            status TEXT,
            observed_by TEXT,
            evidence TEXT,
            photo_path TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS incidents(
            id INTEGER PRIMARY KEY,
            date TEXT,
            time TEXT,
            location TEXT,
            project TEXT,
            activity TEXT,
            classification TEXT,
            severity TEXT,
            title TEXT,
            description TEXT,
            consequence TEXT,
            potential_consequence TEXT,
            people TEXT,
            injury TEXT,
            damage TEXT,
            environment TEXT,
            witnesses TEXT,
            immediate TEXT,
            evidence TEXT,
            investigator TEXT,
            team TEXT,
            scope TEXT,
            timeline TEXT,
            statements TEXT,
            icam_event TEXT,
            icam_individual TEXT,
            icam_task TEXT,
            icam_org TEXT,
            icam_defences TEXT,
            icam_actions TEXT,
            rca_method TEXT,
            direct_cause TEXT,
            underlying_cause TEXT,
            root_cause TEXT,
            contributing TEXT,
            five_whys TEXT,
            fishbone TEXT,
            bowtie TEXT,
            corrective TEXT,
            preventive TEXT,
            system_action TEXT,
            responsible TEXT,
            target TEXT,
            priority TEXT,
            status TEXT,
            verification TEXT,
            closeout TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS inspections(
            id INTEGER PRIMARY KEY,
            date TEXT,
            time TEXT,
            location TEXT,
            inspection_type TEXT,
            inspector TEXT,
            activity TEXT,
            checklist TEXT,
            unsafe_acts TEXT,
            unsafe_conditions TEXT,
            good_practices TEXT,
            ppe TEXT,
            excavation TEXT,
            wah TEXT,
            lifting TEXT,
            scaffolding TEXT,
            electrical TEXT,
            confined_space TEXT,
            hot_work TEXT,
            fire TEXT,
            housekeeping TEXT,
            vehicle TEXT,
            environment TEXT,
            emergency TEXT,
            findings TEXT,
            actions TEXT,
            responsible TEXT,
            target TEXT,
            status TEXT,
            evidence TEXT,
            photo_path TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS audits(
            id INTEGER PRIMARY KEY,
            date TEXT,
            location TEXT,
            audit_type TEXT,
            auditor TEXT,
            scope TEXT,
            findings TEXT,
            nc TEXT,
            good_practices TEXT,
            actions TEXT,
            responsible TEXT,
            target TEXT,
            status TEXT,
            evidence TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS capa(
            id INTEGER PRIMARY KEY,
            date TEXT,
            source TEXT,
            location TEXT,
            finding TEXT,
            root_cause TEXT,
            corrective TEXT,
            preventive TEXT,
            responsible TEXT,
            target TEXT,
            priority TEXT,
            status TEXT,
            verification TEXT,
            closeout TEXT,
            evidence TEXT,
            created_at TEXT
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY,
            module TEXT,
            record_id INTEGER,
            path TEXT,
            description TEXT,
            created_at TEXT
        )
        """)

        self.connection.commit()

        self.ensure_columns(
            "observations",
            {
                "photo_path": "TEXT"
            }
        )

        self.ensure_columns(
            "inspections",
            {
                "photo_path": "TEXT"
            }
        )

    def ensure_columns(self, table, columns):

        existing = [
            row[1]
            for row in self.connection.execute(
                "PRAGMA table_info(" + table + ")"
            ).fetchall()
        ]

        for name, field_type in columns.items():

            if name not in existing:

                self.connection.execute(
                    "ALTER TABLE %s ADD COLUMN %s %s"
                    % (
                        table,
                        name,
                        field_type
                    )
                )

        self.connection.commit()

    def add(self, table, data):

        keys = list(data.keys())

        query = (
            "INSERT INTO "
            + table
            + "("
            + ",".join(keys)
            + ") VALUES("
            + ",".join(["?"] * len(keys))
            + ")"
        )

        self.connection.execute(
            query,
            [data[key] for key in keys]
        )

        self.connection.commit()

        return self.connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

    def update(self, table, record_id, data):

        parts = []

        values = []

        for key, value in data.items():

            parts.append(
                key + "=?"
            )

            values.append(value)

        values.append(record_id)

        self.connection.execute(
            "UPDATE %s SET %s WHERE id=?"
            % (
                table,
                ",".join(parts)
            ),
            values
        )

        self.connection.commit()

    def count(self, table):

        return self.connection.execute(
            "SELECT COUNT(*) FROM " + table
        ).fetchone()[0]

    def status_count(self, table, status):

        return self.connection.execute(
            "SELECT COUNT(*) FROM "
            + table
            + " WHERE status=?",
            (status,)
        ).fetchone()[0]

    def rows(self, table):

        return self.connection.execute(
            "SELECT * FROM "
            + table
            + " ORDER BY id DESC LIMIT 500"
        ).fetchall()

    def observation_rows(self):

        return self.connection.execute("""
        SELECT
            id,
            date,
            location,
            responsible,
            type,
            category,
            observation,
            action,
            status,
            observed_by,
            photo_path,
            evidence
        FROM observations
        ORDER BY id DESC
        """).fetchall()

    def get_settings(self):

        row = self.connection.execute(
            "SELECT project_name,company_name,logo_path "
            "FROM settings WHERE id=1"
        ).fetchone()

        if not row:

            return {
                "project_name": "",
                "company_name": "",
                "logo_path": ""
            }

        return {
            "project_name": row[0] or "",
            "company_name": row[1] or "",
            "logo_path": row[2] or ""
        }

    def save_settings(
        self,
        project_name,
        company_name,
        logo_path
    ):

        self.connection.execute("""
        INSERT INTO settings
        (id,project_name,company_name,logo_path,updated_at)
        VALUES(1,?,?,?,?)
        ON CONFLICT(id)
        DO UPDATE SET
            project_name=excluded.project_name,
            company_name=excluded.company_name,
            logo_path=excluded.logo_path,
            updated_at=excluded.updated_at
        """, (
            project_name,
            company_name,
            logo_path,
            now()
        ))

        self.connection.commit()

    def recent(self):

        return self.connection.execute("""
        SELECT 'Observation',id,location,status,created_at
        FROM observations

        UNION ALL

        SELECT 'Incident',id,location,status,created_at
        FROM incidents

        UNION ALL

        SELECT 'Inspection',id,location,status,created_at
        FROM inspections

        UNION ALL

        SELECT 'Audit',id,location,status,created_at
        FROM audits

        UNION ALL

        SELECT 'CAPA',id,location,status,created_at
        FROM capa

        ORDER BY created_at DESC
        LIMIT 8
        """).fetchall()


# ============================================================
# MAIN APPLICATION
# ============================================================

class HSEPocket(App):

    def build(self):

        Window.clearcolor = BG

        self.app_directory = os.path.join(
            self.user_data_dir,
            "HSE_POCKET"
        )

        os.makedirs(
            self.app_directory,
            exist_ok=True
        )

        self.photo_directory = os.path.join(
            self.app_directory,
            "Photos"
        )

        os.makedirs(
            self.photo_directory,
            exist_ok=True
        )

        self.db = Database(
            os.path.join(
                self.app_directory,
                "hse_pocket.db"
            )
        )

        self.sm = ScreenManager()

        screens = [
            ("home", self.home),
            ("observations", self.observations),
            ("incidents", self.incidents),
            ("inspections", self.inspections),
            ("audits", self.audits),
            ("capa", self.capa),
            ("files", self.files),
            ("settings", self.settings)
        ]

        for name, builder in screens:

            screen = Screen(
                name=name
            )

            screen.add_widget(
                builder()
            )

            self.sm.add_widget(
                screen
            )

        # Android hardware back button
        Window.bind(
            on_keyboard=self.on_back_button
        )

        return self.sm

    # ========================================================
    # BACK BUTTON FIX
    # ========================================================

    def on_back_button(
        self,
        window,
        key,
        scancode,
        codepoint,
        modifiers
    ):

        # Android back key
        if key == 27 or key == 1001:

            current = self.sm.current

            if current != "home":

                self.sm.current = "home"

                self.refresh_dashboard()

                return True

            # On HOME, allow Android to exit
            return False

        return False

    def go(self, name):

        self.sm.current = name

        if name == "home":

            self.refresh_dashboard()

    # ========================================================
    # NAVIGATION
    # ========================================================

    def navigation(self):

        bar = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            spacing=dp(2),
            padding=dp(2)
        )

        buttons = [
            ("HOME", "home"),
            ("OBS", "observations"),
            ("INC", "incidents"),
            ("INSP", "inspections"),
            ("AUDIT", "audits"),
            ("CAPA", "capa"),
            ("FILES", "files")
        ]

        for title, name in buttons:

            button = make_button(
                title,
                NAVY,
                50,
                8
            )

            button.bind(
                on_release=lambda _, n=name:
                self.go(n)
            )

            bar.add_widget(button)

        return bar

    def page(self, title, content):

        root = BoxLayout(
            orientation="vertical"
        )

        header = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            padding=[dp(12), dp(4)]
        )

        header.add_widget(
            make_label(
                title,
                18,
                NAVY,
                True,
                47
            )
        )

        root.add_widget(header)
        root.add_widget(content)
        root.add_widget(self.navigation())

        return root

    def form(self):

        scroll = ScrollView(
            bar_width=dp(4)
        )

        grid = GridLayout(
            cols=1,
            spacing=dp(7),
            padding=dp(10),
            size_hint_y=None
        )

        grid.bind(
            minimum_height=grid.setter(
                "height"
            )
        )

        scroll.add_widget(grid)

        return scroll, grid

    # ========================================================
    # HOME
    # ========================================================

    def home(self):

        scroll, grid = self.form()

        header = Card(
            orientation="vertical",
            padding=dp(12),
            size_hint_y=None,
            height=dp(92)
        )

        header.add_widget(
            make_label(
                "HSE-POCKET",
                25,
                NAVY,
                True,
                38
            )
        )

        settings = self.db.get_settings()

        company_text = settings["company_name"]

        if settings["project_name"]:

            company_text += (
                "  |  "
                + settings["project_name"]
            )

        header.add_widget(
            make_label(
                company_text
                if company_text
                else
                "Health, Safety & Environment Management",
                11,
                MUTED,
                False,
                27
            )
        )

        grid.add_widget(header)

        grid.add_widget(
            make_label(
                "CONTROL CENTER",
                16,
                NAVY,
                True,
                30
            )
        )

        self.dashboard_cards = GridLayout(
            cols=2,
            spacing=dp(7),
            size_hint_y=None
        )

        self.dashboard_cards.bind(
            minimum_height=self.dashboard_cards.setter(
                "height"
            )
        )

        grid.add_widget(
            self.dashboard_cards
        )

        grid.add_widget(
            make_label(
                "QUICK ACTIONS",
                16,
                NAVY,
                True,
                30
            )
        )

        quick = GridLayout(
            cols=2,
            spacing=dp(7),
            size_hint_y=None,
            height=dp(94)
        )

        quick_buttons = [
            ("NEW OBSERVATION", BLUE, "observations"),
            ("NEW INCIDENT", RED, "incidents"),
            ("NEW INSPECTION", TEAL, "inspections"),
            ("NEW CAPA", PURPLE, "capa")
        ]

        for title, color, screen in quick_buttons:

            button = make_button(
                title,
                color,
                43,
                9
            )

            button.bind(
                on_release=lambda _, n=screen:
                self.go(n)
            )

            quick.add_widget(button)

        grid.add_widget(quick)

        settings_button = make_button(
            "SETTINGS",
            ORANGE,
            44,
            10
        )

        settings_button.bind(
            on_release=lambda _: self.go("settings")
        )

        grid.add_widget(settings_button)

        self.dashboard_summary = make_label(
            "",
            12,
            TEXT,
            False,
            85
        )

        summary_card = Card(
            orientation="vertical",
            padding=dp(10),
            size_hint_y=None,
            height=dp(95)
        )

        summary_card.add_widget(
            self.dashboard_summary
        )

        grid.add_widget(summary_card)

        grid.add_widget(
            make_label(
                "RECENT ACTIVITY",
                16,
                NAVY,
                True,
                30
            )
        )

        self.recent_activity = make_label(
            "",
            11,
            MUTED,
            False,
            125
        )

        recent_card = Card(
            orientation="vertical",
            padding=dp(10),
            size_hint_y=None,
            height=dp(135)
        )

        recent_card.add_widget(
            self.recent_activity
        )

        grid.add_widget(recent_card)

        refresh = make_button(
            "REFRESH DASHBOARD",
            NAVY,
            44
        )

        refresh.bind(
            on_release=lambda _: self.refresh_dashboard()
        )

        grid.add_widget(refresh)

        root = BoxLayout(
            orientation="vertical"
        )

        root.add_widget(scroll)
        root.add_widget(self.navigation())

        self.refresh_dashboard()

        return root

    def refresh_dashboard(self):

        if not hasattr(
            self,
            "dashboard_cards"
        ):
            return

        self.dashboard_cards.clear_widgets()

        sections = [
            ("OBSERVATIONS", "observations", BLUE),
            ("INCIDENTS", "incidents", RED),
            ("INSPECTIONS", "inspections", TEAL),
            ("AUDITS", "audits", GREEN),
            ("CAPA", "capa", PURPLE),
            ("FILES", "files", ORANGE)
        ]

        for title, table, color in sections:

            total = self.db.count(table)

            card = Card(
                orientation="vertical",
                padding=dp(9),
                size_hint_y=None,
                height=dp(88)
            )

            card.add_widget(
                make_label(
                    title,
                    11,
                    color,
                    True,
                    24
                )
            )

            row = BoxLayout(
                size_hint_y=None,
                height=dp(43)
            )

            row.add_widget(
                make_label(
                    str(total),
                    24,
                    NAVY,
                    True,
                    40
                )
            )

            open_button = make_button(
                "OPEN",
                color,
                36,
                8
            )

            open_button.size_hint_x = 0.43

            destination = (
                "files"
                if table == "files"
                else table
            )

            open_button.bind(
                on_release=lambda _, n=destination:
                self.go(n)
            )

            row.add_widget(open_button)

            card.add_widget(row)

            self.dashboard_cards.add_widget(card)

        total_records = sum(
            self.db.count(x)
            for x in [
                "observations",
                "incidents",
                "inspections",
                "audits",
                "capa"
            ]
        )

        open_actions = sum(
            self.db.status_count(x, "Open")
            for x in [
                "observations",
                "incidents",
                "inspections",
                "audits",
                "capa"
            ]
        )

        self.dashboard_summary.text = (
            "TOTAL HSE RECORDS: %d\n"
            "OPEN ACTIONS: %d\n"
            "DATABASE: Local SQLite\n"
            "UPDATED: %s"
            % (
                total_records,
                open_actions,
                now()
            )
        )

        recent = self.db.recent()

        if recent:

            self.recent_activity.text = "\n".join(
                "%s #%s | %s | %s | %s"
                % row
                for row in recent
            )

        else:

            self.recent_activity.text = (
                "No records yet."
            )

    # ========================================================
    # ANDROID GALLERY PICKER
    # ========================================================

    def select_gallery_image(
        self,
        callback,
        prefix="photo"
    ):

        self.gallery_callback = callback
        self.gallery_prefix = prefix

        try:

            from jnius import autoclass

            Intent = autoclass(
                "android.content.Intent"
            )

            PythonActivity = autoclass(
                "org.kivy.android.PythonActivity"
            )

            intent = Intent(
                Intent.ACTION_OPEN_DOCUMENT
            )

            intent.setType(
                "image/*"
            )

            intent.addCategory(
                Intent.CATEGORY_OPENABLE
            )

            PythonActivity.mActivity.startActivityForResult(
                intent,
                7001
            )

            show_message(
                "Gallery",
                "Select an image from your phone gallery."
            )

        except Exception as error:

            show_message(
                "Gallery",
                "Android gallery picker could not be opened.\n\n"
                + str(error)
            )

    # ========================================================
    # OBSERVATIONS
    # ========================================================

    def observations(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "OBSERVATION MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.obs_date = make_input("Date")
        self.obs_date.text = today()

        self.obs_location = make_input(
            "Location *"
        )

        self.obs_responsible = make_input(
            "Responsible Person"
        )

        self.obs_designation = make_input(
            "Responsible Designation"
        )

        self.obs_type = Spinner(
            text="Unsafe Condition",
            values=[
                "Unsafe Act",
                "Unsafe Condition",
                "Good Practice"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.obs_category = Spinner(
            text="PPE",
            values=[
                "PPE",
                "Excavation",
                "Work at Height",
                "Lifting",
                "Electrical",
                "Confined Space",
                "Hot Work",
                "Fire Safety",
                "Scaffolding",
                "Housekeeping",
                "Slip/Trip/Fall",
                "Chemical",
                "Vehicle",
                "Plant & Equipment",
                "Environmental",
                "Emergency",
                "Material Management",
                "Other"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.obs_description = make_input(
            "Observation *",
            100,
            True
        )

        self.obs_action = make_input(
            "Corrective Action",
            90,
            True
        )

        self.obs_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.obs_by = make_input(
            "Observed By"
        )

        self.obs_evidence = make_input(
            "Evidence / File Reference",
            70,
            True
        )

        self.obs_photo = ""

        for widget in [
            self.obs_date,
            self.obs_location,
            self.obs_responsible,
            self.obs_designation,
            self.obs_type,
            self.obs_category,
            self.obs_description,
            self.obs_action,
            self.obs_status,
            self.obs_by,
            self.obs_evidence
        ]:

            grid.add_widget(widget)

        grid.add_widget(
            make_label(
                "PHOTO ATTACHMENT",
                13,
                BLUE,
                True,
                28
            )
        )

        self.obs_photo_label = make_label(
            "No photo attached",
            11,
            MUTED,
            False,
            32
        )

        grid.add_widget(
            self.obs_photo_label
        )

        photo_button = make_button(
            "ATTACH PHOTO FROM GALLERY",
            BLUE,
            46
        )

        photo_button.bind(
            on_release=lambda _:
            self.select_gallery_image(
                self.observation_photo_selected,
                "observation"
            )
        )

        grid.add_widget(photo_button)

        save = make_button(
            "SAVE OBSERVATION",
            BLUE,
            46
        )

        save.bind(
            on_release=lambda _:
            self.save_observation()
        )

        grid.add_widget(save)

        view = make_button(
            "VIEW OBSERVATION REGISTER",
            NAVY,
            44
        )

        view.bind(
            on_release=lambda _:
            self.observation_register()
        )

        grid.add_widget(view)

        return self.page(
            "Observations",
            scroll
        )

    def observation_photo_selected(
        self,
        source_path
    ):

        self.obs_photo = source_path

        self.obs_photo_label.text = (
            "Attached: "
            + os.path.basename(source_path)
        )

    def save_observation(self):

        if not self.obs_location.text.strip():

            show_message(
                "Required",
                "Location is required."
            )

            return

        if not self.obs_description.text.strip():

            show_message(
                "Required",
                "Observation is required."
            )

            return

        record_id = self.db.add(
            "observations",
            {
                "date": self.obs_date.text,
                "location": self.obs_location.text,
                "responsible": self.obs_responsible.text,
                "designation": self.obs_designation.text,
                "type": self.obs_type.text,
                "category": self.obs_category.text,
                "observation": self.obs_description.text,
                "action": self.obs_action.text,
                "status": self.obs_status.text,
                "observed_by": self.obs_by.text,
                "evidence": self.obs_evidence.text,
                "photo_path": self.obs_photo,
                "created_at": now()
            }
        )

        show_message(
            "Saved",
            "Observation #%d saved successfully."
            % record_id
        )

        self.refresh_dashboard()

    # ========================================================
    # OBSERVATION REGISTER - TABLE
    # ========================================================

    def observation_register(self):

        rows = self.db.observation_rows()

        box = BoxLayout(
            orientation="vertical",
            padding=dp(6),
            spacing=dp(6)
        )

        scroll = ScrollView(
            do_scroll_x=True,
            do_scroll_y=True
        )

        table = GridLayout(
            cols=12,
            size_hint_y=None,
            spacing=dp(2),
            padding=dp(2)
        )

        table.bind(
            minimum_height=table.setter(
                "height"
            )
        )

        headers = [
            "ID",
            "DATE",
            "LOCATION",
            "RESPONSIBLE",
            "TYPE",
            "CATEGORY",
            "OBSERVATION",
            "ACTION",
            "STATUS",
            "OBSERVED BY",
            "PHOTO",
            "EVIDENCE"
        ]

        for header in headers:

            table.add_widget(
                make_label(
                    header,
                    9,
                    WHITE,
                    True,
                    42
                )
            )

        for row in rows:

            values = list(row)

            for index, value in enumerate(values):

                if value is None:
                    value = ""

                if index == 10:

                    value = (
                        "ATTACHED"
                        if value
                        else "-"
                    )

                table.add_widget(
                    make_label(
                        value,
                        9,
                        TEXT,
                        False,
                        75
                    )
                )

        scroll.add_widget(table)

        box.add_widget(scroll)

        export_label = make_label(
            "EXPORT REGISTER",
            12,
            NAVY,
            True,
            28
        )

        box.add_widget(export_label)

        export_row = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(5)
        )

        word_button = make_button(
            "EXPORT WORD",
            BLUE,
            44,
            9
        )

        excel_button = make_button(
            "EXPORT EXCEL",
            GREEN,
            44,
            9
        )

        export_row.add_widget(
            word_button
        )

        export_row.add_widget(
            excel_button
        )

        box.add_widget(export_row)

        close_button = make_button(
            "CLOSE",
            NAVY,
            44
        )

        box.add_widget(close_button)

        popup = Popup(
            title="Observation Register",
            content=box,
            size_hint=(0.98, 0.96),
            auto_dismiss=False
        )

        close_button.bind(
            on_release=popup.dismiss
        )

        word_button.bind(
            on_release=lambda _:
            self.export_observations_word()
        )

        excel_button.bind(
            on_release=lambda _:
            self.export_observations_excel()
        )

        popup.open()

    # ========================================================
    # REPORT SETTINGS
    # ========================================================

    def report_header_text(self):

        settings = self.db.get_settings()

        return (
            settings["company_name"],
            settings["project_name"],
            settings["logo_path"]
        )

    # ========================================================
    # WORD EXPORT - RTF
    #
    # RTF is opened directly by Microsoft Word.
    # Landscape page.
    # Row height = 2 inches = 2880 twips.
    # ========================================================

    def export_observations_word(self):

        rows = self.db.observation_rows()

        if not rows:

            show_message(
                "Export",
                "No observation records available."
            )

            return

        company, project, logo = (
            self.report_header_text()
        )

        path = os.path.join(
            self.app_directory,
            "Observation_Register_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".rtf"
        )

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                r"{\rtf1\ansi\deff0"
            )

            # Landscape A4
            file.write(
                r"\paperw16840\paperh11900"
            )

            file.write(
                r"\margl500\margr500\margt500\margb500"
            )

            file.write(
                r"\fs28\b HSE-POCKET\b0\par"
            )

            if company:

                file.write(
                    self.rtf_escape(
                        company
                    )
                    + r"\par"
                )

            if project:

                file.write(
                    self.rtf_escape(
                        project
                    )
                    + r"\par"
                )

            file.write(
                r"\fs20 Observation Register\par\par"
            )

            headers = [
                "ID",
                "Date",
                "Location",
                "Responsible",
                "Type",
                "Category",
                "Observation",
                "Action",
                "Status",
                "Observed By",
                "Photo",
                "Evidence"
            ]

            widths = self.rtf_widths(
                headers,
                rows
            )

            file.write(
                r"\trowd\trrh-2880"
            )

            position = 0

            for width in widths:

                position += width

                file.write(
                    r"\cellx%d" % position
                )

            for header in headers:

                file.write(
                    r"\pard\intbl\b "
                    + self.rtf_escape(header)
                    + r"\b0\cell"
                )

            file.write(
                r"\row"
            )

            for row in rows:

                file.write(
                    r"\trowd\trrh-2880"
                )

                position = 0

                for width in widths:

                    position += width

                    file.write(
                        r"\cellx%d"
                        % position
                    )

                for index, value in enumerate(row):

                    if value is None:
                        value = ""

                    if index == 10:

                        value = (
                            "ATTACHED"
                            if value
                            else "-"
                        )

                    file.write(
                        r"\pard\intbl "
                        + self.rtf_escape(
                            str(value)
                        )
                        + r"\cell"
                    )

                file.write(
                    r"\row"
                )

            file.write(
                r"}"
            )

        show_message(
            "WORD EXPORT",
            "Word-compatible report created:\n\n"
            + path
        )

    def rtf_escape(self, value):

        value = str(value)

        value = value.replace(
            "\\",
            "\\\\"
        )

        value = value.replace(
            "{",
            "\\{"
        )

        value = value.replace(
            "}",
            "\\}"
        )

        value = value.replace(
            "\n",
            "\\line "
        )

        return value

    def rtf_widths(self, headers, rows):

        # Landscape width around 10.8 inches.
        total_width = 15500

        weights = []

        for index, header in enumerate(headers):

            longest = len(header)

            for row in rows:

                if index < len(row):

                    value = row[index]

                    if value is None:
                        value = ""

                    longest = max(
                        longest,
                        len(str(value))
                    )

            # Keep extremely long text from taking
            # the entire page.
            longest = min(
                longest,
                65
            )

            weights.append(
                max(5, longest)
            )

        total = sum(weights)

        return [
            int(
                total_width
                * weight
                / total
            )
            for weight in weights
        ]

    # ========================================================
    # EXCEL EXPORT
    #
    # HTML spreadsheet is saved as .xls.
    # Microsoft Excel opens this directly.
    # Row height = 2 inches = 144 points.
    # Column width adapts to text.
    # ========================================================

    def export_observations_excel(self):

        rows = self.db.observation_rows()

        if not rows:

            show_message(
                "Export",
                "No observation records available."
            )

            return

        company, project, logo = (
            self.report_header_text()
        )

        path = os.path.join(
            self.app_directory,
            "Observation_Register_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".xls"
        )

        headers = [
            "ID",
            "Date",
            "Location",
            "Responsible",
            "Type",
            "Category",
            "Observation",
            "Action",
            "Status",
            "Observed By",
            "Photo",
            "Evidence"
        ]

        with open(
            path,
            "w",
            encoding="utf-8"
        ) as file:

            file.write(
                "<html><head>"
                "<meta charset='utf-8'>"
                "<style>"
                "body{font-family:Arial;}"
                "table{border-collapse:collapse;}"
                "th{background:#0b2745;color:white;"
                "border:1px solid #777;padding:6px;}"
                "td{border:1px solid #777;"
                "padding:5px;vertical-align:top;"
                "height:144pt;}"
                "</style></head><body>"
            )

            file.write(
                "<h2>HSE-POCKET</h2>"
            )

            if company:

                file.write(
                    "<h3>%s</h3>"
                    % html.escape(company)
                )

            if project:

                file.write(
                    "<h3>%s</h3>"
                    % html.escape(project)
                )

            file.write(
                "<h3>Observation Register</h3>"
            )

            file.write(
                "<table>"
            )

            file.write(
                "<tr>"
            )

            for header in headers:

                file.write(
                    "<th>%s</th>"
                    % html.escape(header)
                )

            file.write(
                "</tr>"
            )

            for row in rows:

                file.write(
                    "<tr>"
                )

                for index, value in enumerate(row):

                    if value is None:
                        value = ""

                    if index == 10:

                        value = (
                            "ATTACHED"
                            if value
                            else "-"
                        )

                    text = html.escape(
                        str(value)
                    )

                    text = text.replace(
                        "\n",
                        "<br>"
                    )

                    file.write(
                        "<td>%s</td>"
                        % text
                    )

                file.write(
                    "</tr>"
                )

            file.write(
                "</table></body></html>"
            )

        show_message(
            "EXCEL EXPORT",
            "Excel-compatible report created:\n\n"
            + path
        )

    # ========================================================
    # SETTINGS
    # ========================================================

    def settings(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "REPORT SETTINGS",
                17,
                NAVY,
                True,
                32
            )
        )

        grid.add_widget(
            make_label(
                "These details are automatically used in future exported reports.",
                11,
                MUTED,
                False,
                42
            )
        )

        saved = self.db.get_settings()

        self.settings_project = make_input(
            "Project Name"
        )

        self.settings_company = make_input(
            "Company Name"
        )

        self.settings_logo = make_input(
            "Company Logo File"
        )

        self.settings_project.text = (
            saved["project_name"]
        )

        self.settings_company.text = (
            saved["company_name"]
        )

        self.settings_logo.text = (
            saved["logo_path"]
        )

        grid.add_widget(
            self.settings_project
        )

        grid.add_widget(
            self.settings_company
        )

        grid.add_widget(
            self.settings_logo
        )

        logo_button = make_button(
            "SELECT COMPANY LOGO FROM GALLERY",
            ORANGE,
            46
        )

        logo_button.bind(
            on_release=lambda _:
            self.select_gallery_image(
                self.company_logo_selected,
                "company_logo"
            )
        )

        grid.add_widget(
            logo_button
        )

        self.logo_status = make_label(
            (
                "Current logo: "
                + os.path.basename(
                    saved["logo_path"]
                )
                if saved["logo_path"]
                else
                "No company logo selected"
            ),
            11,
            MUTED,
            False,
            38
        )

        grid.add_widget(
            self.logo_status
        )

        save = make_button(
            "SAVE SETTINGS",
            GREEN,
            46
        )

        save.bind(
            on_release=lambda _:
            self.save_settings()
        )

        grid.add_widget(save)

        grid.add_widget(
            make_label(
                "The company name, project name and logo are stored locally on this device.",
                11,
                MUTED,
                False,
                55
            )
        )

        return self.page(
            "Settings",
            scroll
        )

    def company_logo_selected(
        self,
        source_path
    ):

        self.settings_logo.text = (
            source_path
        )

        self.logo_status.text = (
            "Selected logo: "
            + os.path.basename(
                source_path
            )
        )

    def save_settings(self):

        self.db.save_settings(
            self.settings_project.text,
            self.settings_company.text,
            self.settings_logo.text
        )

        show_message(
            "Settings Saved",
            "Project name, company name and logo settings saved."
        )

    # ========================================================
    # INCIDENT
    # Existing feature retained
    # ========================================================

    def incidents(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "INCIDENT / ACCIDENT INVESTIGATION",
                16,
                NAVY,
                True,
                30
            )
        )

        grid.add_widget(
            make_label(
                "ICAM + RCA + 5-WHY + FISHBONE + BOW-TIE",
                11,
                MUTED,
                False,
                30
            )
        )

        fields = [
            ("inc_date", "Date"),
            ("inc_time", "Time"),
            ("inc_location", "Location *"),
            ("inc_project", "Project / Area"),
            ("inc_activity", "Activity"),
            ("inc_title", "Incident Title *")
        ]

        for name, hint in fields:

            widget = make_input(hint)

            setattr(
                self,
                name,
                widget
            )

            grid.add_widget(widget)

        self.inc_date.text = today()

        self.inc_classification = Spinner(
            text="Near Miss",
            values=[
                "Near Miss",
                "First Aid",
                "Medical Treatment",
                "Lost Time Injury",
                "Fatality",
                "Property Damage",
                "Environmental",
                "Fire",
                "Vehicle",
                "Process Safety",
                "Security",
                "Other"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.inc_severity = Spinner(
            text="Medium",
            values=[
                "Low",
                "Medium",
                "High",
                "Critical"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        grid.add_widget(
            self.inc_classification
        )

        grid.add_widget(
            self.inc_severity
        )

        grid.add_widget(
            make_label(
                "INVESTIGATION INFORMATION",
                13,
                RED,
                True,
                28
            )
        )

        fields = [
            ("inc_description", "Detailed Incident Description", 120),
            ("inc_consequence", "Actual Consequence", 70),
            ("inc_potential", "Potential Consequence", 70),
            ("inc_people", "Persons Involved / Roles", 80),
            ("inc_injury", "Injury / Illness Details", 80),
            ("inc_damage", "Property / Equipment Damage", 70),
            ("inc_environment", "Environmental Impact", 70),
            ("inc_witnesses", "Witnesses / Statements", 80),
            ("inc_immediate", "Immediate Action / Containment", 90),
            ("inc_evidence", "Evidence / Photos / Documents", 80),
            ("inc_investigator", "Investigation Leader", 44),
            ("inc_team", "Investigation Team", 60),
            ("inc_scope", "Investigation Scope / Terms", 80),
            ("inc_timeline", "Sequence / Timeline", 110),
            ("inc_statements", "Statements / Evidence Findings", 100)
        ]

        for name, hint, height in fields:

            widget = make_input(
                hint,
                height,
                height > 60
            )

            setattr(
                self,
                name,
                widget
            )

            grid.add_widget(widget)

        grid.add_widget(
            make_label(
                "ICAM ANALYSIS",
                13,
                RED,
                True,
                28
            )
        )

        icam = [
            ("icam_event", "Event / Incident"),
            ("icam_individual", "Individual / Team Actions"),
            ("icam_task", "Task / Environmental Conditions"),
            ("icam_org", "Organisational Factors"),
            ("icam_defences", "Absent / Failed Defences and Barriers"),
            ("icam_actions", "ICAM Actions / Defence Improvements")
        ]

        for name, hint in icam:

            widget = make_input(
                hint,
                90,
                True
            )

            setattr(
                self,
                name,
                widget
            )

            grid.add_widget(widget)

        grid.add_widget(
            make_label(
                "ROOT CAUSE ANALYSIS",
                13,
                PURPLE,
                True,
                28
            )
        )

        self.rca_method = Spinner(
            text="5-Why",
            values=[
                "5-Why",
                "Fishbone / Ishikawa",
                "Bow-Tie",
                "ICAM",
                "Root Cause Tree",
                "Other"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        grid.add_widget(
            self.rca_method
        )

        rca = [
            ("direct_cause", "Direct / Immediate Cause", 80),
            ("underlying_cause", "Underlying Cause", 80),
            ("root_cause", "Root Cause", 100),
            ("contributing", "Contributing Factors", 90),
            ("five_whys", "5-Why Analysis - Why 1 to Why 5", 120),
            ("fishbone", "Fishbone / Ishikawa", 130),
            ("bowtie", "Bow-Tie Analysis", 130)
        ]

        for name, hint, height in rca:

            widget = make_input(
                hint,
                height,
                True
            )

            setattr(
                self,
                name,
                widget
            )

            grid.add_widget(widget)

        grid.add_widget(
            make_label(
                "CORRECTIVE / PREVENTIVE ACTION",
                13,
                GREEN,
                True,
                28
            )
        )

        actions = [
            ("inc_corrective", "Corrective Actions", 100),
            ("inc_preventive", "Preventive Actions", 100),
            ("inc_system", "System / Management Improvement", 90),
            ("inc_responsible", "Responsible Person", 44),
            ("inc_target", "Target Date", 44)
        ]

        for name, hint, height in actions:

            widget = make_input(
                hint,
                height,
                height > 60
            )

            setattr(
                self,
                name,
                widget
            )

            grid.add_widget(widget)

        self.inc_priority = Spinner(
            text="Medium",
            values=[
                "Low",
                "Medium",
                "High",
                "Critical"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.inc_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Investigation",
                "Action In Progress",
                "Closed"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.inc_verification = make_input(
            "Verification / Effectiveness Check",
            90,
            True
        )

        self.inc_closeout = make_input(
            "Closeout Details",
            90,
            True
        )

        grid.add_widget(
            self.inc_priority
        )

        grid.add_widget(
            self.inc_status
        )

        grid.add_widget(
            self.inc_verification
        )

        grid.add_widget(
            self.inc_closeout
        )

        save = make_button(
            "SAVE COMPLETE INVESTIGATION",
            RED,
            48
        )

        save.bind(
            on_release=lambda _:
            self.save_incident()
        )

        grid.add_widget(save)

        view = make_button(
            "VIEW INCIDENT REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _:
            self.view_register("incidents")
        )

        grid.add_widget(view)

        return self.page(
            "Incident Investigation",
            scroll
        )

    def save_incident(self):

        if not self.inc_location.text.strip():

            show_message(
                "Required",
                "Incident location is required."
            )

            return

        if not self.inc_title.text.strip():

            show_message(
                "Required",
                "Incident title is required."
            )

            return

        def v(name):
            return getattr(
                self,
                name
            ).text

        data = {
            "date": v("inc_date"),
            "time": v("inc_time"),
            "location": v("inc_location"),
            "project": v("inc_project"),
            "activity": v("inc_activity"),
            "classification": self.inc_classification.text,
            "severity": self.inc_severity.text,
            "title": v("inc_title"),
            "description": v("inc_description"),
            "consequence": v("inc_consequence"),
            "potential_consequence": v("inc_potential"),
            "people": v("inc_people"),
            "injury": v("inc_injury"),
            "damage": v("inc_damage"),
            "environment": v("inc_environment"),
            "witnesses": v("inc_witnesses"),
            "immediate": v("inc_immediate"),
            "evidence": v("inc_evidence"),
            "investigator": v("inc_investigator"),
            "team": v("inc_team"),
            "scope": v("inc_scope"),
            "timeline": v("inc_timeline"),
            "statements": v("inc_statements"),
            "icam_event": v("icam_event"),
            "icam_individual": v("icam_individual"),
            "icam_task": v("icam_task"),
            "icam_org": v("icam_org"),
            "icam_defences": v("icam_defences"),
            "icam_actions": v("icam_actions"),
            "rca_method": self.rca_method.text,
            "direct_cause": v("direct_cause"),
            "underlying_cause": v("underlying_cause"),
            "root_cause": v("root_cause"),
            "contributing": v("contributing"),
            "five_whys": v("five_whys"),
            "fishbone": v("fishbone"),
            "bowtie": v("bowtie"),
            "corrective": v("inc_corrective"),
            "preventive": v("inc_preventive"),
            "system_action": v("inc_system"),
            "responsible": v("inc_responsible"),
            "target": v("inc_target"),
            "priority": self.inc_priority.text,
            "status": self.inc_status.text,
            "verification": v("inc_verification"),
            "closeout": v("inc_closeout"),
            "created_at": now()
        }

        record_id = self.db.add(
            "incidents",
            data
        )

        show_message(
            "Saved",
            "Incident investigation #%d saved."
            % record_id
        )

        self.refresh_dashboard()

    # ========================================================
    # INSPECTIONS
    # ========================================================

    def inspections(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "SITE INSPECTION",
                17,
                NAVY,
                True,
                32
            )
        )

        grid.add_widget(
            make_label(
                "Complete inspection checklist, record findings, attach photos and close actions.",
                11,
                MUTED,
                False,
                45
            )
        )

        # ----------------------------------------------------
        # HEADER INFORMATION
        # ----------------------------------------------------

        grid.add_widget(
            make_label(
                "INSPECTION DETAILS",
                13,
                TEAL,
                True,
                28
            )
        )

        self.ins_date = make_input(
            "Date"
        )

        self.ins_date.text = today()

        self.ins_time = make_input(
            "Time"
        )

        self.ins_location = make_input(
            "Location *"
        )

        self.inspector = make_input(
            "Inspector / HSE Officer"
        )

        self.inspection_type = Spinner(
            text="Routine Inspection",
            values=[
                "Routine Inspection",
                "Daily Inspection",
                "Weekly Inspection",
                "Joint Inspection",
                "Management Inspection",
                "Client Inspection",
                "Safety Walk",
                "Special Inspection",
                "Pre-Activity Inspection",
                "Post-Incident Inspection",
                "Other"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.ins_activity = make_input(
            "Activity / Work Area"
        )

        for widget in [
            self.ins_date,
            self.ins_time,
            self.ins_location,
            self.inspector,
            self.inspection_type,
            self.ins_activity
        ]:

            grid.add_widget(widget)

        # ----------------------------------------------------
        # GENERAL CHECKLIST
        # ----------------------------------------------------

        grid.add_widget(
            make_label(
                "CHECKLIST",
                13,
                TEAL,
                True,
                28
            )
        )

        self.ins_checklist = make_input(
            "Checklist / Items Checked",
            110,
            True
        )

        grid.add_widget(
            self.ins_checklist
        )

        # ----------------------------------------------------
        # FINDING TYPE
        # ----------------------------------------------------

        grid.add_widget(
            make_label(
                "FINDING CLASSIFICATION",
                13,
                TEAL,
                True,
                28
            )
        )

        self.ins_unsafe_act = make_input(
            "UNSAFE ACTS",
            90,
            True
        )

        self.ins_unsafe_condition = make_input(
            "UNSAFE CONDITIONS",
            90,
            True
        )

        self.ins_good_practice = make_input(
            "GOOD PRACTICES",
            90,
            True
        )

        grid.add_widget(
            self.ins_unsafe_act
        )

        grid.add_widget(
            self.ins_unsafe_condition
        )

        grid.add_widget(
            self.ins_good_practice
        )

        # ----------------------------------------------------
        # SAFETY ELEMENTS
        # ----------------------------------------------------

        grid.add_widget(
            make_label(
                "HSE CHECKPOINTS",
                13,
                TEAL,
                True,
                28
            )
        )

        self.ins_ppe = make_input(
            "PPE",
            70,
            True
        )

        self.ins_excavation = make_input(
            "EXCAVATION",
            70,
            True
        )

        self.ins_wah = make_input(
            "WORK AT HEIGHT",
            70,
            True
        )

        self.ins_lifting = make_input(
            "LIFTING",
            70,
            True
        )

        self.ins_scaffolding = make_input(
            "SCAFFOLDING",
            70,
            True
        )

        self.ins_electrical = make_input(
            "ELECTRICAL",
            70,
            True
        )

        self.ins_confined = make_input(
            "CONFINED SPACE",
            70,
            True
        )

        self.ins_hotwork = make_input(
            "HOT WORK",
            70,
            True
        )

        self.ins_fire = make_input(
            "FIRE SAFETY",
            70,
            True
        )

        self.ins_housekeeping = make_input(
            "HOUSEKEEPING",
            70,
            True
        )

        self.ins_vehicle = make_input(
            "VEHICLE / PLANT",
            70,
            True
        )

        self.ins_environment = make_input(
            "ENVIRONMENTAL",
            70,
            True
        )

        self.ins_emergency = make_input(
            "EMERGENCY PREPAREDNESS",
            70,
            True
        )

        checkpoint_widgets = [
            self.ins_ppe,
            self.ins_excavation,
            self.ins_wah,
            self.ins_lifting,
            self.ins_scaffolding,
            self.ins_electrical,
            self.ins_confined,
            self.ins_hotwork,
            self.ins_fire,
            self.ins_housekeeping,
            self.ins_vehicle,
            self.ins_environment,
            self.ins_emergency
        ]

        for widget in checkpoint_widgets:
            grid.add_widget(widget)

        # ----------------------------------------------------
        # FINDINGS
        # ----------------------------------------------------

        grid.add_widget(
            make_label(
                "INSPECTION FINDINGS",
                13,
                RED,
                True,
                28
            )
        )

        self.ins_findings = make_input(
            "Detailed Findings",
            130,
            True
        )

        self.ins_actions = make_input(
            "Corrective Actions Required",
            120,
            True
        )

        self.ins_responsible = make_input(
            "Responsible Person"
        )

        self.ins_target = make_input(
            "Target Date"
        )

        self.ins_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        grid.add_widget(
            self.ins_findings
        )

        grid.add_widget(
            self.ins_actions
        )

        grid.add_widget(
            self.ins_responsible
        )

        grid.add_widget(
            self.ins_target
        )

        grid.add_widget(
            self.ins_status
        )

        # ----------------------------------------------------
        # PHOTO / EVIDENCE
        # ----------------------------------------------------

        grid.add_widget(
            make_label(
                "PHOTO / EVIDENCE",
                13,
                BLUE,
                True,
                28
            )
        )

        self.ins_photo_path = ""

        self.ins_photo_label = make_label(
            "No inspection photo attached",
            11,
            MUTED,
            False,
            34
        )

        grid.add_widget(
            self.ins_photo_label
        )

        gallery = make_button(
            "ATTACH INSPECTION PHOTO FROM GALLERY",
            BLUE,
            46
        )

        gallery.bind(
            on_release=lambda _:
            self.select_gallery_image(
                self.inspection_photo_selected,
                "inspection"
            )
        )

        grid.add_widget(
            gallery
        )

        self.ins_evidence = make_input(
            "Additional Evidence / File Reference",
            75,
            True
        )

        grid.add_widget(
            self.ins_evidence
        )

        # ----------------------------------------------------
        # SAVE
        # ----------------------------------------------------

        save = make_button(
            "SAVE INSPECTION",
            TEAL,
            48
        )

        save.bind(
            on_release=lambda _:
            self.save_inspection()
        )

        grid.add_widget(save)

        view = make_button(
            "VIEW INSPECTION REGISTER",
            NAVY,
            44
        )

        view.bind(
            on_release=lambda _:
            self.view_register("inspections")
        )

        grid.add_widget(view)

        return self.page(
            "Inspections",
            scroll
        )

    def inspection_photo_selected(
        self,
        source_path
    ):

        self.ins_photo_path = source_path

        self.ins_photo_label.text = (
            "Attached: "
            + os.path.basename(source_path)
        )

    def save_inspection(self):

        if not self.ins_location.text.strip():

            show_message(
                "Required",
                "Inspection location is required."
            )

            return

        data = {
            "date": self.ins_date.text,
            "time": self.ins_time.text,
            "location": self.ins_location.text,
            "inspection_type": self.inspection_type.text,
            "inspector": self.inspector.text,
            "activity": self.ins_activity.text,
            "checklist": self.ins_checklist.text,
            "unsafe_acts": self.ins_unsafe_act.text,
            "unsafe_conditions": self.ins_unsafe_condition.text,
            "good_practices": self.ins_good_practice.text,
            "ppe": self.ins_ppe.text,
            "excavation": self.ins_excavation.text,
            "wah": self.ins_wah.text,
            "lifting": self.ins_lifting.text,
            "scaffolding": self.ins_scaffolding.text,
            "electrical": self.ins_electrical.text,
            "confined_space": self.ins_confined.text,
            "hot_work": self.ins_hotwork.text,
            "fire": self.ins_fire.text,
            "housekeeping": self.ins_housekeeping.text,
            "vehicle": self.ins_vehicle.text,
            "environment": self.ins_environment.text,
            "emergency": self.ins_emergency.text,
            "findings": self.ins_findings.text,
            "actions": self.ins_actions.text,
            "responsible": self.ins_responsible.text,
            "target": self.ins_target.text,
            "status": self.ins_status.text,
            "evidence": self.ins_evidence.text,
            "photo_path": self.ins_photo_path,
            "created_at": now()
        }

        record_id = self.db.add(
            "inspections",
            data
        )

        show_message(
            "Inspection Saved",
            "Inspection #%d saved successfully."
            % record_id
        )

        self.refresh_dashboard()

    # ========================================================
    # AUDITS
    # ========================================================

    def audits(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "HSE AUDIT MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.audit_widgets = [
            make_input("Date"),
            make_input("Location *"),
            make_input("Audit Type"),
            make_input("Auditor / Team"),
            make_input("Scope / Standard", 80, True),
            make_input("Findings / Nonconformities", 110, True),
            make_input("Good Practices / Strengths", 80, True),
            make_input("Corrective Actions", 100, True),
            make_input("Responsible Person"),
            make_input("Target Date")
        ]

        self.audit_widgets[0].text = today()

        for widget in self.audit_widgets:
            grid.add_widget(widget)

        self.audit_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.audit_evidence = make_input(
            "Evidence / File Reference",
            70,
            True
        )

        grid.add_widget(
            self.audit_status
        )

        grid.add_widget(
            self.audit_evidence
        )

        save = make_button(
            "SAVE AUDIT",
            GREEN,
            46
        )

        save.bind(
            on_release=lambda _:
            self.save_audit()
        )

        grid.add_widget(save)

        view = make_button(
            "VIEW AUDIT REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _:
            self.view_register("audits")
        )

        grid.add_widget(view)

        return self.page(
            "Audits",
            scroll
        )

    def save_audit(self):

        keys = [
            "date",
            "location",
            "audit_type",
            "auditor",
            "scope",
            "findings",
            "good_practices",
            "actions",
            "responsible",
            "target"
        ]

        data = {}

        for index, key in enumerate(keys):

            data[key] = (
                self.audit_widgets[index].text
            )

        if not data["location"].strip():

            show_message(
                "Required",
                "Audit location is required."
            )

            return

        data["status"] = (
            self.audit_status.text
        )

        data["evidence"] = (
            self.audit_evidence.text
        )

        data["created_at"] = now()

        record_id = self.db.add(
            "audits",
            data
        )

        show_message(
            "Saved",
            "Audit #%d saved."
            % record_id
        )

        self.refresh_dashboard()

    # ========================================================
    # CAPA
    # ========================================================

    def capa(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "CAPA MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.capa_widgets = [
            make_input("Date"),
            make_input("Source"),
            make_input("Location"),
            make_input("Finding *", 100, True),
            make_input("Root Cause", 90, True),
            make_input("Corrective Action", 100, True),
            make_input("Preventive Action", 100, True),
            make_input("Responsible Person"),
            make_input("Target Date")
        ]

        self.capa_widgets[0].text = today()

        for widget in self.capa_widgets:
            grid.add_widget(widget)

        self.capa_priority = Spinner(
            text="Medium",
            values=[
                "Low",
                "Medium",
                "High",
                "Critical"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.capa_status = Spinner(
            text="Open",
            values=[
                "Open",
                "In Progress",
                "Closed",
                "Overdue"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.capa_verification = make_input(
            "Verification / Effectiveness",
            80,
            True
        )

        self.capa_closeout = make_input(
            "Closeout",
            80,
            True
        )

        self.capa_evidence = make_input(
            "Closeout Evidence / File Reference",
            70,
            True
        )

        for widget in [
            self.capa_priority,
            self.capa_status,
            self.capa_verification,
            self.capa_closeout,
            self.capa_evidence
        ]:

            grid.add_widget(widget)

        save = make_button(
            "SAVE CAPA",
            PURPLE,
            46
        )

        save.bind(
            on_release=lambda _:
            self.save_capa()
        )

        grid.add_widget(save)

        view = make_button(
            "VIEW CAPA REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _:
            self.view_register("capa")
        )

        grid.add_widget(view)

        export = make_button(
            "EXPORT CAPA CSV",
            TEAL,
            42
        )

        export.bind(
            on_release=lambda _:
            self.export_csv("capa")
        )

        grid.add_widget(export)

        return self.page(
            "CAPA",
            scroll
        )

    def save_capa(self):

        if not self.capa_widgets[3].text.strip():

            show_message(
                "Required",
                "CAPA finding is required."
            )

            return

        keys = [
            "date",
            "source",
            "location",
            "finding",
            "root_cause",
            "corrective",
            "preventive",
            "responsible",
            "target"
        ]

        data = {}

        for index, key in enumerate(keys):

            data[key] = (
                self.capa_widgets[index].text
            )

        data.update({
            "priority": self.capa_priority.text,
            "status": self.capa_status.text,
            "verification": self.capa_verification.text,
            "closeout": self.capa_closeout.text,
            "evidence": self.capa_evidence.text,
            "created_at": now()
        })

        record_id = self.db.add(
            "capa",
            data
        )

        show_message(
            "Saved",
            "CAPA #%d saved."
            % record_id
        )

        self.refresh_dashboard()

    # ========================================================
    # FILES
    # ========================================================

    def files(self):

        scroll, grid = self.form()

        grid.add_widget(
            make_label(
                "FILES & EVIDENCE",
                16,
                NAVY,
                True,
                30
            )
        )

        self.file_module = Spinner(
            text="Inspection",
            values=[
                "Observation",
                "Incident",
                "Inspection",
                "Audit",
                "CAPA"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.file_record_id = make_input(
            "Record ID"
        )

        self.file_path = make_input(
            "File path / document reference",
            75,
            True
        )

        self.file_description = make_input(
            "Description",
            70,
            True
        )

        for widget in [
            self.file_module,
            self.file_record_id,
            self.file_path,
            self.file_description
        ]:

            grid.add_widget(widget)

        save = make_button(
            "SAVE FILE REFERENCE",
            ORANGE,
            46
        )

        save.bind(
            on_release=lambda _:
            self.save_file()
        )

        grid.add_widget(save)

        view = make_button(
            "VIEW FILE REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _:
            self.view_files()
        )

        grid.add_widget(view)

        return self.page(
            "Files & Evidence",
            scroll
        )

    def save_file(self):

        try:

            record_id = int(
                self.file_record_id.text.strip()
            )

        except Exception:

            show_message(
                "Invalid",
                "Record ID must be a number."
            )

            return

        self.db.add(
            "files",
            {
                "module": self.file_module.text,
                "record_id": record_id,
                "path": self.file_path.text,
                "description": self.file_description.text,
                "created_at": now()
            }
        )

        show_message(
            "Saved",
            "File reference saved."
        )

    def view_files(self):

        rows = self.db.connection.execute(
            """
            SELECT id,module,record_id,path,
                   description,created_at
            FROM files
            ORDER BY id DESC
            """
        ).fetchall()

        if not rows:

            show_message(
                "FILE REGISTER",
                "No file references."
            )

            return

        output = []

        for row in rows:

            output.append(
                "ID: %s\n"
                "Module: %s\n"
                "Record: %s\n"
                "File: %s\n"
                "Description: %s\n"
                "Created: %s"
                % row
            )

        show_message(
            "FILE REGISTER",
            "\n\n----------------\n\n".join(
                output
            )
        )

    # ========================================================
    # GENERIC REGISTERS
    # ========================================================

    def view_register(self, table):

        rows = self.db.rows(table)

        if not rows:

            show_message(
                table.upper(),
                "No records found."
            )

            return

        output = []

        for row in rows:

            values = []

            for index, value in enumerate(row):

                if value is None:
                    value = "-"

                values.append(
                    "%d: %s"
                    % (
                        index + 1,
                        value
                    )
                )

            output.append(
                "\n".join(values)
            )

        show_message(
            table.upper() + " REGISTER",
            "\n\n----------------\n\n".join(
                output
            )
        )

    # ========================================================
    # CSV
    # ========================================================

    def export_csv(self, table):

        rows = self.db.rows(table)

        if not rows:

            show_message(
                "EXPORT",
                "No records available."
            )

            return

        path = os.path.join(
            self.app_directory,
            table
            + "_register_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".csv"
        )

        with open(
            path,
            "w",
            newline="",
            encoding="utf-8-sig"
        ) as file:

            writer = csv.writer(file)

            for row in rows:

                writer.writerow(row)

        show_message(
            "EXPORT COMPLETE",
            path
        )

    # ========================================================
    # APP CLOSE
    # ========================================================

    def on_stop(self):

        try:

            self.db.connection.close()

        except Exception:

            pass


if __name__ == "__main__":

    HSEPocket().run()