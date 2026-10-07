[app]

# (str) Title of your application
title = HSE Management

# (str) Package name
package.name = hsemanagement

# (str) Package domain
package.domain = org.hse

# (str) Source code directory
source.dir = .

# (str) Main Python file
source.main = main.py

# (list) Application requirements
requirements = python3,kivy==2.3.1,filetype==1.2.0

# (str) Supported source file extensions
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,rtf,csv

# (str) Application version
version = 1.0.0

# (str) Orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 0

# (str) Android package name
android.entrypoint = org.kivy.android.PythonActivity

# (str) Android API
android.api = 35

# (str) Minimum Android API
android.minapi = 24

# (str) Android NDK version
android.ndk = 28c

# (str) Android architecture
android.archs = arm64-v8a

# (str) Android permissions
android.permissions = INTERNET

# (str) Android app activity
android.add_src =

# (str) Presplash
presplash.filename =

# (str) Icon
icon.filename =

# (str) Android private storage
android.private_storage = True

# (bool) Android app backup
android.allow_backup = True

# (str) Android logcat filters
android.logcat_filters = *:S python:D

# (str) Python-for-Android branch
p4a.branch = develop

# (str) Python-for-Android local recipes
p4a.local_recipes =

# (str) Build directory
build_dir = .buildozer

# (str) Bin directory
bin_dir = bin

# (str) Log level
log_level = 2

# (str) Warn about deprecated options
warn_on_root = 1

# (str) Use color
use_colours = 1


[buildozer]

# (str) Log level
log_level = 2

# (bool) Warn when running as root
warn_on_root = 1