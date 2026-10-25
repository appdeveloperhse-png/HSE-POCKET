
[app]
title = HSE Management System
package.name = hsemanagement
package.domain = org.hse

source.dir = .
source.main = main.py
source.include_exts = py,kv,png,jpg,jpeg,json,txt,csv

version = 2.0.0

requirements = python3,kivy==2.3.0

orientation = portrait
fullscreen = 0

android.api = 33
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a

android.permissions = INTERNET
android.private_storage = True
android.allow_backup = True
android.accept_sdk_license = True
android.entrypoint = org.kivy.android.PythonActivity

# Pin python-for-android to the older compatible release.
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
