#!/usr/bin/env python3
import os
import sys
import argparse
import platform
import shutil
import subprocess
import logging
import json
import time
import tarfile
import zipfile
import urllib.request
import urllib.error
import tempfile
from datetime import datetime
from pathlib import Path

# --- Configuration & Constants ---
LOG_DIR_DEFAULT = "wildfly_upgrade_logs"
BACKUP_DIR_DEFAULT = "wildfly_backups"
WILDFLY_DOWNLOAD_BASE_URL = "https://github.com/wildfly/wildfly/releases/download"

# --- Logger Setup ---
class Logger:
    def __init__(self, log_dir):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.run_id = f"run_{self.timestamp}"
        self.run_dir = self.log_dir / self.run_id
        self.run_dir.mkdir()
        
        self.log_file = self.run_dir / "agent.log"
        self.jsonl_file = self.run_dir / "agent-run.jsonl"
        self.report_file = self.run_dir / "README.md"
        
        # Python Logger
        self.logger = logging.getLogger("WildFlyAgent")
        self.logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        
        # File Handler
        fh = logging.FileHandler(self.log_file)
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Console Handler
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

        self.events = []

    def log(self, level, message, details=None):
        if level == "INFO":
            self.logger.info(message)
        elif level == "WARNING":
            self.logger.warning(message)
        elif level == "ERROR":
            self.logger.error(message)
        elif level == "DEBUG":
            self.logger.debug(message)
            
        event = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            "details": details or {}
        }
        self.events.append(event)
        with open(self.jsonl_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def generate_report(self, summary_data):
        with open(self.report_file, "w", encoding="utf-8") as f:
            f.write(f"# WildFly Upgrade Report\n\n")
            f.write(f"**Run ID:** {self.run_id}\n")
            f.write(f"**Timestamp:** {self.timestamp}\n")
            f.write(f"**Status:** {summary_data.get('status', 'Unknown')}\n\n")
            
            f.write("## Summary\n")
            for key, value in summary_data.items():
                f.write(f"*   **{key}:** {value}\n")
            
            f.write("\n## Events\n")
            for event in self.events:
                if event['level'] in ['INFO', 'WARNING', 'ERROR']:
                    icon = "✅" if event['level'] == 'INFO' else "⚠️" if event['level'] == 'WARNING' else "❌"
                    f.write(f"*   {icon} **{event['level']}**: {event['message']}\n")

# --- Utils ---
def run_command(cmd, cwd=None, env=None):
    try:
        result = subprocess.run(
            cmd, 
            cwd=cwd, 
            env=env,
            check=True, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.STDOUT, 
            text=True,
            shell=True 
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr

# --- Agent Class ---
class WildFlyUpgradeAgent:
    def __init__(self, args):
        self.args = args
        self.logger = Logger(args.log_dir)
        self.os_type = platform.system()
        self.target_version = args.target_version
        self.current_home = Path(args.current_home).resolve() if args.current_home else None
        self.install_dir = Path(args.install_dir).resolve() if args.install_dir else Path.cwd()
        self.backup_dir = Path(args.backup_dir).resolve()
        self.health_url = args.health_url
        self.dry_run = args.dry_run
        
        self.logger.log("INFO", "Initializing WildFly Upgrade Agent", {
            "os": self.os_type,
            "target_version": self.target_version,
            "current_home": str(self.current_home),
            "health_url": self.health_url,
            "dry_run": self.dry_run
        })

    def check_prerequisites(self):
        self.logger.log("INFO", "Checking prerequisites")
        
        # Check Java
        success, output = run_command("java -version")
        if not success:
            self.logger.log("ERROR", "Java not found. Please install Java (JDK 11+ recommended).")
            return False
        self.logger.log("INFO", "Java found", {"output": output.splitlines()[0]})
        
        # Check Current Installation
        if self.current_home:
            if not (self.current_home / "bin").exists() or not (self.current_home / "jboss-modules.jar").exists():
                # Allow for some variation, but standard WF has these
                if not (self.current_home / "version.txt").exists() and not (self.current_home / "LICENSE.txt").exists():
                     self.logger.log("WARNING", f"The directory {self.current_home} does not look like a standard WildFly installation.")
            
        return True

    def check_vulnerabilities(self):
        self.logger.log("INFO", f"Checking for vulnerabilities for WildFly {self.target_version}...")
        
        url = "https://api.osv.dev/v1/query"
        # We check wildfly-ee as a proxy for the distribution version
        payload = {
            "version": self.target_version,
            "package": {
                "name": "org.wildfly:wildfly-ee",
                "ecosystem": "Maven"
            }
        }
        
        try:
            req = urllib.request.Request(url, json.dumps(payload).encode('utf-8'))
            with urllib.request.urlopen(req) as response:
                if response.status == 200:
                    data = json.loads(response.read().decode('utf-8'))
                    vulns = data.get("vulns", [])
                    
                    if vulns:
                        self.logger.log("WARNING", f"Found {len(vulns)} vulnerabilities for WildFly {self.target_version}!")
                        print(f"\n[!] Vulnerabilities found for WildFly {self.target_version}:")
                        for vuln in vulns:
                            v_id = vuln.get("id", "Unknown")
                            summary = vuln.get("summary", "No summary")
                            print(f" - {v_id}: {summary}")
                        
                        warning_msg = "Critical vulnerabilities detected. Aborting upgrade to protect system security."
                        self.logger.log("ERROR", warning_msg)
                        return False
                    else:
                        self.logger.log("INFO", "No specific vulnerabilities found for this version in OSV database.")
                        
        except Exception as e:
            self.logger.log("WARNING", f"Failed to check vulnerabilities: {e}")
            # We don't block on API failure, just warn
            
        return True

    def perform_backup(self):
        if not self.current_home:
            self.logger.log("INFO", "No current installation provided, skipping backup.")
            return True

        self.logger.log("INFO", f"Backing up current installation: {self.current_home}")
        if self.dry_run:
            self.logger.log("INFO", "[DRY RUN] Would archive directory to backup location.")
            return True

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_filename = f"wildfly_backup_{self.current_home.name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.zip"
        backup_path = self.backup_dir / backup_filename
        
        try:
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(self.current_home):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = file_path.relative_to(self.current_home)
                        zipf.write(file_path, arcname)
            self.logger.log("INFO", f"Backup created successfully: {backup_path}")
            return True
        except Exception as e:
            self.logger.log("ERROR", f"Backup failed: {str(e)}")
            return False

    def download_and_install(self):
        self.logger.log("INFO", f"Downloading WildFly {self.target_version}")
        
        # Construct URL
        # Format: https://github.com/wildfly/wildfly/releases/download/27.0.0.Final/wildfly-27.0.0.Final.zip
        # User might provide just "27.0.0.Final"
        version = self.target_version
        filename = f"wildfly-{version}.zip"
        url = f"{WILDFLY_DOWNLOAD_BASE_URL}/{version}/{filename}"
        
        target_install_path = self.install_dir / f"wildfly-{version}"
        
        if target_install_path.exists():
            self.logger.log("WARNING", f"Target directory already exists: {target_install_path}. Skipping download.")
            return target_install_path

        if self.dry_run:
            self.logger.log("INFO", f"[DRY RUN] Would download {url} and extract to {self.install_dir}")
            return target_install_path

        # Download
        try:
            temp_file = Path(tempfile.gettempdir()) / filename
            self.logger.log("INFO", f"Downloading from {url} to {temp_file}")
            urllib.request.urlretrieve(url, temp_file)
            
            # Extract
            self.logger.log("INFO", f"Extracting to {self.install_dir}")
            with zipfile.ZipFile(temp_file, 'r') as zip_ref:
                zip_ref.extractall(self.install_dir)
            
            self.logger.log("INFO", "Download and extraction complete")
            return target_install_path
        except urllib.error.URLError as e:
            self.logger.log("ERROR", f"Failed to download WildFly: {e}")
            return None
        except Exception as e:
            self.logger.log("ERROR", f"Installation failed: {e}")
            return None

    def migrate_configuration(self, new_home):
        if not self.current_home:
            return
        
        self.logger.log("INFO", "Migrating configuration and deployments")
        if self.dry_run:
            self.logger.log("INFO", "[DRY RUN] Would copy deployments and configuration files.")
            return

        # 1. Deployments
        old_deployments = self.current_home / "standalone" / "deployments"
        new_deployments = new_home / "standalone" / "deployments"
        if old_deployments.exists():
            for item in old_deployments.iterdir():
                if item.name == "README.txt": continue
                target = new_deployments / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)
            self.logger.log("INFO", "Deployments migrated.")

        # 2. Configuration (Standalone.xml specifically)
        # Attempt to copy standalone.xml, but backup the new one first
        old_config = self.current_home / "standalone" / "configuration" / "standalone.xml"
        new_config_dir = new_home / "standalone" / "configuration"
        new_config = new_config_dir / "standalone.xml"
        
        if old_config.exists():
            shutil.copy2(new_config, new_config_dir / "standalone.xml.original")
            shutil.copy2(old_config, new_config)
            self.logger.log("INFO", "standalone.xml migrated (original backed up).")
            
            # Also copy properties files often referenced in config
            for prop_file in old_config.parent.glob("*.properties"):
                shutil.copy2(prop_file, new_config_dir / prop_file.name)

        # 3. Modules (User added modules)
        # This is complex because 'system' modules shouldn't be overwritten.
        # Minimal effort: Check for a 'layers' directory or custom modules structure.
        # For this agent, we will log a warning to manually check modules.
        self.logger.log("WARNING", "Custom modules were not automatically migrated. Please check 'modules' directory manually if you have custom drivers or libraries.")

    def verify_installation(self, new_home):
        self.logger.log("INFO", "Verifying installation by starting the server...")
        if self.dry_run:
            self.logger.log("INFO", "[DRY RUN] Would start server and check for success log.")
            return True

        bin_dir = new_home / "bin"
        script = "standalone.bat" if self.os_type == "Windows" else "./standalone.sh"
        cmd = str(bin_dir / script)
        
        process = None
        started = False
        
        try:
            # Start standalone mode
            # We need to set NOPAUSE=true for Windows batch to not hang on exit? Actually we kill it anyway.
            env = os.environ.copy()
            env["NOPAUSE"] = "true"
            
            process = subprocess.Popen(
                cmd, 
                shell=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                cwd=bin_dir,
                env=env,
                text=True
            )
            
            # Read stdout line by line
            start_time = time.time()
            while time.time() - start_time < 60: # Wait up to 60 seconds
                line = process.stdout.readline()
                if not line:
                    break
                # print(line.strip()) # Debugging
                if "WFLYSRV0025: WildFly Full" in line and "started in" in line:
                    started = True
                    self.logger.log("INFO", "Server started successfully detected.", {"log": line.strip()})
                    break
            
            if not started:
                self.logger.log("ERROR", "Server did not start within 60 seconds or failed to log startup success.")
                return False

            # Optional Health Check
            if self.health_url:
                self.logger.log("INFO", f"Running health check against {self.health_url}")
                import urllib.request
                try:
                    # Retry loop for health check
                    health_success = False
                    for i in range(10): # Try for 20 seconds
                        try:
                            with urllib.request.urlopen(self.health_url, timeout=2) as response:
                                if response.status == 200:
                                    health_success = True
                                    self.logger.log("INFO", f"Health check passed: {self.health_url} returned 200 OK")
                                    break
                        except:
                            time.sleep(2)
                    
                    if not health_success:
                        self.logger.log("WARNING", f"Health check failed: Could not reach {self.health_url} after startup.")
                        # We don't fail the whole upgrade if health check fails, but we warn.
                except Exception as e:
                     self.logger.log("WARNING", f"Health check error: {e}")

        except Exception as e:

            self.logger.log("ERROR", f"Error during verification: {e}")
            return False
        finally:
            if process:
                self.logger.log("INFO", "Stopping server...")
                if self.os_type == "Windows":
                     subprocess.run(f"taskkill /F /T /PID {process.pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                else:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except:
                        process.kill()
        
        return started

    def run(self):
        self.logger.log("INFO", "--- Starting Upgrade Process ---")
        
        if not self.check_prerequisites():
            self.logger.generate_report({"status": "Failed Pre-checks"})
            return

        if not self.check_vulnerabilities():
            self.logger.generate_report({"status": "Aborted (Vulnerabilities)"})
            return

        if not self.perform_backup():
            self.logger.generate_report({"status": "Failed Backup"})
            return

        new_home_path = self.download_and_install()
        if not new_home_path:
            self.logger.generate_report({"status": "Failed Download/Install"})
            return

        self.migrate_configuration(new_home_path)

        success = self.verify_installation(new_home_path)
        
        status = "Success" if success else "Verification Failed"
        self.logger.log("INFO", f"--- Upgrade Process Finished: {status} ---")
        
        self.logger.generate_report({
            "status": status,
            "new_home": str(new_home_path),
            "old_home": str(self.current_home) if self.current_home else "None"
        })
        print(f"\nReport generated at: {self.logger.report_file}")

# --- Entry Point ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WildFly Upgrade Agent")
    parser.add_argument("--target-version", required=True, help="Target WildFly version (e.g., 27.0.0.Final)")
    parser.add_argument("--current-home", required=False, help="Path to current WildFly installation")
    parser.add_argument("--install-dir", required=False, default=".", help="Directory to install the new version")
    parser.add_argument("--backup-dir", required=False, default=BACKUP_DIR_DEFAULT, help="Directory to store backups")
    parser.add_argument("--log-dir", required=False, default=LOG_DIR_DEFAULT, help="Directory to store logs")
    parser.add_argument("--health-url", required=False, help="URL to check for health after upgrade")
    parser.add_argument("--dry-run", action="store_true", help="Simulate execution without modifying system")
    
    args = parser.parse_args()
    
    agent = WildFlyUpgradeAgent(args)
    agent.run()
