from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
from datetime import datetime, timedelta, timezone
import os
import requests
from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os
from io import StringIO
from zoneinfo import ZoneInfo


TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def send_telegram(chat_id, message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        'chat_id': chat_id,
        'text': message
    })

def calculate_blockside(user_point: Point, closest_point: Point) -> str:
    """Determine which side of the street the user is parked on."""
    if user_point.y > closest_point.y:
        if user_point.x > closest_point.x:
            return 'NorthEast'
        elif user_point.x < closest_point.x:
            return 'NorthWest'
        return 'North'
    elif user_point.y < closest_point.y:
        if user_point.x > closest_point.x:
            return 'SouthEast'
        elif user_point.x < closest_point.x:
            return 'SouthWest'
        return 'South'
    else:
        if user_point.x > closest_point.x:
            return 'East'
        elif user_point.x < closest_point.x:
            return 'West'
        return 'On the Line'

def find_next_sweep_date(ss_at_loc: pd.DataFrame, now: datetime) -> tuple[datetime, int]:
    """Calculate the next street sweeping date."""
    weekdays = ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    for i in range(14):
        day_to_check = now + timedelta(days=i)
        weekday = weekdays[day_to_check.weekday()]
        occurrence = (day_to_check.day - 1) // 7 + 1
        
        if (ss_at_loc['weekday'].iloc[0] == weekday and 
            ss_at_loc[f'week{occurrence}'].iloc[0] == 1):
            return day_to_check, i
    
    return None, None

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
class ParkingRecordDB(Base):
    __tablename__ = 'parking_records'
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(15), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    street_name = Column(String(255), nullable=False)
    between = Column(String(255))
    blockside = Column(String(50))
    cnn = Column(Integer)
    next_sweep_date = Column(Date)
    next_sweep_time = Column(Integer)
    created_at = Column(DateTime, default=datetime.now)


print("Loading SF street data...")
streets_response = requests.get('https://data.sfgov.org/resource/3psu-pn9h.csv?$limit=999999')
all_streets = pd.read_csv(StringIO(streets_response.text))
# all_streets = pd.read_csv('./streets.csv')
all_streets.columns = all_streets.columns.str.lower()
all_streets=all_streets[all_streets['active']]
all_streets['line'] = all_streets['line'].astype(str)
all_streets['geometry'] = all_streets['line'].apply(wkt.loads)
all_streets = gpd.GeoDataFrame(all_streets, geometry='geometry')

ss_response = requests.get('https://data.sfgov.org/resource/yhqp-riqs.csv?$limit=999999')
ss = pd.read_csv(StringIO(ss_response.text))
# ss = pd.read_csv('./SSS.csv')
ss.columns = ss.columns.str.lower()

ss = ss[ss['line'].notnull()]  
ss['line'] = ss['line'].astype(str)
ss['geometry'] = ss['line'].apply(wkt.loads)
ss = gpd.GeoDataFrame(ss, geometry='geometry')
print("Data loaded successfully")

app = FastAPI()

class Location(BaseModel):
    latitude: float
    longitude: float
    phone_number: str

# Startup event - creates tables when app starts
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

@app.post("/next_sweep")
def get_next_sweep(location: Location):
    try:
        now = datetime.now(ZoneInfo("America/Los_Angeles"))

        user_point = Point(location.longitude, location.latitude)
        all_streets['distance'] = all_streets['geometry'].distance(user_point)
        closest_street = all_streets.sort_values(by='distance')[:1]
        main_street = closest_street['street'].values[0]
        between = (closest_street['f_st'].values[0], closest_street['t_st'].values[0])
        between_str = f"{between[0]} and {between[1]}"

        cnn = closest_street['cnn'].values[0]
        print(main_street, between)

        street_sides = ss[ss['cnn'] == int(cnn)]
        if len(street_sides) == 0:
            print('it appears that there is NO street sweeping here')
            db_record = ParkingRecordDB(
                phone_number=int(location.phone_number),
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                street_name=str(main_street),
                between=between_str,
                blockside = str('n/a'),
                cnn = int(cnn),
                next_sweep_date=None,
                next_sweep_time=None

            )
            db = SessionLocal()
            db.add(db_record)
            db.commit()
            db.refresh(db_record)  
            db.close()
            
            # Return a response
            return {
                "message": 
                    f"""Parked on {main_street} between {between_str}.
                        No street sweeping here!"""
            }

        #determine streetside
        line = closest_street['geometry'].iloc[0]
        closest_point = line.interpolate(line.project(user_point))
        blockside = calculate_blockside(user_point, closest_point)
        
        SS_at_loc = street_sides[street_sides.blockside == blockside]
        if len(SS_at_loc) == 0:
            print('it appears that there is NO street sweeping on this side of the street')
            db_record = ParkingRecordDB(
                phone_number=int(location.phone_number),
                latitude=float(location.latitude),
                longitude=float(location.longitude),
                street_name=str(main_street),
                between=between_str, 
                blockside = str(blockside),
                cnn = int(cnn),
                next_sweep_date=None,
                next_sweep_time=None

            )
            db = SessionLocal()
            db.add(db_record)
            db.commit()
            db.refresh(db_record)  
            db.close()
            
            # Return a response
            return {
                "message": 
                    f"""Parked on the {blockside} of {main_street} between {between_str}.
                        No street sweeping on this side!"""
            }
        next_sweep_time = SS_at_loc['fromhour'].values[0]
        blockside = SS_at_loc['blockside'].values[0]
        print('you are parked on the', blockside, 'side of', main_street, 'between',between_str)
        
        next_sweep_date, days_until_sweep = find_next_sweep_date(SS_at_loc, now)

        print('NEXT SWEEP:', next_sweep_date, "AT", next_sweep_time)

        db_record = ParkingRecordDB(
            phone_number=int(location.phone_number),
            latitude=float(location.latitude),
            longitude=float(location.longitude),
            street_name=str(main_street),
            between=between_str,  # Store as readable string
            blockside = str(blockside),
            cnn = int(cnn),
            next_sweep_date=next_sweep_date.date(),
            next_sweep_time=int(next_sweep_time)
        )
        db = SessionLocal()
        db.add(db_record)
        db.commit()
        db.refresh(db_record)  
        db.close()
        
        # Return a response
        return {
            "message": 
                f"""Parked on {main_street} between {between_str}.
                You've got {days_until_sweep} days until
                next sweep on {next_sweep_date.date()} at {next_sweep_time}"""
        }

    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(error_traceback)
        raise HTTPException(status_code=500, detail=f"{str(e)}\n\nTraceback:\n{error_traceback}")



