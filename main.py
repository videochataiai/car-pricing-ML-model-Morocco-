import time
import sqlite3
import json
from wacli_wrapper import Wacli
from brain import app
from db import DB_NAME

def run_system():
    wa = Wacli()
    print("System Active. Polling...")

    while True:
        try:
            # 1. Get new messages
            new_msgs = wa.get_incoming(lookback_seconds=10)
            
            if new_msgs:
                with sqlite3.connect(DB_NAME) as conn:
                    for msg in new_msgs:
                        phone = msg.get('chat', {}).get('jid', '').split('@')[0]
                        text = msg.get('text', {}).get('body', '')
                        
                        if not phone or not text:
                            continue
                            
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
                            msgs = new_state.get('messages', [])
                            last_ai_msg = msgs[-1] if msgs else ""
                            if last_ai_msg.startswith("AI:"):
                                reply_text = last_ai_msg.replace("AI: ", "")
                                wa.send(phone, reply_text)
                            
                            # 5. Save
                            # Also update the status if available
                            status = new_state.get('stage', 'INIT')
                            conn.execute("UPDATE leads SET state_json=?, status=?, updated_at=datetime('now') WHERE phone=?", 
                                        (json.dumps(new_state), status, phone))
                            conn.commit()
                        else:
                            print(f"Ignored message from unknown lead {phone}")
        except Exception as e:
            print(f"Error in main loop: {e}")
            
        time.sleep(5)

if __name__ == "__main__":
    run_system()
