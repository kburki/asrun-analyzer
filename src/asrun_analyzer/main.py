from fastapi import FastAPI, HTTPException, File, UploadFile, Query, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging
from pathlib import Path
from typing import List, Optional
from .database import get_db
from .models import AsRunFile, Event
from .parser import parse_xml_file
from .config import Config
from .scheduler import AsRunScheduler
from .transfer import AsRunTransfer  


# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/asrun.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="AsRun Analyzer")

# Initialize config and scheduler
config = Config()
scheduler = AsRunScheduler()

@app.get("/")
async def root():
    return {"message": "AsRun Analyzer API"}

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/parse/test")
async def test_parse_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Test XML parsing and store results in database"""
    try:
        content = await file.read()
        logger.info(f"Received file: {file.filename}, size: {len(content)} bytes")
        
        # Parse the XML
        events_data = parse_xml_file(content.decode())
        logger.info(f"Successfully parsed {len(events_data)} events")
        
        if not events_data:
            raise ValueError("No events found in XML file")
            
        # Check if file was already processed
        existing_file = db.query(AsRunFile).filter(
            AsRunFile.filename == file.filename
        ).first()
        
        if existing_file:
            return {
                "status": "skipped",
                "message": f"File {file.filename} was already processed",
                "file_info": {
                    "filename": file.filename,
                    "id": existing_file.id,
                    "date_processed": existing_file.date_processed,
                    "events_count": len(existing_file.events)
                }
            }
        
        # Create AsRunFile record
        asrun_file = AsRunFile(
            filename=file.filename,
            date_processed=datetime.utcnow(),
            broadcast_date=events_data[0]['start_time'].date() if events_data else datetime.utcnow()
        )
        db.add(asrun_file)
        db.flush()
        
        # Create Event records
        new_events = 0
        skipped_events = 0
        for event_data in events_data:
            # Check for existing event
            existing_event = db.query(Event).filter(
                Event.event_id == event_data['event_id'],
                Event.start_time == event_data['start_time']
            ).first()
            
            if existing_event:
                skipped_events += 1
                continue
                
            try:
                event = Event(
                    asrun_file_id=asrun_file.id,
                    event_id=event_data['event_id'],
                    event_title=event_data.get('event_title'),
                    event_category=event_data.get('event_category'),
                    description=event_data.get('description'),
                    start_time=event_data.get('start_time'),
                    duration=event_data.get('duration'),
                    spot_type=event_data.get('spot_type'),
                    spot_type_category=event_data.get('spot_type_category'),
                    start_mode=event_data.get('start_mode'),
                    start_mode_category=event_data.get('start_mode_category'),
                    end_mode=event_data.get('end_mode'),
                    end_mode_category=event_data.get('end_mode_category'),
                    status=event_data.get('status'),
                    event_type=event_data.get('event_type'),
                    house_number=event_data.get('house_number'),
                    source=event_data.get('source'),
                    segment_number=event_data.get('segment_number'),
                    segment_name=event_data.get('segment_name'),
                    program_name=event_data.get('program_name')
                )
                db.add(event)
                new_events += 1
            except Exception as e:
                logger.error(f"Error creating event {event_data['event_id']}: {str(e)}")
                continue
        
        db.commit()
        logger.info(f"Successfully processed file. New events: {new_events}, Skipped: {skipped_events}")
        
        return {
            "status": "success",
            "events_count": new_events,
            "skipped_count": skipped_events,
            "file_info": {
                "filename": file.filename,
                "size": len(content),
                "id": asrun_file.id
            }
        }
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        logger.exception("Full traceback:")
        if 'db' in locals():
            db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )

@app.get("/scheduler/status")
async def get_scheduler_status():
    """Get the current status of the scheduler"""
    next_run = scheduler.get_next_run_time()
    return {
        "status": "running" if scheduler.is_running else "stopped",
        "next_run": next_run.isoformat() if next_run else None
    }

@app.post("/scheduler/start")
async def start_scheduler():
    """Start the scheduler"""
    try:
        scheduler.start()
        return {
            "status": "success",
            "message": "Scheduler started successfully",
            "next_run": scheduler.get_next_run_time().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/scheduler/stop")
async def stop_scheduler():
    """Stop the scheduler"""
    try:
        scheduler.stop()
        return {
            "status": "success",
            "message": "Scheduler stopped successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
async def startup_event():
    """Create necessary directories and start scheduler on startup"""
    try:
        Path("logs").mkdir(exist_ok=True)
        scheduler.start()
        logger.info("Application and scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop scheduler on shutdown"""
    try:
        scheduler.stop()
        logger.info("Application and scheduler stopped successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")
        
@app.get("/config/test")
async def test_configuration():
    """Test configuration without exposing sensitive data"""
    try:
        config = Config()
        return {
            "status": "success",
            "config_test": {
                "ssh_host_configured": bool(config.ssh_host),
                "ssh_user_configured": bool(config.ssh_username),
                "ssh_password_configured": bool(config.ssh_password),
                "remote_path_configured": bool(config.remote_path),
                "local_storage_configured": str(config.local_storage),
                "local_storage_exists": config.local_storage.exists(),
            }
        }
    except Exception as e:
        logger.error(f"Configuration test failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Configuration test failed: {str(e)}"
        )
        
@app.get("/ftp/list")
async def list_ftp_files():
    """List BXF PolarisPlayMyers ProTrack files"""
    try:
        config = Config()
        transfer = AsRunTransfer(config)
        
        try:
            transfer.connect()
            
            # Get raw directory listing
            raw_files = []
            transfer.ftp.cwd(config.remote_path)
            transfer.ftp.retrlines('LIST', lambda x: raw_files.append(x))
            
            myers_files = []
            
            for file_info in raw_files:
                parts = file_info.split()
                if len(parts) < 9:
                    continue
                
                filename = ' '.join(parts[8:])
                
                if (filename.startswith('BXF') and 
                    'PolarisPlayMyers' in filename and 
                    'ProTrack' in filename and 
                    filename.endswith('.xml')):
                    try:
                        # Parse the datetime from the filename (BXF20241109T055959...)
                        file_datetime_str = filename[3:18]  # Gets YYYYMMDDTHHMMSS
                        file_datetime = datetime.strptime(file_datetime_str, '%Y%m%dT%H%M%S')
                        
                        myers_files.append({
                            'timestamp': file_datetime,  # Using filename datetime instead of FTP timestamp
                            'filename': filename,
                            'ftp_info': file_info,
                            'size': parts[4]
                        })
                    except Exception as e:
                        logger.warning(f"Could not parse datetime from filename: {filename}, error: {str(e)}")
            
            # Sort by timestamp from filename, newest first
            myers_files.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return {
                "status": "success",
                "total_files": len(myers_files),
                "latest_files": [
                    {
                        "filename": f['filename'],
                        "datetime": f['timestamp'].strftime('%Y-%m-%d %H:%M:%S'),
                        "size": f['size']
                    } for f in myers_files[:3]  # Show latest 3 files
                ],
                "debug": {
                    "datetime_details": [
                        {
                            "filename": f['filename'],
                            "parsed_datetime": f['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                        } for f in myers_files[:5]
                    ]
                }
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": f"Error listing files: {str(e)}",
                "connection": "failed",
                "exception_details": str(e)
            }
            
        finally:
            transfer.disconnect()
            
    except Exception as e:
        logger.error(f"FTP list failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"FTP list failed: {str(e)}"
        )
        
@app.get("/ftp/check")
async def check_latest_file():
    """Check if expected BXF files exist"""
    from datetime import datetime, timezone, timedelta
    import pytz
    
    try:
        config = Config()
        transfer = AsRunTransfer(config)
        
        try:
            transfer.connect()
            
            # Get raw directory listing
            raw_files = []
            transfer.ftp.cwd(config.remote_path)
            transfer.ftp.retrlines('LIST', lambda x: raw_files.append(x))
            
            # Process files and their dates
            processed_files = []
            for file_info in raw_files:
                parts = file_info.split()
                if len(parts) < 9:
                    continue
                
                filename = ' '.join(parts[8:])
                
                # Look for main daily BXF files (usually generated at 6 AM)
                if (filename.startswith('BXF') and 
                    'PolarisPlayMyers' in filename and 
                    'ProTrack' in filename and 
                    'T0559' in filename and  # Looking for the 5:59 AM files
                    filename.endswith('.xml')):
                    try:
                        # Parse the datetime from the filename
                        file_datetime_str = filename[3:18]  # Gets YYYYMMDDTHHMMSS
                        file_datetime = datetime.strptime(file_datetime_str, '%Y%m%dT%H%M%S')
                        
                        processed_files.append({
                            'datetime': file_datetime,
                            'filename': filename,
                            'size': parts[4]
                        })
                    except Exception as e:
                        logger.warning(f"Could not parse datetime from filename: {filename}, error: {str(e)}")
                        continue
            
            if not processed_files:
                return {
                    "status": "error",
                    "message": "No valid BXF files found",
                    "details": {
                        "total_files_checked": len(raw_files),
                        "sample_files": [' '.join(f.split()[8:]) for f in raw_files[:5]]  # Show sample filenames
                    }
                }
            
            # Sort by datetime, newest first
            processed_files.sort(key=lambda x: x['datetime'], reverse=True)
            
            # Get current time in Alaska timezone
            alaska_tz = pytz.timezone('America/Anchorage')
            current_time = datetime.now(timezone.utc).astimezone(alaska_tz)
            
            # Get the latest file info
            latest_file = processed_files[0]
            latest_date = latest_file['datetime']
            
            # Calculate expected dates up to today
            expected_dates = []
            current_date = latest_date + timedelta(days=1)
            while current_date.date() <= current_time.date():
                expected_dates.append(current_date.date())
                current_date += timedelta(days=1)
            
            # Format response based on findings
            response = {
                "status": "success",
                "latest_file": {
                    "date": latest_date.strftime('%Y-%m-%d'),
                    "time": latest_date.strftime('%H:%M:%S'),
                    "filename": latest_file['filename'],
                    "size": latest_file['size']
                },
                "current_time_alaska": current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
                "missing_dates": [d.strftime('%Y-%m-%d') for d in expected_dates] if expected_dates else [],
                "is_current": len(expected_dates) == 0,
                "days_behind": len(expected_dates)
            }
            
            # Add warning message if we're behind
            if expected_dates:
                response["warning"] = (
                    f"Missing {len(expected_dates)} day(s) of files. "
                    f"Last successful file was from {latest_date.strftime('%Y-%m-%d')}"
                )
            else:
                response["message"] = "All expected files are present"
            
            return response
            
        except Exception as e:
            logger.error(f"Error checking files: {str(e)}")
            return {
                "status": "error",
                "error": f"Error checking files: {str(e)}",
                "connection": "failed"
            }
        
        finally:
            transfer.disconnect()
            
    except Exception as e:
        logger.error(f"FTP check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"FTP check failed: {str(e)}"
        )