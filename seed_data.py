import sqlite3
import json
from datetime import datetime, timedelta
import random

DB_NAME = "research_study.db"

def seed():
    conn = sqlite3.connect(DB_NAME)
    
    # Fake Models and Strategies
    models = ["Golf 7", "Clio 4", "Dacia Logan", "Peugeot 208", "Range Rover Evoque"]
    strategies = ["A", "B"]
    
    print("Seeding database with fake research data...")

    for i in range(15):
        phone = f"2126{random.randint(10000000, 99999999)}"
        model = random.choice(models)
        listing_price = random.randint(80000, 250000)
        target = int(listing_price * 0.85)
        
        # Randomize State
        status = random.choice(["INIT", "WAITING_REPLY", "NEGOTIATING", "CLOSED"])
        strategy = random.choice(strategies)
        
        # Create Fake Memory
        state = {
            "phone": phone,
            "messages": [
                "AI: Salam, dispo?",
                "User: Oui dispo.",
                f"AI: Je vous offre {target} DH."
            ],
            "stage": status,
            "car": {
                "model": model,
                "listing_price": listing_price,
                "target_price": target,
                "year": 2018,
                "mileage": 120000
            },
            "strategy_group": strategy
        }
        
        try:
            conn.execute(
                "INSERT INTO leads (phone, model_name, scraped_price, strategy_group, status, state_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    phone, 
                    model, 
                    listing_price, 
                    strategy,
                    status, 
                    json.dumps(state), 
                    datetime.now() - timedelta(hours=random.randint(1, 48)),
                    datetime.now()
                )
            )
        except sqlite3.IntegrityError:
            pass

    conn.commit()
    conn.close()
    print("Seed Complete. 15 Fake Leads inserted.")

if __name__ == "__main__":
    seed()
