# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-08

### Added
- Initial Beta release of `rapidctl`.
- Support for creating custom CLI tools using Podman.
- Automatic container detection and lifecycle management (OSX and Linux).
- State management for container-based tools.
- MCP (Model Context Protocol) support for exposing subcommands.
- Authentication handling for container registries.
- Image caching and version management.
- Comprehensive test suite for core functionality.
- GitHub Actions for automated testing and PyPI publishing.

### Changed
- Refactored state management into a pluggable `StateManager`.
- Optimized GitHub Actions to trigger only on relevant file changes.

### Fixed
- Improved error handling for container command execution.
- Resolved issues with Podman authentication on macOS.
