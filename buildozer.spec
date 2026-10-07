[app]

title = HSE Management
package.name = hsemanagement
package.domain = org.hse

source.dir = .
source.main = main.py

requirements = python3,kivy==2.3.1,filetype==1.2.0

source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,rtf,csv

version = 1.0.0

orientation = portrait
fullscreen = 0

android.entrypoint = org.kivy.android.PythonActivity

android.api = 35
android.minapi = 24
android.ndk = 28c
android.archs = arm64-v8a

android.sdk_path = /home/runner/.buildozer/android/platform/android-sdk

android.permissions = INTERNET

android.private_storage = True
android.allow_backup = True

android.accept_sdk_license = True
android.skip_update = False

android.logcat_filters = *:S python:D

p4a.branch = develop
p4a.local_recipes =

android.add_src =

presplash.filename =
icon.filename =

build_dir = .buildozer
bin_dir = bin

log_level = 2
warn_on_root = 1
use_colours = 1


[buildozer]

log_level = 2
warn_on_root = 1