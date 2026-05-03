import sqlite3
import pandas as pd
import numpy as np
import os
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import joblib
import tensorflow as tf
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler
from sklearn.compose import ColumnTransformer

def train_new_brain():
    conn = sqlite3.connect("research_study.db")
    
    # 1. LOAD DATA
    query = """
        SELECT 
            model_name,
            json_extract(state_json, '$.car.year') as year,
            json_extract(state_json, '$.car.mileage') as mileage,
            json_extract(state_json, '$.car.target_price') as true_value
        FROM leads 
        WHERE status IN ('NEGOTIATING', 'CLOSED')
        AND true_value IS NOT NULL
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    if len(df) < 5:
        print(f"Not enough data to train yet. Found {len(df)} samples. Need 50+.")
        return

    print(f"Training TensorFlow model on {len(df)} verified negotiations...")

    # 2. FEATURE ENGINEERING
    df['car_age'] = 2026 - df['year']
    df['mileage'] = df['mileage'].fillna(df['mileage'].median() if not df['mileage'].isna().all() else 150000)
    
    # 3. PREPROCESSING
    categorical_features = ['model_name']
    numeric_features = ['car_age', 'mileage']
    
    preprocessor = ColumnTransformer(
        transformers=[
            ('num', MinMaxScaler(), numeric_features),
            ('cat', OneHotEncoder(sparse_output=False, handle_unknown='ignore'), categorical_features)
        ])
        
    X = df[['model_name', 'car_age', 'mileage']]
    y = df['true_value'].values
    
    # Fit and transform features
    X_processed = preprocessor.fit_transform(X)
    
    if not os.path.exists("models"):
        os.makedirs("models")
        
    # Save preprocessor for inference
    joblib.dump(preprocessor, "models/tf_preprocessor.pkl")
    
    # 4. TRAIN/TEST SPLIT
    test_size = 1 if len(df) <= 5 else 0.2
    X_train, X_test, y_train, y_test = train_test_split(X_processed, y, test_size=test_size, random_state=42)


    # 5. TENSORFLOW MODEL
    model = tf.keras.Sequential([
        tf.keras.layers.Input(shape=(X_train.shape[1],)),
        tf.keras.layers.Dense(64, activation='relu'),
        tf.keras.layers.Dense(32, activation='relu'),
        tf.keras.layers.Dense(16, activation='relu'),
        tf.keras.layers.Dense(1, activation='linear')
    ])
    
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=0.01),
        loss='mean_absolute_error',
        metrics=['mae']
    )
                  
    print("Training TensorFlow Neural Network...")
    
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor='loss' if len(df) <= 5 else 'val_loss', 
        patience=20, 
        restore_best_weights=True
    )
    
    # 6. TRAINING
    fit_kwargs = {
        'epochs': 500,
        'batch_size': min(32, len(X_train)),
        'callbacks': [early_stop],
        'verbose': 0
    }
    
    if len(df) > 5:
        fit_kwargs['validation_data'] = (X_test, y_test)
        
    history = model.fit(X_train, y_train, **fit_kwargs)
    
    # 7. EVALUATION
    loss, mae = model.evaluate(X_test, y_test, verbose=0)
    print(f"Model Evaluation -> Mean Absolute Error: {mae:,.2f} DH")
    
    # 8. SAVE BRAIN
    model.save("models/tf_price_predictor.keras")
    print("TensorFlow Brain Saved. AI is now smarter.")

if __name__ == "__main__":
    train_new_brain()
