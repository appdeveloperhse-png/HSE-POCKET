[app]

title = HSE Management System
package.name = hsemanagement
package.domain = org.hse

source.dir = .

source.include_exts = py,png,jpg,jpeg,kv,atlas,ttf,otf,txt,rtf,pdf,csv

version = 1.0.0

orientation = portrait
fullscreen = 0

requirements = python3,kivy==2.3.1,requests==2.28.2,charset-normalizer==2.1.1,certifi==2022.12.7,idna==3.4,urllib3==1.26.14,filetype==1.2.0

android.api = 35
android.minapi = 24
android.ndk = 28c

android.archs = arm64-v8a

android.accept_sdk_license = True

android.permissions = android.permission.INTERNET

android.private_storage = True

android.logcat_filters = *:S python:D

p4a.branch = master

[buildozer]

log_level = 2
warn_on_root = 1