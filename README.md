# Modpack CLI

This repository contains a command line interface for searching and downloading modpacks from [Modrinth](https://modrinth.com/).

## Building

```bash
git submodule update --init --recursive
cmake -S . -B build
cmake --build build
```

Qt 6 and its development components must be installed for the build to
succeed. Extra CMake Modules (ECM) will be pulled from the repository via the
submodule update step above.

The resulting executable is `${Launcher_Name}_modpack` when using the provided build configuration.

## Usage

### Search for modpacks

```bash
${Launcher_Name}_modpack --search <name>
```

Displays the first ten results with their titles and IDs.

### Download a modpack

```bash
${Launcher_Name}_modpack --download <id|url> [--dest <directory>]
```

Downloads the latest file for the specified modpack. If `--dest` is omitted, the file is saved in the current directory. The program exits with a non-zero status and prints an error message if the download fails.
