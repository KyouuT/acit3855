from sqlalchemy.orm import DeclarativeBase, mapped_column 
from sqlalchemy import Integer, String, DateTime, Boolean, func 
from storage import engine

class Base(DeclarativeBase): 
    pass 

class TicketBooking(Base): 
    __tablename__ = "ticket_booking" 
    ticket_id = mapped_column(String(255), primary_key=True)
    num_people = mapped_column(Integer, nullable=False) 
    date = mapped_column(DateTime, nullable=False) 
    attraction = mapped_column(Boolean, nullable=False)
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    trace_id = mapped_column(String(255), nullable=False)

    def to_dict(self):
        return {
            "ticket_id": self.ticket_id,
            "num_people": self.num_people,
            "date": self.date.strftime('%Y-%m-%d %H:%M:%S'),
            "attraction": self.attraction,
            "date_created": self.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            "trace_id": self.trace_id
        }

class EventBooking(Base): 
    __tablename__ = "event_booking" 
    attraction_id = mapped_column(String(255), primary_key=True) 
    num_people = mapped_column(Integer, nullable=False)
    start_date = mapped_column(DateTime, nullable=False) 
    end_date = mapped_column(DateTime, nullable=False) 
    date_created = mapped_column(DateTime, nullable=False, default=func.now())
    trace_id = mapped_column(String(255), nullable=False)

    def to_dict(self):
        return {
            "attraction_id": self.attraction_id,
            "num_people": self.num_people,
            "start_date": self.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            "end_date": self.end_date.strftime('%Y-%m-%d %H:%M:%S'),
            "date_created": self.date_created.strftime('%Y-%m-%d %H:%M:%S'),
            "trace_id": self.trace_id
        }

def create():
    Base.metadata.create_all(engine)

def drop():
    Base.metadata.drop_all(engine)