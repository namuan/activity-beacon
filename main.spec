import sys
import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

a = Analysis(['src/activity_beacon/__main__.py'],
             pathex=['.'],
             binaries=None,
             datas=[('assets', 'assets')],
             hiddenimports=[],
             hookspath=None,
             runtime_hooks=None,
             excludes=None,
             cipher=block_cipher)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='activity-beacon',
          debug=False,
          strip=False,
          upx=True,
          console=False,
          icon='assets/icon.icns',
          entitlements='activity-beacon.entitlements')

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='ActivityBeacon')

app = BUNDLE(coll,
             name='ActivityBeacon.app',
             icon='assets/icon.icns',
             bundle_identifier='com.activitybeacon.app',
             info_plist={
                'CFBundleName': 'ActivityBeacon',
                'CFBundleDisplayName': 'ActivityBeacon',
                'CFBundleVersion': '0.1.0',
                'CFBundleShortVersionString': '0.1.0',
                'CFBundlePackageType': 'APPL',
                'CFBundleExecutable': 'activity-beacon',
                'NSPrincipalClass': 'NSApplication',
                'NSHighResolutionCapable': True,
                'LSUIElement': True,
                'LSMinimumSystemVersion': '13.0',
                'NSHumanReadableCopyright': 'Copyright © 2025. All rights reserved.',
                'NSAppleEventsUsageDescription': 'ActivityBeacon needs to capture screenshots to track activity.',
                }
             )
