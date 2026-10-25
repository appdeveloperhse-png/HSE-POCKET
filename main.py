
import csv
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput


APP_TITLE = "HSE Management System"

MODULES = {
    "Observations": [
        "Observation number",
        "Project / company",
        "Location / area",
        "Observation description",
        "Immediate action",
        "Corrective action",
        "Responsible person",
        "Target date",
    ],
    "Incidents": [
        "Incident number",
        "Project / company",
        "Location / area",
        "Incident description",
        "Immediate action",
        "Investigation findings",
        "Responsible person",
        "Incident date",
    ],
    "Inspections": [
        "Inspection number",
        "Project / company",
        "Location / area",
        "Inspection findings",
        "Immediate action",
        "Corrective action",
        "Inspector",
        "Inspection date",
    ],
    "Audits": [
        "Audit number",
        "Project / company",
        "Location / area",
        "Audit findings",
        "Immediate action",
        "Corrective action",
        "Auditor",
        "Audit date",
    ],
    "CAPA": [
        "CAPA number",
        "Project / company",
        "Location / area",
        "Non-conformity / finding",
        "Immediate correction",
        "Corrective / preventive action",
        "Responsible person",
        "Target date",
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
        self.conn.commit()

    def add(self, module, values):
        self.conn.execute("""
            INSERT INTO records (
                module, record_number, project, location,
                description, immediate_action, corrective_action,
                responsible, target_date, priority, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            module,
            values.get("number", ""),
            values.get("project", ""),
            values.get("location", ""),
            values.get("description", ""),
            values.get("immediate_action", ""),
            values.get("corrective_action", ""),
            values.get("responsible", ""),
            values.get("target_date", ""),
            values.get("priority", "Medium"),
            values.get("status", "Open"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ))
        self.conn.commit()

    def list_records(self, module=None, search=""):
        sql = "SELECT * FROM records WHERE 1=1"
        args = []

        if module:
            sql += " AND module=?"
            args.append(module)

        if search.strip():
            term = "%" + search.strip() + "%"
            sql += """
                AND (
                    record_number LIKE ? OR project LIKE ?
                    OR location LIKE ? OR description LIKE ?
                    OR responsible LIKE ? OR status LIKE ?
                )
            """
            args.extend([term] * 6)

        sql += " ORDER BY id DESC"
        return self.conn.execute(sql, args).fetchall()

    def counts(self):
        result = {}
        for module in MODULES:
            result[module] = self.conn.execute(
                "SELECT COUNT(*) FROM records WHERE module=?",
                (module,)
            ).fetchone()[0]

        result["Open"] = self.conn.execute(
            "SELECT COUNT(*) FROM records WHERE status='Open'"
        ).fetchone()[0]
        result["Closed"] = self.conn.execute(
            "SELECT COUNT(*) FROM records WHERE status='Closed'"
        ).fetchone()[0]
        return result

    def set_status(self, record_id, status):
        self.conn.execute(
            "UPDATE records SET status=? WHERE id=?",
            (status, record_id)
        )
        self.conn.commit()

    def export_csv(self, module, output_path):
        rows = self.list_records(module)
        columns = [
            "id", "module", "record_number", "project", "location",
            "description", "immediate_action", "corrective_action",
            "responsible", "target_date", "priority", "status", "created_at"
        ]
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(columns)
            for row in rows:
                writer.writerow([row[column] for column in columns])
        return len(rows)

    def close(self):
        self.conn.close()


def make_button(text, callback, height=dp(48)):
    button = Button(
        text=text,
        size_hint_y=None,
        height=height,
        font_size="15sp"
    )
    button.bind(on_release=lambda *_: callback())
    return button


def show_message(title, message):
    content = BoxLayout(
        orientation="vertical",
        padding=dp(12),
        spacing=dp(10)
    )
    content.add_widget(Label(text=message))
    popup = Popup(
        title=title,
        content=content,
        size_hint=(0.88, 0.42),
        auto_dismiss=True
    )
    content.add_widget(make_button("OK", popup.dismiss))
    popup.open()


class DashboardScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(8)
        )
        self.add_widget(self.layout)

    def on_pre_enter(self, *args):
        self.refresh()

    def refresh(self):
        self.layout.clear_widgets()
        app = App.get_running_app()

        self.layout.add_widget(Label(
            text="[b]HSE MANAGEMENT SYSTEM[/b]",
            markup=True,
            font_size="22sp",
            size_hint_y=None,
            height=dp(48)
        ))
        self.layout.add_widget(Label(
            text="Dashboard • Local offline database",
            size_hint_y=None,
            height=dp(28)
        ))

        counts = app.db.counts()
        summary = (
            f"Open records: {counts['Open']}     "
            f"Closed records: {counts['Closed']}"
        )
        self.layout.add_widget(Label(
            text=summary,
            size_hint_y=None,
            height=dp(36)
        ))

        scroll = ScrollView()
        items = BoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
            padding=(0, dp(4))
        )
        items.bind(minimum_height=items.setter("height"))

        for module in MODULES:
            count = counts.get(module, 0)
            items.add_widget(make_button(
                f"{module}  •  {count} records",
                lambda m=module: self.open_module(m)
            ))

        items.add_widget(make_button(
            "Refresh dashboard",
            self.refresh
        ))
        items.add_widget(make_button(
            "About / data storage",
            lambda: show_message(
                "About",
                "Records are stored in this app's private local database. "
                "Export CSV backups regularly. This starter version does "
                "not synchronise records to a server."
            )
        ))

        scroll.add_widget(items)
        self.layout.add_widget(scroll)

    def open_module(self, module):
        screen = self.manager.get_screen("register")
        screen.configure(module)
        self.manager.current = "register"


class RegisterScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.module = "Observations"
        self.inputs = {}
        self.root_layout = BoxLayout(
            orientation="vertical",
            padding=dp(10),
            spacing=dp(8)
        )
        self.add_widget(self.root_layout)

    def configure(self, module):
        self.module = module
        self.build_screen()

    def build_screen(self):
        app = App.get_running_app()
        self.root_layout.clear_widgets()
        self.inputs = {}

        header = BoxLayout(
            size_hint_y=None,
            height=dp(46),
            spacing=dp(8)
        )
        header.add_widget(make_button(
            "← Dashboard",
            lambda: setattr(self.manager, "current", "dashboard"),
            height=dp(42)
        ))
        header.add_widget(Label(
            text=f"[b]{self.module} Register[/b]",
            markup=True,
            font_size="18sp"
        ))
        self.root_layout.add_widget(header)

        search = TextInput(
            hint_text="Search records",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        search.bind(text=lambda *_: self.refresh_records(search.text))
        self.root_layout.add_widget(search)

        form_scroll = ScrollView(size_hint_y=0.53)
        form = BoxLayout(
            orientation="vertical",
            spacing=dp(7),
            size_hint_y=None,
            padding=(dp(2), dp(4))
        )
        form.bind(minimum_height=form.setter("height"))

        for field in MODULES[self.module]:
            form.add_widget(Label(
                text=field,
                size_hint_y=None,
                height=dp(24),
                halign="left",
                valign="middle"
            ))
            widget = TextInput(
                hint_text=field,
                multiline=field in (
                    "Observation description",
                    "Incident description",
                    "Inspection findings",
                    "Audit findings",
                    "Non-conformity / finding",
                    "Immediate action",
                    "Immediate correction",
                    "Corrective action",
                    "Corrective / preventive action",
                    "Investigation findings",
                ),
                size_hint_y=None,
                height=dp(84) if field in (
                    "Observation description",
                    "Incident description",
                    "Inspection findings",
                    "Audit findings",
                    "Non-conformity / finding",
                    "Immediate action",
                    "Immediate correction",
                    "Corrective action",
                    "Corrective / preventive action",
                    "Investigation findings",
                ) else dp(44)
            )
            self.inputs[field] = widget
            form.add_widget(widget)

        form.add_widget(Label(
            text="Priority (Low / Medium / High / Critical)",
            size_hint_y=None,
            height=dp(26)
        ))
        self.inputs["Priority"] = TextInput(
            text="Medium",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        form.add_widget(self.inputs["Priority"])

        form.add_widget(Label(
            text="Status (Open / In Progress / Closed)",
            size_hint_y=None,
            height=dp(26)
        ))
        self.inputs["Status"] = TextInput(
            text="Open",
            multiline=False,
            size_hint_y=None,
            height=dp(44)
        )
        form.add_widget(self.inputs["Status"])

        form_scroll.add_widget(form)
        self.root_layout.add_widget(form_scroll)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(48),
            spacing=dp(6)
        )
        buttons.add_widget(make_button("Save record", self.save_record))
        buttons.add_widget(make_button("Export CSV", self.export_csv))
        self.root_layout.add_widget(buttons)

        self.records_label = Label(
            text="Recent records appear here",
            size_hint_y=None,
            height=dp(34)
        )
        self.root_layout.add_widget(self.records_label)

        self.records_scroll = ScrollView(size_hint_y=0.48)
        self.records_list = BoxLayout(
            orientation="vertical",
            spacing=dp(6),
            size_hint_y=None
        )
        self.records_list.bind(
            minimum_height=self.records_list.setter("height")
        )
        self.records_scroll.add_widget(self.records_list)
        self.root_layout.add_widget(self.records_scroll)

        self.refresh_records()

    def save_record(self):
        app = App.get_running_app()
        values = {
            "number": self.value_for("Observation number",
                                     "Incident number",
                                     "Inspection number",
                                     "Audit number",
                                     "CAPA number"),
            "project": self.value_for("Project / company"),
            "location": self.value_for("Location / area"),
            "description": self.value_for(
                "Observation description",
                "Incident description",
                "Inspection findings",
                "Audit findings",
                "Non-conformity / finding"
            ),
            "immediate_action": self.value_for(
                "Immediate action", "Immediate correction"
            ),
            "corrective_action": self.value_for(
                "Corrective action",
                "Corrective / preventive action",
                "Investigation findings"
            ),
            "responsible": self.value_for(
                "Responsible person", "Inspector", "Auditor"
            ),
            "target_date": self.value_for(
                "Target date", "Incident date", "Inspection date",
                "Audit date"
            ),
            "priority": self.inputs["Priority"].text.strip() or "Medium",
            "status": self.inputs["Status"].text.strip() or "Open",
        }

        if not values["description"].strip():
            show_message(
                "Required field",
                "Enter a description or finding before saving."
            )
            return

        if values["status"].lower() not in (
            "open", "in progress", "closed"
        ):
            show_message(
                "Invalid status",
                "Use Open, In Progress, or Closed."
            )
            return

        values["status"] = values["status"].title()
        values["priority"] = values["priority"].title()
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
        app = App.get_running_app()
        rows = app.db.list_records(self.module, search)
        self.records_list.clear_widgets()

        self.records_label.text = (
            f"{self.module}: {len(rows)} record(s)"
        )

        if not rows:
            self.records_list.add_widget(Label(
                text="No records found.",
                size_hint_y=None,
                height=dp(40)
            ))
            return

        for row in rows:
            detail = (
                f"#{row['id']}  |  {row['record_number'] or 'No number'}\n"
                f"{row['description']}\n"
                f"Location: {row['location'] or '-'}\n"
                f"Priority: {row['priority']}  |  Status: {row['status']}\n"
                f"Created: {row['created_at']}"
            )
            card = BoxLayout(
                orientation="vertical",
                padding=dp(8),
                spacing=dp(4),
                size_hint_y=None,
                height=dp(156)
            )
            card.add_widget(Label(
                text=detail,
                halign="left",
                valign="middle",
                text_size=(None, None)
            ))
            actions = BoxLayout(
                size_hint_y=None,
                height=dp(40),
                spacing=dp(6)
            )
            actions.add_widget(make_button(
                "Mark in progress",
                lambda rid=row["id"]: self.change_status(rid, "In Progress"),
                height=dp(38)
            ))
            actions.add_widget(make_button(
                "Close",
                lambda rid=row["id"]: self.change_status(rid, "Closed"),
                height=dp(38)
            ))
            card.add_widget(actions)
            self.records_list.add_widget(card)

    def change_status(self, record_id, status):
        App.get_running_app().db.set_status(record_id, status)
        self.refresh_records()

    def export_csv(self):
        app = App.get_running_app()
        safe_name = self.module.lower().replace(" ", "_")
        filename = f"{safe_name}_{datetime.now():%Y%m%d_%H%M%S}.csv"
        path = os.path.join(app.user_data_dir, filename)

        try:
            count = app.db.export_csv(self.module, path)
            show_message(
                "CSV exported",
                f"Exported {count} record(s).\n\nSaved in app storage:\n{path}"
            )
        except Exception as exc:
            show_message("Export failed", str(exc))


class HSEManagementApp(App):
    title = APP_TITLE

    def build(self):
        self.db = HSEDatabase(
            os.path.join(self.user_data_dir, "hse_management.db")
        )
        manager = ScreenManager()
        manager.add_widget(DashboardScreen(
            name="dashboard"
        ))
        manager.add_widget(RegisterScreen(
            name="register"
        ))
        return manager

    def on_stop(self):
        if hasattr(self, "db"):
            self.db.close()


if __name__ == "__main__":
    HSEManagementApp().run()
