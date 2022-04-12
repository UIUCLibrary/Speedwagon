from PyInstaller.utils.hooks import copy_metadata, collect_all
datas, binaries, hiddenimports = collect_all('speedwagon')
datas += copy_metadata('speedwagon', recursive=True)
