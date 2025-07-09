# -*- mode: python ; coding: utf-8 -*-

# The "from kivy_deps import hook_dirs" line has been removed.

block_cipher = None

a = Analysis(['main.py'],
             pathex=[], # You can leave this empty.
             binaries=[],
             # This 'datas' section is correct and must be kept!
             # It tells PyInstaller where YOUR game's assets are.
             datas=[
                 # Top-level assets and files
                 ('assets', 'assets'),
                 ('main.kv', '.'),
                 ('custom_map.json', '.'),
                 ('default_map.json', '.'),
                 # PingPong game assets
                 ('pingpong_new/assets', 'pingpong_new/assets'),
                 ('pingpong_new/fonts', 'pingpong_new/fonts'),
                 ('pingpong_new/sounds', 'pingpong_new/sounds'),
                 # Tank game assets
                 ('tank_game/assets', 'tank_game/assets'),
                 ('tank_game/sounds', 'tank_game/sounds')
             ],
             hiddenimports=[],
             hookspath=[],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

# The rest of the file (EXE, etc.) can stay exactly as it was.
exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='KivyGame',
          debug=False,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False, # This is correct for --windowed
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='KivyGame')