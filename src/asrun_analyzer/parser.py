# parser.py
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import List, Dict, Optional, Set, Union
import logging
from enum import Enum, auto

logger = logging.getLogger(__name__)

class SpotType(Enum):
    """Known spot types in the AsRun system.
    This is used to track and categorize different types of content:
    - Commercial: Commercial content
    - Program: Program content
    - StationID: Station identification
    - PSA: Public Service Announcement
    - ID: Identity spots and IDs
    - FL: Feature Length - or Fillers
    - NS: News Segment
    - GS: Generic Segment - or Gavel Spots
    - SF: Special Feature
    - PG: Program Guide
    - RS: Re-run Segment
    - FI: Filler
    - PR: Promotional
    - PS: Program Segment
    - PA: Public Affairs
    - FR: Fundraising
    - DA: Daily Announcement
    - TN: Technical Notice
    - AJ: Adjustments - or Adjacency
    """
    COMMERCIAL = auto()
    PROGRAM = auto()
    STATION_ID = auto()
    PSA = auto()
    ID = auto()
    FL = auto()
    NS = auto()
    GS = auto()
    SF = auto()
    PG = auto()
    RS = auto()
    FI = auto()
    PR = auto()
    PS = auto()
    PA = auto()
    FR = auto()
    DA = auto()
    TN = auto()
    AJ = auto()
    UNKNOWN = auto()  # For tracking new/unexpected types

class StartMode(Enum):
    """Start modes for events"""
    FIXED = auto()
    FOLLOW = auto()
    SEQUENTIAL = auto()
    MANUAL = auto()
    UNKNOWN = auto()

class EndMode(Enum):
    """End modes for events"""
    DURATION = auto()
    FIXED = auto()
    MANUAL = auto()
    FOLLOW = auto()
    UNKNOWN = auto()

def parse_smpte_time(date_str: str, time_code: str) -> datetime:
    """Convert SMPTE date and timecode to datetime.
    
    Args:
        date_str: Date in YYYY-MM-DD format
        time_code: Time in HH:MM:SS;FF format (frames removed for parsing)
    
    Returns:
        datetime object
    """
    try:
        time_str = time_code.split(';')[0]  # Remove frame count
        return datetime.strptime(f"{date_str} {time_str}", '%Y-%m-%d %H:%M:%S')
    except Exception as e:
        logger.error(f"Error parsing SMPTE time - date: {date_str}, time: {time_code}, error: {str(e)}")
        raise

def categorize_spot_type(spot_type: str) -> SpotType:
    """Categorize spot type and log any unknown types.
    
    Args:
        spot_type: String representation of spot type from XML
    
    Returns:
        SpotType enum value
    """
    try:
        return SpotType[spot_type.upper()]
    except KeyError:
        logger.warning(f"Unknown spot type encountered: {spot_type}")
        return SpotType.UNKNOWN

def parse_mode(mode: str, mode_type: str) -> Union[StartMode, EndMode]:
    """Parse start or end mode strings into enums.
    
    Args:
        mode: Mode string from XML
        mode_type: Either 'start' or 'end' for logging
    
    Returns:
        StartMode or EndMode enum value
    """
    mode_map = {
        'start': {
            'FIXED': StartMode.FIXED,
            'FOLLOW': StartMode.FOLLOW,
            'SEQUENTIAL': StartMode.SEQUENTIAL,
            'MANUAL': StartMode.MANUAL
        },
        'end': {
            'DURATION': EndMode.DURATION,
            'FIXED': EndMode.FIXED,
            'MANUAL': EndMode.MANUAL,
            'FOLLOW': EndMode.FOLLOW
        }
    }
    
    try:
        return mode_map[mode_type.lower()][mode.upper()]
    except KeyError:
        logger.warning(f"Unknown {mode_type} mode encountered: {mode}")
        return StartMode.UNKNOWN if mode_type.lower() == 'start' else EndMode.UNKNOWN

# Update the relevant section in the parse_xml_file function where we handle NonProgramEvent

def parse_xml_file(file_content: str) -> List[Dict]:
    try:
        root = ET.fromstring(file_content)
        logger.info(f"Successfully parsed XML root element: {root.tag}")
        
        ns = {
            'bxf': 'http://smpte-ra.org/schemas/2021/2012/BXF',
            'pmcp': 'http://www.atsc.org/XMLSchemas/pmcp/2007/3.1'
        }
        
        # Track unique spot types and modes for monitoring
        unique_spot_types: Set[str] = set()
        unique_start_modes: Set[str] = set()
        unique_end_modes: Set[str] = set()
        
        asruns = root.findall(".//bxf:AsRun/bxf:CompleteAsRun", ns)
        logger.info(f"Found {len(asruns)} CompleteAsRun elements")
        
        events = []
        for asrun in asruns:
            try:
                event = {}
                
                # Extract basic event information
                event_id = asrun.find(".//bxf:EventId/bxf:EventId", ns)
                event['event_id'] = event_id.text if event_id is not None else None
                
                event_title = asrun.find(".//bxf:EventTitle", ns)
                event['event_title'] = event_title.text if event_title is not None else None
                
                # Extract SpotType from the correct path
                spot_type = asrun.find(".//bxf:PrimaryEvent/bxf:NonProgramEvent/bxf:Details/bxf:SpotType", ns)
                if spot_type is not None and spot_type.text:
                    event['spot_type'] = spot_type.text
                    event['spot_type_category'] = categorize_spot_type(spot_type.text).name
                    unique_spot_types.add(spot_type.text)
                
                # Program Event details
                program_event = asrun.find(".//bxf:ProgramEvent", ns)
                if program_event is not None:
                    event['event_category'] = 'Program'
                    segment_number = program_event.find("bxf:SegmentNumber", ns)
                    segment_name = program_event.find("bxf:SegmentName", ns)
                    program_name = program_event.find("bxf:ProgramName", ns)
                    
                    event['segment_number'] = segment_number.text if segment_number is not None else None
                    event['segment_name'] = segment_name.text if segment_name is not None else None
                    event['program_name'] = program_name.text if program_name is not None else None

                # Non-Program Event details
                non_program_event = asrun.find(".//bxf:NonProgramEvent", ns)
                if non_program_event is not None:
                    event['event_category'] = 'NonProgram'
                    non_program_name = non_program_event.find("bxf:NonPrimaryEventName", ns)
                    event['non_program_name'] = non_program_name.text if non_program_name is not None else None
                
                # Description for all events
                description = asrun.find(".//bxf:Description", ns)
                event['description'] = description.text if description is not None else None
                
                # Start and End modes with tracking
                start_mode = asrun.find(".//bxf:StartMode", ns)
                end_mode = asrun.find(".//bxf:EndMode", ns)
                
                if start_mode is not None and start_mode.text:
                    unique_start_modes.add(start_mode.text)
                    event['start_mode'] = start_mode.text
                    event['start_mode_category'] = parse_mode(start_mode.text, 'start').name
                
                if end_mode is not None and end_mode.text:
                    unique_end_modes.add(end_mode.text)
                    event['end_mode'] = end_mode.text
                    event['end_mode_category'] = parse_mode(end_mode.text, 'end').name
                
                # Router source
                router_source = asrun.find(".//bxf:RouterSource/bxf:Name", ns)
                event['source'] = router_source.text if router_source is not None else None
                
                # Status and Type
                status = asrun.find(".//bxf:AsRunDetail/bxf:Status", ns)
                event['status'] = status.text if status is not None else None
                
                event_type = asrun.find(".//bxf:AsRunDetail/bxf:Type", ns)
                event['event_type'] = event_type.text if event_type is not None else None
                
                # Timing
                start_time_elem = asrun.find(".//bxf:AsRunDetail/bxf:StartDateTime/bxf:SmpteDateTime", ns)
                if start_time_elem is not None:
                    date = start_time_elem.get('broadcastDate')
                    time_code = start_time_elem.find('bxf:SmpteTimeCode', ns).text
                    event['start_time'] = parse_smpte_time(date, time_code)
                else:
                    event['start_time'] = None
                
                duration = asrun.find(".//bxf:AsRunDetail/bxf:Duration/bxf:SmpteDuration/bxf:SmpteTimeCode", ns)
                event['duration'] = duration.text if duration is not None else None
                
                # House Number
                house_number = asrun.find(".//bxf:ContentId/bxf:HouseNumber", ns)
                event['house_number'] = house_number.text if house_number is not None else None
                
                events.append(event)
                logger.info(f"Added event: {event['event_id']}")
                
            except Exception as e:
                logger.error(f"Error parsing event: {str(e)}")
                continue
        
        # Log unique values found
        logger.info(f"Found unique spot types: {unique_spot_types}")
        logger.info(f"Found unique start modes: {unique_start_modes}")
        logger.info(f"Found unique end modes: {unique_end_modes}")
        
        return events
    
    except Exception as e:
        logger.error(f"Unexpected error parsing XML: {str(e)}")
        raise