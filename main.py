from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import geopandas as gpd
import pandas as pd
from shapely import wkt
from shapely.geometry import Point
from datetime import datetime, timedelta, timezone
import os
import requests

# Load street sweeping schedule
df = pd.read_csv("SSS.csv")
df = df[df['Line'].notnull()]  
df['Line'] = df['Line'].astype(str)
df['geometry'] = df['Line'].apply(wkt.loads)
gdf = gpd.GeoDataFrame(df, geometry='geometry')

app = FastAPI()

class Location(BaseModel):
    latitude: float
    longitude: float

@app.post("/next_sweep")
def get_next_sweep(location: Location):
    try:
        # Get current time
        now = datetime.now(timezone.utc)
        
        # Convert lat/lon to a point
        user_point = Point(location.longitude, location.latitude)
        gdf['distance'] = gdf['geometry'].distance(user_point)

        # Get the two closest street segments
        closest_streets = gdf.sort_values(by='distance')[:2]

        # if you're note close to any street it shouldnt just find the one you're closest to
        if closest_streets.empty:
            raise HTTPException(status_code=404, detail="No street sweeping data found.")

        # Determine street side
        line = closest_streets['geometry'].iloc[0]
        closest_point = line.interpolate(line.project(user_point))

        blockside = ''
        if user_point.y > closest_point.y:
            if user_point.x > closest_point.x:
                blockside = 'NorthEast'
            elif user_point.x < closest_point.x:
                blockside = 'NorthWest'
            else:
                blockside = 'North'
        elif user_point.y < closest_point.y:
            if user_point.x > closest_point.x:
                blockside = 'SouthEast'
            elif user_point.x < closest_point.x:
                blockside = 'SouthWest'
            else:
                blockside = 'South'
        else:
            if user_point.x > closest_point.x:
                blockside = 'East'
            elif user_point.x < closest_point.x:
                blockside = 'West'
            else:
                blockside = 'On the Line'

        # Filter by correct block side
        parking_loc_sss = closest_streets[closest_streets.BlockSide == blockside]
        # print(parking_loc_sss.iloc[0])
        if parking_loc_sss.empty:
            raise HTTPException(status_code=404, detail="No street sweeping schedule found for this location.")

        main_street = parking_loc_sss['Corridor'].iloc[0]
        limits = parking_loc_sss['Limits'].iloc[0].split('-')
        # print(f'you are parked on  {main_street} between {limits[0]} and {limits[1]}')
        # print(parking_loc_sss)
        # Get next sweeping day
        weekdays = ['Mon', 'Tues', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        next_sweep_date = None

        for i in range(14):
            day_to_check = now + timedelta(days=i)
            weekday = weekdays[day_to_check.weekday()]
            occurrence = (day_to_check.day - 1) // 7 + 1
            if (parking_loc_sss['WeekDay'].iloc[0] == weekday) and (parking_loc_sss[f'Week{occurrence}'].iloc[0] == 1):
                next_sweep_date = day_to_check.strftime("%A, %B %d")
                days_until_sweep = i
                break

        if not next_sweep_date:
            raise HTTPException(status_code=404, detail="No upcoming street sweeping found.")

        rJSON =  {
            "street": main_street,
            "blockside": blockside,
            "location_limits": f"{limits[0].strip()} - {limits[1].strip()}",
            "next_sweep_date": next_sweep_date,
            "next_sweep_time": (int(parking_loc_sss['FromHour'].iloc[0]), int(parking_loc_sss['ToHour'].iloc[0])),
            "days_until_sweep": int(days_until_sweep)
        }

        # print(rJSON)
        return rJSON

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



