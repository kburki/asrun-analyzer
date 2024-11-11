import paramiko
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import List, Optional

logger = logging.getLogger(__name__)

class AsRunTransfer:
    def __init__(self, config):
        self.config = config
        self.ssh = None
        self.sftp = None
        
    def connect(self):
        """Establish SFTP connection"""
        try:
            self.ssh = paramiko.SSHClient()
            self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Get connection details from config
            hostname = self.config.get('sftp.hostname')
            username = self.config.get('sftp.username')
            password = self.config.get('sftp.password')
            port = self.config.get('sftp.port', 22)
            
            self.ssh.connect(
                hostname=hostname,
                username=username,
                password=password,
                port=port
            )
            
            self.sftp = self.ssh.open_sftp()
            logger.info(f"Successfully connected to {hostname}")
            
        except Exception as e:
            logger.error(f"Error connecting to SFTP server: {str(e)}")
            raise
            
    def disconnect(self):
        """Close SFTP connection"""
        try:
            if self.sftp:
                self.sftp.close()
            if self.ssh:
                self.ssh.close()
            logger.info("Disconnected from SFTP server")
        except Exception as e:
            logger.error(f"Error disconnecting from SFTP server: {str(e)}")
            
    def list_files(self, hours_ago: int = 1) -> List[str]:
        """List AsRun files from the last N hours"""
        try:
            remote_path = self.config.get('sftp.remote_path')
            file_pattern = self.config.get('sftp.file_pattern', 'BXF*.xml')
            
            # Get list of files
            files = self.sftp.listdir(remote_path)
            
            # Filter for matching files
            matching_files = []
            cutoff_time = datetime.now() - timedelta(hours=hours_ago)
            
            for filename in files:
                if not filename.startswith('BXF') or not filename.endswith('.xml'):
                    continue
                    
                file_stat = self.sftp.stat(os.path.join(remote_path, filename))
                file_time = datetime.fromtimestamp(file_stat.st_mtime)
                
                if file_time >= cutoff_time:
                    matching_files.append(filename)
            
            logger.info(f"Found {len(matching_files)} files from the last {hours_ago} hours")
            return matching_files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise
            
    def download_file(self, remote_filename: str, local_path: Optional[str] = None) -> str:
        """Download a single file from the remote server"""
        try:
            remote_path = self.config.get('sftp.remote_path')
            remote_full_path = os.path.join(remote_path, remote_filename)
            
            if local_path is None:
                local_path = self.config.get('local.download_path', 'downloads')
                
            # Ensure local directory exists
            Path(local_path).mkdir(parents=True, exist_ok=True)
            
            local_full_path = os.path.join(local_path, remote_filename)
            
            # Download the file
            self.sftp.get(remote_full_path, local_full_path)
            logger.info(f"Successfully downloaded {remote_filename}")
            
            return local_full_path
            
        except Exception as e:
            logger.error(f"Error downloading file {remote_filename}: {str(e)}")
            raise
            
    def process_new_files(self, hours_ago: int = 1) -> List[str]:
        """Download and return paths of new files from the last N hours"""
        try:
            self.connect()
            
            # Get list of new files
            new_files = self.list_files(hours_ago)
            downloaded_files = []
            
            # Download each file
            for filename in new_files:
                try:
                    local_path = self.download_file(filename)
                    downloaded_files.append(local_path)
                except Exception as e:
                    logger.error(f"Error processing file {filename}: {str(e)}")
                    continue
                    
            return downloaded_files
            
        finally:
            self.disconnect()