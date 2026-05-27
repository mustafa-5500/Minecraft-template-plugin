"""
Documentation Template Generator for Java Plugin Projects.

Given a source code directory, plugin folder, and documentation output folder,
this script generates template .md and _SDD.md documentation files mirroring
the source folder structure. Templates follow the existing documentation format.

Usage:
    python generate_docs.py <source_dir> <plugin_folder> <docs_output_dir>

Example:
    python generate_docs.py ../src/main/java/org/almond/buildinglore ../bin/main ../Documentation
"""

import os
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MethodInfo:
    name: str
    signature: str
    return_type: str
    parameters: List[tuple]  # [(type, name), ...]
    annotations: List[str] = field(default_factory=list)
    access: str = "public"
    is_static: bool = False
    is_constructor: bool = False


@dataclass
class FieldInfo:
    name: str
    type: str
    access: str = "private"
    is_static: bool = False
    is_final: bool = False


@dataclass
class JavaClassInfo:
    name: str
    file_name: str
    package: str
    imports: List[str]
    class_declaration: str
    fields: List[FieldInfo]
    methods: List[MethodInfo]
    extends_class: Optional[str] = None
    implements: List[str] = field(default_factory=list)
    javadoc: Optional[str] = None


def parse_java_file(file_path: str) -> Optional[JavaClassInfo]:
    """Parse a Java file and extract class information."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
    except (IOError, UnicodeDecodeError):
        return None

    lines = content.split("\n")

    # Extract package
    package = ""
    pkg_match = re.search(r"^package\s+([\w.]+)\s*;", content, re.MULTILINE)
    if pkg_match:
        package = pkg_match.group(1)

    # Extract imports
    imports = re.findall(r"^import\s+([\w.*]+)\s*;", content, re.MULTILINE)

    # Extract class declaration
    class_match = re.search(
        r"(public\s+(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+"
        r"(\w+)(?:\s+extends\s+([\w<>,\s]+?))?(?:\s+implements\s+([\w<>,\s]+?))?\s*\{)",
        content,
    )

    if not class_match:
        return None

    class_declaration = class_match.group(1)
    class_name = class_match.group(2)
    extends_class = class_match.group(3).strip() if class_match.group(3) else None
    implements_raw = class_match.group(4)
    implements = (
        [i.strip() for i in implements_raw.split(",")]
        if implements_raw
        else []
    )

    # Extract class-level javadoc (immediately before class declaration)
    javadoc = None
    class_line_idx = content.find(class_match.group(0))
    before_class = content[:class_line_idx].rstrip()
    javadoc_match = re.search(r"/\*\*(.*?)\*/\s*$", before_class, re.DOTALL)
    if javadoc_match:
        raw = javadoc_match.group(1)
        javadoc = re.sub(r"^\s*\*\s?", "", raw, flags=re.MULTILINE).strip()

    # Extract fields
    fields = extract_fields(content, class_match.end())

    # Extract methods
    methods = extract_methods(content, class_name)

    file_name = os.path.basename(file_path)

    return JavaClassInfo(
        name=class_name,
        file_name=file_name,
        package=package,
        imports=imports,
        class_declaration=class_declaration,
        fields=fields,
        methods=methods,
        extends_class=extends_class,
        implements=implements,
        javadoc=javadoc,
    )


def extract_fields(content: str, class_body_start: int) -> List[FieldInfo]:
    """Extract field declarations from the class body."""
    fields = []
    # Match field declarations (not inside methods)
    # Look for lines like: private final Type name; or private Type name = ...;
    field_pattern = re.compile(
        r"^\s*((?:private|protected|public)\s+)?"
        r"(static\s+)?(final\s+)?"
        r"([\w<>\[\],\s]+?)\s+"
        r"(\w+)\s*(?:=|;)",
        re.MULTILINE,
    )

    # Only look at the top-level of the class (before first method)
    # Find the first method start
    method_start = re.search(
        r"(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:synchronized\s+)?"
        r"(?:[\w<>\[\],\s]+?)\s+\w+\s*\([^)]*\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
        content[class_body_start:],
    )

    search_region = (
        content[class_body_start : class_body_start + method_start.start()]
        if method_start
        else content[class_body_start : class_body_start + 500]
    )

    for match in field_pattern.finditer(search_region):
        access = (match.group(1) or "package-private").strip()
        is_static = bool(match.group(2))
        is_final = bool(match.group(3))
        field_type = match.group(4).strip()
        field_name = match.group(5).strip()

        # Skip common false positives
        if field_type in ("return", "if", "for", "while", "new", "class", "import"):
            continue

        fields.append(
            FieldInfo(
                name=field_name,
                type=field_type,
                access=access,
                is_static=is_static,
                is_final=is_final,
            )
        )

    return fields


def extract_methods(content: str, class_name: str) -> List[MethodInfo]:
    """Extract method signatures from the class."""
    methods = []

    # Pattern for method declarations
    method_pattern = re.compile(
        r"(?:(@\w+(?:\([^)]*\))?)\s+)?"  # optional annotation
        r"(public|private|protected)\s+"
        r"(static\s+)?"
        r"(?:synchronized\s+)?"
        r"([\w<>\[\],?\s]+?)\s+"  # return type
        r"(\w+)\s*"  # method name
        r"\(([^)]*)\)\s*"  # parameters
        r"(?:throws\s+[\w,\s]+)?\s*\{",
        re.MULTILINE,
    )

    # Also match constructors
    constructor_pattern = re.compile(
        r"(?:(@\w+(?:\([^)]*\))?)\s+)?"
        r"(public|private|protected)\s+"
        + re.escape(class_name)
        + r"\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*\{",
        re.MULTILINE,
    )

    # Find constructors
    for match in constructor_pattern.finditer(content):
        annotation = match.group(1) or ""
        access = match.group(2)
        params_raw = match.group(3).strip()
        parameters = parse_parameters(params_raw)

        annotations = [annotation] if annotation else []
        sig = f"{access} {class_name}({params_raw})"

        methods.append(
            MethodInfo(
                name=class_name,
                signature=sig,
                return_type="",
                parameters=parameters,
                annotations=annotations,
                access=access,
                is_static=False,
                is_constructor=True,
            )
        )

    # Find methods
    for match in method_pattern.finditer(content):
        annotation = match.group(1) or ""
        access = match.group(2)
        is_static = bool(match.group(3))
        return_type = match.group(4).strip()
        method_name = match.group(5).strip()
        params_raw = match.group(6).strip()

        # Skip if this is actually a constructor (caught above)
        if method_name == class_name:
            continue

        parameters = parse_parameters(params_raw)
        annotations = [annotation] if annotation else []

        static_str = "static " if is_static else ""
        sig = f"{access} {static_str}{return_type} {method_name}({params_raw})"

        methods.append(
            MethodInfo(
                name=method_name,
                signature=sig,
                return_type=return_type,
                parameters=parameters,
                annotations=annotations,
                access=access,
                is_static=is_static,
                is_constructor=False,
            )
        )

    return methods


def parse_parameters(params_raw: str) -> List[tuple]:
    """Parse a parameter string into a list of (type, name) tuples."""
    if not params_raw:
        return []

    params = []
    for param in params_raw.split(","):
        param = param.strip()
        if not param:
            continue
        # Handle annotations in params (e.g., @NotNull String name)
        param = re.sub(r"@\w+\s+", "", param)
        parts = param.rsplit(" ", 1)
        if len(parts) == 2:
            params.append((parts[0].strip(), parts[1].strip()))
        else:
            params.append((param, ""))

    return params


def compute_relative_source_path(
    source_file: str, source_root: str, doc_file_dir: str
) -> str:
    """Compute the relative path from the doc file to the source file."""
    source_abs = os.path.abspath(source_file)
    doc_dir_abs = os.path.abspath(doc_file_dir)

    return os.path.relpath(source_abs, doc_dir_abs).replace("\\", "/")


def generate_api_doc(
    class_info: JavaClassInfo, relative_source_path: str
) -> str:
    """Generate the API documentation (.md) template."""
    lines = []

    # Title with link to source
    lines.append(
        f"# [{class_info.file_name}]({relative_source_path})"
    )
    lines.append("")

    # Description placeholder
    if class_info.javadoc:
        lines.append(class_info.javadoc)
    else:
        lines.append(f"TODO: Add description for `{class_info.name}`.")
    lines.append("")

    # Fields section
    if class_info.fields:
        lines.append("**Fields:**")
        for f in class_info.fields:
            lines.append(f"- `{f.name}` — TODO: describe field")
        lines.append("")

    # Constants section
    constants = [f for f in class_info.fields if f.is_static and f.is_final]
    non_constant_fields = [
        f for f in class_info.fields if not (f.is_static and f.is_final)
    ]
    if constants and non_constant_fields:
        # Already listed all above, no need to separate
        pass

    # Functions table of contents
    if class_info.methods:
        public_methods = [m for m in class_info.methods if m.access == "public"]
        private_methods = [m for m in class_info.methods if m.access != "public"]
        
        all_display_methods = public_methods + private_methods
        if all_display_methods:
            lines.append("**Functions:**")
            seen_names = set()
            for m in all_display_methods:
                display_name = m.name if not m.is_constructor else f"{m.name} (Constructor)"
                anchor = m.name.lower().replace(" ", "-")
                if m.name not in seen_names:
                    lines.append(f"- [{display_name}](#{anchor})")
                    seen_names.add(m.name)
            lines.append("")

    # Method details
    lines.append("---")
    lines.append("")

    for method in class_info.methods:
        if method.is_constructor:
            lines.append(f"## {method.name} (Constructor)")
        else:
            lines.append(f"## {method.name}")
        lines.append("")

        lines.append("### Signature")
        lines.append("```java")
        if method.annotations:
            for ann in method.annotations:
                lines.append(ann)
        lines.append(method.signature)
        lines.append("```")
        lines.append("")

        lines.append("### Description")
        lines.append(f"TODO: Describe what `{method.name}` does.")
        lines.append("")

        if method.parameters:
            lines.append("### Parameters")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for ptype, pname in method.parameters:
                lines.append(f"| `{pname}` | `{ptype}` | TODO: describe |")
            lines.append("")
        else:
            lines.append("### Parameters")
            lines.append("None.")
            lines.append("")

        lines.append("### Returns")
        if method.is_constructor:
            lines.append(f"`{method.name}` instance.")
        elif method.return_type == "void":
            lines.append("`void`")
        else:
            lines.append(f"`{method.return_type}` — TODO: describe return value.")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_sdd_doc(
    class_info: JavaClassInfo,
    relative_source_path: str,
    api_doc_filename: str,
) -> str:
    """Generate the Software Detailed Design (_SDD.md) template."""
    lines = []

    # Title
    lines.append(f"# {class_info.name} — Software Detailed Design")
    lines.append("")

    # Header links
    lines.append(f"> **API Documentation:** [{api_doc_filename}](./{api_doc_filename})  ")
    lines.append(
        f"> **Source File:** [{class_info.file_name}]({relative_source_path})"
    )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 1: Overview
    lines.append("## 1. Overview")
    lines.append("")
    if class_info.javadoc:
        lines.append(class_info.javadoc)
    else:
        lines.append(f"TODO: Provide a high-level overview of `{class_info.name}`.")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 2: Package & Imports
    lines.append("## 2. Package Declaration & Imports")
    lines.append("")
    lines.append("```java")
    lines.append(f"package {class_info.package};")
    lines.append("```")
    lines.append("")

    if class_info.imports:
        lines.append("```java")
        for imp in class_info.imports:
            lines.append(f"import {imp};")
        lines.append("```")
        lines.append("")

        lines.append("| Import | Purpose |")
        lines.append("|--------|---------|")
        for imp in class_info.imports:
            short_name = imp.split(".")[-1]
            lines.append(f"| `{short_name}` | TODO: describe purpose |")
        lines.append("")

    lines.append("---")
    lines.append("")

    # Section 3: Class Declaration
    lines.append("## 3. Class Declaration")
    lines.append("")
    lines.append("```java")
    lines.append(class_info.class_declaration)
    lines.append("```")
    lines.append("")

    if class_info.extends_class:
        lines.append(
            f"- **`extends {class_info.extends_class}`** — TODO: explain inheritance."
        )
    if class_info.implements:
        lines.append(
            f"- **`implements {', '.join(class_info.implements)}`** — TODO: explain interfaces."
        )
    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 4: Instance Fields
    section_num = 4
    if class_info.fields:
        lines.append(f"## {section_num}. Instance Fields")
        lines.append("")
        lines.append("```java")
        for f in class_info.fields:
            static_str = "static " if f.is_static else ""
            final_str = "final " if f.is_final else ""
            lines.append(f"{f.access} {static_str}{final_str}{f.type} {f.name};")
        lines.append("```")
        lines.append("")

        lines.append("| Field | Type | Description |")
        lines.append("|-------|------|-------------|")
        for f in class_info.fields:
            lines.append(f"| `{f.name}` | `{f.type}` | TODO: describe |")
        lines.append("")
        lines.append("---")
        lines.append("")
        section_num += 1

    # Method sections
    for method in class_info.methods:
        if method.is_constructor:
            lines.append(f"## {section_num}. Constructor")
        else:
            lines.append(f"## {section_num}. `{method.name}()`")
        lines.append("")

        lines.append("```java")
        if method.annotations:
            for ann in method.annotations:
                lines.append(ann)
        lines.append(method.signature)
        lines.append("```")
        lines.append("")
        lines.append(f"TODO: Provide detailed design explanation for `{method.name}`.")
        lines.append("")
        lines.append("---")
        lines.append("")
        section_num += 1

    return "\n".join(lines)


def process_source_directory(
    source_dir: str, plugin_folder: str, docs_output_dir: str, overwrite: bool = False
):
    """Walk the source directory and generate documentation templates."""
    source_dir = os.path.abspath(source_dir)
    docs_output_dir = os.path.abspath(docs_output_dir)

    # Determine the base package directory structure
    # We want to mirror subfolders relative to source_dir
    generated_count = 0
    skipped_count = 0

    for root, dirs, files in os.walk(source_dir):
        java_files = [f for f in files if f.endswith(".java")]
        if not java_files:
            continue

        # Compute relative path from source root
        rel_dir = os.path.relpath(root, source_dir)
        if rel_dir == ".":
            # Files at the root of source_dir go directly into docs_output_dir
            doc_dir = docs_output_dir
        else:
            doc_dir = os.path.join(docs_output_dir, rel_dir)

        # Create output directory
        os.makedirs(doc_dir, exist_ok=True)

        for java_file in java_files:
            source_file = os.path.join(root, java_file)
            base_name = java_file.replace(".java", "")
            api_doc_path = os.path.join(doc_dir, f"{base_name}.md")
            sdd_doc_path = os.path.join(doc_dir, f"{base_name}_SDD.md")

            # Skip if files already exist and overwrite is False
            if not overwrite:
                api_exists = os.path.exists(api_doc_path)
                sdd_exists = os.path.exists(sdd_doc_path)
                if api_exists and sdd_exists:
                    print(f"  SKIP (exists): {base_name}.md & {base_name}_SDD.md")
                    skipped_count += 1
                    continue

            # Parse the Java file
            class_info = parse_java_file(source_file)
            if not class_info:
                print(f"  WARN: Could not parse {java_file}")
                continue

            # Compute relative path from doc file to source file
            relative_source = compute_relative_source_path(
                source_file, source_dir, doc_dir
            )

            # Generate API doc
            if overwrite or not os.path.exists(api_doc_path):
                api_content = generate_api_doc(class_info, relative_source)
                with open(api_doc_path, "w", encoding="utf-8") as f:
                    f.write(api_content)
                print(f"  CREATED: {os.path.relpath(api_doc_path, docs_output_dir)}")

            # Generate SDD doc
            if overwrite or not os.path.exists(sdd_doc_path):
                sdd_content = generate_sdd_doc(
                    class_info, relative_source, f"{base_name}.md"
                )
                with open(sdd_doc_path, "w", encoding="utf-8") as f:
                    f.write(sdd_content)
                print(f"  CREATED: {os.path.relpath(sdd_doc_path, docs_output_dir)}")

            generated_count += 1

    return generated_count, skipped_count


def main():
    parser = argparse.ArgumentParser(
        description="Generate documentation templates from Java source files."
    )
    parser.add_argument(
        "source_dir",
        help="Path to the Java source code root directory (e.g., src/main/java/org/almond/buildinglore)",
    )
    parser.add_argument(
        "plugin_folder",
        help="Path to the plugin folder (used for reference context)",
    )
    parser.add_argument(
        "docs_output_dir",
        help="Path to the documentation output directory",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing documentation files (default: skip existing)",
    )

    args = parser.parse_args()

    # Validate paths
    if not os.path.isdir(args.source_dir):
        print(f"ERROR: Source directory not found: {args.source_dir}")
        sys.exit(1)

    if not os.path.isdir(args.plugin_folder):
        print(f"ERROR: Plugin folder not found: {args.plugin_folder}")
        sys.exit(1)

    print(f"Source directory: {os.path.abspath(args.source_dir)}")
    print(f"Plugin folder:   {os.path.abspath(args.plugin_folder)}")
    print(f"Output directory: {os.path.abspath(args.docs_output_dir)}")
    print(f"Overwrite mode:  {'ON' if args.overwrite else 'OFF'}")
    print()
    print("Generating documentation templates...")
    print("-" * 50)

    generated, skipped = process_source_directory(
        args.source_dir, args.plugin_folder, args.docs_output_dir, args.overwrite
    )

    print("-" * 50)
    print(f"Done. Generated: {generated} file pairs, Skipped: {skipped} (already exist)")


if __name__ == "__main__":
    main()
