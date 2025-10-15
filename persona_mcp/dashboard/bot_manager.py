"""
Bot Process Manager for PersonaAPI server.

Manages Matrix bot processes independently from the MCP server,
providing lifecycle management, logging, and monitoring.
"""

import subprocess
import sys
import asyncio
import os
import signal
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..logging import get_logger
from ..core import ConfigManager


@dataclass
class BotProcess:
    """Information about a running bot process"""
    persona_id: str
    persona_name: str
    process: subprocess.Popen
    log_file: Path
    start_time: datetime
    status: str = "running"
    restart_count: int = 0


class BotProcessManager:
    """Manages Matrix bot processes independently of MCP"""

    def __init__(self):
        self.config = ConfigManager()
        self.logger = get_logger(__name__)
        
        # Get bot configuration
        bot_config = self.config.get_bot_config()
        self.log_directory = Path(bot_config["log_directory"])
        self.max_log_file_size = bot_config["max_log_file_size"]
        self.startup_timeout = bot_config["startup_timeout"]
        self.shutdown_timeout = bot_config["shutdown_timeout"]
        self.restart_delay = bot_config["restart_delay"]
        self.max_restart_attempts = bot_config["max_restart_attempts"]
        
        # Ensure log directory exists
        self.log_directory.mkdir(parents=True, exist_ok=True)
        
        # Active bot processes
        self.running_bots: Dict[str, BotProcess] = {}
        
        # Background monitoring task
        self._monitor_task = None

    async def initialize(self):
        """Initialize the bot process manager"""
        self.logger.info("Initializing BotProcessManager")
        
        # Start background monitoring
        self._monitor_task = asyncio.create_task(self._monitor_processes())
        
        self.logger.info("BotProcessManager initialized")

    async def shutdown(self):
        """Shutdown all bots and cleanup"""
        self.logger.info("Shutting down BotProcessManager")
        
        # Cancel monitoring task
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Stop all running bots
        await self.stop_all_bots()
        
        self.logger.info("BotProcessManager shutdown complete")

    async def start_bot(self, persona_id: str, persona_name: str, 
                       additional_args: Optional[List[str]] = None) -> BotProcess:
        """Start a Matrix bot for a persona"""
        if persona_id in self.running_bots:
            raise ValueError(f"Bot already running for persona: {persona_name}")

        # Create unique log file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_file = self.log_directory / f"{persona_name.lower()}_{timestamp}.log"

        # Prepare bot command
        bot_script = "matrix/bots/universal_mcp_bot.py"
        command = [
            sys.executable, bot_script,
            "--persona-id", persona_id,
            "--persona-name", persona_name,
            "--log-file", str(log_file)
        ]
        
        # Add additional arguments if provided
        if additional_args:
            command.extend(additional_args)

        try:
            # Start the bot process
            with open(log_file, 'w') as log_fp:
                process = subprocess.Popen(
                    command,
                    stdout=log_fp,
                    stderr=subprocess.STDOUT,
                    cwd=os.getcwd(),
                    env=os.environ.copy()
                )

            # Create bot process record
            bot_process = BotProcess(
                persona_id=persona_id,
                persona_name=persona_name,
                process=process,
                log_file=log_file,
                start_time=datetime.now(timezone.utc),
                status="starting"
            )

            self.running_bots[persona_id] = bot_process
            
            # Wait for startup (with timeout)
            await self._wait_for_startup(bot_process)
            
            self.logger.info(f"Started bot for persona {persona_name} (PID: {process.pid})")
            return bot_process

        except Exception as e:
            self.logger.error(f"Failed to start bot for persona {persona_name}: {e}")
            # Cleanup on failure
            if persona_id in self.running_bots:
                del self.running_bots[persona_id]
            raise

    async def stop_bot(self, persona_id: str) -> bool:
        """Stop a Matrix bot"""
        if persona_id not in self.running_bots:
            self.logger.warning(f"No bot running for persona ID: {persona_id}")
            return False

        bot_process = self.running_bots[persona_id]
        
        try:
            # Graceful shutdown
            bot_process.process.terminate()
            bot_process.status = "stopping"
            
            # Wait for graceful shutdown
            try:
                await asyncio.wait_for(
                    asyncio.create_task(self._wait_for_exit(bot_process.process)),
                    timeout=self.shutdown_timeout
                )
                self.logger.info(f"Bot for persona {bot_process.persona_name} stopped gracefully")
                
            except asyncio.TimeoutError:
                # Force kill if graceful shutdown failed
                bot_process.process.kill()
                await asyncio.create_task(self._wait_for_exit(bot_process.process))
                self.logger.warning(f"Force killed bot for persona {bot_process.persona_name}")

            # Remove from active bots
            del self.running_bots[persona_id]
            return True

        except Exception as e:
            self.logger.error(f"Error stopping bot for persona {bot_process.persona_name}: {e}")
            return False

    async def restart_bot(self, persona_id: str) -> bool:
        """Restart a Matrix bot"""
        if persona_id not in self.running_bots:
            self.logger.error(f"Cannot restart - no bot running for persona ID: {persona_id}")
            return False

        bot_process = self.running_bots[persona_id]
        persona_name = bot_process.persona_name
        
        # Check restart limit
        if bot_process.restart_count >= self.max_restart_attempts:
            self.logger.error(f"Max restart attempts reached for persona {persona_name}")
            await self.stop_bot(persona_id)
            return False

        self.logger.info(f"Restarting bot for persona {persona_name}")
        
        # Stop current process
        await self.stop_bot(persona_id)
        
        # Wait before restart
        await asyncio.sleep(self.restart_delay)
        
        try:
            # Start new process
            new_bot = await self.start_bot(persona_id, persona_name)
            new_bot.restart_count = bot_process.restart_count + 1
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restart bot for persona {persona_name}: {e}")
            return False

    async def stop_all_bots(self):
        """Stop all running bots"""
        if not self.running_bots:
            return

        self.logger.info("Stopping all running bots")
        
        # Stop all bots concurrently
        stop_tasks = [
            self.stop_bot(persona_id) 
            for persona_id in list(self.running_bots.keys())
        ]
        
        await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        self.logger.info("All bots stopped")

    def get_bot_status(self) -> List[Dict[str, Any]]:
        """Get status of all bots"""
        status_list = []
        
        for persona_id, bot_process in self.running_bots.items():
            # Check if process is still running
            poll_result = bot_process.process.poll()
            if poll_result is None:
                status = "running"
            else:
                status = f"exited ({poll_result})"
                bot_process.status = status

            status_list.append({
                "persona_id": persona_id,
                "persona_name": bot_process.persona_name,
                "status": status,
                "pid": bot_process.process.pid,
                "start_time": bot_process.start_time.isoformat(),
                "restart_count": bot_process.restart_count,
                "log_file": str(bot_process.log_file)
            })
        
        return status_list

    async def get_bot_logs(self, persona_id: str, lines: int = 100) -> List[str]:
        """Get recent log lines for a bot"""
        if persona_id not in self.running_bots:
            raise ValueError(f"No bot running for persona ID: {persona_id}")

        bot_process = self.running_bots[persona_id]
        
        try:
            with open(bot_process.log_file, 'r') as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) > lines else all_lines
                
        except Exception as e:
            self.logger.error(f"Error reading logs for persona {bot_process.persona_name}: {e}")
            return [f"Error reading logs: {e}"]

    async def _wait_for_startup(self, bot_process: BotProcess):
        """Wait for bot startup with timeout"""
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < self.startup_timeout:
            # Check if process died
            if bot_process.process.poll() is not None:
                raise Exception(f"Bot process exited during startup")
            
            # Check log file for success indicators
            try:
                if bot_process.log_file.exists():
                    with open(bot_process.log_file, 'r') as f:
                        content = f.read()
                        if "Connected to MCP server" in content or "Bot started successfully" in content:
                            bot_process.status = "running"
                            return
                        if "ERROR" in content or "FATAL" in content:
                            raise Exception("Bot startup failed - check logs")
            except Exception:
                pass  # Continue waiting
            
            await asyncio.sleep(1)
        
        # Timeout reached
        bot_process.status = "startup_timeout"
        raise Exception(f"Bot startup timeout ({self.startup_timeout}s)")

    async def _wait_for_exit(self, process: subprocess.Popen):
        """Wait for process to exit"""
        while process.poll() is None:
            await asyncio.sleep(0.1)

    async def _monitor_processes(self):
        """Background task to monitor bot processes"""
        while True:
            try:
                # Check each running bot
                for persona_id, bot_process in list(self.running_bots.items()):
                    poll_result = bot_process.process.poll()
                    
                    if poll_result is not None:
                        # Process has exited
                        self.logger.warning(
                            f"Bot for persona {bot_process.persona_name} exited "
                            f"with code {poll_result}"
                        )
                        
                        # Remove from running bots
                        del self.running_bots[persona_id]
                        
                        # Could implement auto-restart logic here if desired
                
                # Monitor every 10 seconds
                await asyncio.sleep(10)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in bot process monitoring: {e}")
                await asyncio.sleep(10)