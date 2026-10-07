# HSE-POCKET - Complete Single-File Kivy HSE Management System

import os
import csv
import sqlite3
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


APP = "HSE-POCKET"

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


def L(text="", size=13, color=TEXT, bold=False, height=34):
    label = Label(
        text=str(text),
        size_hint_y=None,
        height=dp(height),
        font_size=dp(size),
        color=color,
        bold=bold,
        halign="left",
        valign="middle",
    )

    label.bind(
        width=lambda obj, value: setattr(
            obj,
            "text_size",
            (max(1, value - dp(4)), None)
        )
    )

    return label


def I(hint="", height=44, multiline=False):
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
        hint_text_color=MUTED,
    )


def B(text, color=BLUE, height=44, size=11):
    return Button(
        text=text,
        size_hint_y=None,
        height=dp(height),
        background_normal="",
        background_down="",
        background_color=color,
        color=WHITE,
        bold=True,
        font_size=dp(size),
    )


def msg(title, message):
    box = BoxLayout(
        orientation="vertical",
        padding=dp(10),
        spacing=dp(8)
    )

    scroll = ScrollView()

    label = L(
        message,
        13,
        TEXT,
        False,
        100
    )

    label.size_hint_y = None

    label.bind(
        texture_size=lambda obj, value: setattr(
            obj,
            "height",
            max(dp(100), value[1] + dp(15))
        )
    )

    scroll.add_widget(label)
    box.add_widget(scroll)

    close_button = B(
        "CLOSE",
        NAVY,
        44
    )

    box.add_widget(close_button)

    popup = Popup(
        title=title,
        content=box,
        size_hint=(0.94, 0.82),
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
            self.col = Color(*bg)
            self.rect = RoundedRectangle(
                pos=self.pos,
                size=self.size,
                radius=[dp(12)]
            )

        self.bind(
            pos=self.sync,
            size=self.sync
        )

    def sync(self, *args):
        self.rect.pos = self.pos
        self.rect.size = self.size


class Database:

    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.create_tables()

    def create_tables(self):

        c = self.connection

        c.execute("""
        CREATE TABLE IF NOT EXISTS observations(
            id INTEGER PRIMARY KEY,
            date,
            location,
            responsible,
            designation,
            type,
            category,
            observation,
            action,
            status,
            observed_by,
            evidence,
            created_at
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS incidents(
            id INTEGER PRIMARY KEY,
            date,
            time,
            location,
            project,
            activity,
            classification,
            severity,
            title,
            description,
            consequence,
            potential_consequence,
            people,
            injury,
            damage,
            environment,
            witnesses,
            immediate,
            evidence,
            investigator,
            team,
            scope,
            timeline,
            statements,
            icam_event,
            icam_individual,
            icam_task,
            icam_org,
            icam_defences,
            icam_actions,
            rca_method,
            direct_cause,
            underlying_cause,
            root_cause,
            contributing,
            five_whys,
            fishbone,
            bowtie,
            corrective,
            preventive,
            system_action,
            responsible,
            target,
            priority,
            status,
            verification,
            closeout,
            created_at
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS inspections(
            id INTEGER PRIMARY KEY,
            date,
            time,
            location,
            inspection_type,
            inspector,
            activity,
            checklist,
            unsafe_acts,
            unsafe_conditions,
            good_practices,
            ppe,
            excavation,
            wah,
            lifting,
            scaffolding,
            electrical,
            confined_space,
            hot_work,
            fire,
            housekeeping,
            vehicle,
            environment,
            emergency,
            findings,
            actions,
            responsible,
            target,
            status,
            evidence,
            created_at
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS audits(
            id INTEGER PRIMARY KEY,
            date,
            location,
            audit_type,
            auditor,
            scope,
            findings,
            nc,
            good_practices,
            actions,
            responsible,
            target,
            status,
            evidence,
            created_at
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS capa(
            id INTEGER PRIMARY KEY,
            date,
            source,
            location,
            finding,
            root_cause,
            corrective,
            preventive,
            responsible,
            target,
            priority,
            status,
            verification,
            closeout,
            evidence,
            created_at
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS files(
            id INTEGER PRIMARY KEY,
            module,
            record_id,
            path,
            description,
            created_at
        )
        """)

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
            [data[x] for x in keys]
        )

        self.connection.commit()

        return self.connection.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

    def count(self, table):
        return self.connection.execute(
            "SELECT COUNT(*) FROM " + table
        ).fetchone()[0]

    def status_count(self, table, status):
        return self.connection.execute(
            "SELECT COUNT(*) FROM " + table + " WHERE status=?",
            (status,)
        ).fetchone()[0]

    def rows(self, table):

        return self.connection.execute(
            "SELECT * FROM "
            + table
            + " ORDER BY id DESC LIMIT 100"
        ).fetchall()

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


class HSEApp(App):

    def build(self):

        Window.clearcolor = BG

        self.app_dir = os.path.join(
            self.user_data_dir,
            "HSE_POCKET"
        )

        os.makedirs(
            self.app_dir,
            exist_ok=True
        )

        self.db = Database(
            os.path.join(
                self.app_dir,
                "hse_pocket.db"
            )
        )

        self.screen_manager = ScreenManager()

        pages = [
            ("home", self.home),
            ("observations", self.observations),
            ("incidents", self.incidents),
            ("inspections", self.inspections),
            ("audits", self.audits),
            ("capa", self.capa),
            ("files", self.files),
        ]

        for name, function in pages:

            screen = Screen(name=name)

            screen.add_widget(
                function()
            )

            self.screen_manager.add_widget(
                screen
            )

        return self.screen_manager

    def go(self, name):

        self.screen_manager.current = name

        if name == "home":
            self.refresh_dashboard()

    def navigation(self):

        bar = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            spacing=dp(2),
            padding=dp(2)
        )

        items = [
            ("HOME", "home"),
            ("OBS", "observations"),
            ("INC", "incidents"),
            ("INSP", "inspections"),
            ("AUDIT", "audits"),
            ("CAPA", "capa"),
            ("FILES", "files"),
        ]

        for title, name in items:

            button = B(
                title,
                NAVY,
                50,
                8
            )

            button.bind(
                on_release=lambda _, n=name: self.go(n)
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
            L(
                title,
                19,
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
            minimum_height=grid.setter("height")
        )

        scroll.add_widget(grid)

        return scroll, grid

    # =========================================================
    # DASHBOARD
    # =========================================================

    def home(self):

        scroll, grid = self.form()

        header_card = Card(
            orientation="vertical",
            padding=dp(13),
            size_hint_y=None,
            height=dp(90)
        )

        header_card.add_widget(
            L(
                "HSE-POCKET",
                25,
                NAVY,
                True,
                38
            )
        )

        header_card.add_widget(
            L(
                "Health, Safety & Environment Management",
                12,
                MUTED,
                False,
                25
            )
        )

        grid.add_widget(header_card)

        grid.add_widget(
            L(
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
            L(
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

        quick_items = [
            ("NEW OBSERVATION", BLUE, "observations"),
            ("NEW INCIDENT", RED, "incidents"),
            ("NEW INSPECTION", TEAL, "inspections"),
            ("NEW CAPA", PURPLE, "capa"),
        ]

        for title, color, name in quick_items:

            button = B(
                title,
                color,
                43,
                9
            )

            button.bind(
                on_release=lambda _, n=name: self.go(n)
            )

            quick.add_widget(button)

        grid.add_widget(quick)

        self.dashboard_summary = L(
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
            L(
                "RECENT ACTIVITY",
                16,
                NAVY,
                True,
                30
            )
        )

        self.recent_activity = L(
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

        refresh_button = B(
            "REFRESH DASHBOARD",
            NAVY,
            44
        )

        refresh_button.bind(
            on_release=lambda _: self.refresh_dashboard()
        )

        grid.add_widget(refresh_button)

        root = BoxLayout(
            orientation="vertical"
        )

        root.add_widget(scroll)
        root.add_widget(self.navigation())

        self.refresh_dashboard()

        return root

    def refresh_dashboard(self):

        if not hasattr(self, "dashboard_cards"):
            return

        self.dashboard_cards.clear_widgets()

        sections = [
            ("OBSERVATIONS", "observations", BLUE),
            ("INCIDENTS", "incidents", RED),
            ("INSPECTIONS", "inspections", TEAL),
            ("AUDITS", "audits", GREEN),
            ("CAPA", "capa", PURPLE),
            ("FILES", "files", ORANGE),
        ]

        for title, table, color in sections:

            number = self.db.count(table)

            card = Card(
                orientation="vertical",
                padding=dp(9),
                size_hint_y=None,
                height=dp(88)
            )

            card.add_widget(
                L(
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
                L(
                    number,
                    24,
                    NAVY,
                    True,
                    40
                )
            )

            open_button = B(
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
                on_release=lambda _, n=destination: self.go(n)
            )

            row.add_widget(open_button)

            card.add_widget(row)

            self.dashboard_cards.add_widget(card)

        total = sum(
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
                total,
                open_actions,
                now()
            )
        )

        recent = self.db.recent()

        if recent:

            self.recent_activity.text = "\n".join(
                "%s #%s | %s | %s | %s" % item
                for item in recent
            )

        else:

            self.recent_activity.text = (
                "No records yet."
            )

    # =========================================================
    # OBSERVATIONS
    # =========================================================

    def observations(self):

        scroll, grid = self.form()

        grid.add_widget(
            L(
                "OBSERVATION MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.obs_date = I("Date")
        self.obs_date.text = today()

        self.obs_location = I("Location *")
        self.obs_responsible = I("Responsible Person")
        self.obs_designation = I("Responsible Designation")

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

        self.obs_description = I(
            "Observation *",
            100,
            True
        )

        self.obs_action = I(
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

        self.obs_by = I("Observed By")

        self.obs_evidence = I(
            "Evidence / Photo / File Reference",
            70,
            True
        )

        widgets = [
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
        ]

        for widget in widgets:
            grid.add_widget(widget)

        save = B(
            "SAVE OBSERVATION",
            BLUE,
            46
        )

        save.bind(
            on_release=lambda _: self.save_observation()
        )

        grid.add_widget(save)

        view = B(
            "VIEW OBSERVATION REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _: self.view_register(
                "observations"
            )
        )

        grid.add_widget(view)

        return self.page(
            "Observations",
            scroll
        )

    def save_observation(self):

        if not self.obs_location.text.strip():

            msg(
                "Required",
                "Location is required."
            )

            return

        if not self.obs_description.text.strip():

            msg(
                "Required",
                "Observation is required."
            )

            return

        record = {
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
            "created_at": now()
        }

        record_id = self.db.add(
            "observations",
            record
        )

        msg(
            "Saved",
            "Observation #%d saved successfully."
            % record_id
        )

        self.refresh_dashboard()

    # =========================================================
    # INCIDENT / ACCIDENT INVESTIGATION
    # =========================================================

    def incidents(self):

        scroll, grid = self.form()

        grid.add_widget(
            L(
                "INCIDENT / ACCIDENT INVESTIGATION",
                16,
                NAVY,
                True,
                30
            )
        )

        grid.add_widget(
            L(
                "ICAM + RCA + 5-WHY + FISHBONE + BOW-TIE",
                11,
                MUTED,
                True,
                30
            )
        )

        self.inc_date = I("Date")
        self.inc_date.text = today()

        self.inc_time = I("Time")
        self.inc_location = I("Location *")
        self.inc_project = I("Project / Area")
        self.inc_activity = I("Activity")
        self.inc_title = I("Incident Title *")

        for widget in [
            self.inc_date,
            self.inc_time,
            self.inc_location,
            self.inc_project,
            self.inc_activity,
            self.inc_title
        ]:
            grid.add_widget(widget)

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

        # -----------------------------------------------------
        # BASIC INVESTIGATION INFORMATION
        # -----------------------------------------------------

        grid.add_widget(
            L(
                "INCIDENT INFORMATION",
                13,
                RED,
                True,
                28
            )
        )

        investigation_fields = [
            ("inc_description", "Detailed Incident Description", 120),
            ("inc_consequence", "Actual Consequence", 70),
            ("inc_potential", "Potential Consequence", 70),
            ("inc_people", "Persons Involved / Roles", 80),
            ("inc_injury", "Injury / Illness Details", 80),
            ("inc_damage", "Property / Equipment Damage", 70),
            ("inc_environment", "Environmental Impact", 70),
            ("inc_witnesses", "Witnesses / Statements", 80),
            ("inc_immediate", "Immediate Action / Containment", 90),
            ("inc_evidence", "Evidence / Photos / Documents / File References", 80),
            ("inc_investigator", "Investigation Leader", 44),
            ("inc_team", "Investigation Team", 60),
            ("inc_scope", "Investigation Scope / Terms", 80),
            ("inc_timeline", "Sequence / Timeline", 110),
            ("inc_statements", "Statements / Evidence Findings", 100)
        ]

        for name, hint, height in investigation_fields:

            widget = I(
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

        # -----------------------------------------------------
        # ICAM
        # -----------------------------------------------------

        grid.add_widget(
            L(
                "ICAM ANALYSIS",
                13,
                RED,
                True,
                28
            )
        )

        icam_fields = [
            (
                "icam_event",
                "Event / Incident"
            ),
            (
                "icam_individual",
                "Individual / Team Actions"
            ),
            (
                "icam_task",
                "Task / Environmental Conditions"
            ),
            (
                "icam_org",
                "Organisational Factors"
            ),
            (
                "icam_defences",
                "Absent / Failed Defences and Barriers"
            ),
            (
                "icam_actions",
                "ICAM Actions / Defence Improvements"
            )
        ]

        for name, hint in icam_fields:

            widget = I(
                hint,
                90 if name not in [
                    "icam_defences",
                    "icam_actions"
                ] else 100,
                True
            )

            setattr(
                self,
                name,
                widget
            )

            grid.add_widget(widget)

        # -----------------------------------------------------
        # ROOT CAUSE ANALYSIS
        # -----------------------------------------------------

        grid.add_widget(
            L(
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

        rca_fields = [
            (
                "direct_cause",
                "Direct / Immediate Cause",
                80
            ),
            (
                "underlying_cause",
                "Underlying Cause",
                80
            ),
            (
                "root_cause",
                "Root Cause",
                100
            ),
            (
                "contributing",
                "Contributing Factors",
                90
            ),
            (
                "five_whys",
                "5-Why Analysis - Why 1 to Why 5",
                120
            ),
            (
                "fishbone",
                "Fishbone / Ishikawa - People / Method / Machine / Material / Environment / Management / Measurement",
                130
            ),
            (
                "bowtie",
                "Bow-Tie - Threats / Top Event / Preventive Barriers / Consequences / Mitigating Barriers / Barrier Failures",
                130
            )
        ]

        for name, hint, height in rca_fields:

            widget = I(
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

        # -----------------------------------------------------
        # ACTIONS
        # -----------------------------------------------------

        grid.add_widget(
            L(
                "CORRECTIVE / PREVENTIVE ACTION",
                13,
                GREEN,
                True,
                28
            )
        )

        action_fields = [
            (
                "inc_corrective",
                "Corrective Actions",
                100
            ),
            (
                "inc_preventive",
                "Preventive Actions",
                100
            ),
            (
                "inc_system",
                "System / Management Improvement",
                90
            ),
            (
                "inc_responsible",
                "Responsible Person",
                44
            ),
            (
                "inc_target",
                "Target Date",
                44
            )
        ]

        for name, hint, height in action_fields:

            widget = I(
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

        self.inc_verification = I(
            "Verification / Effectiveness Check",
            90,
            True
        )

        self.inc_closeout = I(
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

        save = B(
            "SAVE COMPLETE INVESTIGATION",
            RED,
            48
        )

        save.bind(
            on_release=lambda _: self.save_incident()
        )

        grid.add_widget(save)

        view = B(
            "VIEW INCIDENT REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _: self.view_register(
                "incidents"
            )
        )

        grid.add_widget(view)

        return self.page(
            "Incident Investigation",
            scroll
        )

    def save_incident(self):

        if not self.inc_location.text.strip():

            msg(
                "Required",
                "Incident location is required."
            )

            return

        if not self.inc_title.text.strip():

            msg(
                "Required",
                "Incident title is required."
            )

            return

        def value(name):
            return getattr(
                self,
                name
            ).text

        record = {
            "date": value("inc_date"),
            "time": value("inc_time"),
            "location": value("inc_location"),
            "project": value("inc_project"),
            "activity": value("inc_activity"),
            "classification": self.inc_classification.text,
            "severity": self.inc_severity.text,
            "title": value("inc_title"),
            "description": value("inc_description"),
            "consequence": value("inc_consequence"),
            "potential_consequence": value("inc_potential"),
            "people": value("inc_people"),
            "injury": value("inc_injury"),
            "damage": value("inc_damage"),
            "environment": value("inc_environment"),
            "witnesses": value("inc_witnesses"),
            "immediate": value("inc_immediate"),
            "evidence": value("inc_evidence"),
            "investigator": value("inc_investigator"),
            "team": value("inc_team"),
            "scope": value("inc_scope"),
            "timeline": value("inc_timeline"),
            "statements": value("inc_statements"),

            "icam_event": value("icam_event"),
            "icam_individual": value("icam_individual"),
            "icam_task": value("icam_task"),
            "icam_org": value("icam_org"),
            "icam_defences": value("icam_defences"),
            "icam_actions": value("icam_actions"),

            "rca_method": self.rca_method.text,
            "direct_cause": value("direct_cause"),
            "underlying_cause": value("underlying_cause"),
            "root_cause": value("root_cause"),
            "contributing": value("contributing"),
            "five_whys": value("five_whys"),
            "fishbone": value("fishbone"),
            "bowtie": value("bowtie"),

            "corrective": value("inc_corrective"),
            "preventive": value("inc_preventive"),
            "system_action": value("inc_system"),
            "responsible": value("inc_responsible"),
            "target": value("inc_target"),
            "priority": self.inc_priority.text,
            "status": self.inc_status.text,
            "verification": value("inc_verification"),
            "closeout": value("inc_closeout"),
            "created_at": now()
        }

        record_id = self.db.add(
            "incidents",
            record
        )

        msg(
            "Saved",
            "Complete incident investigation #%d saved."
            % record_id
        )

        self.refresh_dashboard()

    # =========================================================
    # INSPECTIONS
    # =========================================================

    def inspections(self):

        scroll, grid = self.form()

        grid.add_widget(
            L(
                "INSPECTION MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.ins_date = I("Date")
        self.ins_date.text = today()

        self.ins_time = I("Time")
        self.ins_location = I("Location *")
        self.ins_type = I("Inspection Type")
        self.inspector = I("Inspector")
        self.ins_activity = I("Activity / Work Area")

        fields = [
            self.ins_date,
            self.ins_time,
            self.ins_location,
            self.ins_type,
            self.inspector,
            self.ins_activity
        ]

        for widget in fields:
            grid.add_widget(widget)

        inspection_fields = [
            ("Checklist / Areas Checked", 100),
            ("Unsafe Acts", 80),
            ("Unsafe Conditions", 80),
            ("Good Practices", 80),
            ("PPE", 65),
            ("Excavation", 65),
            ("Work at Height", 65),
            ("Lifting", 65),
            ("Scaffolding", 65),
            ("Electrical", 65),
            ("Confined Space", 65),
            ("Hot Work", 65),
            ("Fire Safety", 65),
            ("Housekeeping", 65),
            ("Vehicle / Plant", 65),
            ("Environmental", 65),
            ("Emergency Preparedness", 65),
            ("Findings", 100),
            ("Actions Required", 100),
            ("Responsible Person", 44),
            ("Target Date", 44)
        ]

        self.inspection_widgets = []

        for hint, height in inspection_fields:

            widget = I(
                hint,
                height,
                height > 60
            )

            self.inspection_widgets.append(widget)
            grid.add_widget(widget)

        self.ins_status = Spinner(
            text="Open",
            values=[
                "Open",
                "Closed"
            ],
            size_hint_y=None,
            height=dp(44)
        )

        self.ins_evidence = I(
            "Evidence / Photo / File Reference",
            70,
            True
        )

        grid.add_widget(
            self.ins_status
        )

        grid.add_widget(
            self.ins_evidence
        )

        save = B(
            "SAVE INSPECTION",
            TEAL,
            46
        )

        save.bind(
            on_release=lambda _: self.save_inspection()
        )

        grid.add_widget(save)

        view = B(
            "VIEW INSPECTION REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _: self.view_register(
                "inspections"
            )
        )

        grid.add_widget(view)

        return self.page(
            "Inspections",
            scroll
        )

    def save_inspection(self):

        keys = [
            "date",
            "time",
            "location",
            "inspection_type",
            "inspector",
            "activity",
            "checklist",
            "unsafe_acts",
            "unsafe_conditions",
            "good_practices",
            "ppe",
            "excavation",
            "wah",
            "lifting",
            "scaffolding",
            "electrical",
            "confined_space",
            "hot_work",
            "fire",
            "housekeeping",
            "vehicle",
            "environment",
            "emergency",
            "findings",
            "actions",
            "responsible",
            "target"
        ]

        data = {}

        for index, key in enumerate(keys):

            data[key] = (
                self.inspection_widgets[index].text
            )

        if not data["location"].strip():

            msg(
                "Required",
                "Inspection location is required."
            )

            return

        data["status"] = self.ins_status.text
        data["evidence"] = self.ins_evidence.text
        data["created_at"] = now()

        record_id = self.db.add(
            "inspections",
            data
        )

        msg(
            "Saved",
            "Inspection #%d saved successfully."
            % record_id
        )

        self.refresh_dashboard()

    # =========================================================
    # AUDITS
    # =========================================================

    def audits(self):

        scroll, grid = self.form()

        grid.add_widget(
            L(
                "HSE AUDIT MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.audit_widgets = [
            I("Date"),
            I("Location *"),
            I("Audit Type"),
            I("Auditor / Team"),
            I("Scope / Standard", 80, True),
            I("Findings / Nonconformities", 110, True),
            I("Good Practices / Strengths", 80, True),
            I("Corrective Actions", 100, True),
            I("Responsible Person"),
            I("Target Date")
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

        self.audit_evidence = I(
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

        save = B(
            "SAVE AUDIT",
            GREEN,
            46
        )

        save.bind(
            on_release=lambda _: self.save_audit()
        )

        grid.add_widget(save)

        view = B(
            "VIEW AUDIT REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _: self.view_register(
                "audits"
            )
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

            msg(
                "Required",
                "Audit location is required."
            )

            return

        data["status"] = self.audit_status.text
        data["evidence"] = self.audit_evidence.text
        data["created_at"] = now()

        record_id = self.db.add(
            "audits",
            data
        )

        msg(
            "Saved",
            "Audit #%d saved successfully."
            % record_id
        )

        self.refresh_dashboard()

    # =========================================================
    # CAPA
    # =========================================================

    def capa(self):

        scroll, grid = self.form()

        grid.add_widget(
            L(
                "CAPA MANAGEMENT",
                16,
                NAVY,
                True,
                30
            )
        )

        self.capa_widgets = [
            I("Date"),
            I("Source"),
            I("Location"),
            I("Finding *", 100, True),
            I("Root Cause", 90, True),
            I("Corrective Action", 100, True),
            I("Preventive Action", 100, True),
            I("Responsible Person"),
            I("Target Date")
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

        self.capa_verification = I(
            "Verification / Effectiveness",
            80,
            True
        )

        self.capa_closeout = I(
            "Closeout",
            80,
            True
        )

        self.capa_evidence = I(
            "Closeout Evidence / File Reference",
            70,
            True
        )

        grid.add_widget(
            self.capa_priority
        )

        grid.add_widget(
            self.capa_status
        )

        grid.add_widget(
            self.capa_verification
        )

        grid.add_widget(
            self.capa_closeout
        )

        grid.add_widget(
            self.capa_evidence
        )

        save = B(
            "SAVE CAPA",
            PURPLE,
            46
        )

        save.bind(
            on_release=lambda _: self.save_capa()
        )

        grid.add_widget(save)

        view = B(
            "VIEW CAPA REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _: self.view_register(
                "capa"
            )
        )

        grid.add_widget(view)

        export = B(
            "EXPORT CAPA CSV",
            TEAL,
            42
        )

        export.bind(
            on_release=lambda _: self.export_csv(
                "capa"
            )
        )

        grid.add_widget(export)

        return self.page(
            "CAPA",
            scroll
        )

    def save_capa(self):

        if not self.capa_widgets[3].text.strip():

            msg(
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

        msg(
            "Saved",
            "CAPA #%d saved successfully."
            % record_id
        )

        self.refresh_dashboard()

    # =========================================================
    # FILES & EVIDENCE
    # =========================================================

    def files(self):

        scroll, grid = self.form()

        grid.add_widget(
            L(
                "FILES & EVIDENCE",
                16,
                NAVY,
                True,
                30
            )
        )

        grid.add_widget(
            L(
                "Store photo, document, report or file references against any HSE record.",
                11,
                MUTED,
                False,
                42
            )
        )

        self.file_module = Spinner(
            text="Incident",
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

        self.file_record_id = I(
            "Record ID *"
        )

        self.file_path = I(
            "File path / photo / document reference *",
            75,
            True
        )

        self.file_description = I(
            "Description",
            70,
            True
        )

        grid.add_widget(
            self.file_module
        )

        grid.add_widget(
            self.file_record_id
        )

        grid.add_widget(
            self.file_path
        )

        grid.add_widget(
            self.file_description
        )

        save = B(
            "SAVE FILE REFERENCE",
            ORANGE,
            46
        )

        save.bind(
            on_release=lambda _: self.save_file_reference()
        )

        grid.add_widget(save)

        view = B(
            "VIEW FILE REGISTER",
            NAVY,
            42
        )

        view.bind(
            on_release=lambda _: self.view_files()
        )

        grid.add_widget(view)

        return self.page(
            "Files & Evidence",
            scroll
        )

    def save_file_reference(self):

        try:

            record_id = int(
                self.file_record_id.text.strip()
            )

        except ValueError:

            msg(
                "Invalid",
                "Record ID must be a number."
            )

            return

        if not self.file_path.text.strip():

            msg(
                "Required",
                "File reference is required."
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

        msg(
            "Saved",
            "File reference saved successfully."
        )

    # =========================================================
    # REGISTERS
    # =========================================================

    def view_files(self):

        rows = self.db.connection.execute(
            """
            SELECT
                id,
                module,
                record_id,
                path,
                description,
                created_at
            FROM files
            ORDER BY id DESC
            """
        ).fetchall()

        if not rows:

            msg(
                "FILE REGISTER",
                "No file references found."
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

        msg(
            "FILE REGISTER",
            "\n\n----------------\n\n".join(output)
        )

    def view_register(self, table):

        rows = self.db.rows(table)

        if not rows:

            msg(
                table.upper() + " REGISTER",
                "No records found."
            )

            return

        output = []

        for row in rows:

            lines = []

            for index, value in enumerate(row):

                if value in (None, ""):
                    value = "-"

                lines.append(
                    "%d: %s"
                    % (
                        index + 1,
                        value
                    )
                )

            output.append(
                "\n".join(lines)
            )

        msg(
            table.upper() + " REGISTER",
            "\n\n----------------\n\n".join(output)
        )

    # =========================================================
    # CSV EXPORT
    # =========================================================

    def export_csv(self, table):

        rows = self.db.rows(table)

        if not rows:

            msg(
                "EXPORT",
                "No records available."
            )

            return

        file_name = (
            table
            + "_register_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".csv"
        )

        path = os.path.join(
            self.app_dir,
            file_name
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

        msg(
            "EXPORT COMPLETE",
            path
        )

    # =========================================================
    # APP CLOSE
    # =========================================================

    def on_stop(self):

        try:
            self.db.connection.close()
        except Exception:
            pass


if __name__ == "__main__":
    HSEApp().run()