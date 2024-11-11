from ftplib import FTP
import os
from pathlib import Path
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from .config import Config

logger = logging.getLogger(__name__)

class AsRunTransfer:
    def __init__(self, config: Config):
        self.config = config
        self.ftp = None
        
    def connect(self):
        """Establish FTP connection"""
        try:
            self.ftp = FTP()
            self.ftp.connect(
                host=self.config.ssh_host,  # we'll keep using ssh_host for now
                port=21  # default FTP port
            )
            self.ftp.login(
                user=self.config.ssh_username,
                passwd=self.config.ssh_password
            )
            logger.info(f"Successfully connected to {self.config.ssh_host}")
            
        except Exception as e:
            logger.error(f"Error connecting to FTP server: {str(e)}")
            raise
            
    def disconnect(self):
        """Close FTP connection"""
        try:
            if self.ftp:
                self.ftp.quit()
            logger.info("Disconnected from FTP server")
        except Exception as e:
            logger.error(f"Error disconnecting from FTP server: {str(e)}")
            
    def list_files(self, hours_ago: int = 1) -> List[str]:
        """List AsRun files from the last N hours"""
        try:
            self.ftp.cwd(self.config.remote_path)
            
            # Get list of files
            files = []
            self.ftp.retrlines('LIST', lambda x: files.append(x))
            
            # Parse file listings and filter
            matching_files = []
            cutoff_time = datetime.now() - timedelta(hours=hours_ago)
            
            for file_info in files:
                # Parse FTP LIST output (typical format: "drwxr-xr-x 2 owner group size month day time filename")
                parts = file_info.split()
                if len(parts) < 9:
                    continue
                    
                filename = parts[-1]
                if not filename.startswith('BXF') or not filename.endswith('.xml'):
                    continue
                
                # Get file time from FTP listing
                try:
                    # Handle different time formats in FTP listings
                    time_str = ' '.join(parts[-4:-1])
                    file_time = datetime.strptime(time_str, '%b %d %H:%M')
                    # Add year (assume current year, adjust if needed)
                    file_time = file_time.replace(year=datetime.now().year)
                    
                    if file_time >= cutoff_time:
                        matching_files.append(filename)
                except Exception as e:
                    logger.warning(f"Could not parse time for file {filename}: {str(e)}")
                    continue
            
            logger.info(f"Found {len(matching_files)} files from the last {hours_ago} hours")
            return matching_files
            
        except Exception as e:
            logger.error(f"Error listing files: {str(e)}")
            raise
            
    def download_file(self, remote_filename: str, local_path: Optional[str] = None) -> str:
        """Download a single file from the remote server"""
        try:
            if local_path is None:
                local_path = str(self.config.local_storage)
                
            # Ensure local directory exists
            Path(local_path).mkdir(parents=True, exist_ok=True)
            
            local_full_path = os.path.join(local_path, remote_filename)
            
            # Download the file
            with open(local_full_path, 'wb') as local_file:
                self.ftp.retrbinary(f'RETR {remote_filename}', local_file.write)
            
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