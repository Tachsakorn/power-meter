# Builds dist/PowerMeter.exe, a single file with Python and the web UI inside.
#   pip install . pyinstaller
#   pyinstaller packaging/power-meter.spec
from pathlib import Path

root = Path(SPECPATH).parent

a = Analysis(
    [str(root / "packaging" / "launch.py")],
    pathex=[str(root / "src")],
    datas=[(str(root / "src" / "power_meter" / "web"), "power_meter/web")],
    # holidays loads its country modules by name at runtime.
    hiddenimports=["holidays.countries.thailand"],
    excludes=["tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="PowerMeter",
    icon=str(root / "packaging" / "icon.ico"),
    console=False,
    upx=False,
)
