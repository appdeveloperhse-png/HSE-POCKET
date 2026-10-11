# HSE-POCKET - Kivy HSE Management System
# Android-friendly single-file application.
# Existing modules are kept; this version adds:
# - Settings (company / project / logo)
# - Working gallery attachment
# - Observation register with selection
# - SOP Safety Observation Card drafting
# - One observation = one SOP card page; multiple observations = multiple pages
# - Local Android save dialog for PDF / Word / Excel / SOP cards
# - Observation PDF / Word / Excel exports

import os
import csv
import sqlite3
import base64
import mimetypes
import zlib
import struct
from datetime import datetime
import sys
import traceback
import faulthandler

from kivy.app import App
from kivy.clock import Clock
from kivy.base import ExceptionManager, ExceptionHandler
from kivy.metrics import dp
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
