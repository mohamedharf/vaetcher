import os
import ast
import json
import django
from django.conf import settings
from pathlib import Path


# -------------------------------------------
# Convert any value to something JSON-safe
# -------------------------------------------
def to_json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value

    # Convert Path → string
    if isinstance(value, Path):
        return str(value)

    # Convert lists
    if isinstance(value, list):
        return [to_json_safe(v) for v in value]

    # Convert dicts
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}

    # Fallback
    return str(value)


# -------------------------------------------
# Initialize Django
# -------------------------------------------
def init_django():
    if not os.environ.get("DJANGO_SETTINGS_MODULE"):
        for item in os.listdir("."):
            if os.path.isdir(item) and os.path.isfile(f"{item}/settings.py"):
                os.environ.setdefault("DJANGO_SETTINGS_MODULE", f"{item}.settings")
                break

    django.setup()


# -------------------------------------------
# Safe file reader
# -------------------------------------------
def read_file_safe(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except:
        return ""


# -------------------------------------------
# Python AST Inspector
# -------------------------------------------
class FileInspector(ast.NodeVisitor):
    def __init__(self):
        self.classes = []
        self.functions = []
        self.imports = []

    def visit_ClassDef(self, node):
        self.classes.append(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.functions.append(node.name)
        self.generic_visit(node)

    def visit_Import(self, node):
        for n in node.names:
            self.imports.append(n.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        if node.module:
            self.imports.append(node.module)
        self.generic_visit(node)


# -------------------------------------------
# Inspect ANY folder (apps, templates, static…)
# -------------------------------------------
def inspect_folder(folder_path):
    folder_data = {
        "python_files": [],
        "html_files": [],
        "css_files": [],
        "js_files": [],
        "all_files": [],
        "details": {}
    }

    for root, dirs, files in os.walk(folder_path):
        for file in files:

            file_path = os.path.join(root, file)
            folder_data["all_files"].append(file_path)

            # Python
            if file.endswith(".py"):
                folder_data["python_files"].append(file_path)

                code = read_file_safe(file_path)
                if not code:
                    continue

                try:
                    tree = ast.parse(code)
                    inspector = FileInspector()
                    inspector.visit(tree)

                    folder_data["details"][file_path] = {
                        "classes": inspector.classes,
                        "functions": inspector.functions,
                        "imports": inspector.imports,
                        "lines": len(code.splitlines())
                    }

                except:
                    continue

            # HTML
            elif file.endswith(".html"):
                folder_data["html_files"].append(file_path)
                content = read_file_safe(file_path)
                folder_data["details"][file_path] = {
                    "contains_blocks": "{% block" in content,
                    "extends": "{% extends" in content,
                    "includes": "{% include" in content,
                    "lines": len(content.splitlines())
                }

            # CSS
            elif file.endswith(".css"):
                folder_data["css_files"].append(file_path)
                content = read_file_safe(file_path)
                folder_data["details"][file_path] = {"lines": len(content.splitlines())}

            # JS
            elif file.endswith(".js"):
                folder_data["js_files"].append(file_path)
                content = read_file_safe(file_path)
                folder_data["details"][file_path] = {"lines": len(content.splitlines())}

    return folder_data


# -------------------------------------------
# Extract settings and installed apps
# -------------------------------------------
def extract_settings():
    try:
        data = {
            "INSTALLED_APPS": list(settings.INSTALLED_APPS),
            "MIDDLEWARE": list(settings.MIDDLEWARE),
            "DATABASES": settings.DATABASES,
            "TEMPLATES": settings.TEMPLATES,
            "LANGUAGE_CODE": settings.LANGUAGE_CODE,
            "TIME_ZONE": settings.TIME_ZONE,
            "STATIC_URL": getattr(settings, "STATIC_URL", None),
            "STATICFILES_DIRS": getattr(settings, "STATICFILES_DIRS", []),
            "STATIC_ROOT": getattr(settings, "STATIC_ROOT", None),
            "MEDIA_URL": getattr(settings, "MEDIA_URL", None),
            "MEDIA_ROOT": getattr(settings, "MEDIA_ROOT", None),
            "ROOT_URLCONF": settings.ROOT_URLCONF,
            "WSGI_APPLICATION": settings.WSGI_APPLICATION,
        }

        # 🔥 Convert everything to safe JSON values
        return to_json_safe(data)

    except Exception as e:
        return {"error": f"Settings load failed: {str(e)}"}


# -------------------------------------------
# MAIN PROJECT SCAN
# -------------------------------------------
def inspect_project(base_path="."):
    init_django()

    project_data = {
        "settings": extract_settings(),
        "folders": {}
    }

    print("\n🔍 Scanning entire Django project...\n")

    for item in os.listdir(base_path):
        path = os.path.join(base_path, item)

        if item in ["env", "venv", ".git", "__pycache__"]:
            continue

        if os.path.isdir(path):
            print(f"📂 Inspecting → {item}")
            project_data["folders"][item] = inspect_folder(path)

    # Save JSON safely
    with open("project_full_index.json", "w", encoding="utf-8") as f:
        json.dump(to_json_safe(project_data), f, indent=4, ensure_ascii=False)

    print("\n✔ DONE — Full index saved to: project_full_index.json\n")


if __name__ == "__main__":
    inspect_project()
