[app]

title = HSE Management System
package.name = hsemanagement
package.domain = org.hse

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf

version = 1.0.0

orientation = portrait
fullscreen = 0

requirements = python3,kivy,openpyxl,reportlab,python-docx

android.api = 35
android.minapi = 24

android.ndk = 28c

android.archs = arm64-v8a

android.accept_sdk_license = True

android.permissions = android.permission.INTERNET

android.private_storage = True

android.logcat_filters = *:S python:D


[buildozer]

log_level = 2
warn_on_root = 1
