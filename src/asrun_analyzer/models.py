from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
from .parser import SpotType, StartMode, EndMode

Base = declarative_base()

class AsRunFile(Base):
    """Tracks processed AsRun files"""
    __tablename__ = 'asrun_files'

    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, nullable=False)
    date_processed = Column(DateTime, default=datetime.utcnow)
    broadcast_date = Column(DateTime, nullable=False)
    events = relationship("Event", back_populates="asrun_file")

class Event(Base):
    """Stores individual events from AsRun files"""
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    event_id = Column(String, nullable=False)
    event_title = Column(String)
    event_category = Column(String)  # Program or NonProgram
    description = Column(String)
    
    # Timing information
    start_time = Column(DateTime)
    duration = Column(String)  # Stored as SMPTE timecode
    
    # Event details
    spot_type = Column(String)
    spot_type_category = Column(Enum(SpotType))
    start_mode = Column(String)
    start_mode_category = Column(Enum(StartMode))
    end_mode = Column(String)
    end_mode_category = Column(Enum(EndMode))
    
    # Status and identifiers
    status = Column(String)
    event_type = Column(String)
    house_number = Column(String)
    source = Column(String)
    
    # Program-specific fields
    segment_number = Column(String)
    segment_name = Column(String)
    program_name = Column(String)
    
    # Relationships
    asrun_file_id = Column(Integer, ForeignKey('asrun_files.id'))
    asrun_file = relationship("AsRunFile", back_populates="events")

    # Add unique constraint for event_id within the same broadcast date
    __table_args__ = (
        UniqueConstraint('event_id', 'start_time', name='uix_event_id_start_time'),
    )

    def __repr__(self):
        return f"<Event(id={self.id}, title='{self.event_title}', status='{self.status}')>"