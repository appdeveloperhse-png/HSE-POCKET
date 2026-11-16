"""Safety Observation Card - Kivy form and PDF generator.

This application intentionally contains only the Safety Observation Card workflow.
PDF layout follows the supplied reference image. Existing HSE modules are not included.
"""

import os
from datetime import datetime, date
from pathlib import Path

from kivy.app import App
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.checkbox import CheckBox
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

APP_TITLE = "Safety Observation Card"
PROJECT_LINE_1 = "EPIC FOR COMMON COOLING WATER SYSTEM (CCWS) PHASE-IV"
PROJECT_LINE_2 = "FOR NFS EXPANSION PROJECT RLIC– CONTRACT NO: GC23109100/4568"
FOOTER_TEXT = "SAFETY FIRST, THINK SAFE, BE SAFE & SAVE ENVIRONMENT"

OBSERVATION_TYPES = [
    "Safe Behavior/Positive Observation (Action that enhance safety and should be encourage)",
    "Unsafe Act (Behavior that could cause harm or lead to an accident)",
    "Unsafe Condition (a hazardous workplace condition that could lead to injury)",
    "Near Misses (an incident that almost cause an injury or damage but avoided)",
]

# Column order follows the three columns in the supplied sample form.
OBSERVATION_CATEGORY_COLUMNS = [
    [
        "PPE Compliance", "Confined Space Entry (CSE)", "Barrication / Signage’s",
        "Heat Stress / Weather Condition", "Welfare Facilities", "Traffic Rules",
        "Ergonomics & Handling", "Work at Height", "Equipment & Machinery", "Other:",
    ],
    [
        "PTW Compliance", "Housekeeping", "Lifting Operation & Procedure",
        "Access / Egress", "Sharp Object", "Scaffolding Erection", "Property Damage",
        "Environmental Impact", "Slips, Trips & Falls",
    ],
    [
        "Training & Competence", "Hand & Power Tools", "Electrical Hazards",
        "Excavation", "Material Arrangement", "Vehicle Incident",
        "COSHH / Chemicals Safety", "Fire Hazard", "Drop Object",
    ],
]
OBSERVATION_CATEGORIES = [item for column in OBSERVATION_CATEGORY_COLUMNS for item in column]
STATUSES = ["Open", "Closed", "Stop Work"]


def show_popup(title, message):
    body = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(10))
    label = Label(text=message, halign="center", valign="middle", color=(1, 1, 1, 1))
    label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
    body.add_widget(label)
    dialog = Popup(title=title, content=body, size_hint=(0.88, 0.42), auto_dismiss=True)
    ok = Button(text="OK", size_hint_y=None, height=dp(46))
    ok.bind(on_release=dialog.dismiss)
    body.add_widget(ok)
    dialog.open()


def generate_observation_pdf(data, output_path):
    """Generate a standards-compliant A4 PDF using only Python's standard library.

    This deliberately avoids ReportLab so the APK does not need an extra PDF package.
    The first page follows the supplied Safety Observation Card layout; overflowing
    narrative text is continued on extra pages without being lost.
    """
    import re

    PAGE_W, PAGE_H = 595.276, 841.89  # A4 points
    MM = 72.0 / 25.4
    BLACK = (0, 0, 0)
    GREEN = (0.20, 0.60, 0.38)
    RED = (0.75, 0.12, 0.12)
    pages = []
    commands = []

    def safe(value):
        value = str(value or "")
        replacements = {"–": "-", "—": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "✓": "X", "•": "-", " ": " "}
        for old, replacement in replacements.items():
            value = value.replace(old, replacement)
        return value.encode("latin-1", "replace").decode("latin-1")

    def pdf_string(value):
        return safe(value).replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')

    def X(mm): return mm * MM
    def Y(mm): return PAGE_H - mm * MM

    def set_rgb(color, stroke=False):
        op = "RG" if stroke else "rg"
        commands.append("%.3f %.3f %.3f %s" % (*color, op))

    def text(value, x, top, size=7, font="F1", color=BLACK):
        set_rgb(color)
        commands.append("BT /%s %.2f Tf 1 0 0 1 %.2f %.2f Tm (%s) Tj ET" %
                        (font, size, X(x), Y(top), pdf_string(value)))

    def line(x1, y1, x2, y2, width=0.5, color=BLACK):
        set_rgb(color, True)
        commands.append("%.2f w %.2f %.2f m %.2f %.2f l S" %
                        (width, X(x1), Y(y1), X(x2), Y(y2)))

    def rect(x, top, w, h, width=0.6, color=BLACK):
        set_rgb(color, True)
        commands.append("%.2f w %.2f %.2f %.2f %.2f re S" %
                        (width, X(x), PAGE_H - X(top + h), X(w), X(h)))

    def checkbox(x, top, checked=False, size=5.7):
        rect(x, top, size, size, 0.7)
        if checked:
            line(x + 0.9, top + 3.0, x + 2.3, top + 4.5, 1.0)
            line(x + 2.3, top + 4.5, x + 5.0, top + 0.8, 1.0)

    def heading(label, top, size=8.2):
        text(label, 11.2, top, size, "F2")
        # Approximate underline length for Helvetica bold.
        line(11.2, top + 0.7, 11.2 + len(label) * size * 0.49, top + 0.7, 0.45)

    def field(label, value, x, top, end_x):
        text(label, x, top, 7.1)
        label_w = len(label) * 7.1 * 0.51
        start = x + label_w + 1.2
        line(start, top + 0.7, end_x, top + 0.7, 0.45)
        val = safe(value)
        if val:
            max_chars = max(1, int((end_x - start - 1) / 1.25))
            text(val[:max_chars], start + 0.8, top - 1.2, 7.1)

    def wrap(value, max_chars):
        result = []
        for para in safe(value).replace("\r", "").split("\n"):
            if not para:
                result.append("")
                continue
            words = para.split()
            current = ""
            for word in words:
                while len(word) > max_chars:
                    if current:
                        result.append(current)
                        current = ""
                    result.append(word[:max_chars])
                    word = word[max_chars:]
                candidate = (current + " " + word).strip()
                if len(candidate) <= max_chars:
                    current = candidate
                else:
                    if current:
                        result.append(current)
                    current = word
            result.append(current)
        return result or [""]

    def new_page():
        nonlocal commands
        if commands:
            pages.append("\n".join(commands))
        commands = []

    # Main card page: double border and project heading.
    rect(8, 8, 194, 281, 0.85)
    rect(10, 10, 190, 277, 0.4)
    left, right, width = 11.2, 198.8, 187.6
    rect(left, 11.5, width, 18, 0.55)
    rect(left + 1.5, 13, 17, 15, 0.55)
    rect(right - 18.5, 13, 17, 15, 0.55)
    text(PROJECT_LINE_1, 35, 18, 7.4, "F2")
    text(PROJECT_LINE_2, 42, 25, 7.1)
    text("Safety Observation Card", 79, 36, 10, "F2")
    line(78, 36.8, 132, 36.8, 0.7)

    heading("Personal Information:", 44)
    text("Department:", left, 51, 7.1)
    checkbox(34.5, 46.5, data.get("department") == "CIVIL")
    text("CIVIL", 41.5, 51, 7.1)
    checkbox(52.5, 46.5, data.get("department") == "MECHANICAL")
    text("MECHANICAL", 59.5, 51, 7.1)
    field("Location:", data.get("location"), 87, 51, 153)
    field("Date:", data.get("date"), 158, 51, right)
    field("In-Charge Name:", data.get("incharge_name"), left, 59, 91)
    field("Designation:", data.get("incharge_designation"), 94, 59, 151)
    field("Time:", data.get("time"), 157, 59, right)

    heading("Type of Observation:", 68)
    yy = 75
    for item in OBSERVATION_TYPES:
        checkbox(left + 1, yy - 5.8, data.get("observation_type") == item)
        text(item, left + 8.2, yy, 7.0)
        yy += 7.0

    continuation = []
    def narrative_box(label, key, title_top, box_top, box_bottom):
        heading(label, title_top)
        rect(left, box_top, width, box_bottom - box_top, 0.75)
        content = str(data.get(key, "") or "")
        lines = wrap(content, 118)
        max_lines = max(1, int((box_bottom - box_top - 4) / 3.2))
        for index, row in enumerate(lines[:max_lines]):
            text(row, left + 1.8, box_top + 4 + index * 3.2, 7.2)
        if len(lines) > max_lines:
            continuation.append((label, content))
            text("Continued on attached page", right - 43, box_bottom - 1.8, 5.8, "F3")

    narrative_box("Description of the Observation:", "description", 108, 111, 133)
    narrative_box("Immediate Corrective action taken:", "immediate_action", 138, 141, 163)

    text("Observation Status:", left, 171, 7.5, "F2")
    status_x = 49
    for status in STATUSES:
        checkbox(status_x, 165.2, data.get("status") == status)
        text(status, status_x + 7, 171, 7.1, "F1", RED if status == "Stop Work" else BLACK)
        status_x += 27 if status != "Stop Work" else 35

    heading("Observation Categories:", 181)
    col_x = [14, 82, 145]
    selected = set(data.get("categories", []))
    for col_index, column in enumerate(OBSERVATION_CATEGORY_COLUMNS):
        for row_index, category in enumerate(column):
            top = 185.5 + row_index * 6.5
            checkbox(col_x[col_index], top - 0.6, category in selected, 5.4)
            text(category, col_x[col_index] + 6.8, top, 6.35)
    if "Other:" in selected and str(data.get("other_category", "")).strip():
        text("Specify: " + data.get("other_category", ""), 21, 251, 6.0)

    heading("Observer's Information:", 259)
    field("Name:", data.get("observer_name"), left, 267, 87)
    field("Emp. #:", data.get("employee_number"), 91, 267, 124)
    field("Designation:", data.get("observer_designation"), 128, 267, right)
    text(FOOTER_TEXT, 56, 282, 7.6, "F2", GREEN)

    # Extra pages for full narrative content when the original card's boxes overflow.
    for label, content in continuation:
        new_page()
        rect(12, 12, 186, 273, 0.8)
        text("Safety Observation Card - Continuation", 18, 22, 12, "F2")
        text(label, 18, 34, 10, "F2")
        rows = wrap(content, 105)
        y = 45
        for row in rows:
            if y > 278:
                new_page()
                rect(12, 12, 186, 273, 0.8)
                text("Safety Observation Card - Continuation", 18, 22, 10, "F2")
                y = 34
            text(row, 18, y, 8.5)
            y += 5.0

    if commands:
        pages.append("\n".join(commands))

    # Assemble a minimal PDF 1.4 file with built-in Type 1 fonts. No third-party
    # libraries, Android package dependencies, or network access are required.
    objects = []
    def add_obj(content):
        objects.append(content if isinstance(content, bytes) else content.encode("latin-1", "replace"))
        return len(objects)

    catalog_id = add_obj(b"")
    pages_id = add_obj(b"")
    font_regular = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    font_bold = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")
    font_italic = add_obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Oblique >>")
    page_ids = []
    for stream_text in pages:
        stream = stream_text.encode("latin-1", "replace")
        content_id = add_obj(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_id = add_obj(("<< /Type /Page /Parent %d 0 R /MediaBox [0 0 %.2f %.2f] "
                           "/Resources << /Font << /F1 %d 0 R /F2 %d 0 R /F3 %d 0 R >> >> "
                           "/Contents %d 0 R >>") %
                          (pages_id, PAGE_W, PAGE_H, font_regular, font_bold, font_italic, content_id))
        page_ids.append(page_id)

    kids = " ".join("%d 0 R" % item for item in page_ids)
    objects[catalog_id - 1] = ("<< /Type /Catalog /Pages %d 0 R >>" % pages_id).encode("ascii")
    objects[pages_id - 1] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (kids, len(page_ids))).encode("ascii")

    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(("%d 0 obj\n" % index).encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(("xref\n0 %d\n" % (len(objects) + 1)).encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(("%010d 00000 n \n" % offset).encode("ascii"))
    output.extend(("trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF" %
                   (len(objects) + 1, catalog_id, xref_offset)).encode("ascii"))
    Path(output_path).write_bytes(output)
    return output_path

class SafetyObservationApp(App):
    title = APP_TITLE

    def build(self):
        # Force a light, high-contrast interface on Android regardless of system dark mode.
        Window.clearcolor = (0.96, 0.97, 0.98, 1)
        self.fields = {}
        self.type_checks = {}
        self.category_checks = {}
        self.status_checks = {}
        self.department_checks = {}

        root = BoxLayout(orientation="vertical", spacing=dp(6), padding=dp(8))
        with root.canvas.before:
            from kivy.graphics import Color, Rectangle
            Color(0.96, 0.97, 0.98, 1)
            self._root_bg = Rectangle(pos=root.pos, size=root.size)
        root.bind(pos=lambda inst, value: setattr(self._root_bg, "pos", value),
                  size=lambda inst, value: setattr(self._root_bg, "size", value))
        heading = Label(
            text="[b]SAFETY OBSERVATION CARD[/b]", markup=True,
            size_hint_y=None, height=dp(44), font_size="20sp", color=(0.04, 0.12, 0.20, 1),
        )
        root.add_widget(heading)

        scroll = ScrollView(do_scroll_x=False, bar_width=dp(5))
        form = BoxLayout(
            orientation="vertical", spacing=dp(7), size_hint_y=None,
            padding=(dp(5), dp(5), dp(5), dp(12)),
        )
        form.bind(minimum_height=form.setter("height"))
        scroll.add_widget(form)
        root.add_widget(scroll)

        self.add_section(form, "Project / Contract Information")
        project_label = Label(
            text=f"{PROJECT_LINE_1}\n{PROJECT_LINE_2}",
            size_hint_y=None, height=dp(54), halign="center", valign="middle",
            font_size="12sp", color=(0.05, 0.10, 0.16, 1),
        )
        project_label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        form.add_widget(project_label)

        self.add_section(form, "Personal Information:")
        dept_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        dept_row.add_widget(Label(text="Department:", size_hint_x=0.30, halign="left", color=(0.04, 0.10, 0.16, 1)))
        for department in ("CIVIL", "MECHANICAL"):
            item = BoxLayout(spacing=dp(3))
            check = CheckBox(size_hint_x=None, width=dp(34), group="department")
            self.department_checks[department] = check
            item.add_widget(check)
            item.add_widget(Label(text=department, font_size="12sp", color=(0.04, 0.10, 0.16, 1)))
            dept_row.add_widget(item)
        self.department_checks["CIVIL"].active = True
        form.add_widget(dept_row)

        self.add_text_field(form, "Location", "location", height=dp(46))
        self.add_text_field(form, "Date", "date", date.today().strftime("%d-%m-%Y"), height=dp(46))
        self.add_text_field(form, "In-Charge Name", "incharge_name", height=dp(46))
        self.add_text_field(form, "Designation", "incharge_designation", height=dp(46))
        self.add_text_field(form, "Time", "time", datetime.now().strftime("%I:%M %p"), height=dp(46))

        self.add_section(form, "Type of Observation:")
        for item in OBSERVATION_TYPES:
            self.add_check_row(form, item, self.type_checks, group="observation_type", height=dp(54))

        self.add_section(form, "Description of the Observation:")
        self.add_text_field(
            form, "Enter full observation description", "description",
            multiline=True, height=dp(190),
        )
        self.add_section(form, "Immediate Corrective action taken:")
        self.add_text_field(
            form, "Enter immediate corrective action taken", "immediate_action",
            multiline=True, height=dp(190),
        )

        self.add_section(form, "Observation Status:")
        status_row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(8))
        for status in STATUSES:
            item = BoxLayout(spacing=dp(2))
            check = CheckBox(size_hint_x=None, width=dp(34), group="observation_status")
            self.status_checks[status] = check
            item.add_widget(check)
            item.add_widget(Label(
                text=status, font_size="12sp",
                color=(0.75, 0.12, 0.12, 1) if status == "Stop Work" else (0.04, 0.10, 0.16, 1),
            ))
            status_row.add_widget(item)
        self.status_checks["Open"].active = True
        form.add_widget(status_row)

        self.add_section(form, "Observation Categories:")
        category_columns = GridLayout(cols=3, spacing=dp(5), size_hint_y=None)
        category_columns.bind(minimum_height=category_columns.setter("height"))
        for column_categories in OBSERVATION_CATEGORY_COLUMNS:
            column = BoxLayout(orientation="vertical", spacing=dp(2), size_hint_y=None)
            column.bind(minimum_height=column.setter("height"))
            for category in column_categories:
                row = BoxLayout(size_hint_y=None, height=dp(43), spacing=dp(1))
                check = CheckBox(size_hint_x=None, width=dp(29))
                self.category_checks[category] = check
                row.add_widget(check)
                label = Label(text=category, halign="left", valign="middle", font_size="10sp", color=(0.04, 0.10, 0.16, 1))
                label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
                row.add_widget(label)
                column.add_widget(row)
            category_columns.add_widget(column)
        form.add_widget(category_columns)
        self.add_text_field(form, "If Other, please specify", "other_category", height=dp(46))

        self.add_section(form, "Observer's Information:")
        self.add_text_field(form, "Name", "observer_name", height=dp(46))
        self.add_text_field(form, "Emp. #", "employee_number", height=dp(46))
        self.add_text_field(form, "Designation", "observer_designation", height=dp(46))

        footer = Label(
            text=f"[b][color=339966]{FOOTER_TEXT}[/color][/b]", markup=True,
            size_hint_y=None, height=dp(48), font_size="12sp", color=(0.10, 0.48, 0.28, 1),
        )
        form.add_widget(footer)

        submit = Button(
            text="SUBMIT & GENERATE PDF", size_hint_y=None, height=dp(56),
            background_normal="", background_down="", background_color=(0.04, 0.42, 0.25, 1),
            color=(1, 1, 1, 1), font_size="16sp", bold=True,
        )
        submit.bind(on_release=lambda *_: self.submit_form())
        root.add_widget(submit)
        return root

    def add_section(self, parent, title):
        label = Label(
            text=f"[b]{title}[/b]", markup=True, halign="left",
            size_hint_y=None, height=dp(32), color=(0.04, 0.12, 0.20, 1),
        )
        label.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        parent.add_widget(label)

    def add_text_field(self, parent, label, key, default="", multiline=False, height=None):
        title = Label(text=label, halign="left", size_hint_y=None, height=dp(25), color=(0.04, 0.10, 0.16, 1))
        title.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        parent.add_widget(title)
        widget = TextInput(
            text=default, hint_text=label, multiline=multiline,
            size_hint_y=None, height=height or (dp(190) if multiline else dp(46)),
            padding=(dp(9), dp(9)), font_size="14sp",
            foreground_color=(0.04, 0.06, 0.09, 1),
            background_normal="", background_active="",
            background_color=(1, 1, 1, 1), cursor_color=(0.05, 0.30, 0.65, 1),
            hint_text_color=(0.38, 0.42, 0.48, 1),
            write_tab=False,
        )
        self.fields[key] = widget
        parent.add_widget(widget)

    def add_check_row(self, parent, label, store, group=None, height=dp(42)):
        row = BoxLayout(size_hint_y=None, height=height, spacing=dp(6))
        check = CheckBox(size_hint_x=None, width=dp(38), group=group)
        store[label] = check
        row.add_widget(check)
        text = Label(text=label, halign="left", valign="middle", font_size="11sp", color=(0.04, 0.10, 0.16, 1))
        text.bind(size=lambda inst, size: setattr(inst, "text_size", size))
        row.add_widget(text)
        parent.add_widget(row)

    def submit_form(self):
        data = {key: widget.text.strip() for key, widget in self.fields.items()}
        data["department"] = next((name for name, cb in self.department_checks.items() if cb.active), "")
        data["observation_type"] = next((name for name, cb in self.type_checks.items() if cb.active), "")
        data["status"] = next((name for name, cb in self.status_checks.items() if cb.active), "")
        data["categories"] = [name for name, cb in self.category_checks.items() if cb.active]

        required = [
            ("location", "Please enter the observation location."),
            ("description", "Please enter the description of the observation."),
            ("observer_name", "Please enter the observer's name."),
        ]
        for key, message in required:
            if not data.get(key):
                show_popup("Required field", message)
                return
        if not data["observation_type"]:
            show_popup("Required field", "Please select a type of observation.")
            return
        if not data["status"]:
            show_popup("Required field", "Please select an observation status.")
            return
        if not data["categories"]:
            show_popup("Required field", "Please select at least one observation category.")
            return

        try:
            output_dir = Path(self.user_data_dir) / "SafetyObservationReports"
            output_dir.mkdir(parents=True, exist_ok=True)
            filename = f"Safety_Observation_{datetime.now():%Y%m%d_%H%M%S}.pdf"
            output_path = str(output_dir / filename)
            generate_observation_pdf(data, output_path)
            show_popup(
                "PDF Generated",
                "Your completed Safety Observation Card PDF has been generated.\n\n"
                f"File: {filename}\n\nSaved in app storage:\n{output_path}\n\n"
                "Use your device's file manager to open or share the PDF.",
            )
        except Exception as exc:
            show_popup("PDF generation failed", str(exc))


if __name__ == "__main__":
    SafetyObservationApp().run()
