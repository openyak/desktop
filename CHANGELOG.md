# Changelog

All notable changes to this project will be documented in this file.

Format follows [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Fixed

- **frontend:** Prevent duplicate messages on rapid double-click send ([P0-01])
- **frontend:** Preserve unsent draft text and attachments across session switches ([P0-02])
- **frontend:** Abort backend generation when switching sessions ([P0-03])
- **frontend:** Reset SSE module-level state when navigating away during generation ([P0-04])
- **frontend/backend:** Abort generation before deleting active session; publish DONE event on IntegrityError ([P0-05])
- **backend:** Persist tool error status to database on RejectedError and generic Exception ([P0-06])
- **backend:** Isolate MCP connector failures so one bad connector doesn't block app startup ([P0-07])
- **frontend:** Redirect to provider setup page after skipping onboarding ([P0-08])

### Added

- GitHub Issue templates (Bug Report, Feature Request)
- Pull Request template
- Label definitions for GitHub Issues
- Contributing guide with Conventional Commits convention
- Changelog
