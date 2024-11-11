import paramiko
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

class TrafficControl:
    def __init__(self, config):
        self.config = config
        self.ssh = None

    async def connect(self):
        """Establish SSH connection to traffic server"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Get connection details from config
            self.ssh.connect(
                hostname=self.config.ssh_host,
                username=self.config.ssh_username,
                password=self.config.ssh_password
            )
            
            logger.info(f"Successfully connected to traffic server at {self.config.ssh_host}")
            
        except Exception as e:
            logger.error(f"Error connecting to traffic server: {str(e)}")
            raise

    async def disconnect(self):
        """Close SSH connection"""
        if self.ssh:
            self.ssh.close()
            self.ssh = None

    async def restart_traffic_module(self) -> bool:
        """Restart the traffic module"""
        try:
            await self.connect()
            
            # Commands to restart traffic module
            commands = [
                "sudo service traffic-module stop",
                "sleep 5",
                "sudo service traffic-module start"
            ]
            
            for cmd in commands:
                stdin, stdout, stderr = self.ssh.exec_command(cmd)
                exit_status = stdout.channel.recv_exit_status()
                
                if exit_status != 0:
                    error_output = stderr.read().decode().strip()
                    logger.error(f"Command '{cmd}' failed with status {exit_status}: {error_output}")
                    return False
                
                logger.info(f"Successfully executed: {cmd}")
            
            logger.info("Traffic module restart completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error restarting traffic module: {str(e)}")
            return False
            
        finally:
            await self.disconnect()

    async def check_service_status(self) -> Optional[str]:
        """Check the current status of the traffic module"""
        try:
            await self.connect()
            
            stdin, stdout, stderr = self.ssh.exec_command("sudo service traffic-module status")
            status_output = stdout.read().decode().strip()
            
            return status_output
            
        except Exception as e:
            logger.error(f"Error checking traffic module status: {str(e)}")
            return None
            
        finally:
            await self.disconnect()