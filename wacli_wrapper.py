import subprocess
import json
from datetime import datetime, timedelta

class Wacli:
    def __init__(self):
        self.cmd = "wacli" # Ensure wacli is in your system PATH

    def send(self, phone, message):
        """Executes the Go command to send a message."""
        # Sanitize phone number for CLI
        clean_phone = phone.replace("+", "").replace(" ", "")
        
        try:
            subprocess.run(
                [self.cmd, "send", "text", "--to", clean_phone, "--message", message],
                check=True, capture_output=True
            )
            print(f"Sent to {clean_phone}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"Send Failed: {e}")
            return False

    def get_incoming(self, lookback_seconds=10):
        """Polls local DB for messages received in the last X seconds."""
        # This assumes wacli has a JSON export or query feature
        # If wacli lacks a time filter, you fetch the last 20 and filter in Python
        cutoff = datetime.now() - timedelta(seconds=lookback_seconds)
        
        try:
            # Hypothetical command structure based on wacli capabilities
            result = subprocess.run(
                [self.cmd, "messages", "list", "--limit", "10", "--json"],
                capture_output=True, text=True
            )
            
            if result.returncode != 0:
                print(f"wacli get_incoming failed: {result.stderr}")
                return []
                
            if not result.stdout.strip():
                return []
                
            messages = json.loads(result.stdout)
            
            # Filter for recent incoming messages only
            recent = []
            for m in messages:
                # Timestamp parsing depends on wacli's specific output format
                # Assuming standard ISO or Unix timestamp
                if not m.get('from_me') and m.get('timestamp') > cutoff.timestamp():
                    recent.append(m)
            return recent
            
        except Exception as e:
            # Fail silently on poll errors to avoid log spam
            return []
