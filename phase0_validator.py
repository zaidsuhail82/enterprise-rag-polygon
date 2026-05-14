#!/usr/bin/env python3
"""
Phase 0 Validator - Enterprise RAG System
Checks all prerequisites before ingestion and deployment.

Aligned with this repo layout (api/ + src/) and src/utils/config.py / .env.example
(CF_ACCESS_* keys, not legacy CLOUDFLARE_* names).
"""

import sys
import json
from pathlib import Path
import subprocess

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

class Phase0Validator:
    # Values copied from .env.example — treat as unset for Phase 0 gating
    _PLACEHOLDER_SUBSTRINGS = {
        "SUPABASE_URL": ("your-project.supabase.co",),
        "SUPABASE_SERVICE_KEY": ("your-supabase-service-role-key",),
        "GOOGLE_DRIVE_ROOT_FOLDER_ID": ("your-root-folder-id-here",),
    }
    _PLACEHOLDER_CF_TEAM = "yourcompany.cloudflareaccess.com"
    _PLACEHOLDER_CF_AUD = "your-cloudflare-access-aud-tag"

    def __init__(self):
        self.results = {
            'passed': [],
            'warnings': [],
            'failed': [],
            'missing': []
        }
        self._dotenv: dict[str, str] = {}
        
    def check(self, name: str, condition: bool, required: bool = True, details: str = ""):
        """Register a check result"""
        status = "✓" if condition else "✗"
        color = Colors.GREEN if condition else (Colors.RED if required else Colors.YELLOW)
        
        result = {
            'name': name,
            'passed': condition,
            'required': required,
            'details': details
        }
        
        if condition:
            self.results['passed'].append(result)
        elif required:
            self.results['failed'].append(result)
        else:
            self.results['warnings'].append(result)
            
        print(f"{color}{status}{Colors.END} {name}")
        if details and not condition:
            print(f"  → {details}")
        
        return condition
    
    def section(self, title: str):
        """Print a section header"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{title}{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

    # ==================== CHECKS ====================
    
    def check_python_version(self):
        """Verify Python 3.11+"""
        version = sys.version_info
        is_valid = version.major == 3 and version.minor >= 11
        self.check(
            "Python 3.11+",
            is_valid,
            required=True,
            details=f"Found Python {version.major}.{version.minor}.{version.micro}, need 3.11+"
        )
        return is_valid
    
    def check_virtual_env(self):
        """Check if running in virtual environment"""
        in_venv = hasattr(sys, 'real_prefix') or (
            hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
        )
        self.check(
            "Virtual environment active",
            in_venv,
            required=True,
            details="Run: python3.11 -m venv venv && source venv/bin/activate"
        )
        return in_venv

    @staticmethod
    def _load_dotenv(path: Path) -> dict[str, str]:
        """Parse simple KEY=VALUE lines (no multiline values)."""
        if not path.exists():
            return {}
        out: dict[str, str] = {}
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            # Inline comment (matches .env.example style: KEY=value  # note)
            if " #" in val:
                val = val.split(" #", 1)[0].rstrip()
            out[key] = val
        return out

    def _env_value_placeholder(self, key: str, value: str) -> bool:
        """True if value is empty or still an .env.example placeholder."""
        if not value.strip():
            return True
        lowered = value.lower()
        for needle in self._PLACEHOLDER_SUBSTRINGS.get(key, ()):
            if needle.lower() in lowered:
                return True
        if "YOUR_" in value:
            return True
        return False

    def check_env_file(self):
        """Verify .env file exists and has required keys"""
        env_path = Path('.env')
        exists = env_path.exists()
        
        if not exists:
            self.check(
                ".env file exists",
                False,
                required=True,
                details="Run: cp .env.example .env"
            )
            return False
        
        self._dotenv = self._load_dotenv(env_path)

        # Must match src/utils/config.py + Phase 1 ingestion prerequisites
        required_keys = [
            'SUPABASE_URL',
            'SUPABASE_SERVICE_KEY',
            'GOOGLE_DRIVE_ROOT_FOLDER_ID',
            'QDRANT_URL',
            'EMBEDDING_PROVIDER',
            'GENERATOR_PROVIDER',
        ]
        
        missing_keys = []
        for key in required_keys:
            val = self._dotenv.get(key, "")
            if key not in self._dotenv or self._env_value_placeholder(key, val):
                missing_keys.append(key)
        
        all_set = len(missing_keys) == 0
        self.check(
            ".env configured with all required keys",
            all_set,
            required=True,
            details=f"Missing or placeholder: {', '.join(missing_keys)}" if not all_set else ""
        )
        
        return all_set
    
    def check_service_account(self):
        """Verify Google service account JSON exists"""
        service_account_path = Path('secrets/service_account.json')
        exists = service_account_path.exists()
        
        if exists:
            # Validate it's valid JSON
            try:
                with open(service_account_path) as f:
                    data = json.load(f)
                    has_required = all(k in data for k in ['type', 'project_id', 'private_key', 'client_email'])
                    self.check(
                        "Google service account JSON valid",
                        has_required,
                        required=True,
                        details="JSON missing required fields: type, project_id, private_key, client_email"
                    )
                    return has_required
            except json.JSONDecodeError:
                self.check(
                    "Google service account JSON valid",
                    False,
                    required=True,
                    details="File exists but is not valid JSON"
                )
                return False
        else:
            self.check(
                "Google service account JSON exists",
                False,
                required=True,
                details="Place your service_account.json in secrets/ directory"
            )
            return False
    
    def check_docker(self):
        """Verify Docker is installed and running"""
        try:
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            docker_installed = result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            docker_installed = False
        
        self.check(
            "Docker installed",
            docker_installed,
            required=True,
            details="Install Docker Desktop: https://docs.docker.com/get-docker/"
        )
        
        if not docker_installed:
            return False
        
        # Check if Docker daemon is running
        try:
            result = subprocess.run(['docker', 'ps'], 
                                  capture_output=True, text=True, timeout=5)
            docker_running = result.returncode == 0
        except subprocess.TimeoutExpired:
            docker_running = False
        
        self.check(
            "Docker daemon running",
            docker_running,
            required=True,
            details="Start Docker Desktop"
        )
        
        return docker_running
    
    def check_qdrant_container(self):
        """Check if Qdrant container is running"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=rag_qdrant', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=5
            )
            is_running = 'rag_qdrant' in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            is_running = False
        
        self.check(
            "Qdrant container running",
            is_running,
            required=True,
            details="Run: docker compose -f docker/docker-compose.yml up -d qdrant"
        )
        
        return is_running
    
    def check_ollama_container(self, required: bool = False):
        """Check if Ollama container is running"""
        try:
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=rag_ollama', '--format', '{{.Names}}'],
                capture_output=True, text=True, timeout=5
            )
            is_running = 'rag_ollama' in result.stdout
        except (FileNotFoundError, subprocess.TimeoutExpired):
            is_running = False
        
        self.check(
            "Ollama container running",
            is_running,
            required=required,
            details="Run: docker compose -f docker/docker-compose.yml up -d ollama"
        )
        
        return is_running
    
    def check_ollama_model(self, required: bool = False):
        """Check if configured Ollama model is pulled (see GENERATOR_MODEL in .env)."""
        model = (self._dotenv.get("GENERATOR_MODEL") or "mistral").strip().lower()
        try:
            result = subprocess.run(
                ['docker', 'exec', 'rag_ollama', 'ollama', 'list'],
                capture_output=True, text=True, timeout=10
            )
            stdout_lower = result.stdout.lower()
            has_model = model in stdout_lower
        except (FileNotFoundError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
            has_model = False
        
        label = f"Ollama model pulled ({model})"
        self.check(
            label,
            has_model,
            required=required,
            details=f"Run: docker exec rag_ollama ollama pull {model}"
        )
        
        return has_model
    
    def check_corpus_ready(self):
        """Check if corpus is ready for ingestion"""
        if not self._dotenv and Path(".env").exists():
            self._dotenv = self._load_dotenv(Path(".env"))
        folder_id = self._dotenv.get("GOOGLE_DRIVE_ROOT_FOLDER_ID", "").strip()
        has_folder_id = bool(folder_id) and not self._env_value_placeholder(
            "GOOGLE_DRIVE_ROOT_FOLDER_ID", folder_id
        )

        self.check(
            "Google Drive root folder ID configured",
            has_folder_id,
            required=True,
            details="Set GOOGLE_DRIVE_ROOT_FOLDER_ID in .env to your shared Drive folder ID"
        )
        
        return has_folder_id
    
    def check_cloudflare_config(self):
        """Check if Cloudflare Access is configured (.env.example: CF_ACCESS_*)."""
        if not self._dotenv and Path(".env").exists():
            self._dotenv = self._load_dotenv(Path(".env"))

        team = self._dotenv.get("CF_ACCESS_TEAM_DOMAIN", "").strip()
        aud = self._dotenv.get("CF_ACCESS_AUD", "").strip()

        team_ok = bool(team) and team != self._PLACEHOLDER_CF_TEAM and "cloudflareaccess.com" in team
        aud_ok = bool(aud) and aud != self._PLACEHOLDER_CF_AUD
        cloudflare_ready = team_ok and aud_ok
        
        self.check(
            "Cloudflare Access configured",
            cloudflare_ready,
            required=False,  # Required for production, not for local dev
            details="Set CF_ACCESS_TEAM_DOMAIN and CF_ACCESS_AUD in .env (see .env.example)"
        )
        
        return cloudflare_ready

    def check_openai_for_generator(self):
        """When GENERATOR_PROVIDER=openai, require OPENAI_API_KEY."""
        if not self._dotenv and Path(".env").exists():
            self._dotenv = self._load_dotenv(Path(".env"))
        provider = (self._dotenv.get("GENERATOR_PROVIDER") or "").strip().lower()
        if provider != "openai":
            return True
        key = (self._dotenv.get("OPENAI_API_KEY") or "").strip()
        ok = bool(key) and len(key) >= 20 and not key.lower().startswith("sk-your")
        self.check(
            "OpenAI API key set (GENERATOR_PROVIDER=openai)",
            ok,
            required=True,
            details="Set OPENAI_API_KEY in .env for cloud generation",
        )
        return ok

    def check_project_structure(self):
        """Verify expected project structure (README layout: api/, src/, frontend/)."""
        required_dirs = [
            "api",
            "api/routes",
            "src",
            "src/utils",
            "src/ingestion",
            "frontend/src",
            "docker",
            "scripts",
            "tests",
        ]
        required_files = [
            "api/main.py",
            "src/utils/config.py",
        ]
        missing = [p for p in required_dirs if not Path(p).exists()]
        missing += [p for p in required_files if not Path(p).exists()]
        all_exist = len(missing) == 0

        self.check(
            "Project structure intact",
            all_exist,
            required=True,
            details=f"Missing paths: {', '.join(missing)}" if missing else "",
        )
        
        return all_exist
    
    # ==================== RUNNER ====================
    
    def run_all_checks(self):
        """Run all validation checks"""
        print(f"\n{Colors.BOLD}Enterprise RAG System - Phase 0 Validator{Colors.END}")
        print(f"{Colors.BOLD}Checking prerequisites before ingestion...{Colors.END}\n")

        self._dotenv = self._load_dotenv(Path(".env")) if Path(".env").exists() else {}
        
        # Section 1: Python Environment
        self.section("1. Python Environment")
        self.check_python_version()
        self.check_virtual_env()
        
        # Section 2: Project Structure
        self.section("2. Project Structure")
        self.check_project_structure()
        
        # Section 3: Configuration Files
        self.section("3. Configuration Files")
        self.check_env_file()
        self.check_openai_for_generator()
        self.check_service_account()
        
        # Section 4: Docker Services
        self.section("4. Docker Services")
        self.check_docker()
        self.check_qdrant_container()
        ollama_required = (self._dotenv.get("GENERATOR_PROVIDER") or "ollama").strip().lower() == "ollama"
        self.check_ollama_container(required=ollama_required)
        self.check_ollama_model(required=ollama_required)
        
        # Section 5: Data Sources
        self.section("5. Data Sources")
        self.check_corpus_ready()
        
        # Section 6: Deployment (Optional for now)
        self.section("6. Deployment Configuration (Optional for Local Dev)")
        self.check_cloudflare_config()
        
        # Final Report
        self.print_summary()
    
    def print_summary(self):
        """Print final summary and next steps"""
        print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
        print(f"{Colors.BOLD}VALIDATION SUMMARY{Colors.END}")
        print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")
        
        total_checks = len(self.results['passed']) + len(self.results['warnings']) + len(self.results['failed'])
        passed = len(self.results['passed'])
        
        print(f"{Colors.GREEN}✓ Passed:{Colors.END} {passed}/{total_checks}")
        print(f"{Colors.YELLOW}⚠ Warnings:{Colors.END} {len(self.results['warnings'])}")
        print(f"{Colors.RED}✗ Failed:{Colors.END} {len(self.results['failed'])}")
        
        if self.results['failed']:
            print(f"\n{Colors.RED}{Colors.BOLD}REQUIRED ACTIONS:{Colors.END}")
            for i, failure in enumerate(self.results['failed'], 1):
                print(f"\n{i}. {Colors.RED}{failure['name']}{Colors.END}")
                if failure['details']:
                    print(f"   {failure['details']}")
        
        if self.results['warnings']:
            print(f"\n{Colors.YELLOW}{Colors.BOLD}OPTIONAL (but recommended):{Colors.END}")
            for warning in self.results['warnings']:
                print(f"  • {warning['name']}")
                if warning['details']:
                    print(f"    {warning['details']}")
        
        # Phase readiness
        print(f"\n{Colors.BOLD}PHASE READINESS:{Colors.END}")
        
        critical_failed = [f for f in self.results['failed'] if f['required']]
        
        if len(critical_failed) == 0:
            print(f"{Colors.GREEN}✓ Phase 0 Complete{Colors.END} - Ready to proceed to Phase 1 (Ingestion)")
            print(f"\nNext step: python scripts/initial_ingest.py")
        else:
            print(f"{Colors.RED}✗ Phase 0 Incomplete{Colors.END} - Fix required items above")
            print(f"\nCannot proceed to ingestion until all required checks pass.")
        
        print()

if __name__ == '__main__':
    validator = Phase0Validator()
    validator.run_all_checks()
