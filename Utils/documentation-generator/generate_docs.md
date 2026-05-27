# generate_docs.py

A Python script that automatically generates template documentation files from Java source code. It parses `.java` files and produces both API reference (`.md`) and Software Detailed Design (`_SDD.md`) templates mirroring the source folder structure.

---

## Usage

```
python generate_docs.py <source_dir> <plugin_folder> <docs_output_dir> [--overwrite]
```

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `source_dir` | Yes | Path to the Java source code root directory (e.g., `src/main/java/org/almond/buildinglore`) |
| `plugin_folder` | Yes | Path to the plugin folder (e.g., `bin/main`) — used for path validation |
| `docs_output_dir` | Yes | Path to the documentation output directory (e.g., `Documentation`) |
| `--overwrite` | No | If set, overwrites existing documentation files. Default behavior skips files that already exist. |

### Examples

Generate docs (skip existing):
```
python Utils/generate_docs.py src/main/java/org/almond/buildinglore bin/main Documentation
```

Regenerate all docs (overwrite):
```
python Utils/generate_docs.py src/main/java/org/almond/buildinglore bin/main Documentation --overwrite
```

---

## Output

The script produces two files per Java source file:

### `[ClassName].md` — API Documentation

Contains:
- **Title** — Linked to the source file with a relative path
- **Description** — Extracted from class-level Javadoc, or a `TODO` placeholder
- **Fields** — List of class fields with placeholder descriptions
- **Functions** — Table of contents with anchor links to each method
- **Method Sections** — For each method:
  - Signature (with annotations)
  - Description placeholder
  - Parameter table (type, name, description)
  - Return type

### `[ClassName]_SDD.md` — Software Detailed Design

Contains:
- **Header** — Links to the API doc and source file
- **Section 1: Overview** — High-level description from Javadoc or placeholder
- **Section 2: Package Declaration & Imports** — Full import list with purpose table
- **Section 3: Class Declaration** — Class signature with inheritance/interface notes
- **Section 4: Instance Fields** — Code block and description table
- **Sections 5+: Methods** — One section per method with signature and design placeholder

### Folder Structure

The output mirrors the source directory hierarchy:

```
source_dir/                    docs_output_dir/
├── BuildingLorePlugin.java    ├── BuildingLorePlugin.md
│                              ├── BuildingLorePlugin_SDD.md
├── command/                   ├── command/
│   └── MyCommand.java         │   ├── MyCommand.md
│                              │   └── MyCommand_SDD.md
├── model/                     ├── model/
│   └── MyModel.java           │   ├── MyModel.md
│                              │   └── MyModel_SDD.md
```

---

## Behavior

- **Skip existing** — By default, if both `.md` and `_SDD.md` already exist for a file, the script skips that file entirely. Use `--overwrite` to regenerate.
- **Relative links** — Source file links in generated docs use relative paths computed from the doc file location back to the source file.
- **TODO placeholders** — All descriptions are filled with `TODO:` markers for manual completion.
- **Javadoc extraction** — If a class has a Javadoc comment immediately above the class declaration, it is used as the description instead of a TODO placeholder.
- **Constructor detection** — Constructors are identified and labeled separately from regular methods.
- **Annotation preservation** — Method annotations (e.g., `@Override`) are included in the signature block.

---

## Console Output

```
Source directory: C:\...\src\main\java\org\almond\buildinglore
Plugin folder:   C:\...\bin\main
Output directory: C:\...\Documentation
Overwrite mode:  OFF

Generating documentation templates...
--------------------------------------------------
  CREATED: BuildingLorePlugin.md
  CREATED: BuildingLorePlugin_SDD.md
  CREATED: command\BuildingLoreCommand.md
  CREATED: command\BuildingLoreCommand_SDD.md
  SKIP (exists): Selection.md & Selection_SDD.md
  WARN: Could not parse InvalidFile.java
--------------------------------------------------
Done. Generated: 2 file pairs, Skipped: 1 (already exist)
```

---

## Requirements

- Python 3.7+ (uses `dataclasses`, `typing`, `pathlib`)
- No external dependencies — uses only the standard library
