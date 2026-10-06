# AEI Engine Manifest

Status: draft, version 1.

## Introduction

An engine manifest is a small JSON file that describes one release of an
AEI engine: what it is, where to download it for each platform, how to start
it, and what options it takes. Downloads are optional: a manifest without
them describes an engine installed some other way, such as a developer's
own build, and a controller simply offers no download for it. A controller (a GUI or another program that
runs engines) can read a manifest to offer the engine for download, install
it, and show its options, without the user finding binaries and typing
paths.

A manifest is published with each release of the engine, alongside the
files it points at. The usual place is a release asset named
`engine.json`. On GitHub the URL

    https://github.com/OWNER/REPO/releases/latest/download/engine.json

always leads to the newest release's manifest, so a controller that
remembers that URL can find updates by fetching it again. A self-hosted
engine works the same way: any stable https URL that serves the current
manifest.

The manifest doesn't replace the protocol: the engine itself remains the
authority on how it behaves. The options listed here describe the release
for controllers that can't ask the engine (see "Options").

## Format

A manifest is a JSON object encoded in UTF-8. Keys are lower case with
underscores. Controllers must ignore keys they don't recognize, so later
versions can add keys without breaking older readers.

### Top level

| Key | Required | Meaning |
|---|---|---|
| `manifest_version` | yes | The version of this format: `1`. A controller should refuse a manifest whose major version it doesn't know. |
| `id` | yes | A stable identifier for the engine, the same in every release, used to recognize updates. Use a path you control, such as `github.com/Janzert/OpFor`. |
| `name` | yes | The engine's name for people, e.g. `OpFor`. |
| `version` | yes | This release's version, as a string, e.g. `2026.10.1` or `1.4`. Controllers compare versions only for equality unless both are dotted numbers. |
| `author` | no | Who wrote the engine. |
| `description` | no | A sentence or two about the engine. |
| `homepage` | no | A URL with more about the engine. |
| `license` | no | The license of the release, as an SPDX identifier where there is one (e.g. `MIT`, `BSD-3-Clause`). |
| `update_url` | no | Where the newest manifest is published, e.g. the GitHub `releases/latest/download/engine.json` URL above. A controller that loaded the manifest from a URL may use that URL instead. |
| `args` | no | Command line arguments to start the engine in AEI mode, as a list of strings. Default: none. |
| `downloads` | no | The files for each platform (see "Downloads"). Without it (or with no entry for its platform), a controller offers no download. |
| `options` | no | The engine's options (see "Options"). |

### Downloads

`downloads` is an object keyed by platform. A platform is `<os>-<arch>`:

- `os`: `linux`, `windows` or `macos`;
- `arch`: `x86_64` or `aarch64`.

(These are the names Rust's `std::env::consts` uses. Other values may be
used for other platforms; controllers ignore platforms they don't run on.)
A universal macOS build can be listed under both `macos-x86_64` and
`macos-aarch64`.

Each entry is an object:

| Key | Required | Meaning |
|---|---|---|
| `url` | yes | The file to download. Must be `https`. |
| `sha256` | yes | The file's SHA-256 digest, as 64 hexadecimal digits. A controller must refuse a file that doesn't match. |
| `archive` | no | `zip` or `tar.gz` when the file is an archive; absent when it's the executable itself. |
| `program` | for archives | The path of the executable inside the archive, with `/` separators, e.g. `opfor/bot_opfor.exe`. For a bare executable, the file name to save it as (default: the last part of `url`). |
| `args` | no | Arguments for this platform, replacing the top-level `args`. |

An archive is unpacked into a directory of its own, and the engine is
started with that directory as its working directory, so it can find any
files that come with it (opening books, data). Paths in an archive must stay
inside it: a controller must refuse entries that are absolute or contain
`..`. On Linux and macOS the controller marks `program` executable.

### Options

`options` is a list describing the options the engine accepts with
`setoption`, beyond the standard game state options in the AEI protocol
(`tcmove`, `rated` and the rest, which controllers set themselves). Each
entry is an object:

| Key | Required | Meaning |
|---|---|---|
| `name` | yes | The option's name, as sent in `setoption name <name>`. One word, matched exactly (case matters). |
| `type` | yes | One of the types below. |
| `default` | no | The engine's default, as a JSON value of the type's kind. |
| `min`, `max` | no | Bounds for a `spin` or a `float`. |
| `choices` | for `combo` | The allowed values, as strings. |
| `description` | no | What the option does, for people, including any limits on when it can be changed (for example, not during a search). |

The types, and how their values are sent in `setoption name <name> value <value>`:

| Type | Value | Default | Meaning |
|---|---|---|---|
| `check` | `true` or `false`, exactly | boolean | On or off. |
| `spin` | a decimal integer | integer | A whole number. |
| `float` | a decimal number, such as `0.75` | number | A number with a fraction. |
| `combo` | one of `choices` | string | A choice from a list. |
| `string` | the text | string | Free text. |
| `file` | a file's path | string | Like `string`; a controller can offer a file picker (an opening book, say). |
| `path` | a directory's path | string | Like `string`; a controller can offer a directory picker (tablebases, say). |
| `button` | none | none | An action: sent as `setoption name <name>` with no value. Only engines that declare a button need to accept a `setoption` without a value. |

A value is the rest of the `setoption` line after `value`, so it may
contain spaces, but not line breaks; engines may trim it and collapse runs
of spaces, so values shouldn't depend on them.

Options are documentation for controllers: an engine must still
handle an unrecognized option or value as the protocol says (log a
warning), and the engine's own report of its options, where the protocol
gives one, takes precedence over the manifest's.

## Example

```json
{
  "manifest_version": 1,
  "id": "github.com/Janzert/OpFor",
  "name": "OpFor",
  "version": "2026.10.1",
  "author": "Brian Haskin Jr.",
  "description": "An alpha-beta Arimaa engine.",
  "homepage": "https://github.com/Janzert/OpFor",
  "license": "MIT",
  "update_url": "https://github.com/Janzert/OpFor/releases/latest/download/engine.json",
  "downloads": {
    "linux-x86_64": {
      "url": "https://github.com/Janzert/OpFor/releases/download/v2026.10.1/opfor-linux-x86_64.tar.gz",
      "sha256": "…64 hex digits…",
      "archive": "tar.gz",
      "program": "opfor/bot_opfor"
    },
    "windows-x86_64": {
      "url": "https://github.com/Janzert/OpFor/releases/download/v2026.10.1/opfor-windows-x86_64.zip",
      "sha256": "…",
      "archive": "zip",
      "program": "opfor/bot_opfor.exe"
    },
    "macos-aarch64": {
      "url": "https://github.com/Janzert/OpFor/releases/download/v2026.10.1/opfor-macos-aarch64.tar.gz",
      "sha256": "…",
      "archive": "tar.gz",
      "program": "opfor/bot_opfor"
    }
  },
  "options": [
    { "name": "hash", "type": "spin", "default": 10, "min": 1,
      "description": "Size of the hash table in megabytes." },
    { "name": "threads", "type": "spin", "default": 1, "min": 1,
      "description": "Search threads." }
  ]
}
```

## Notes for controllers

- Fetch manifests and files only over https, and check every download's
  digest before using it.
- Installing an engine runs someone else's program: let the user choose to
  install it, show where the manifest came from, and don't update an
  installed engine without the user asking.
- Keep each version in its own directory, so an update can be undone and a
  running engine isn't replaced under it.
