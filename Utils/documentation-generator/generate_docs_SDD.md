# generate_docs.py — Software Detailed Design

> **Usage Documentation:** [generate_docs.md](./generate_docs.md)  
> **Source File:** [generate_docs.py](./generate_docs.py)

---

## 1. Overview

`generate_docs.py` is a standalone Python utility that parses Java source files using regex-based extraction and generates structured Markdown documentation templates. It produces two documentation files per Java class: an API reference and a Software Detailed Design document. The script walks the source directory tree recursively, mirrors the folder structure in the output directory, and populates templates with extracted metadata (class names, fields, methods, imports, annotations).

---

## 2. Imports

```python
import os
import re
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
```

| Import | Purpose |
|--------|---------|
| `os` | File system operations: path resolution, directory walking, existence checks |
| `re` | Regular expression engine for parsing Java source code |
| `sys` | `sys.exit()` for error termination |
| `argparse` | CLI argument parsing with help generation |
| `Path` | Object-oriented path manipulation (available but primarily `os.path` is used) |
| `dataclass` | Declarative data classes for structured parse results |
| `field` | Default factory for mutable dataclass fields (lists) |
| `List`, `Optional` | Type annotations for clarity |

---

## 3. Data Models

### 3.1 `MethodInfo`

```python
@dataclass
class MethodInfo:
    name: str
    signature: str
    return_type: str
    parameters: List[tuple]
    annotations: List[str]
    access: str
    is_static: bool
    is_constructor: bool
```

Represents a single method or constructor extracted from a Java file.

| Field | Description |
|-------|-------------|
| `name` | Method identifier (or class name for constructors) |
| `signature` | Full reconstructed signature string for display in code blocks |
| `return_type` | Return type string (empty for constructors) |
| `parameters` | List of `(type, name)` tuples parsed from the parameter list |
| `annotations` | List of annotation strings (e.g., `"@Override"`) |
| `access` | Access modifier: `"public"`, `"private"`, or `"protected"` |
| `is_static` | Whether the method is declared `static` |
| `is_constructor` | Distinguishes constructors from regular methods |

### 3.2 `FieldInfo`

```python
@dataclass
class FieldInfo:
    name: str
    type: str
    access: str
    is_static: bool
    is_final: bool
```

Represents a class-level field declaration.

### 3.3 `JavaClassInfo`

```python
@dataclass
class JavaClassInfo:
    name: str
    file_name: str
    package: str
    imports: List[str]
    class_declaration: str
    fields: List[FieldInfo]
    methods: List[MethodInfo]
    extends_class: Optional[str]
    implements: List[str]
    javadoc: Optional[str]
```

Aggregate result of parsing a single Java file. Contains all metadata needed to generate both documentation templates.

---

## 4. Parsing Pipeline

### 4.1 `parse_java_file(file_path) → Optional[JavaClassInfo]`

The main parsing entry point. Reads the file content and delegates to sub-parsers.

**Steps:**
1. Read file with UTF-8 encoding (returns `None` on I/O or encoding errors)
2. Extract package declaration via regex: `^package\s+([\w.]+)\s*;`
3. Extract all import statements via regex: `^import\s+([\w.*]+)\s*;`
4. Locate the class/interface/enum declaration via a compound regex matching access modifiers, `extends`, and `implements` clauses
5. Extract class-level Javadoc by searching backward from the class declaration for a `/** ... */` block
6. Delegate to `extract_fields()` for field parsing
7. Delegate to `extract_methods()` for method/constructor parsing
8. Assemble and return a `JavaClassInfo` instance

**Class Declaration Regex:**
```
public\s+(?:abstract\s+)?(?:final\s+)?(?:class|interface|enum)\s+
(\w+)(?:\s+extends\s+([\w<>,\s]+?))?(?:\s+implements\s+([\w<>,\s]+?))?\s*\{
```

This handles standard Java class declarations including abstract classes, final classes, interfaces, and enums with optional inheritance and interface implementation.

### 4.2 `extract_fields(content, class_body_start) → List[FieldInfo]`

Extracts field declarations from the region between the class opening brace and the first method declaration.

**Strategy:**
- Finds the first method signature after `class_body_start` to bound the search region
- If no method is found, searches the first 500 characters after the class body start
- Matches lines of the form: `[access] [static] [final] Type name [= ...| ;]`
- Filters out false positives where the "type" is a keyword (`return`, `if`, `for`, etc.)

### 4.3 `extract_methods(content, class_name) → List[MethodInfo]`

Extracts all method and constructor signatures from the entire file content.

**Constructor Detection:**
- Uses a separate regex that matches `[access] ClassName(params) {`
- The class name is escaped with `re.escape()` to handle special characters safely
- Constructors are processed first, then excluded from the general method regex by name comparison

**Method Detection Regex:**
```
(?:(@\w+(?:\([^)]*\))?)\s+)?          # optional annotation
(public|private|protected)\s+          # access modifier
(static\s+)?                           # optional static
(?:synchronized\s+)?                   # optional synchronized
([\w<>\[\],?\s]+?)\s+                  # return type
(\w+)\s*                               # method name
\(([^)]*)\)\s*                         # parameters
(?:throws\s+[\w,\s]+)?\s*\{           # optional throws clause
```

**Limitations:**
- Only captures the first annotation per method
- Does not handle multi-line parameter lists (parameters must be on one line)
- Does not parse method bodies

### 4.4 `parse_parameters(params_raw) → List[tuple]`

Splits a comma-separated parameter string into `(type, name)` tuples.

- Strips parameter annotations (e.g., `@NotNull`)
- Uses `rsplit(" ", 1)` to separate type from name (handles generic types with spaces like `Map<String, List<Integer>>`)

---

## 5. Document Generation

### 5.1 `generate_api_doc(class_info, relative_source_path) → str`

Produces the API reference Markdown file content.

**Template Structure:**
```
# [FileName.java](relative/path/to/source)

[Description or TODO placeholder]

**Fields:**
- `fieldName` — TODO: describe field

**Functions:**
- [methodName](#methodname)

---

## methodName

### Signature
```java
[annotations]
[full signature]
```

### Description
TODO: ...

### Parameters
| Name | Type | Description |
...

### Returns
...
```

**Ordering:** Public methods are listed first in the table of contents, followed by private/protected methods. Duplicate names are deduplicated in the TOC.

### 5.2 `generate_sdd_doc(class_info, relative_source_path, api_doc_filename) → str`

Produces the Software Detailed Design Markdown file content.

**Template Structure:**
```
# ClassName — Software Detailed Design

> **API Documentation:** [ClassName.md](./ClassName.md)
> **Source File:** [FileName.java](relative/path)

---

## 1. Overview
## 2. Package Declaration & Imports
## 3. Class Declaration
## 4. Instance Fields
## 5+. [One section per method]
```

**Section Numbering:** Sections are auto-numbered sequentially. If there are no fields, the fields section is omitted and method sections start at 4.

---

## 6. Directory Traversal & File Generation

### 6.1 `process_source_directory(source_dir, plugin_folder, docs_output_dir, overwrite) → (int, int)`

Orchestrates the full generation pipeline.

**Algorithm:**
1. Convert paths to absolute
2. Walk the source directory with `os.walk()`
3. For each directory containing `.java` files:
   - Compute the relative path from `source_dir` to determine the output subdirectory
   - Create the output subdirectory with `os.makedirs(exist_ok=True)`
4. For each `.java` file:
   - Check if output files already exist (skip if both exist and `overwrite=False`)
   - Parse the Java file via `parse_java_file()`
   - Compute the relative source path from the doc file back to the source file
   - Generate and write the API doc
   - Generate and write the SDD doc
5. Return counts of generated and skipped file pairs

### 6.2 `compute_relative_source_path(source_file, source_root, doc_file_dir) → str`

Computes the relative path from a documentation file's directory to the corresponding source file. Uses `os.path.relpath()` and normalizes backslashes to forward slashes for Markdown link compatibility.

---

## 7. CLI Entry Point

### `main()`

1. Defines the argument parser with three positional args and one optional flag
2. Validates that `source_dir` and `plugin_folder` exist as directories
3. Prints configuration summary
4. Calls `process_source_directory()`
5. Prints final statistics

**Exit Codes:**
- `0` — Success
- `1` — Invalid source directory or plugin folder path

---

## 8. Design Decisions

| Decision | Rationale |
|----------|-----------|
| Regex-based parsing (not AST) | Zero external dependencies; sufficient for signature extraction without needing a full Java parser |
| Skip-by-default behavior | Prevents accidental loss of manually-written documentation |
| Relative source links | Documentation remains valid regardless of absolute project location |
| TODO placeholders | Templates are immediately identifiable as incomplete, guiding the author |
| Public methods first in TOC | Matches the convention used in existing project documentation |
| Single-pass field extraction (before first method) | Avoids capturing local variables inside method bodies as fields |
| Constructor detection via class name | Reliable heuristic that doesn't require full syntax analysis |

---

## 9. Known Limitations

- **Inner classes** — Not detected or documented separately; only the outermost class is parsed
- **Multi-line annotations** — Only single-line annotations immediately preceding a method are captured
- **Generic type parameters on class** — Not extracted (e.g., `class Foo<T>` captures `Foo` but not `<T>`)
- **Enum constants** — Not listed as fields for enum types
- **Interface default methods** — Parsed as regular methods (no special handling)
- **Overloaded methods** — Only one entry appears in the TOC (deduplicated by name), though all overloads get individual sections
