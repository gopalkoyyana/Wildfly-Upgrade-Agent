# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2025-12-06

### Added
- **Core Upgrade Logic**: Automated download and extraction of WildFly releases from GitHub.
- **Vulnerability Check**: Integration with OSV.dev API to detect vulnerabilities in the target version before upgrading.
    - Strict abort mode if critical vulnerabilities are found.
    - Dry-run support for vulnerability scanning.
- **Backup**: Automated zip backup of the existing installation.
- **Configuration Migration**:
    - Migration of `standalone/deployments`.
    - Migration of `standalone/configuration/standalone.xml` and properties files.
- **Verification**: Service startup verification and optional `--health-url` check.
- **Platform Support**: Cross-platform compatibility (Windows, Linux, macOS) via Python `subprocess` and `pathlib`.
- **Documentation**: Comprehensive `README.md` with usage examples and `CONTRIBUTING.md`.
