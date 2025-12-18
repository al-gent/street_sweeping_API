import os
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
SIMPLEPUSH_KEY = os.getenv("SIMPLEPUSH_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def notify(record, today_or_tomorrow):
    message = f"🚨 Move your car from {record.street_name}. Street sweeping starts {today_or_tomorrow} at {record.next_sweep_time}:00"
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
            print(f"Sent reminder for {record.phone_number}")
        else:
            print(f"Failed to send: {response.text}")
    except Exception as e:
        print(f"Error: {e}")


def send_reminders():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT DISTINCT phone_number FROM parking_records"))
        phone_nums = [row.phone_number for row in result] 
        today = datetime.now(ZoneInfo("America/Los_Angeles"))
        tomorrow = today + timedelta(days=1)
        print(f"Checking reminders for {tomorrow}...")
        for num in phone_nums:
            print('checking for', num)
            result = db.execute(text("SELECT * FROM parking_records WHERE phone_number = :num ORDER BY created_at DESC LIMIT 1"), {"num": num})
            res = result.mappings().fetchone()
            
            if (tomorrow.date() == res.next_sweep_date):
                print(f"Sweeping TOMORROW AT {res.next_sweep_time}: sending reminder to {num}, they are parked on {res.street_name} between {res.between}.")
                notify(res, 'TOMORROW')
            if (today.date() == res.next_sweep_date):
                print(f"SWEEPING TODAY AT {res.next_sweep_time}: sending reminder to {num}, they are parked on {res.street_name} between {res.between}")
                notify(res, 'TODAY')
    finally:
        db.close()
    


if __name__ == "__main__":
    send_reminders()