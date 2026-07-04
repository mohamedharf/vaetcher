"""
inspect_templates.py  —  V4
============================
Django template deep analyzer.

Outputs
-------
  templates_full.json   كل البيانات الخام
  templates_agent.md    تقرير جاهز للـ AI agent

Fixes over V3
-------------
  ✔ forms: استبدل chunk[3000] بـ find("</form>") الصحيح
  ✔ cache: atomic write بـ os.replace على tmp file
  ✔ RE_LOAD: split كل tag library على حدة
  ✔ HTMX used: يحسب triggers + targets مش بس endpoints
  ✔ RE_FILTERS: يستخرج داخل {{ }} بس مش في الـ HTML
  ✔ dynamic include/extends: يكتشفهم ويعلّم عليهم كـ flag
  ✔ unused template detection
  ✔ reverse dependency graph (included_by / extended_by)
  ✔ large template warning (> 500 lines)
  ✔ static file existence check (اختياري)
"""

import os
import re
import json
import hashlib
import logging
from collections import defaultdict

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

# -------------------------------------------------------
# Logging
# -------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
)
log = logging.getLogger("inspect_templates")

# -------------------------------------------------------
# Config
# -------------------------------------------------------

CACHE_FILE = ".template_inspector_cache.json"

SKIP_DIRS = {
    "venv", "env", ".git", "node_modules",
    "__pycache__", ".tox", "dist", "build",
}

LARGE_TEMPLATE_THRESHOLD = 500  # lines

DJANGO_BUILTINS = {
    "user", "request", "perms", "messages", "csrf_token",
    "True", "False", "None", "forloop", "block",
    "STATIC_URL", "MEDIA_URL", "LANGUAGE_CODE", "DEBUG",
    "now", "widget", "form",
}

# -------------------------------------------------------
# Helpers
# -------------------------------------------------------

def read_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def file_hash(content):
    # utf-8 explicit — الـ default encoding بيختلف حسب platform
    return hashlib.md5(content.encode("utf-8")).hexdigest()


def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_cache(cache):
    """Atomic write — لو السكربت وقف أثناء الكتابة الملف مش هيتكسر"""
    tmp = CACHE_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
        os.replace(tmp, CACHE_FILE)
    except Exception as e:
        log.warning("Cache write failed: %s", e)
        try:
            os.remove(tmp)
        except OSError:
            pass


def find_template_dirs(base_path="."):
    dirs = []
    for root, dirnames, _ in os.walk(base_path):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for d in list(dirnames):
            if d == "templates":
                dirs.append(os.path.join(root, d))
    return dirs


# -------------------------------------------------------
# Template Parser — V4
# -------------------------------------------------------

class TemplateParser:

    # --- inheritance & composition ---
    # static strings فقط — dynamic cases اتشال لـ RE_EXTENDS_DYN
    RE_EXTENDS      = re.compile(r'{%[-\s]*extends\s+["\'](.+?)["\']')
    RE_EXTENDS_DYN  = re.compile(r'{%[-\s]*extends\s+(?!["\'])(\w+)')
    RE_INCLUDE      = re.compile(r'{%[-\s]*include\s+["\'](.+?)["\']')
    RE_INCLUDE_DYN  = re.compile(r'{%[-\s]*include\s+(?!["\'])(\w+)')
    RE_BLOCK        = re.compile(r'{%[-\s]*block\s+(\w+)')
    RE_ENDBLOCK     = re.compile(r'{%[-\s]*endblock')

    # FIX: load — يمسك كل المحتوى بين load و%} ثم يعمل split
    RE_LOAD         = re.compile(r'{%[-\s]*load\s+([^%]+)%}')

    # --- variables & filters ---
    RE_VARIABLE     = re.compile(r'{{\s*([a-zA-Z_][\w\.]*)')

    # FIX: نمسك الـ {{ expression }} الكاملة الأول ثم نستخرج الـ filters منها
    RE_EXPR_BLOCK   = re.compile(r'{{([^}]+)}}')
    RE_FILTER_NAME  = re.compile(r'\|\s*([\w_]+)')

    # --- loops & conditions ---
    RE_LOOP         = re.compile(r'{%[-\s]*for\s+(\w[\w,\s]*)\s+in\s+([\w\.]+)')
    RE_CONDITION    = re.compile(r'{%[-\s]*if\s+(.+?)[\s%]')

    # --- URLs ---
    RE_URL          = re.compile(r'{%[-\s]*url\s+["\'](.+?)["\']([^%]*?)%}')

    # --- static ---
    RE_STATIC       = re.compile(r'{%[-\s]*static\s+["\'](.+?)["\']')

    # --- with / trans ---
    RE_WITH         = re.compile(r'{%[-\s]*with\s+(.+?)%}')
    RE_TRANS        = re.compile(r'{%[-\s]*(?:trans|blocktrans)\s+["\'](.+?)["\']')

    # --- developer comments ---
    RE_COMMENTS     = re.compile(r'{#(.+?)#}', re.DOTALL)

    # --- Django form object ---
    RE_FORM_OBJ     = re.compile(r'{{\s*form(?:\.\w+)?')

    # --- HTMX ---
    RE_HX_GET       = re.compile(r'hx-get=["\']([^"\']+)["\']')
    RE_HX_POST      = re.compile(r'hx-post=["\']([^"\']+)["\']')
    RE_HX_TARGET    = re.compile(r'hx-target=["\']([^"\']+)["\']')
    RE_HX_SWAP      = re.compile(r'hx-swap=["\']([^"\']+)["\']')
    RE_HX_TRIGGER   = re.compile(r'hx-trigger=["\']([^"\']+)["\']')
    RE_HX_PUSH      = re.compile(r'hx-push-url=["\']([^"\']+)["\']')
    RE_HX_BOOST     = re.compile(r'hx-boost=["\']([^"\']+)["\']')

    # --- misc flags ---
    RE_PAGINATOR    = re.compile(
        r'\b(?:paginator|page_obj|is_paginated|page\.has_next|page\.has_previous)\b'
    )
    RE_MESSAGES     = re.compile(r'{%[-\s]*for\s+\w+\s+in\s+messages')
    RE_HREF         = re.compile(r'<a\s[^>]*href=["\']([^"\']+)["\']', re.IGNORECASE)

    # --- regex fallback forms ---
    RE_FORM_TAG     = re.compile(r'<form[^>]*>', re.IGNORECASE)
    RE_FORM_ACTION  = re.compile(r'action=["\']([^"\']*)["\']', re.IGNORECASE)
    RE_FORM_METHOD  = re.compile(r'method=["\'](\w+)["\']', re.IGNORECASE)
    RE_INPUT_TAG    = re.compile(r'<input[^>]*>', re.IGNORECASE)
    RE_INPUT_NAME   = re.compile(r'name=["\']([^"\']+)["\']', re.IGNORECASE)
    RE_INPUT_TYPE   = re.compile(r'type=["\']([^"\']+)["\']', re.IGNORECASE)
    RE_SELECT_NAME  = re.compile(r'<select[^>]*name=["\']([^"\']+)["\']', re.IGNORECASE)
    RE_TEXTAREA_NAME= re.compile(r'<textarea[^>]*name=["\']([^"\']+)["\']', re.IGNORECASE)

    # --------------------------------------------------------

    def parse(self, content, path):
        loops     = self._parse_loops(content)
        loop_vars = self._extract_loop_vars(loops)
        lines     = len(content.splitlines())

        result = {
            "file":  path,
            "lines": lines,

            # inheritance & composition
            "extends":          self.RE_EXTENDS.findall(content),
            "extends_dynamic":  self.RE_EXTENDS_DYN.findall(content),   # NEW
            "includes":         self.RE_INCLUDE.findall(content),
            "includes_dynamic": self.RE_INCLUDE_DYN.findall(content),   # NEW
            "blocks":           self.RE_BLOCK.findall(content),
            "endblock_count":   len(self.RE_ENDBLOCK.findall(content)),
            "loaded_tags":      self._parse_load(content),              # FIX

            # context
            "variables":     sorted(set(self.RE_VARIABLE.findall(content))),
            "filters_used":  self._parse_filters(content),             # FIX
            "with_contexts": self.RE_WITH.findall(content),
            "loops":         loops,
            "conditions":    self.RE_CONDITION.findall(content)[:20],

            # forms
            "forms":                   self._parse_forms(content),
            "uses_django_form_object": bool(self.RE_FORM_OBJ.search(content)),

            # HTMX
            "htmx": self._parse_htmx(content),                         # FIX

            # URLs & nav
            "url_tags":   self._parse_url_tags(content),
            "href_links": self.RE_HREF.findall(content),

            # static
            "static_files": self._classify_static(self.RE_STATIC.findall(content)),

            # flags
            "uses_pagination": bool(self.RE_PAGINATOR.search(content)),
            "uses_messages":   bool(self.RE_MESSAGES.search(content)),
            "translations":    self.RE_TRANS.findall(content),
            "is_large":        lines > LARGE_TEMPLATE_THRESHOLD,       # NEW

            # developer notes
            "template_comments": [
                c.strip() for c in self.RE_COMMENTS.findall(content) if c.strip()
            ],
        }

        # classification
        result["is_base"]    = bool(result["blocks"] and not result["extends"])
        result["is_partial"] = (
            not result["extends"]
            and not result["is_base"]
            and lines < 60
        )

        # inferred context
        result["context_requirements"] = self._infer_context(result, loop_vars)

        return result

    # --------------------------------------------------------
    # FIX: RE_LOAD — split each library correctly
    # --------------------------------------------------------

    def _parse_load(self, content):
        loaded = []
        for m in self.RE_LOAD.finditer(content):
            loaded.extend(m.group(1).strip().split())
        return sorted(set(loaded))

    # --------------------------------------------------------
    # FIX: Filters — extract only from {{ }} blocks
    # --------------------------------------------------------

    def _parse_filters(self, content):
        filters = defaultdict(list)
        for expr_m in self.RE_EXPR_BLOCK.finditer(content):
            expr = expr_m.group(1)
            for f_m in self.RE_FILTER_NAME.finditer(expr):
                name = f_m.group(1)
                raw  = f_m.group(0).strip()
                filters[name].append(raw)
        return dict(filters)

    # --------------------------------------------------------
    # Forms
    # --------------------------------------------------------

    def _parse_forms(self, content):
        if BS4_AVAILABLE:
            return self._parse_forms_bs4(content)
        return self._parse_forms_regex(content)

    def _parse_forms_bs4(self, content):
        soup  = BeautifulSoup(content, "html.parser")
        forms = []
        for form in soup.find_all("form"):
            fields = []
            for inp in form.find_all("input"):
                fields.append({
                    "tag":  "input",
                    "name": inp.get("name"),
                    "type": inp.get("type", "text"),
                })
            for sel in form.find_all("select"):
                fields.append({"tag": "select",   "name": sel.get("name"), "type": "select"})
            for ta  in form.find_all("textarea"):
                fields.append({"tag": "textarea", "name": ta.get("name"),  "type": "textarea"})
            forms.append({
                "action":  form.get("action"),
                "method":  (form.get("method") or "GET").upper(),
                "enctype": form.get("enctype"),
                "fields":  fields,
            })
        return forms

    def _parse_forms_regex(self, content):
        """FIX: استخدم find("</form>") بدل chunk[3000]"""
        forms = []
        for m in self.RE_FORM_TAG.finditer(content):
            tag_html = m.group(0)
            action_m = self.RE_FORM_ACTION.search(tag_html)
            method_m = self.RE_FORM_METHOD.search(tag_html)

            # FIX: مش هنقص الـ form بشكل تعسفي
            end_pos = content.find("</form>", m.end())
            if end_pos == -1:
                chunk = content[m.end():]
            else:
                chunk = content[m.end(): end_pos]

            fields = []
            for inp in self.RE_INPUT_TAG.finditer(chunk):
                h  = inp.group(0)
                nm = self.RE_INPUT_NAME.search(h)
                tp = self.RE_INPUT_TYPE.search(h)
                fields.append({
                    "tag":  "input",
                    "name": nm.group(1) if nm else None,
                    "type": tp.group(1) if tp else "text",
                })
            for sel in self.RE_SELECT_NAME.finditer(chunk):
                fields.append({"tag": "select",   "name": sel.group(1), "type": "select"})
            for ta  in self.RE_TEXTAREA_NAME.finditer(chunk):
                fields.append({"tag": "textarea", "name": ta.group(1),  "type": "textarea"})

            forms.append({
                "action":  action_m.group(1) if action_m else None,
                "method":  method_m.group(1).upper() if method_m else "GET",
                "enctype": None,
                "fields":  fields,
            })
        return forms

    # --------------------------------------------------------
    # FIX: HTMX — used يحسب triggers + targets مش بس endpoints
    # --------------------------------------------------------

    def _parse_htmx(self, content):
        htmx = {
            "get_endpoints":  self.RE_HX_GET.findall(content),
            "post_endpoints": self.RE_HX_POST.findall(content),
            "targets":        self.RE_HX_TARGET.findall(content),
            "swaps":          self.RE_HX_SWAP.findall(content),
            "triggers":       self.RE_HX_TRIGGER.findall(content),
            "push_urls":      self.RE_HX_PUSH.findall(content),
            "boost":          self.RE_HX_BOOST.findall(content),
        }
        # FIX: مش any(htmx.values()) لأنه circular مع "used" نفسه
        htmx["used"] = any([
            htmx["get_endpoints"],
            htmx["post_endpoints"],
            htmx["triggers"],
            htmx["targets"],
        ])
        return htmx

    # --------------------------------------------------------
    # Loops
    # --------------------------------------------------------

    def _parse_loops(self, content):
        loops = []
        for m in self.RE_LOOP.finditer(content):
            loops.append({
                "item":     m.group(1).strip(),
                "iterable": m.group(2).strip(),
            })
        return loops

    def _extract_loop_vars(self, loops):
        vars_ = set()
        for l in loops:
            for v in l["item"].replace(" ", "").split(","):
                vars_.add(v.strip())
        return vars_

    # --------------------------------------------------------
    # URLs
    # --------------------------------------------------------

    def _parse_url_tags(self, content):
        urls = []
        for m in self.RE_URL.finditer(content):
            urls.append({
                "name": m.group(1),
                "args": m.group(2).strip() or None,
            })
        return urls

    # --------------------------------------------------------
    # Static
    # --------------------------------------------------------

    def _classify_static(self, files):
        out = {"css": [], "js": [], "images": [], "other": []}
        for f in files:
            if f.endswith(".css"):
                out["css"].append(f)
            elif f.endswith(".js"):
                out["js"].append(f)
            elif f.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico")):
                out["images"].append(f)
            else:
                out["other"].append(f)
        return out

    # --------------------------------------------------------
    # Context inference
    # --------------------------------------------------------

    def _infer_context(self, result, loop_vars):
        ctx = set()
        for loop in result["loops"]:
            top = loop["iterable"].split(".")[0]
            if top not in DJANGO_BUILTINS:
                ctx.add(top)
        for var in result["variables"]:
            top = var.split(".")[0]
            if top in DJANGO_BUILTINS:
                continue
            if top in loop_vars:
                continue
            ctx.add(top)
        return sorted(ctx)


# -------------------------------------------------------
# NEW: Reverse dependency graph
# -------------------------------------------------------

def build_dependency_graph(results):
    """
    Forward graph:  child  -> parent (extends/includes)
    Reverse graph:  parent -> children (extended_by / included_by)
    """
    graph = {}
    for path, data in results.items():
        graph[path] = {
            "extends":     data["extends"][0] if data["extends"] else None,
            "includes":    data["includes"],
            # reverse — يتملا بعدين
            "extended_by": [],
            "included_by": [],
        }

    # بنمشي تاني مرة نملا الـ reverse
    for path, data in results.items():
        parent = graph[path]["extends"]
        if parent and parent in graph:
            graph[parent]["extended_by"].append(path)

        for inc in graph[path]["includes"]:
            if inc in graph:
                graph[inc]["included_by"].append(path)

    return graph


# -------------------------------------------------------
# NEW: Unused template detection
# -------------------------------------------------------

def find_unused_templates(results, graph):
    """
    Template محسوبة unused لو:
    - مش بتعمل extends لحاجة (يعني مش page template)
    - ومش متضمنة في أي include
    - ومش base لأي template (extended_by فاضية)
    - ومش base template (is_base = False)
    - ومش اسمها فيه hint إنها base
    """
    base_name_hints = {"base", "layout", "master", "skeleton", "root", "foundation"}
    unused = []

    for path, data in results.items():
        g = graph.get(path, {})

        # لو بتعمل extends → هي page template فعلية مش unused
        if g.get("extends"):
            continue

        # لو حد بيعملها extend أو include → مش unused
        if g.get("extended_by") or g.get("included_by"):
            continue

        # لو هي نفسها base → مش unused (هي نقطة البداية)
        if data.get("is_base"):
            continue

        # لو اسمها فيه hint إنها base → تجاهل
        name_lower = os.path.basename(path).lower().replace(".html", "")
        if any(hint in name_lower for hint in base_name_hints):
            continue

        unused.append(path)

    return unused


# -------------------------------------------------------
# NEW: Static files existence check
# -------------------------------------------------------

def check_static_files(results, static_root=None):
    """
    بيتحقق إن الـ static files المستخدمة في التمبليتس موجودة فعلاً.
    static_root: المسار الـ static الرئيسي — لو None يجرب يلاقيه تلقائياً.
    """
    if static_root is None:
        candidates = ["static", "assets", "staticfiles"]
        for c in candidates:
            if os.path.isdir(c):
                static_root = c
                break

    if not static_root:
        return {}

    missing = defaultdict(list)
    for path, data in results.items():
        all_static = (
            data["static_files"]["css"]
            + data["static_files"]["js"]
            + data["static_files"]["images"]
            + data["static_files"]["other"]
        )
        for f in all_static:
            full = os.path.join(static_root, f)
            if not os.path.exists(full):
                missing[path].append(f)

    return dict(missing)


# -------------------------------------------------------
# Tree rendering
# -------------------------------------------------------

def build_tree(graph):
    tree = defaultdict(list)
    for tpl, data in graph.items():
        if data["extends"]:
            tree[data["extends"]].append(tpl)
    return tree


def render_tree(tree, node, depth=0):
    prefix = "  " * depth + ("└─ " if depth else "")
    lines  = [f"{prefix}{node}"]
    for child in sorted(tree.get(node, [])):
        lines.extend(render_tree(tree, child, depth + 1))
    return lines


# -------------------------------------------------------
# Markdown Report — V4
# -------------------------------------------------------

def build_agent_report(results, graph, unused, missing_static):
    lines = []
    lines.append("# Django Templates — Backend Requirements (V4)")
    lines.append("_Generated by inspect_templates.py V4_\n")
    lines.append("---\n")

    bases    = {k: v for k, v in results.items() if v["is_base"]}
    partials = {k: v for k, v in results.items() if v["is_partial"]}
    pages    = {k: v for k, v in results.items()
                if not v["is_base"] and not v["is_partial"]}
    large    = {k: v for k, v in results.items() if v.get("is_large")}

    # ---- Summary ----
    lines.append("## Summary\n")
    lines.append("| Type | Count |")
    lines.append("|------|-------|")
    lines.append(f"| Total templates | {len(results)} |")
    lines.append(f"| Base/layout | {len(bases)} |")
    lines.append(f"| Page templates | {len(pages)} |")
    lines.append(f"| Partials | {len(partials)} |")
    lines.append(f"| With forms | {sum(1 for v in results.values() if v['forms'])} |")
    lines.append(f"| With HTMX | {sum(1 for v in results.values() if v['htmx']['used'])} |")
    lines.append(f"| With pagination | {sum(1 for v in results.values() if v['uses_pagination'])} |")
    lines.append(f"| Large (>{LARGE_TEMPLATE_THRESHOLD} lines) | {len(large)} |")
    lines.append(f"| Possibly unused | {len(unused)} |")
    lines.append("")

    # ---- Warnings ----
    has_warnings = large or unused or missing_static
    if has_warnings:
        lines.append("## Warnings\n")

        if large:
            lines.append("### Large templates (consider splitting)\n")
            for path in sorted(large):
                lines.append(f"- `{path}` ({results[path]['lines']} lines)")
            lines.append("")

        if unused:
            lines.append("### Possibly unused templates\n")
            for path in sorted(unused):
                lines.append(f"- `{path}`")
            lines.append("")

        if missing_static:
            lines.append("### Missing static files\n")
            for path, files in sorted(missing_static.items()):
                lines.append(f"- `{path}`:")
                for f in files:
                    lines.append(f"  - `{f}`")
            lines.append("")

    # ---- Hierarchy ----
    lines.append("## Template Hierarchy\n\n```")
    tree  = build_tree(graph)
    roots = [k for k, v in graph.items() if not v["extends"]]
    for root in sorted(roots):
        lines.extend(render_tree(tree, root))
    lines.append("```\n")

    # ---- Base templates ----
    if bases:
        lines.append("## Base Templates\n")
        for path, t in sorted(bases.items()):
            g = graph.get(path, {})
            lines.append(f"### `{path}` ({t['lines']} lines)")
            if t["blocks"]:
                lines.append(f"- Blocks: `{'`, `'.join(t['blocks'])}`")
            if t["loaded_tags"]:
                lines.append(f"- Loaded: {', '.join(t['loaded_tags'])}")
            if g.get("extended_by"):
                lines.append(f"- Extended by: {', '.join(f'`{x}`' for x in sorted(g['extended_by']))}")
            if t["htmx"]["used"]:
                lines.append("- HTMX detected")
            lines.append("")

    # ---- Page templates ----
    lines.append("## Page Templates\n")
    lines.append("> Each section = one URL + one view\n")

    for path, t in sorted(pages.items()):
        g = graph.get(path, {})
        lines.append(f"### `{path}`")
        lines.append(f"- Lines: {t['lines']}" + (" ⚠️ large" if t.get("is_large") else ""))

        if t["extends"]:
            lines.append(f"- Extends: `{t['extends'][0]}`")
        if t.get("extends_dynamic"):
            lines.append(f"- Extends dynamic var: `{'`, `'.join(t['extends_dynamic'])}`")
        if t["includes"]:
            lines.append(f"- Includes: {', '.join(f'`{i}`' for i in t['includes'])}")
        if t.get("includes_dynamic"):
            lines.append(f"- Includes dynamic var: `{'`, `'.join(t['includes_dynamic'])}`")

        # Context
        if t["context_requirements"]:
            lines.append("\n**Context variables (view must pass):**")
            for var in t["context_requirements"]:
                lines.append(f"  - `{var}`")

        # Loops → QuerySets
        if t["loops"]:
            lines.append("\n**QuerySets / Lists:**")
            for loop in t["loops"]:
                lines.append(f"  - `{loop['iterable']}` iterated as `{loop['item']}`")

        # Forms
        if t["forms"] or t["uses_django_form_object"]:
            lines.append("\n**Forms:**")
            if t["uses_django_form_object"]:
                lines.append("  - Uses `{{ form }}` — pass Django Form instance from view")
            for i, form in enumerate(t["forms"], 1):
                enc = f" enctype=`{form['enctype']}`" if form.get("enctype") else ""
                lines.append(
                    f"  - Form #{i}: `{form['method']}` → `{form['action'] or 'same URL'}`{enc}"
                )
                for field in form["fields"]:
                    if field["name"]:
                        lines.append(f"    - `{field['name']}` ({field['type']})")

        # HTMX
        if t["htmx"]["used"]:
            lines.append("\n**HTMX endpoints needed:**")
            for ep in t["htmx"]["get_endpoints"]:
                lines.append(f"  - GET `{ep}`")
            for ep in t["htmx"]["post_endpoints"]:
                lines.append(f"  - POST `{ep}`")
            if t["htmx"]["targets"]:
                lines.append(f"  - Targets: {', '.join(f'`{x}`' for x in t['htmx']['targets'])}")
            if t["htmx"]["triggers"]:
                lines.append(f"  - Triggers: {', '.join(f'`{x}`' for x in t['htmx']['triggers'])}")

        # URL names
        if t["url_tags"]:
            lines.append("\n**URL names:**")
            for u in t["url_tags"]:
                args = f" `{u['args']}`" if u["args"] else ""
                lines.append(f"  - `{u['name']}`{args}")

        # Flags
        flags = []
        if t["uses_pagination"]:
            flags.append("pagination (`page_obj`)")
        if t["uses_messages"]:
            flags.append("messages framework")
        if t["translations"]:
            flags.append("i18n translations")
        if flags:
            lines.append(f"\n**Flags:** {', '.join(flags)}")

        # Filters
        if t["filters_used"]:
            lines.append(
                f"\n**Filters:** {', '.join(f'`{f}`' for f in sorted(t['filters_used']))}"
            )

        # Developer notes
        if t["template_comments"]:
            lines.append("\n**Developer notes:**")
            for c in t["template_comments"]:
                lines.append(f"  > {c}")

        lines.append("\n---\n")

    # ---- Partials ----
    if partials:
        lines.append("## Partial / Include Templates\n")
        for path, t in sorted(partials.items()):
            g = graph.get(path, {})
            lines.append(f"### `{path}` ({t['lines']} lines)")
            if t["context_requirements"]:
                lines.append(
                    f"- Context: {', '.join(f'`{v}`' for v in t['context_requirements'])}"
                )
            if g.get("included_by"):
                lines.append(
                    f"- Included by: {', '.join(f'`{x}`' for x in sorted(g['included_by']))}"
                )
            if t["htmx"]["used"]:
                eps = t["htmx"]["get_endpoints"] + t["htmx"]["post_endpoints"]
                lines.append(f"- HTMX: {', '.join(f'`{e}`' for e in eps)}")
            if t["forms"]:
                lines.append(f"- Contains {len(t['forms'])} form(s)")
            lines.append("")

    # ---- Consolidated checklists ----
    all_urls  = set()
    htmx_get  = set()
    htmx_post = set()
    for t in results.values():
        for u in t["url_tags"]:
            all_urls.add(u["name"])
        for ep in t["htmx"]["get_endpoints"]:
            htmx_get.add(ep)
        for ep in t["htmx"]["post_endpoints"]:
            htmx_post.add(ep)

    lines.append("## Checklist: urls.py\n")
    if all_urls:
        for name in sorted(all_urls):
            lines.append(f"- [ ] `{name}`")
    else:
        lines.append("_No `{% url %}` tags found_")

    if htmx_get or htmx_post:
        lines.append("\n## Checklist: HTMX endpoints\n")
        for ep in sorted(htmx_get):
            lines.append(f"- [ ] GET  `{ep}`")
        for ep in sorted(htmx_post):
            lines.append(f"- [ ] POST `{ep}`")

    lines.append("\n---")
    lines.append("_V4 — use `templates_full.json` for full raw data_")
    return "\n".join(lines)


# -------------------------------------------------------
# MAIN
# -------------------------------------------------------

def main(base_path=".", check_static=False):
    log.info("\nDjango Template Inspector — V4")
    log.info("=" * 42)

    parser  = TemplateParser()
    cache   = load_cache()
    results = {}

    template_dirs = find_template_dirs(base_path)
    if not template_dirs:
        log.warning("No templates/ folder found — scanning all .html files")
        template_dirs = [base_path]

    log.info("Template dirs: %s\n", template_dirs)

    cached_count = 0

    for tdir in template_dirs:
        for root, dirs, files in os.walk(tdir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            for fname in files:
                if not fname.endswith(".html"):
                    continue
                fpath   = os.path.join(root, fname)
                rel     = os.path.relpath(fpath, base_path)
                content = read_file(fpath)
                if not content:
                    continue
                h = file_hash(content)
                if rel in cache and cache[rel].get("hash") == h:
                    results[rel] = cache[rel]["data"]
                    cached_count += 1
                    continue
                parsed       = parser.parse(content, rel)
                results[rel] = parsed
                cache[rel]   = {"hash": h, "data": parsed}
                log.info("  parsed: %s", rel)

    save_cache(cache)   # atomic write

    if cached_count:
        log.info("\n  %d template(s) from cache", cached_count)

    if not results:
        log.error("No templates found!")
        return

    # Analysis
    graph          = build_dependency_graph(results)
    unused         = find_unused_templates(results, graph)
    missing_static = check_static_files(results) if check_static else {}

    # Save JSON
    with open("templates_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    # Save Markdown
    report = build_agent_report(results, graph, unused, missing_static)
    with open("templates_agent.md", "w", encoding="utf-8") as f:
        f.write(report)

    # Summary
    bases    = sum(1 for v in results.values() if v["is_base"])
    partials = sum(1 for v in results.values() if v["is_partial"])
    pages    = len(results) - bases - partials
    large    = sum(1 for v in results.values() if v.get("is_large"))

    log.info("\n" + "=" * 42)
    log.info("Done — %d templates", len(results))
    log.info("  Base     : %d", bases)
    log.info("  Pages    : %d", pages)
    log.info("  Partials : %d", partials)
    if large:
        log.info("  Large    : %d  ⚠️", large)
    if unused:
        log.info("  Unused   : %d  ⚠️", len(unused))
    log.info("\n  -> templates_full.json")
    log.info("  -> templates_agent.md")
    log.info("=" * 42 + "\n")


if __name__ == "__main__":
    import sys
    import argparse

    ap = argparse.ArgumentParser(description="Django Template Inspector V4")
    ap.add_argument("path", nargs="?", default=".", help="Project root (default: .)")
    ap.add_argument(
        "--check-static", action="store_true",
        help="Check if static files referenced in templates actually exist"
    )
    args = ap.parse_args()
    main(base_path=args.path, check_static=args.check_static)