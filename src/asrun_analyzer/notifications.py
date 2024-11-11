import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
from typing import List
import os
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)

class EmailNotifier:
    def __init__(self):
        # Get email configuration from environment variables
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL')
        self.to_emails = os.getenv('TO_EMAILS', '').split(',')
        self.alaska_tz = pytz.timezone('America/Anchorage')

    async def send_missing_files_alert(self, check_result: dict):
        """Send email alert about missing files"""
        try:
            subject = f"AsRun File Alert - {check_result['days_behind']} Day(s) Behind"
            
            # Create message body with HTML formatting
            html_content = f"""
            <html>
            <body>
                <h2>AsRun File Alert</h2>
                <p>Missing files have been detected in the AsRun system.</p>
                
                <h3>Status Details:</h3>
                <ul>
                    <li><strong>Current Time (AK):</strong> {check_result['current_time_alaska']}</li>
                    <li><strong>Days Behind:</strong> {check_result['days_behind']}</li>
                    <li><strong>Last Successful File:</strong> {check_result['latest_file']['date']}</li>
                </ul>
                
                <h3>Missing Dates:</h3>
                <ul>
                    {''.join([f'<li>{date}</li>' for date in check_result['missing_dates']])}
                </ul>
                
                <h3>Latest File Details:</h3>
                <ul>
                    <li><strong>Filename:</strong> {check_result['latest_file']['filename']}</li>
                    <li><strong>Time:</strong> {check_result['latest_file']['time']}</li>
                    <li><strong>Size:</strong> {check_result['latest_file']['size']} bytes</li>
                </ul>
                
                <p style="color: #666; margin-top: 20px;">
                This is an automated message from the AsRun Analyzer system.
                </p>
            </body>
            </html>
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            
            # Add HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True
            )
            
            logger.info(f"Alert email sent successfully to {', '.join(self.to_emails)}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
            return False

    async def send_system_status(self, status_info: dict):
        """Send regular system status update"""
        try:
            subject = "AsRun System Status Update"
            
            html_content = f"""
            <html>
            <body>
                <h2>AsRun System Status Report</h2>
                <p>Daily status report for the AsRun system.</p>
                
                <h3>File Processing Status:</h3>
                <ul>
                    <li><strong>Total Files Processed:</strong> {status_info.get('total_files', 0)}</li>
                    <li><strong>Files Last 24 Hours:</strong> {status_info.get('recent_files', 0)}</li>
                    <li><strong>System Status:</strong> {status_info.get('system_status', 'Unknown')}</li>
                </ul>
                
                <p style="color: #666; margin-top: 20px;">
                This is an automated status report from the AsRun Analyzer system.
                </p>
            </body>
            </html>
            """
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg.attach(MIMEText(html_content, 'html'))
            
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_server,
                port=self.smtp_port,
                username=self.smtp_username,
                password=self.smtp_password,
                use_tls=True
            )
            
            logger.info("Status email sent successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error sending status email: {str(e)}")
            return False