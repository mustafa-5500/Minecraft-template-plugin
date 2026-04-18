# Minecraft Plugin Template (Paper)

This repository is a starter template for building Minecraft plugins using the Paper API and Gradle.

## Requirements
- Java 21+

## Build

```bash
./gradlew build
```

On Windows PowerShell:

```powershell
.\gradlew.bat build
```

The plugin JAR will be generated in `build/libs/`.

## Run in Server

1. Build the plugin.
2. Copy the generated JAR from `build/libs/` into your Paper server's `plugins/` folder.
3. Start or restart the server.
4. Run `/template` in-game or from the server console.

## Change Package and Names

Before using in production, update:

- `group` / `rootProject.name` / `version` in `build.gradle` and `settings.gradle`
- package path under `src/main/java`
- `main` entry and metadata in `plugin.yml`
