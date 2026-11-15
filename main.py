import os
from datetime import datetime, date
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

APP_TITLE = "Safety Observation Card"
OBSERVATION_TYPES = [
    "Safe Behavior/Positive Observation (Action that enhance safety and should be encourage)",
    "Unsafe Act (Behavior that could cause harm or lead to an accident)",
    "Unsafe Condition (a hazardous workplace condition that could lead to injury)",
    "Near Misses (an incident that almost cause an injury or damage but avoided)",
]
OBSERVATION_CATEGORIES = [
    "PPE Compliance", "Confined Space Entry (CSE)", "Barrication / Signage’s",
    "Heat Stress / Weather Condition", "Welfare Facilities", "Traffic Rules",
    "Ergonomics & Handling", "Work at Height", "Equipment & Machinery", "Other:",
    "PTW Compliance", "Housekeeping", "Lifting Operation & Procedure",
    "Access / Egress", "Sharp Object", "Scaffolding Erection", "Property Damage",
    "Environmental Impact", "Slips, Trips & Falls", "Training & Competence",
    "Hand & Power Tools", "Electrical Hazards", "Excavation", "Material Arrangement",
    "Vehicle Incident", "COSHH / Chemicals Safety", "Fire Hazard", "Drop Object",
]


def popup(title, message):
    body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    body.add_widget(Label(text=message, halign="center", valign="middle"))
    win = Popup(title=title, content=body, size_hint=(0.88, 0.38))
    ok = Button(text="OK", size_hint_y=None, height=dp(44))
    ok.bind(on_release=win.dismiss)
    body.add_widget(ok)
    win.open()


def draw_wrapped(c, text, x, y, max_width, font="Helvetica", size=8.2, leading=None):
    """Draw wrapped text and return the next y coordinate."""
    leading = leading or size * 1.25
    c.setFont(font, size)
    words = str(text or "").split()
    lines, line = [], ""
    for word in words:
        candidate = (line + " " + word).strip()
        if c.stringWidth(candidate, font, size) <= max_width:
            line = candidate
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    if not lines:
        lines = [""]
    for item in lines:
        c.drawString(x, y, item)
        y -= leading
    return y


def generate_observation_pdf(data, output_path):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:
        raise RuntimeError("PDF library is missing. Install reportlab in the Android build: pip install reportlab") from exc

    page_w, page_h = A4
    c = canvas.Canvas(output_path, pagesize=A4)
    left, right = 30, page_w - 30
    width = right - left
    top = page_h - 27
    c.setLineWidth(0.8)
    c.rect(left, 25, width, page_h - 50)
    c.setLineWidth(0.45)
    c.rect(left + 5, 30, width - 10, page_h - 60)

    # Header block and title
    c.setFont("Helvetica-Bold", 8.4)
    c.drawCentredString(page_w / 2, top - 13, "EPIC FOR COMMON COOLING WATER SYSTEM (CCWS) PHASE-IV")
    c.setFont("Helvetica", 8.2)
    c.drawCentredString(page_w / 2, top - 28, "FOR NFS EXPANSION PROJECT RLIC– CONTRACT NO: GC23109100/4568")
    c.setLineWidth(0.5)
    c.line(left + 8, top - 38, right - 8, top - 38)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(page_w / 2, top - 57, "Safety Observation Card")

    y = top - 79
    def section(title):
        nonlocal y
        c.setFont("Helvetica-Bold", 9)
        c.drawString(left + 8, y, title)
        y -= 14

    def field(label, value, x, y0, w):
        c.setFont("Helvetica", 8)
        c.drawString(x, y0, label)
        label_w = c.stringWidth(label, "Helvetica", 8) + 4
        c.setLineWidth(0.45)
        c.line(x + label_w, y0 - 2, x + w, y0 - 2)
        c.setFont("Helvetica", 8)
        c.drawString(x + label_w + 3, y0 + 1, str(value or ""))

    section("Personal Information:")
    field("Department:", data.get("department", ""), left + 8, y, 165)
    field("Location:", data.get("location", ""), left + 180, y, 180)
    field("Date:", data.get("date", ""), left + 365, y, width - 375)
    y -= 19
    field("In-Charge Name:", data.get("incharge_name", ""), left + 8, y, 220)
    field("Designation:", data.get("incharge_designation", ""), left + 240, y, 150)
    field("Time:", data.get("time", ""), left + 400, y, width - 410)
    y -= 20

    section("Type of Observation:")
    for item in OBSERVATION_TYPES:
        checked = item == data.get("observation_type")
        c.rect(left + 10, y - 2, 10, 10)
        if checked:
            c.setFont("Helvetica-Bold", 10)
            c.drawString(left + 11, y - 1, "✓")
        y = draw_wrapped(c, item, left + 27, y, width - 45, size=7.7, leading=9.3) - 3

    section("Description of the Observation:")
    desc_y_top = y + 3
    desc_height = 54
    c.rect(left + 8, desc_y_top - desc_height, width - 16, desc_height)
    text_y = desc_y_top - 13
    draw_wrapped(c, data.get("description", ""), left + 13, text_y, width - 26, size=8, leading=10)
    y = desc_y_top - desc_height - 15

    section("Immediate Corrective action taken:")
    action_y_top = y + 3
    action_height = 48
    c.rect(left + 8, action_y_top - action_height, width - 16, action_height)
    draw_wrapped(c, data.get("immediate_action", ""), left + 13, action_y_top - 13, width - 26, size=8, leading=10)
    y = action_y_top - action_height - 19

    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(left + 8, y, "Observation Status:")
    x = left + 115
    for status in ("Open", "Closed", "Stop Work"):
        c.rect(x, y - 4, 10, 10)
        if status == data.get("status"):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x + 1, y - 3, "✓")
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.75, 0.12, 0.12) if status == "Stop Work" else c.setFillColorRGB(0, 0, 0)
        c.drawString(x + 14, y - 1, status)
        c.setFillColorRGB(0, 0, 0)
        x += 82 if status != "Stop Work" else 95
    y -= 26

    section("Observation Categories:")
    col_x = [left + 15, left + 220, left + 410]
    col_width = [190, 180, width - 425]
    row_step = 17
    rows_per_col = 10
    for idx, category in enumerate(OBSERVATION_CATEGORIES):
        col = idx // rows_per_col
        row = idx % rows_per_col
        if col > 2:
            break
        cy = y - row * row_step
        bx = col_x[col]
        c.rect(bx, cy - 3, 10, 10)
        if category in data.get("categories", []):
            c.setFont("Helvetica-Bold", 10)
            c.drawString(bx + 1, cy - 2, "✓")
        c.setFont("Helvetica", 7.4)
        c.drawString(bx + 14, cy - 1, category)
    y -= rows_per_col * row_step + 8

    if "Other:" in data.get("categories", []) and data.get("other_category"):
        c.setFont("Helvetica", 7.4)
        c.drawString(col_x[0] + 14, y - 9 * row_step - 1, "Other: " + data.get("other_category", ""))

    section("Observer's Information:")
    field("Name:", data.get("observer_name", ""), left + 8, y, 225)
    field("Emp. #:", data.get("employee_number", ""), left + 240, y, 115)
    field("Designation:", data.get("observer_designation", ""), left + 365, y, width - 375)

    c.setFillColorRGB(0.20, 0.60, 0.38)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(page_w / 2, 43, "SAFETY FIRST, THINK SAFE, BE SAFE & SAVE ENVIRONMENT")
    c.setFillColorRGB(0, 0, 0)
    c.save()
    return output_path


class SafetyObservationApp(App):
    title = APP_TITLE

    def build(self):
        self.fields = {}
        self.type_checks = {}
        self.category_checks = {}
        self.status_checks = {}
        self.department_checks = {}

        root = BoxLayout(orientation="vertical", spacing=dp(5), padding=dp(8))
        header = Label(text="[b]SAFETY OBSERVATION CARD[/b]", markup=True,
                       size_hint_y=None, height=dp(42), font_size="20sp")
        root.add_widget(header)

        scroll = ScrollView(do_scroll_x=False)
        form = BoxLayout(orientation="vertical", spacing=dp(7), size_hint_y=None, padding=(dp(5), dp(5)))
        form.bind(minimum_height=form.setter("height"))
        scroll.add_widget(form)
        root.add_widget(scroll)

        self.add_section(form, "Project / Contract Information")
        form.add_widget(Label(text="EPIC FOR COMMON COOLING WATER SYSTEM (CCWS) PHASE-IV\nFOR NFS EXPANSION PROJECT RLIC – CONTRACT NO: GC23109100/4568",
                              size_hint_y=None, height=dp(48), halign="center", valign="middle"))
        self.add_section(form, "Personal Information:")
        dept_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        dept_row.add_widget(Label(text="Department:", size_hint_x=0.28))
        for dept in ("CIVIL", "MECHANICAL"):
            line = BoxLayout(spacing=dp(3))
            cb = CheckBox(size_hint_x=None, width=dp(34), group="department")
            self.department_checks[dept] = cb
            line.add_widget(cb)
            line.add_widget(Label(text=dept))
            dept_row.add_widget(line)
        self.department_checks["CIVIL"].active = True
        form.add_widget(dept_row)
        self.add_text_field(form, "Location", "location")
        self.add_text_field(form, "Date", "date", date.today().strftime("%d-%m-%Y"))
        self.add_text_field(form, "In-Charge Name", "incharge_name")
        self.add_text_field(form, "Designation", "incharge_designation")
        self.add_text_field(form, "Time", "time", datetime.now().strftime("%I:%M %p"))

        self.add_section(form, "Type of Observation:")
        for item in OBSERVATION_TYPES:
            self.add_check_row(form, item, self.type_checks, group="observation_type")

        self.add_section(form, "Description of the Observation:")
        self.add_text_field(form, "Enter observation description", "description", multiline=True)
        self.add_section(form, "Immediate Corrective action taken:")
        self.add_text_field(form, "Enter immediate corrective action", "immediate_action", multiline=True)

        self.add_section(form, "Observation Status:")
        status_row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(8))
        for status in ("Open", "Closed", "Stop Work"):
            line = BoxLayout(spacing=dp(2))
            cb = CheckBox(size_hint_x=None, width=dp(34), group="observation_status")
            self.status_checks[status] = cb
            line.add_widget(cb)
            line.add_widget(Label(text=status, color=(0.75, 0.12, 0.12, 1) if status == "Stop Work" else (0, 0, 0, 1)))
            status_row.add_widget(line)
        self.status_checks["Open"].active = True
        form.add_widget(status_row)

        self.add_section(form, "Observation Categories:")
        category_grid = GridLayout(cols=3, spacing=dp(4), size_hint_y=None, row_default_height=dp(42), row_force_default=True)
        category_grid.bind(minimum_height=category_grid.setter("height"))
        for category in OBSERVATION_CATEGORIES:
            line = BoxLayout(spacing=dp(2))
            cb = CheckBox(size_hint_x=None, width=dp(30))
            self.category_checks[category] = cb
            line.add_widget(cb)
            line.add_widget(Label(text=category, halign="left", valign="middle", font_size="11sp"))
            category_grid.add_widget(line)
        form.add_widget(category_grid)
        self.add_text_field(form, "If Other, please specify", "other_category")

        self.add_section(form, "Observer's Information:")
        self.add_text_field(form, "Name", "observer_name")
        self.add_text_field(form, "Emp. #", "employee_number")
        self.add_text_field(form, "Designation", "observer_designation")
        form.add_widget(Label(text="SAFETY FIRST, THINK SAFE, BE SAFE & SAVE ENVIRONMENT",
                              color=(0.20, 0.60, 0.38, 1), bold=True,
                              size_hint_y=None, height=dp(45)))

        submit = Button(text="SUBMIT & GENERATE PDF", size_hint_y=None, height=dp(54),
                        background_normal="", background_color=(0.10, 0.48, 0.32, 1),
                        font_size="16sp")
        submit.bind(on_release=lambda *_: self.submit_form())
        root.add_widget(submit)
        return root

    def add_section(self, parent, title):
        parent.add_widget(Label(text=f"[b]{title}[/b]", markup=True, halign="left",
                                size_hint_y=None, height=dp(32), color=(0.08, 0.18, 0.28, 1)))

    def add_text_field(self, parent, label, key, default="", multiline=False):
        parent.add_widget(Label(text=label, halign="left", size_hint_y=None, height=dp(23)))
        widget = TextInput(text=default, hint_text=label, multiline=multiline,
                           size_hint_y=None, height=dp(92) if multiline else dp(42),
                           padding=(dp(8), dp(8)))
        self.fields[key] = widget
        parent.add_widget(widget)

    def add_check_row(self, parent, label, store, group=None):
        row = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        cb = CheckBox(size_hint_x=None, width=dp(38), group=group)
        store[label] = cb
        row.add_widget(cb)
        row.add_widget(Label(text=label, halign="left", valign="middle", font_size="11sp"))
        parent.add_widget(row)

    def submit_form(self):
        data = {key: widget.text.strip() for key, widget in self.fields.items()}
        data["department"] = next((name for name, cb in self.department_checks.items() if cb.active), "")
        data["observation_type"] = next((name for name, cb in self.type_checks.items() if cb.active), "")
        data["status"] = next((name for name, cb in self.status_checks.items() if cb.active), "")
        data["categories"] = [name for name, cb in self.category_checks.items() if cb.active]

        if not data["location"]:
            popup("Required field", "Please enter the observation location.")
            return
        if not data["description"]:
            popup("Required field", "Please enter the description of the observation.")
            return
        if not data["observer_name"]:
            popup("Required field", "Please enter the observer's name.")
            return
        if not data["observation_type"]:
            popup("Required field", "Please select a type of observation.")
            return

        try:
            output_dir = Path(self.user_data_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"Safety_Observation_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            output_path = str(output_dir / filename)
            generate_observation_pdf(data, output_path)
            popup("PDF Generated", f"Your Safety Observation Card PDF has been created.\n\nSaved at:\n{output_path}")
        except Exception as exc:
            popup("PDF generation failed", str(exc))


if __name__ == "__main__":
    SafetyObservationApp().run()
