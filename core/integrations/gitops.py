"""
GitOps Integration for Policy Management
Automatically sync policies from Git repositories
"""
import os
import yaml
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib
import tempfile
import subprocess
import shutil
from pathlib import Path
import threading
import time

from core.engine.policy_engine import PolicyEngine


@dataclass
class GitConfig:
    """Git repository configuration"""
    name: str
    repo_url: str
    branch: str = "main"
    path: str = "policies/"  # Path within repo
    sync_interval: int = 300  # Seconds
    auth_token: Optional[str] = None
    last_sync: Optional[datetime] = None
    last_hash: Optional[str] = None
    is_active: bool = True
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "repo_url": self.repo_url,
            "branch": self.branch,
            "path": self.path,
            "sync_interval": self.sync_interval,
            "is_active": self.is_active,
            "last_sync": self.last_sync.isoformat() if self.last_sync else None,
            "last_hash": self.last_hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'GitConfig':
        """Create from dictionary"""
        return cls(
            name=data["name"],
            repo_url=data["repo_url"],
            branch=data.get("branch", "main"),
            path=data.get("path", "policies/"),
            sync_interval=data.get("sync_interval", 300),
            auth_token=data.get("auth_token"),
            last_sync=(
                datetime.fromisoformat(data["last_sync"])
                if data.get("last_sync") else None
            ),
            last_hash=data.get("last_hash"),
            is_active=data.get("is_active", True)
        )


class GitOpsManager:
    """
    GitOps manager for policy synchronization
    """
    
    def __init__(self, base_dir: str = "gitops"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(exist_ok=True)
        
        self.repos: Dict[str, GitConfig] = {}
        self.local_policy_dirs: Dict[str, Path] = {}
        self.watcher_thread: Optional[threading.Thread] = None
        self.stop_watcher = threading.Event()
        self.lock = threading.RLock()
        
        # Load existing configs
        self._load_configs()
        
        print(f"GitOpsManager initialized with {len(self.repos)} repos")
    
    def _load_configs(self):
        """Load repository configurations"""
        config_file = self.base_dir / "repositories.yaml"
        
        if not config_file.exists():
            # Create default config
            default_configs = {
                "repositories": [
                    {
                        "name": "default_policies",
                        "repo_url": "https://github.com/example/maais-policies.git",
                        "branch": "main",
                        "path": "policies/",
                        "sync_interval": 300
                    }
                ]
            }
            
            with open(config_file, 'w') as f:
                yaml.dump(default_configs, f)
            
            print("Created default GitOps configuration")
            return
        
        with open(config_file, 'r') as f:
            configs = yaml.safe_load(f)
        
        for repo_data in configs.get("repositories", []):
            try:
                repo = GitConfig.from_dict(repo_data)
                self.repos[repo.name] = repo
                
                # Set up local directory
                local_dir = self.base_dir / "repos" / repo.name
                local_dir.mkdir(parents=True, exist_ok=True)
                self.local_policy_dirs[repo.name] = local_dir
                
                print(f"Loaded repo config: {repo.name}")
                
            except Exception as e:
                print(f"Error loading repo config {repo_data.get('name', 'unknown')}: {e}")
    
    def _save_configs(self):
        """Save repository configurations"""
        config_file = self.base_dir / "repositories.yaml"
        
        configs = {
            "repositories": [repo.to_dict() for repo in self.repos.values()]
        }
        
        with open(config_file, 'w') as f:
            yaml.dump(configs, f, default_flow_style=False)
    
    def add_repository(self, config: GitConfig) -> bool:
        """Add a Git repository for policy sync"""
        with self.lock:
            if config.name in self.repos:
                print(f"Repository {config.name} already exists")
                return False
            
            self.repos[config.name] = config
            
            # Create local directory
            local_dir = self.base_dir / "repos" / config.name
            local_dir.mkdir(parents=True, exist_ok=True)
            self.local_policy_dirs[config.name] = local_dir
            
            self._save_configs()
            
            print(f"Added repository: {config.name}")
            return True
    
    def remove_repository(self, name: str) -> bool:
        """Remove a repository"""
        with self.lock:
            if name not in self.repos:
                return False
            
            # Remove local directory
            if name in self.local_policy_dirs:
                local_dir = self.local_policy_dirs[name]
                if local_dir.exists():
                    shutil.rmtree(local_dir)
                del self.local_policy_dirs[name]
            
            del self.repos[name]
            self._save_configs()
            
            print(f"Removed repository: {name}")
            return True
    
    def sync_repository(self, name: str, force: bool = False) -> Dict[str, Any]:
        """
        Sync a repository
        
        Returns:
            Sync result with success flag and details
        """
        if name not in self.repos:
            return {"success": False, "error": f"Repository not found: {name}"}
        
        repo = self.repos[name]
        
        if not repo.is_active:
            return {"success": False, "error": f"Repository is inactive: {name}"}
        
        local_dir = self.local_policy_dirs[name]
        
        try:
            # Calculate current hash to check for changes
            current_hash = self._get_repo_hash(local_dir)
            
            if not force and current_hash == repo.last_hash:
                return {
                    "success": True,
                    "changed": False,
                    "message": "No changes detected",
                    "hash": current_hash
                }
            
            # Clone or pull repository
            if not (local_dir / ".git").exists():
                # Clone repository
                clone_url = self._add_auth_to_url(repo.repo_url, repo.auth_token)
                result = subprocess.run(
                    ["git", "clone", "--branch", repo.branch, clone_url, str(local_dir)],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Clone failed: {result.stderr}",
                        "returncode": result.returncode
                    }
                
                print(f"Cloned repository: {name}")
            
            else:
                # Pull latest changes
                # Stash any local changes first
                subprocess.run(
                    ["git", "stash"],
                    cwd=local_dir,
                    capture_output=True,
                    timeout=30
                )
                
                # Pull latest
                result = subprocess.run(
                    ["git", "pull", "origin", repo.branch],
                    cwd=local_dir,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    return {
                        "success": False,
                        "error": f"Pull failed: {result.stderr}",
                        "returncode": result.returncode
                    }
                
                print(f"Pulled repository: {name}")
            
            # Get new hash
            new_hash = self._get_repo_hash(local_dir)
            
            # Update repo config
            repo.last_sync = datetime.utcnow()
            repo.last_hash = new_hash
            
            # Get list of policy files
            policy_files = self._find_policy_files(local_dir, repo.path)
            
            # Validate policies
            validation_results = []
            for policy_file in policy_files:
                is_valid, error = self._validate_policy_file(policy_file)
                validation_results.append({
                    "file": str(policy_file.relative_to(local_dir)),
                    "valid": is_valid,
                    "error": error
                })
            
            self._save_configs()
            
            return {
                "success": True,
                "changed": True,
                "hash": new_hash,
                "previous_hash": current_hash,
                "policy_files": [str(f.relative_to(local_dir)) for f in policy_files],
                "validation": validation_results,
                "timestamp": repo.last_sync.isoformat()
            }
        
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Sync timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _add_auth_to_url(self, url: str, token: Optional[str]) -> str:
        """Add authentication token to Git URL"""
        if not token:
            return url
        
        if url.startswith("https://"):
            # Insert token after https://
            parts = url.split("//")
            if len(parts) == 2:
                return f"{parts[0]}//{token}@{parts[1]}"
        
        return url
    
    def _get_repo_hash(self, repo_dir: Path) -> str:
        """Get hash of repository state"""
        try:
            # Get latest commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_dir,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return result.stdout.strip()
            
            # Fallback to directory hash
            return self._hash_directory(repo_dir)
        
        except Exception:
            return self._hash_directory(repo_dir)
    
    def _hash_directory(self, directory: Path) -> str:
        """Create hash of directory contents"""
        if not directory.exists():
            return "0" * 40
        
        hasher = hashlib.sha256()
        
        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                # Add file path
                hasher.update(str(file_path.relative_to(directory)).encode())
                
                # Add file content hash
                try:
                    with open(file_path, 'rb') as f:
                        content_hash = hashlib.sha256(f.read()).hexdigest()
                        hasher.update(content_hash.encode())
                except Exception:
                    pass
        
        return hasher.hexdigest()
    
    def _find_policy_files(self, repo_dir: Path, policy_path: str) -> List[Path]:
        """Find policy files in repository"""
        search_dir = repo_dir / policy_path
        
        if not search_dir.exists():
            return []
        
        policy_files = []
        
        # Look for YAML files
        for ext in ["yaml", "yml"]:
            policy_files.extend(search_dir.rglob(f"*.{ext}"))
        
        # Also look for JSON files
        policy_files.extend(search_dir.rglob("*.json"))
        
        return sorted(policy_files)
    
    def _validate_policy_file(self, policy_file: Path) -> Tuple[bool, Optional[str]]:
        """Validate policy file syntax"""
        try:
            with open(policy_file, 'r') as f:
                if policy_file.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                elif policy_file.suffix == '.json':
                    data = json.load(f)
                else:
                    return False, f"Unsupported file format: {policy_file.suffix}"
            
            # Basic validation - check for required fields
            if not isinstance(data, dict):
                return False, "Policy file must be a dictionary"
            
            if "policies" not in data:
                return False, "Missing 'policies' key"
            
            if not isinstance(data["policies"], list):
                return False, "'policies' must be a list"
            
            # Validate each policy
            for i, policy in enumerate(data["policies"]):
                if not isinstance(policy, dict):
                    return False, f"Policy {i} must be a dictionary"
                
                required_fields = ["id", "applies_to", "condition", "decision", "reason"]
                for field in required_fields:
                    if field not in policy:
                        return False, f"Policy {i} missing required field: {field}"
            
            return True, None
        
        except yaml.YAMLError as e:
            return False, f"YAML parsing error: {e}"
        except json.JSONDecodeError as e:
            return False, f"JSON parsing error: {e}"
        except Exception as e:
            return False, f"Validation error: {e}"
    
    def get_policy_files(self, repo_name: str) -> List[Dict]:
        """Get list of policy files from repository"""
        if repo_name not in self.local_policy_dirs:
            return []
        
        local_dir = self.local_policy_dirs[repo_name]
        policy_files = self._find_policy_files(local_dir, self.repos[repo_name].path)
        
        files_info = []
        for file_path in policy_files:
            try:
                with open(file_path, 'r') as f:
                    content = f.read()
                
                is_valid, error = self._validate_policy_file(file_path)
                
                files_info.append({
                    "path": str(file_path.relative_to(local_dir)),
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat(),
                    "valid": is_valid,
                    "error": error,
                    "content_preview": content[:500]  # First 500 chars
                })
            
            except Exception as e:
                files_info.append({
                    "path": str(file_path.relative_to(local_dir)),
                    "error": str(e),
                    "valid": False
                })
        
        return files_info
    
    def create_policy_engine(self, repo_name: str, policy_file: str = None) -> Optional[PolicyEngine]:
        """Create policy engine from repository policies"""
        if repo_name not in self.local_policy_dirs:
            return None
        
        local_dir = self.local_policy_dirs[repo_name]
        repo = self.repos[repo_name]
        
        if policy_file:
            # Use specific policy file
            policy_path = local_dir / repo.path / policy_file
            if not policy_path.exists():
                print(f"Policy file not found: {policy_path}")
                return None
            
            return PolicyEngine(str(policy_path))
        
        else:
            # Merge all policy files in repository
            policy_files = self._find_policy_files(local_dir, repo.path)
            
            if not policy_files:
                print(f"No policy files found in {repo_name}")
                return None
            
            # Create merged policy file
            merged_content = []
            for policy_file in policy_files:
                try:
                    with open(policy_file, 'r') as f:
                        merged_content.append(f.read())
                        merged_content.append("\n---\n")
                except Exception as e:
                    print(f"Error reading policy file {policy_file}: {e}")
            
            # Write merged file
            merged_dir = self.base_dir / "merged"
            merged_dir.mkdir(exist_ok=True)
            
            merged_file = merged_dir / f"{repo_name}_merged.yaml"
            with open(merged_file, 'w') as f:
                f.writelines(merged_content)
            
            return PolicyEngine(str(merged_file))
    
    def start_watcher(self, interval: int = 60):
        """Start background watcher for automatic sync"""
        if self.watcher_thread and self.watcher_thread.is_alive():
            print("Watcher already running")
            return
        
        self.stop_watcher.clear()
        
        def watch_loop():
            while not self.stop_watcher.is_set():
                try:
                    # Sync all active repositories
                    for repo_name, repo in list(self.repos.items()):
                        if not repo.is_active:
                            continue
                        
                        # Check if it's time to sync
                        if repo.last_sync:
                            time_since_sync = datetime.utcnow() - repo.last_sync
                            if time_since_sync.total_seconds() < repo.sync_interval:
                                continue
                        
                        print(f"Auto-syncing repository: {repo_name}")
                        result = self.sync_repository(repo_name)
                        
                        if result.get("success") and result.get("changed"):
                            print(f"Repository {repo_name} updated with {len(result.get('policy_files', []))} policy files")
                
                except Exception as e:
                    print(f"Error in watcher loop: {e}")
                
                # Wait for next check
                self.stop_watcher.wait(interval)
        
        self.watcher_thread = threading.Thread(target=watch_loop, daemon=True)
        self.watcher_thread.start()
        
        print(f"Started GitOps watcher with {interval}s interval")
    
    def stop_watcher(self):
        """Stop background watcher"""
        self.stop_watcher.set()
        if self.watcher_thread:
            self.watcher_thread.join(timeout=5)
            self.watcher_thread = None
        
        print("Stopped GitOps watcher")
    
    def get_status(self) -> Dict[str, Any]:
        """Get GitOps status"""
        status = {
            "total_repositories": len(self.repos),
            "active_repositories": sum(1 for r in self.repos.values() if r.is_active),
            "watcher_running": self.watcher_thread is not None and self.watcher_thread.is_alive(),
            "repositories": {}
        }
        
        for repo_name, repo in self.repos.items():
            status["repositories"][repo_name] = {
                "url": repo.repo_url,
                "branch": repo.branch,
                "path": repo.path,
                "is_active": repo.is_active,
                "last_sync": repo.last_sync.isoformat() if repo.last_sync else None,
                "sync_interval": repo.sync_interval,
                "policy_files_count": len(self.get_policy_files(repo_name))
            }
        
        return status