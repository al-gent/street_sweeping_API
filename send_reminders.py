import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main import ParkingRecord

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://rag_user@postgres:5432/rag_logs")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

SIMPLEPUSH_KEY = os.getenv("SIMPLEPUSH_KEY")  # Your SimplePush key

def send_reminders():
    db = SessionLocal()
    
    records = db.query(ParkingRecord).filter(
        ParkingRecord.days_until_sweep == 1,
        ParkingRecord.notified == 0
    ).all()
    
    for record in records:
        message = f"🚨 Move your car from {record.street} by {record.next_sweep_time} tomorrow ({record.next_sweep_date})"
        
        try:
            # Send via SimplePush
            response = requests.post(
                'https://api.simplepush.io/send',
                data={
                    'key': SIMPLEPUSH_KEY,
                    'title': 'Street Sweeping Reminder',
                    'msg': message
                }
            )
            
            if response.status_code == 200:
                record.notified = 1
                db.commit()
                print(f"Sent reminder for {record.street}")
            else:
                print(f"Failed to send: {response.text}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    db.close()
    print(f"Processed {len(records)} reminders")

if __name__ == "__main__":
    send_reminders()