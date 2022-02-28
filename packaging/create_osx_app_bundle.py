import PyInstaller.__main__
import PyInstaller.building.makespec
import PyInstaller.building.build_main
import os

SPEC_FILE = "Speedwagon.spec"

TOP_LEVEL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
WORKPATH = os.path.join(TOP_LEVEL_DIR, "build")


def main():
    if not os.path.exists(
            os.path.join(WORKPATH, "hook-speedwagon.workflows.py")
    ):
        create_hook_file(
            TOP_LEVEL_DIR,
            WORKPATH,
            hook_name="hook-speedwagon.workflows.py"
        )

    PyInstaller.__main__.run([
        '--noconfirm',
        os.path.join(os.path.dirname(__file__), SPEC_FILE),
        "--distpath", os.path.join(TOP_LEVEL_DIR, "dist"),
        "--workpath", WORKPATH,
        "--clean"
    ])


def only_workflows(entry: os.DirEntry["str"]):
    if not entry.is_file():
        return False
    if entry.name == "__init__.py":
        return False
    if not entry.name.endswith(".py"):
        return False
    return True


def get_workflow_modules(root: str, src: str):
    tree = os.scandir(os.path.join(root, src))
    subpackage = src.replace("/", ".")
    for s in filter(only_workflows, tree):
        a = os.path.splitext(s.name)[0]
        yield f"{subpackage}.{a}"


class HookGenerator:
    def __init__(self, filename):
        self.filename = filename
        self._hidden_imports = []

    def add_hidden_import(self, value):
        self._hidden_imports.append(value)

    def write(self):
        print(f"Writing to {self.filename}")
        with open(self.filename, "w", encoding="utf-8") as write_file:
            write_file.write('hiddenimports = [\n')
            for hidden_import in self._hidden_imports:
                write_file.write(f'    "{hidden_import}",\n')

            write_file.write(']\n')


def create_hook_file(
        package_path,
        output_path,
        hook_name="hook-speedwagon.workflows.py"
):
    if not os.path.exists(output_path):
        os.makedirs(output_path)
    hook_generator = \
        HookGenerator(os.path.join(output_path, hook_name))

    for x in get_workflow_modules(package_path,
                                  os.path.join("speedwagon", "workflows")):

        hook_generator.add_hidden_import(x)
        print(f"Added to hiddenignore: {x}")
    hook_generator.write()

if __name__ == '__main__':
    main()