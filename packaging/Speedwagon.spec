# -*- mode: python ; coding: utf-8 -*-
import os
try:  # pragma: no cover
    from importlib import metadata
except ImportError:  # pragma: no cover
    import importlib_metadata as metadata  # type: ignore

block_cipher = None
# a = Analysis(['../speedwagon/__main__.py'],
a = Analysis(['./speedwagon-bootstrap.py'],
             pathex=[],
             binaries=[],
             datas=[
                ('../speedwagon/favicon.ico', 'speedwagon'),
                ('../speedwagon/logo.png', 'speedwagon'),
                ('../speedwagon/frontend/qtwidgets/ui/*.ui', 'speedwagon/frontend/qtwidgets/ui'),
             ],
             hiddenimports=[],
             hookspath=[os.path.join(workpath, ".."), SPECPATH],
             hooksconfig={},
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher,
             noarchive=True)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)

exe = EXE(pyz,
          a.scripts,
          [],
          exclude_binaries=True,
          name='Speedwagon App',
          debug=True,
          bootloader_ignore_signals=False,
          strip=False,
          upx=True,
          console=False,
          disable_windowed_traceback=False,
          target_arch=None,
          codesign_identity=None,
          entitlements_file=None, icon='../speedwagon/favicon.ico')
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               upx_exclude=[],
               name='Speedwagon!')
pkg_metadata = metadata.metadata("speedwagon")

app = BUNDLE(coll,
             name='Speedwagon.app',
             version=pkg_metadata['Version'],
             icon='favicon.icns',
             bundle_identifier=None)
