import os
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from main import ParkingRecord
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta

from dotenv import load_dotenv
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

SIMPLEPUSH_KEY = os.getenv("SIMPLEPUSH_KEY")  # Your SimplePush key

def notify(record):
    message = f"🚨 Move your car from {record.street_name}. Street sweeping starts tomorrow at {record.next_sweep_time}"
    try:
        # Send via SimplePush
        response = requests.post(
            'https://api.simplepush.io/send',
            data={
                'key': os.getenv('SIMPLEPUSH_KEY'),
                'title': 'Street Sweeping Reminder',
                'msg': message
            }
        )
        if response.status_code == 200:
            print(f"Sent reminder for {record.street_name}")
        else:
            print(f"Failed to send: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def send_reminders():
    result = db.execute(text("SELECT DISTINCT phone_number FROM parking_records"))
    phone_nums = [row.phone_number for row in result] 
    for num in phone_nums:
        result = db.execute(text("SELECT * FROM parking_records WHERE phone_number = :num ORDER BY created_at DESC LIMIT 1"), {"num": num})
        res = result.mappings().fetchone()

    today = datetime.now(ZoneInfo("America/Los_Angeles"))
    today = today + timedelta(days=8)
    if today.date() == res.next_sweep_date:
        notify(res)
    


if __name__ == "__main__":
    send_reminders()