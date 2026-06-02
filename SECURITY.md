# Security Policy

## Supported Versions

Security fixes are handled on the default branch, `main`, until the project adopts versioned releases.

## Reporting a Vulnerability

Do not open a public issue for secrets, credential leaks, or exploitable vulnerabilities.

Report privately through one of these channels:

* GitHub private vulnerability reporting, if enabled for this repository.
* A direct maintainer contact listed in the GitHub repository profile.

Include:

* A concise description of the issue.
* Reproduction steps or affected files.
* Impact and whether credentials, local files, or generated media can be exposed.

## Secret Handling

The app stores Gemini API keys and Google Cloud service account JSON in macOS Keychain under the `com.phongho.translatedubai` service. The local `~/.translatedub_ai/config.json` file is reserved for non-secret preferences and is written with restrictive file permissions. If an older config file contains secrets, the app migrates them to Keychain and rewrites the file without those secret fields.

The configuration API returns only non-secret settings plus boolean "configured" flags, not stored Gemini API keys or Google Cloud service account JSON.

Never commit local `config.json`, Google Cloud service account JSON, API keys, temporary videos, generated audio, or app build artifacts.
