# Contributing to WildFly Upgrade Agent

Thank you for your interest in contributing to the WildFly Upgrade Agent! We welcome contributions from the community to help improve this tool.

## How to Contribute

### Reporting Bugs

If you find a bug, please create a new issue in the GitHub repository. Be sure to include:
*   A clear description of the issue.
*   Steps to reproduce the bug.
*   The version of WildFly you are targeting.
*   Your operating system and Python version.
*   Log output (please redact any sensitive information).

### Suggesting Enhancements

If you have an idea for a new feature or improvement, please open an issue to discuss it. We value your feedback!

### Pull Requests

1.  **Fork the repository**: Create a fork of the project to your own GitHub account.
2.  **Create a branch**: Create a new branch for your feature or bug fix (e.g., `feature/new-check` or `fix/download-error`).
3.  **Make changes**: Implement your changes. cleanliness and readability are appreciated.
4.  **Test**: Run the agent locally to ensure your changes work as expected.
    *   Use the `--dry-run` flag for safety.
    *   Verify the vulnerability check logic if modifying that area.
5.  **Commit**: Commit your changes with clear and descriptive commit messages.
6.  **Push**: Push your branch to your forked repository.
7.  **Submit a Pull Request**: Open a Pull Request (PR) against the `main` branch of the original repository. Provide a detailed description of your changes and reference any related issues.

## key Areas for Contribution

*   **Platform Support**: Testing and refining support for various Unix-like systems (AIX, Solaris, etc.).
*   **Vulnerability Database**: Improving the integration with OSV.dev or adding support for other vulnerability sources.
*   **Configuration Migration**: Enhancing the logic for migrating complex domain configurations or custom modules.
*   **Health Checks**: Adding more robust health check mechanisms beyond simple HTTP pings.

## Code Style

*   Follow standard Python PEP 8 style guidelines.
*   Keep code modular and well-documented.

Thank you for contributing!
