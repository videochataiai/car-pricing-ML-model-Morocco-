import sqlite3
import pandas as pd
import joblib
import os
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.metrics import mean_absolute_error

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
    
    if len(df) < 5:
        print(f"Not enough data to train yet. Found {len(df)} samples. Need 50+.")
        return

    print(f"Training on {len(df)} verified negotiations...")

    # 2. FEATURE ENGINEERING
    # Convert 'year' to 'car_age'
    df['car_age'] = 2026 - df['year']
    
    # 3. PREPROCESSING PIPELINE
    categorical_features = ['model_name']
    numeric_features = ['car_age', 'mileage']

    preprocessor = ColumnTransformer(
        transformers=[
            ('num', SimpleImputer(strategy='median'), numeric_features),
            ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
        ])

    # 4. MODEL ARCHITECTURE & HYPERPARAMETER TUNING
    pipeline = Pipeline(steps=[
        ('preprocessor', preprocessor),
        ('regressor', GradientBoostingRegressor(random_state=42))
    ])

    # Define hyperparameter grid
    param_grid = {
        'regressor__n_estimators': [50, 100, 200],
        'regressor__learning_rate': [0.01, 0.05, 0.1],
        'regressor__max_depth': [3, 4, 5]
    }

    # 5. TRAIN/TEST SPLIT
    X = df.drop(['true_value', 'year'], axis=1) # Drop 'year' as we use 'car_age'
    y = df['true_value']
    
    # If data is extremely small, we use 1 sample for test
    test_size = 1 if len(df) <= 5 else 0.2
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=42)

    print("Tuning hyperparameters via Grid Search...")
    # Using cv=2 for very small dataset
    grid_search = GridSearchCV(pipeline, param_grid, cv=2 if len(df) < 10 else 5, scoring='neg_mean_absolute_error')
    grid_search.fit(X_train, y_train)
    
    best_model = grid_search.best_estimator_
    print(f"Best Params: {grid_search.best_params_}")

    # 6. EVALUATION
    y_pred = best_model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    print(f"Model Evaluation -> Mean Absolute Error: {mae:,.2f} DH")

    # 7. SAVE BRAIN
    if not os.path.exists("models"):
        os.makedirs("models")
        
    joblib.dump(best_model, "models/price_predictor.pkl")
    print("New Brain Saved. AI is now smarter.")

if __name__ == "__main__":
    train_new_brain()

