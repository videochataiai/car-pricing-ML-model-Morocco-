import time
import sqlite3
import json
from wacli_wrapper import Wacli
from brain import app
from db import DB_NAME

def run_system():
    wa = Wacli()
    conn = sqlite3.connect(DB_NAME)
    print("System Active. Polling...")

    while True:
        # 1. Get new messages
        new_msgs = wa.get_incoming(lookback_seconds=10)
        
        for msg in new_msgs:
            phone = msg['chat']['jid'].split('@')[0]
            text = msg['text']['body']
            
            print(f"Incoming from {phone}: {text}")
            
            # 2. Load State
            cursor = conn.execute("SELECT state_json FROM leads WHERE phone=?", (phone,))
            row = cursor.fetchone()
            
            if row:
                state = json.loads(row[0])
                state['messages'].append(f"User: {text}")
                
                # 3. Run AI
                new_state = app.invoke(state)
                
                # 4. Reply?
                last_ai_msg = new_state['messages'][-1]
                if last_ai_msg.startswith("AI:"):
                    reply_text = last_ai_msg.replace("AI: ", "")
                    wa.send(phone, reply_text)
                
                # 5. Save
                conn.execute("UPDATE leads SET state_json=? WHERE phone=?", 
                            (json.dumps(new_state), phone))
                conn.commit()
        
        time.sleep(5)

if __name__ == "__main__":
    run_system()
