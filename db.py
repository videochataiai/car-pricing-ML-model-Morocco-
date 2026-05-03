import sqlite3
import json
from datetime import datetime

DB_NAME = "research_study.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    # FIXED: Added 'strategy_group' column
    conn.execute('''CREATE TABLE IF NOT EXISTS leads (
        phone TEXT PRIMARY KEY,
        model_name TEXT,
        scraped_price INTEGER,
        strategy_group TEXT,
        status TEXT DEFAULT 'INIT',
        state_json TEXT, 
        created_at DATETIME,
        updated_at DATETIME
    )''')
    conn.commit()
    conn.close()
    print(f"Database {DB_NAME} initialized with correct schema.")

def register_lead(phone, model, price, specs=None, seller_name="Unknown"):
    conn = sqlite3.connect(DB_NAME)
    
    # Logic: Deterministic A/B Split based on phone number
    strategy = "A" if hash(phone) % 2 == 0 else "B"

    initial_state = {
        "phone": phone,
        "messages": [],
        "stage": "INIT",
        "car": {
            "model": model,
            "listing_price": price, 
            "year": specs.get('year') if specs else None,
            "mileage": specs.get('mileage') if specs else None,
            "target_price": int(price * 0.85) if price else None
        },
        "strategy_group": strategy,
        "seller_name": seller_name,
        "language": "UNKNOWN"
    }
    
    try:
        # FIXED: Insert statement now includes strategy_group and seller_name
        conn.execute(
            "INSERT INTO leads (phone, model_name, scraped_price, strategy_group, seller_name, state_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (phone, model, price, strategy, seller_name, json.dumps(initial_state), datetime.now(), datetime.now())
        )
        conn.commit()
        print(f"Lead Saved: {phone} [{model}]")
    except sqlite3.IntegrityError:
        print(f"Duplicate Lead: {phone}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
