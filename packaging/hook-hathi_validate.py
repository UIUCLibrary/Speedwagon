from PyInstaller.utils.hooks import collect_data_files
hiddenimports = ['hathi_validate.xsd']
datas = collect_data_files('hathi_validate.xsd')
