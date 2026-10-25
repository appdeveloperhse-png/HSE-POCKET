import csv
import os
import sqlite3
from datetime import datetime, date
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner
from kivy.uix.textinput import TextInput

APP_TITLE = "HSE Management System"
HAZARD_CATEGORIES = [
    "PPE", "Excavation", "Work at Height", "Scaffolding", "Lifting Operations",
    "Confined Space", "Electrical Safety", "Fire / Hot Work", "Housekeeping",
    "Manual Handling", "Plant / Equipment", "Vehicle / Traffic", "Chemical Safety",
    "Heat Stress", "Environmental", "Dropped Objects", "Permit to Work", "Other"
]
STATUSES = ["Open", "In Progress", "Closed"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

MODULES = {
    "Observations": [
        "Observation number", "Project / company", "Location / area",
        "Observer name", "Observer designation", "Date of observation",
        "Hazard category", "Observation description", "Corrective action",
        "Responsible person", "Target date",
    ],
    "Incidents": [
        "Incident number", "Project / company", "Location / area",
        "Incident description", "Immediate action", "Investigation findings",
        "Responsible person", "Incident date",
    ],
    "Inspections": [
        "Inspection number", "Project / company", "Location / area",
        "Inspection findings", "Immediate action", "Corrective action",
        "Inspector", "Inspection date",
    ],
    "Audits": [
        "Audit number", "Project / company", "Location / area", "Audit findings",
        "Immediate action", "Corrective action", "Auditor", "Audit date",
    ],
    "CAPA": [
        "CAPA number", "Project / company", "Location / area",
        "Non-conformity / finding", "Immediate correction",
        "Corrective / preventive action", "Responsible person", "Target date",
    ],
}


class HSEDatabase:
    def __init__(self, path):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                module TEXT NOT NULL,
                record_number TEXT DEFAULT '',
                project TEXT DEFAULT '',
                location TEXT DEFAULT '',
                description TEXT DEFAULT '',
                immediate_action TEXT DEFAULT '',
                corrective_action TEXT DEFAULT '',
                responsible TEXT DEFAULT '',
                target_date TEXT DEFAULT '',
                priority TEXT DEFAULT 'Medium',
                status TEXT DEFAULT 'Open',
                created_at TEXT NOT NULL
            )
        """)
        # Safe, additive migration: existing records and columns are retained.
        existing = {r[1] for r in self.conn.execute("PRAGMA table_info(records)").fetchall()}
        for name in ("observer_name", "observer_designation", "observation_date", "hazard_category"):
            if name not in existing:
                self.conn.execute(f"ALTER TABLE records ADD COLUMN {name} TEXT DEFAULT ''")
        self.conn.commit()

    def add(self, module, values):
        self.conn.execute("""
            INSERT INTO records (
                module, record_number, project, location, description,
                immediate_action, corrective_action, responsible, target_date,
                priority, status, created_at, observer_name, observer_designation,
                observation_date, hazard_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            module, values.get("number", ""), values.get("project", ""),
            values.get("location", ""), values.get("description", ""),
            values.get("immediate_action", ""), values.get("corrective_action", ""),
            values.get("responsible", ""), values.get("target_date", ""),
            values.get("priority", "Medium"), values.get("status", "Open"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            values.get("observer_name", ""), values.get("observer_designation", ""),
            values.get("observation_date", ""), values.get("hazard_category", "")
        ))
        self.conn.commit()

    def next_observation_number(self):
        rows = self.conn.execute(
            "SELECT record_number FROM records WHERE module='Observations'"
        ).fetchall()
        year = datetime.now().year
        max_num = 0
        prefix = f"OBS-{year}-"
        for row in rows:
            value = row["record_number"] or ""
            if value.startswith(prefix):
                try:
                    max_num = max(max_num, int(value[len(prefix):]))
                except ValueError:
                    pass
        return f"{prefix}{max_num + 1:04d}"

    def list_records(self, module=None, search=""):
        sql = "SELECT * FROM records WHERE 1=1"
        args = []
        if module:
            sql += " AND module=?"
            args.append(module)
        if search.strip():
            term = "%" + search.strip() + "%"
            sql += " AND (record_number LIKE ? OR project LIKE ? OR location LIKE ? OR description LIKE ? OR responsible LIKE ? OR status LIKE ? OR observer_name LIKE ? OR observer_designation LIKE ? OR hazard_category LIKE ?)"
            args.extend([term] * 9)
        sql += " ORDER BY id DESC"
        return self.conn.execute(sql, args).fetchall()

    def counts(self):
        result = {}
        for module in MODULES:
            result[module] = self.conn.execute(
                "SELECT COUNT(*) FROM records WHERE module=?", (module,)
            ).fetchone()[0]
        result["Open"] = self.conn.execute("SELECT COUNT(*) FROM records WHERE status='Open'").fetchone()[0]
        result["In Progress"] = self.conn.execute("SELECT COUNT(*) FROM records WHERE status='In Progress'").fetchone()[0]
        result["Closed"] = self.conn.execute("SELECT COUNT(*) FROM records WHERE status='Closed'").fetchone()[0]
        return result

    def set_status(self, record_id, status):
        self.conn.execute("UPDATE records SET status=? WHERE id=?", (status, record_id))
        self.conn.commit()

    def export_csv(self, module, output_path):
        rows = self.list_records(module)
        columns = ["id", "module", "record_number", "project", "location", "observer_name", "observer_designation", "observation_date", "hazard_category", "description", "immediate_action", "corrective_action", "responsible", "target_date", "priority", "status", "created_at"]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row[column] if column in row.keys() else "" for column in columns])
        return len(rows)

    def close(self):
        self.conn.close()


def make_button(text, callback, height=dp(48), color=(0.12, 0.35, 0.62, 1)):
    button = Button(text=text, size_hint_y=None, height=height, font_size="15sp",
                    background_normal="", background_color=color, color=(1, 1, 1, 1))
    button.bind(on_release=lambda *_: callback())
    return button


def show_message(title, message):
    content = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    content.add_widget(Label(text=message, halign="center", valign="middle"))
    popup = Popup(title=title, content=content, size_hint=(0.88, 0.42), auto_dismiss=True)
    content.add_widget(make_button("OK", popup.dismiss))
    popup.open()


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        self.layout.clear_widgets()
        app = App.get_running_app()
        self.layout.add_widget(Label(text="[b]HSE MANAGEMENT SYSTEM[/b]", markup=True,
                                     font_size="24sp", color=(0.08, 0.28, 0.48, 1),
                                     size_hint_y=None, height=dp(54)))
        self.layout.add_widget(Label(text="Safety 鈥� Compliance 鈥� Continuous Improvement",
                                     size_hint_y=None, height=dp(30), color=(0.25, 0.35, 0.45, 1)))
        counts = app.db.counts()
        self.layout.add_widget(Label(text=f"OPEN  {counts['Open']}     IN PROGRESS  {counts['In Progress']}     CLOSED  {counts['Closed']}",
                                     size_hint_y=None, height=dp(40), color=(0.05, 0.38, 0.30, 1)))
        scroll = ScrollView()
        items = BoxLayout(orientation="vertical", spacing=dp(9), size_hint_y=None, padding=(0, dp(5)))
        items.bind(minimum_height=items.setter("height"))
        items.add_widget(make_button(f"馃煢  OBSERVATION REGISTER  鈥�  {counts['Observations']} records", self.open_observations, dp(58), (0.05, 0.42, 0.65, 1)))
        items.add_widget(make_button(f"Incident Register  鈥�  {counts['Incidents']} records", lambda: self.open_module("Incidents"), dp(52), (0.70, 0.25, 0.20, 1)))
        items.add_widget(make_button(f"Inspection Register  鈥�  {counts['Inspections']} records", lambda: self.open_module("Inspections"), dp(52), (0.13, 0.48, 0.39, 1)))
        items.add_widget(make_button(f"Audit Register  鈥�  {counts['Audits']} records", lambda: self.open_module("Audits"), dp(52), (0.43, 0.30, 0.62, 1)))
        items.add_widget(make_button(f"CAPA Register  鈥�  {counts['CAPA']} records", lambda: self.open_module("CAPA"), dp(52), (0.72, 0.43, 0.10, 1)))
        items.add_widget(make_button("About / Data storage", lambda: show_message("About", "Records are stored in this app's private local database. Export CSV backups regularly. This app does not synchronise records to a server."), dp(46), (0.30, 0.36, 0.42, 1)))
        scroll.add_widget(items)
        self.layout.add_widget(scroll)

    def open_observations(self):
        self.manager.current = "observation_hub"

    def open_module(self, module):
        screen = self.manager.get_screen("register")
        screen.configure(module)
        self.manager.current = "register"


class ObservationHubScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(9))
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        self.layout.clear_widgets()
        app = App.get_running_app()
        counts = app.db.counts()
        header = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        header.add_widget(make_button("鈫� Home", lambda: setattr(self.manager, "current", "dashboard"), dp(42), (0.30, 0.36, 0.42, 1)))
        header.add_widget(Label(text="[b]OBSERVATION REGISTER[/b]", markup=True, font_size="19sp", color=(0.05, 0.35, 0.55, 1)))
        self.layout.add_widget(header)
        self.layout.add_widget(Label(text=f"Total: {counts['Observations']}     Open: {counts['Open']}     In Progress: {counts['In Progress']}     Closed: {counts['Closed']}", size_hint_y=None, height=dp(42)))
        scroll = ScrollView()
        menu = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None, padding=(0, dp(4)))
        menu.bind(minimum_height=menu.setter("height"))
        menu.add_widget(make_button("馃搳  Observation Dashboard\nTrends and status overview", lambda: self.open_screen("observation_dashboard"), dp(72), (0.10, 0.47, 0.65, 1)))
        menu.add_widget(make_button("锛�  Raise Observation\nCreate a new observation", lambda: self.open_screen("observation_form"), dp(72), (0.12, 0.52, 0.36, 1)))
        menu.add_widget(make_button("鈻�  Master Register\nView all saved observations", lambda: self.open_screen("observation_master"), dp(72), (0.44, 0.32, 0.64, 1)))
        menu.add_widget(make_button("鈬�  Reports\nExport the Master Register for Excel", lambda: self.open_screen("observation_reports"), dp(72), (0.75, 0.43, 0.10, 1)))
        self.layout.add_widget(scroll)
        scroll.add_widget(menu)

    def open_screen(self, name):
        self.manager.current = name


class ObservationDashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.layout.clear_widgets()
        app = App.get_running_app()
        rows = app.db.list_records("Observations")
        counts = {s: sum(1 for r in rows if r["status"] == s) for s in STATUSES}
        self.layout.add_widget(make_button("鈫� Observation Register", lambda: setattr(self.manager, "current", "observation_hub"), dp(42), (0.30, 0.36, 0.42, 1)))
        self.layout.add_widget(Label(text="[b]OBSERVATION DASHBOARD[/b]", markup=True, font_size="21sp", size_hint_y=None, height=dp(45), color=(0.05, 0.35, 0.55, 1)))
        self.layout.add_widget(Label(text=f"Total observations: {len(rows)}", size_hint_y=None, height=dp(38)))
        for status, color in (("Open", (0.75, 0.22, 0.18, 1)), ("In Progress", (0.78, 0.48, 0.08, 1)), ("Closed", (0.12, 0.48, 0.32, 1))):
            self.layout.add_widget(make_button(f"{status}: {counts[status]}", lambda: None, dp(45), color))
        hazards = {}
        for row in rows:
            for hazard in (row["hazard_category"] or "Uncategorised").split(", "):
                hazards[hazard] = hazards.get(hazard, 0) + 1
        self.layout.add_widget(Label(text="[b]Hazard category summary[/b]", markup=True, size_hint_y=None, height=dp(36)))
        scroll = ScrollView()
        content = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(4))
        content.bind(minimum_height=content.setter("height"))
        if hazards:
            for hazard, count in sorted(hazards.items(), key=lambda item: (-item[1], item[0])):
                content.add_widget(Label(text=f"{hazard}: {count}", size_hint_y=None, height=dp(30)))
        else:
            content.add_widget(Label(text="No observations saved yet.", size_hint_y=None, height=dp(35)))
        content.add_widget(Label(text="Predictive indicator: review repeated hazard categories and observations that remain Open or In Progress. This is a simple trend indicator, not an automated risk prediction.", size_hint_y=None, height=dp(90), halign="left", valign="middle"))
        scroll.add_widget(content)
        self.layout.add_widget(scroll)


class HazardPicker(BoxLayout):
    def __init__(self, initial="", **kwargs):
        super().__init__(orientation="vertical", spacing=dp(5), size_hint_y=None, **kwargs)
        self.bind(minimum_height=self.setter("height"))
        self.selected = set(x.strip() for x in initial.split(",") if x.strip())
        self.summary = Label(text=self.summary_text(), size_hint_y=None, height=dp(36), halign="left", valign="middle")
        self.add_widget(self.summary)
        self.add_widget(make_button("Choose hazard categories (multiple allowed)", self.open_picker, dp(42), (0.16, 0.43, 0.58, 1)))

    def summary_text(self):
        return "Selected: " + (", ".join(sorted(self.selected)) if self.selected else "None")

    def open_picker(self):
        body = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(5))
        scroll = ScrollView()
        choices = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(2))
        choices.bind(minimum_height=choices.setter("height"))
        checks = {}
        for category in HAZARD_CATEGORIES:
            line = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(8))
            cb = CheckBox(size_hint_x=None, width=dp(44), active=category in self.selected)
            checks[category] = cb
            line.add_widget(cb)
            line.add_widget(Label(text=category, halign="left", valign="middle"))
            choices.add_widget(line)
        scroll.add_widget(choices)
        body.add_widget(scroll)
        popup = Popup(title="Select hazard categories", content=body, size_hint=(0.92, 0.86))
        def save():
            self.selected = {name for name, cb in checks.items() if cb.active}
            self.summary.text = self.summary_text()
            popup.dismiss()
        body.add_widget(make_button("Save selection", save, dp(44)))
        popup.open()

    def value(self):
        return ", ".join(sorted(self.selected))


class ObservationFormScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.inputs = {}
        self.hazard_picker = None
        self.layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(7))
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.build_form()

    def build_form(self):
        self.layout.clear_widgets()
        self.inputs = {}
        app = App.get_running_app()
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        header.add_widget(make_button("鈫� Back", lambda: setattr(self.manager, "current", "observation_hub"), dp(40), (0.30, 0.36, 0.42, 1)))
        header.add_widget(Label(text="[b]RAISE OBSERVATION[/b]", markup=True, font_size="18sp"))
        self.layout.add_widget(header)
        scroll = ScrollView()
        form = BoxLayout(orientation="vertical", spacing=dp(6), padding=(dp(2), dp(4)), size_hint_y=None)
        form.bind(minimum_height=form.setter("height"))
        fields = [
            ("Observation number", app.db.next_observation_number(), False),
            ("Project / company", "", False), ("Location / area", "", False),
            ("Observer name", "", False), ("Observer designation", "", False),
            ("Date of observation", date.today().isoformat(), False),
        ]
        for name, default, multiline in fields:
            self.add_field(form, name, default, multiline)
        form.add_widget(Label(text="Hazard category (select all that apply)", size_hint_y=None, height=dp(26), halign="left"))
        self.hazard_picker = HazardPicker()
        form.add_widget(self.hazard_picker)
        self.add_field(form, "Observation description", "", True)
        self.add_field(form, "Corrective action", "", True)
        self.add_field(form, "Responsible person", "", False)
        self.add_field(form, "Target date", "", False)
        form.add_widget(Label(text="Priority", size_hint_y=None, height=dp(26), halign="left"))
        self.inputs["Priority"] = Spinner(text="Medium", values=PRIORITIES, size_hint_y=None, height=dp(44))
        form.add_widget(self.inputs["Priority"])
        form.add_widget(Label(text="Status", size_hint_y=None, height=dp(26), halign="left"))
        self.inputs["Status"] = Spinner(text="Open", values=STATUSES, size_hint_y=None, height=dp(44))
        form.add_widget(self.inputs["Status"])
        scroll.add_widget(form)
        self.layout.add_widget(scroll)
        self.layout.add_widget(make_button("Save Observation", self.save_observation, dp(50), (0.12, 0.52, 0.36, 1)))

    def add_field(self, form, name, default="", multiline=False):
        form.add_widget(Label(text=name, size_hint_y=None, height=dp(25), halign="left", valign="middle"))
        widget = TextInput(text=default, hint_text=name, multiline=multiline, size_hint_y=None, height=dp(84) if multiline else dp(44))
        self.inputs[name] = widget
        form.add_widget(widget)

    def save_observation(self):
        app = App.get_running_app()
        value = lambda key: self.inputs[key].text.strip()
        values = {
            "number": value("Observation number"), "project": value("Project / company"),
            "location": value("Location / area"), "observer_name": value("Observer name"),
            "observer_designation": value("Observer designation"), "observation_date": value("Date of observation"),
            "hazard_category": self.hazard_picker.value(), "description": value("Observation description"),
            "corrective_action": value("Corrective action"), "responsible": value("Responsible person"),
            "target_date": value("Target date"), "priority": self.inputs["Priority"].text,
            "status": self.inputs["Status"].text,
        }
        if not values["description"]:
            show_message("Required field", "Enter the observation description before saving.")
            return
        if not values["observer_name"]:
            show_message("Required field", "Enter the observer name.")
            return
        app.db.add("Observations", values)
        show_message("Saved", f"Observation {values['number']} saved to the Master Register.")
        self.manager.current = "observation_master"


class ObservationMasterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(6))
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.build_screen()

    def build_screen(self):
        self.layout.clear_widgets()
        header = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        header.add_widget(make_button("鈫� Back", lambda: setattr(self.manager, "current", "observation_hub"), dp(40), (0.30, 0.36, 0.42, 1)))
        header.add_widget(Label(text="[b]MASTER REGISTER[/b]", markup=True, font_size="18sp"))
        self.layout.add_widget(header)
        search = TextInput(hint_text="Search number, observer, location, hazard, status...", multiline=False, size_hint_y=None, height=dp(42))
        self.layout.add_widget(search)
        self.records = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.records.bind(minimum_height=self.records.setter("height"))
        scroll = ScrollView()
        scroll.add_widget(self.records)
        self.layout.add_widget(scroll)
        search.bind(text=lambda *_: self.refresh_records(search.text))
        self.refresh_records()

    def refresh_records(self, search=""):
        rows = App.get_running_app().db.list_records("Observations", search)
        self.records.clear_widgets()
        if not rows:
            self.records.add_widget(Label(text="No observations found.", size_hint_y=None, height=dp(42)))
            return
        for row in rows:
            detail = (f"[b]{row['record_number'] or 'No number'}[/b]  鈥�  {row['status']}\n"
                      f"{row['description']}\nProject: {row['project'] or '-'} | Location: {row['location'] or '-'}\n"
                      f"Observer: {row['observer_name'] or '-'} ({row['observer_designation'] or '-'}) | Date: {row['observation_date'] or '-'}\n"
                      f"Hazard: {row['hazard_category'] or '-'} | Priority: {row['priority']}\n"
                      f"Corrective action: {row['corrective_action'] or '-'} | Responsible: {row['responsible'] or '-'} | Target: {row['target_date'] or '-'}")
            card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4), size_hint_y=None, height=dp(200))
            card.add_widget(Label(text=detail, markup=True, halign="left", valign="middle", text_size=(None, None)))
            row_buttons = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(5))
            spinner = Spinner(text=row["status"], values=STATUSES, size_hint_x=0.6)
            spinner.bind(text=lambda instance, status, rid=row["id"]: App.get_running_app().db.set_status(rid, status))
            row_buttons.add_widget(spinner)
            row_buttons.add_widget(make_button("Refresh", self.build_screen, dp(36), (0.16, 0.43, 0.58, 1)))
            card.add_widget(row_buttons)
            self.records.add_widget(card)


class ObservationReportsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(8))
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.layout.clear_widgets()
        app = App.get_running_app()
        rows = app.db.list_records("Observations")
        self.layout.add_widget(make_button("鈫� Observation Register", lambda: setattr(self.manager, "current", "observation_hub"), dp(42), (0.30, 0.36, 0.42, 1)))
        self.layout.add_widget(Label(text="[b]OBSERVATION REPORTS[/b]", markup=True, font_size="21sp", size_hint_y=None, height=dp(48)))
        self.layout.add_widget(Label(text=f"The report is generated directly from the Master Register. Current records: {len(rows)}", size_hint_y=None, height=dp(60)))
        self.layout.add_widget(Label(text="Exports a UTF-8 CSV register that opens in Microsoft Excel. No separate Excel library is required.", size_hint_y=None, height=dp(70)))
        self.layout.add_widget(make_button("Export Master Register (Excel-compatible CSV)", self.export, dp(58), (0.75, 0.43, 0.10, 1)))

    def export(self):
        app = App.get_running_app()
        filename = f"observation_master_register_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = os.path.join(app.user_data_dir, filename)
        try:
            count = app.db.export_csv("Observations", path)
            show_message("Report exported", f"Exported {count} observation(s).\n\nSaved in app storage:\n{path}\n\nOpen the CSV file with Microsoft Excel.")
        except Exception as exc:
            show_message("Export failed", str(exc))


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.module = "Incidents"
        self.inputs = {}
        self.root_layout = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))
        self.add_widget(self.root_layout)

    def configure(self, module):
        self.module = module
        self.build_screen()

    def build_screen(self):
        self.root_layout.clear_widgets()
        self.inputs = {}
        header = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        header.add_widget(make_button("鈫� Dashboard", lambda: setattr(self.manager, "current", "dashboard"), dp(42), (0.30, 0.36, 0.42, 1)))
        header.add_widget(Label(text=f"[b]{self.module} Register[/b]", markup=True, font_size="18sp"))
        self.root_layout.add_widget(header)
        search = TextInput(hint_text="Search records", multiline=False, size_hint_y=None, height=dp(44))
        search.bind(text=lambda *_: self.refresh_records(search.text))
        self.root_layout.add_widget(search)
        form_scroll = ScrollView(size_hint_y=0.53)
        form = BoxLayout(orientation="vertical", spacing=dp(7), size_hint_y=None, padding=(dp(2), dp(4)))
        form.bind(minimum_height=form.setter("height"))
        for field in MODULES[self.module]:
            form.add_widget(Label(text=field, size_hint_y=None, height=dp(24), halign="left", valign="middle"))
            multiline = field in ("Incident description", "Inspection findings", "Audit findings", "Immediate action", "Corrective action", "Immediate correction", "Corrective / preventive action", "Investigation findings", "Non-conformity / finding")
            widget = TextInput(hint_text=field, multiline=multiline, size_hint_y=None, height=dp(84) if multiline else dp(44))
            self.inputs[field] = widget
            form.add_widget(widget)
        form.add_widget(Label(text="Priority", size_hint_y=None, height=dp(26)))
        self.inputs["Priority"] = Spinner(text="Medium", values=PRIORITIES, size_hint_y=None, height=dp(44))
        form.add_widget(self.inputs["Priority"])
        form.add_widget(Label(text="Status", size_hint_y=None, height=dp(26)))
        self.inputs["Status"] = Spinner(text="Open", values=STATUSES, size_hint_y=None, height=dp(44))
        form.add_widget(self.inputs["Status"])
        form_scroll.add_widget(form)
        self.root_layout.add_widget(form_scroll)
        buttons = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        buttons.add_widget(make_button("Save record", self.save_record))
        buttons.add_widget(make_button("Export CSV", self.export_csv, color=(0.15, 0.45, 0.35, 1)))
        self.root_layout.add_widget(buttons)
        self.records_label = Label(text="Recent records appear here", size_hint_y=None, height=dp(34))
        self.root_layout.add_widget(self.records_label)
        self.records_scroll = ScrollView(size_hint_y=0.48)
        self.records_list = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        self.records_list.bind(minimum_height=self.records_list.setter("height"))
        self.records_scroll.add_widget(self.records_list)
        self.root_layout.add_widget(self.records_scroll)
        self.refresh_records()

    def save_record(self):
        app = App.get_running_app()
        values = {
            "number": self.value_for("Incident number", "Inspection number", "Audit number", "CAPA number"),
            "project": self.value_for("Project / company"), "location": self.value_for("Location / area"),
            "description": self.value_for("Incident description", "Inspection findings", "Audit findings", "Non-conformity / finding"),
            "immediate_action": self.value_for("Immediate action", "Immediate correction"),
            "corrective_action": self.value_for("Corrective action", "Corrective / preventive action", "Investigation findings"),
            "responsible": self.value_for("Responsible person", "Inspector", "Auditor"),
            "target_date": self.value_for("Target date", "Incident date", "Inspection date", "Audit date"),
            "priority": self.inputs["Priority"].text.strip() or "Medium",
            "status": self.inputs["Status"].text.strip() or "Open",
        }
        if not values["description"].strip():
            show_message("Required field", "Enter a description or finding before saving.")
            return
        if values["status"] not in STATUSES:
            show_message("Invalid status", "Select Open, In Progress, or Closed.")
            return
        app.db.add(self.module, values)
        for widget in self.inputs.values():
            if isinstance(widget, TextInput):
                widget.text = ""
        self.inputs["Priority"].text = "Medium"
        self.inputs["Status"].text = "Open"
        show_message("Saved", f"{self.module} record saved locally.")
        self.refresh_records()

    def value_for(self, *names):
        for name in names:
            widget = self.inputs.get(name)
            if widget and widget.text.strip():
                return widget.text.strip()
        return ""

    def refresh_records(self, search=""):
        rows = App.get_running_app().db.list_records(self.module, search)
        self.records_list.clear_widgets()
        self.records_label.text = f"{self.module}: {len(rows)} record(s)"
        if not rows:
            self.records_list.add_widget(Label(text="No records found.", size_hint_y=None, height=dp(40)))
            return
        for row in rows:
            detail = f"#{row['id']}  |  {row['record_number'] or 'No number'}\n{row['description']}\nLocation: {row['location'] or '-'}\nPriority: {row['priority']}  |  Status: {row['status']}\nCreated: {row['created_at']}"
            card = BoxLayout(orientation="vertical", padding=dp(8), spacing=dp(4), size_hint_y=None, height=dp(156))
            card.add_widget(Label(text=detail, halign="left", valign="middle"))
            actions = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            actions.add_widget(make_button("Mark in progress", lambda rid=row["id"]: self.change_status(rid, "In Progress"), dp(38)))
            actions.add_widget(make_button("Close", lambda rid=row["id"]: self.change_status(rid, "Closed"), dp(38), (0.15, 0.45, 0.35, 1)))
            card.add_widget(actions)
            self.records_list.add_widget(card)

    def change_status(self, record_id, status):
        App.get_running_app().db.set_status(record_id, status)
        self.refresh_records()

    def export_csv(self):
        app = App.get_running_app()
        filename = f"{self.module.lower().replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = os.path.join(app.user_data_dir, filename)
        try:
            count = app.db.export_csv(self.module, path)
            show_message("CSV exported", f"Exported {count} record(s).\n\nSaved in app storage:\n{path}")
        except Exception as exc:
            show_message("Export failed", str(exc))


class HSEManagementApp(App):
    title = APP_TITLE

    def build(self):
        self.db = HSEDatabase(os.path.join(self.user_data_dir, "hse_management.db"))
        manager = ScreenManager()
        manager.add_widget(DashboardScreen(name="dashboard"))
        manager.add_widget(ObservationHubScreen(name="observation_hub"))
        manager.add_widget(ObservationDashboardScreen(name="observation_dashboard"))
        manager.add_widget(ObservationFormScreen(name="observation_form"))
        manager.add_widget(ObservationMasterScreen(name="observation_master"))
        manager.add_widget(ObservationReportsScreen(name="observation_reports"))
        manager.add_widget(RegisterScreen(name="register"))
        return manager

    def on_stop(self):
        if hasattr(self, "db"):
            self.db.close()


if __name__ == "__main__":
    HSEManagementApp().run()