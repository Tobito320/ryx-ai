"""
Ryx AI - Permission Manager & Command Executor
Safely executes commands with 3-level permission system
"""

import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from enum import Enum
from core.paths import get_project_root, get_data_dir, get_config_dir, get_runtime_dir

class PermissionLevel(Enum):
    """Permission levels for command execution"""
    SAFE = "SAFE"
    MODIFY = "MODIFY"
    DESTROY = "DESTROY"
    BLOCKED = "BLOCKED"

class PermissionManager:
    """Manages command permissions and safety analysis"""

    def __init__(self) -> None:
        """Initialize permission manager with configuration"""
        self.config_path = get_project_root() / "configs" / "permissions.json"
        self.config = self.load_config()

    def load_config(self) -> Dict:
        """Load permission configuration from JSON file"""
        with open(self.config_path, 'r') as f:
            return json.load(f)
    
    def analyze_command(self, command: str) -> Tuple[PermissionLevel, str]:
        """
        Analyze command and return permission level + reason
        
        Returns: (PermissionLevel, reason)
        """
        cmd_lower = command.lower().strip()
        
        # Check global blocks first
        for blocked in self.config["global_blocks"]:
            if blocked in cmd_lower:
                return (PermissionLevel.BLOCKED, 
                       f"Blocked: matches dangerous pattern '{blocked}'")
        
        # Extract base command
        base_cmd = cmd_lower.split()[0] if cmd_lower.split() else ""
        
        # Check DESTROY level (highest risk)
        destroy_config = self.config["levels"]["DESTROY"]
        if base_cmd in destroy_config["allowed_commands"]:
            # Check blocked patterns
            for pattern in destroy_config.get("blocked_patterns", []):
                if re.search(pattern, cmd_lower):
                    return (PermissionLevel.BLOCKED,
                           f"Blocked: matches dangerous pattern")
            
            return (PermissionLevel.DESTROY, 
                   "Destructive operation - confirmation required")
        
        # Check MODIFY level
        modify_config = self.config["levels"]["MODIFY"]
        if base_cmd in modify_config["allowed_commands"]:
            # Check if modifying safe directories
            safe = any(safe_dir in command for safe_dir 
                      in modify_config["safe_directories"])
            
            blocked = any(blocked_dir in command for blocked_dir
                         in modify_config["blocked_directories"])
            
            if blocked:
                return (PermissionLevel.DESTROY,
                       "Modifying system directory - confirmation required")
            
            return (PermissionLevel.MODIFY,
                   "Modification operation - auto-approved in safe directories")
        
        # Check SAFE level
        safe_config = self.config["levels"]["SAFE"]
        if base_cmd in safe_config["allowed_commands"]:
            return (PermissionLevel.SAFE,
                   "Read-only operation - auto-approved")
        
        # Check patterns
        for pattern in safe_config.get("allowed_patterns", []):
            if re.match(pattern, cmd_lower):
                return (PermissionLevel.SAFE,
                       "Safe operation pattern - auto-approved")
        
        # Unknown command - treat as MODIFY
        return (PermissionLevel.MODIFY,
               "Unknown command - treating as modification")
    
    def requires_confirmation(self, level: PermissionLevel) -> bool:
        """Check if level requires user confirmation"""
        return level in [PermissionLevel.DESTROY, PermissionLevel.BLOCKED]


class CommandExecutor:
    """Executes commands safely with permission checking and logging"""

    def __init__(self, permission_manager: PermissionManager) -> None:
        """Initialize command executor with permission manager"""
        self.perm_manager = permission_manager
        self.history_file = get_project_root() / "data" / "history" / "commands.log"
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
    
    def parse_commands(self, ai_response: str) -> List[Dict]:
        """
        Extract executable commands from AI response
        
        Returns list of:
        {
            "command": str,
            "level": PermissionLevel,
            "reason": str,
            "auto_approve": bool
        }
        """
        commands = []
        
        # Extract code blocks
        in_code_block = False
        current_block = []
        block_lang = None
        
        for line in ai_response.split('\n'):
            if line.strip().startswith('```'):
                if not in_code_block:
                    # Start of block
                    in_code_block = True
                    # Extract language
                    parts = line.strip()[3:].strip()
                    block_lang = parts if parts else "bash"
                    current_block = []
                else:
                    # End of block
                    if block_lang == "bash" and current_block:
                        full_cmd = '\n'.join(current_block)
                        level, reason = self.perm_manager.analyze_command(full_cmd)
                        
                        commands.append({
                            "command": full_cmd,
                            "level": level,
                            "reason": reason,
                            "auto_approve": not self.perm_manager.requires_confirmation(level)
                        })
                    
                    in_code_block = False
                    current_block = []
                    block_lang = None
                continue
            
            if in_code_block:
                current_block.append(line)
        
        return commands
    
    def _is_interactive_program(self, command: str) -> bool:
        """Check if command is an interactive program (editor, TUI, etc.)"""
        # Extract base command
        cmd_lower = command.lower().strip()
        base_cmd = cmd_lower.split()[0] if cmd_lower.split() else ""

        # Common interactive programs
        interactive_programs = [
            'nvim', 'vim', 'vi', 'nano', 'emacs',
            'htop', 'top', 'less', 'more',
            'man', 'tmux', 'screen',
            'python', 'python3', 'ipython',
            'mysql', 'psql', 'redis-cli'
        ]

        return base_cmd in interactive_programs

    def execute(self, command: str, confirm: bool = False) -> Dict:
        """
        Execute a command safely

        Returns:
        {
            "success": bool,
            "stdout": str,
            "stderr": str,
            "exit_code": int
        }
        """
        level, reason = self.perm_manager.analyze_command(command)

        if level == PermissionLevel.BLOCKED:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Command blocked: {reason}",
                "exit_code": -1
            }

        if self.perm_manager.requires_confirmation(level) and not confirm:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Confirmation required - run with confirm=True",
                "exit_code": -2
            }

        # Execute command
        try:
            # Expand shell variables
            expanded_cmd = command.replace("~", str(Path.home()))

            # Check if this is an interactive program
            if self._is_interactive_program(command) and not command.endswith('&'):
                # Interactive program - use os.system for proper terminal handling
                import os
                exit_code = os.system(expanded_cmd)

                # Log to history
                self._log_command(command, exit_code == 0)

                return {
                    "success": exit_code == 0,
                    "stdout": "",
                    "stderr": "" if exit_code == 0 else f"Exit code: {exit_code}",
                    "exit_code": exit_code
                }
            else:
                # Non-interactive or background command - use subprocess with capture
                result = subprocess.run(
                    expanded_cmd,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                # Log to history
                self._log_command(command, result.returncode == 0)

                return {
                    "success": result.returncode == 0,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode
                }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "stdout": "",
                "stderr": "Command timed out after 30 seconds",
                "exit_code": -3
            }
        except Exception as e:
            return {
                "success": False,
                "stdout": "",
                "stderr": f"Execution error: {str(e)}",
                "exit_code": -4
            }
    
    def _log_command(self, command: str, success: bool) -> None:
        """Log command to history"""
        from datetime import datetime
        
        with open(self.history_file, 'a') as f:
            timestamp = datetime.now().isoformat()
            status = "SUCCESS" if success else "FAILED"
            f.write(f"[{timestamp}] {status}: {command}\n")


class InteractiveConfirm:
    """Handle interactive command confirmation"""
    
    @staticmethod
    def confirm(command: str, level: PermissionLevel, reason: str) -> bool:
        """
        Show confirmation prompt
        
        Returns: True if user approves
        """
        print()
        print("\033[1;31m⚠️  CONFIRMATION REQUIRED\033[0m")
        print()
        print(f"\033[1;33mLevel:\033[0m {level.value}")
        print(f"\033[1;33mReason:\033[0m {reason}")
        print()
        print("\033[1;36mCommand:\033[0m")
        print(f"  \033[1;37m{command}\033[0m")
        print()
        
        response = input("\033[1mAllow this command? [y/N]: \033[0m").strip().lower()
        
        return response in ['y', 'yes']