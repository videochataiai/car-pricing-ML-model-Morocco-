import sqlite3
import pandas as pd
from sklearn.model_selection import train_test_split

def get_clean_data():
    conn = sqlite3.connect('../research_study.db')
    # Load completed negotiations
    df = pd.read_sql("SELECT * FROM leads WHERE status='NEGOTIATING'", conn)
    
    # Convert JSON specs to columns
    # ... (Pandas logic to flatten JSON) ...
    
    return train_test_split(df[['year', 'mileage']], df['scraped_price'])
