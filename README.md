# WildFly Upgrade Agent

A cross-platform Python agent designed to detect, backup, and upgrade WildFly Application Server installations on Windows and Unix-like systems.

## Features

*   **Detection**: Identifies existing WildFly installations and verifies Java prerequisites.
*   **Vulnerability Check**: Queries the OSV.dev database for known vulnerabilities (CVEs) associated with the target WildFly version before downloading. **The upgrade will automatically abort if critical vulnerabilities are found.**
*   **Backup**: Automatically backs up the existing WildFly home directory to a zip archive before processing.
*   **Automated Upgrade**:
    *   Downloads the specified version of WildFly from the official GitHub releases.
    *   Extracts the new version to the target directory.
*   **Configuration Migration**:
    *   Migrates `standalone/deployments` to the new installation.
    *   Migrates `standalone/configuration/standalone.xml` (creating a backup of the default new config).
    *   Migrates properties files in the configuration directory.
    *   *Note*: Custom modules must currently be migrated manually.
*   **Verification**: Starts the upgraded server instance and waits for the successful startup log message ("WFLYSRV0025") to ensure the server is healthy.
*   **Reporting**: Generates detailed JSON logs and a Markdown summary report for every run.
*   **Dry Run**: specific flag `--dry-run` to simulate the entire process without making changes.

## Prerequisites

*   **Python 3.x** installed on the system.
*   **Java (JDK)** installed and available in the system PATH (WildFly requirement).
*   **Internet Access**: Required to download WildFly artifacts.

## Installation

No special installation is required. Simply download the script `wildfly_upgrade_agent.py` to the target machine.

## Usage

Run the script from the command line using Python 3.

### Basic Usage

To upgrade (or install) WildFly to a specific version (e.g., 27.0.0.Final):

```bash
python3 wildfly_upgrade_agent.py --target-version 27.0.0.Final
```

### Upgrading an Existing Installation

To upgrade an existing installation, provide the `--current-home` path:

```bash
python3 wildfly_upgrade_agent.py \
  --target-version 27.0.0.Final \
  --current-home /opt/wildfly-26.0.0.Final
```

### Customizing Directories

You can specify install location, backup location, and log directory:

```bash
python3 wildfly_upgrade_agent.py \
  --target-version 27.0.0.Final \
  --current-home C:\WildFly\wildfly-Old \
  --install-dir C:\WildFly \
  --backup-dir C:\Backups \
  --log-dir C:\Logs
```

### Health Check (Optional)
Run a health check against a URL after the server starts:

```bash
python3 wildfly_upgrade_agent.py --target-version 27.0.0.Final --health-url http://localhost:8080
```

### Dry Run (Recommended First Step)

check what the agent will do without modifying anything:

```bash
python3 wildfly_upgrade_agent.py --target-version 27.0.0.Final --dry-run
```

## Command Line Arguments

| Argument | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `--target-version` | The WildFly version to install (e.g., `27.0.0.Final`). | **Yes** | - |
| `--current-home` | Path to the existing WildFly installation to upgrade/migrate from. | No | `None` |
| `--install-dir` | Parent directory where the new WildFly version will be extracted. | No | `.` (Current Dir) |
| `--backup-dir` | Directory to store zip backups of the old installation. | No | `wildfly_backups` |
| `--log-dir` | Directory to store logs and reports. | No | `wildfly_upgrade_logs` |
| `--health-url` | URL or host for verification tests (e.g., `http://localhost:8080`). | No | `None` |
| `--dry-run` | Simulate the process without making changes. | No | `False` |

## Output

The agent creates a timestamped run directory in the `log-dir` containing:
*   `README.md`: A summary report of the run.
*   `agent.log`: A detailed text log of all operations.
*   `agent-run.jsonl`: Structured logs in JSONL format for machine parsing.

## Rollback

If the upgrade process fails or the verification step does not pass:
1.  The agent will report the failure in the console and the report file.
2.  If the new server was installed side-by-side, your original installation (`--current-home`) defaults to untouched.
3.  A zip backup of the original installation is stored in the `backup-dir` as an additional safety measure. Unzip this file to restore the previous state if needed.
