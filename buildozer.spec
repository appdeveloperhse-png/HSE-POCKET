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
requirements = python3,kivy==2.3.0,filetype==1.2.0

# (str) Version
version = 1.0.0

# (list) Source file extensions to include
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,txt,rtf,csv

# (str) Application orientation
orientation = portrait

# (bool) Fullscreen
fullscreen = 0


# ------------------------------------------------------------------
# ANDROID
# ------------------------------------------------------------------

# Android API
android.api = 35

# Minimum Android API
android.minapi = 24

# Use Android NDK 25b with the stable p4a 2024 toolchain
android.ndk = 25b

# Build only ARM64
android.archs = arm64-v8a

# Android SDK location used by Buildozer
android.sdk_path = /home/runner/.buildozer/android/platform/android-sdk

# Application permissions
android.permissions = INTERNET

# Private application storage
android.private_storage = True

# Android backup
android.allow_backup = True

# Accept SDK licenses
android.accept_sdk_license = True

# Android entry point
android.entrypoint = org.kivy.android.PythonActivity

# Logcat
android.logcat_filters = *:S python:D


# ------------------------------------------------------------------
# PYTHON-FOR-ANDROID
# ------------------------------------------------------------------

# Stable python-for-android release
p4a.branch = master

# v2024.01.21
p4a.commit = 957a3e5

# Local recipes
p4a.local_recipes =


# ------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------

build_dir = .buildozer
bin_dir = bin

log_level = 2
warn_on_root = 1
use_colours = 1


[buildozer]

log_level = 2
warn_on_root = 1