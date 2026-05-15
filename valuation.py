import pandas as pd
import joblib
import os
import numpy as np

MODEL_PATH = "models/price_predictor.pkl"
TF_MODEL_PATH = "models/tf_price_predictor.keras"
TF_PREPROCESSOR_PATH = "models/tf_preprocessor.pkl"
NUMPY_WEIGHTS_PATH = "models/numpy_nn_weights.pkl"
CAT_ENCODER_PATH = "models/cat_encoder.pkl"
NUM_SCALER_PATH = "models/num_scaler.pkl"

class ValuationEngine:
    def __init__(self):
        self.model = None
        self.tf_model = None
        self.tf_preprocessor = None
        self.nn_weights = None
        self.cat_encoder = None
        self.num_scaler = None
        self.load_model()

    def load_model(self):
        """Loads the latest trained ML model or NumPy NN if available."""
        # Load NumPy NN if it exists (User preference)
        if os.path.exists(NUMPY_WEIGHTS_PATH) and os.path.exists(CAT_ENCODER_PATH) and os.path.exists(NUM_SCALER_PATH):
            try:
                self.nn_weights = joblib.load(NUMPY_WEIGHTS_PATH)
                self.cat_encoder = joblib.load(CAT_ENCODER_PATH)
                self.num_scaler = joblib.load(NUM_SCALER_PATH)
                print("Deep Learning NumPy Brain Loaded: Neural Net active.")
                return
            except Exception as e:
                print(f"NumPy Model Load Failed: {e}")

        # Try TensorFlow Keras model
        if os.path.exists(TF_MODEL_PATH) and os.path.exists(TF_PREPROCESSOR_PATH):
            try:
                import tensorflow as tf
                self.tf_model = tf.keras.models.load_model(TF_MODEL_PATH)
                self.tf_preprocessor = joblib.load(TF_PREPROCESSOR_PATH)
                print("TensorFlow Brain Loaded: Pricing logic active.")
                return
            except Exception as e:
                print(f"TF Model Load Failed: {e}")

        # Fallback to Scikit-Learn
        if os.path.exists(MODEL_PATH):
            try:
                self.model = joblib.load(MODEL_PATH)
                print("ML Brain Loaded: Pricing logic active.")
            except Exception as e:
                print(f"Model Load Failed: {e}")
        else:
            print("No ML Model found. Using 'Cold Start'.")

    def predict_fair_value(self, car_model, year, mileage, listed_price):
        """
        Returns the AI's estimated 'True Market Value'.
        """
        import datetime
        current_year = datetime.datetime.now().year
        car_age = current_year - year if year else 10
        mileage_val = mileage if mileage else 150000
        
        # SCENARIO A: NumPy Neural Network
        if self.nn_weights:
            try:
                # 1. Preprocess
                cat_features = self.cat_encoder.transform(pd.DataFrame([{'model_name': car_model}]))
                
                num_features = self.num_scaler.transform(pd.DataFrame([{'car_age': car_age, 'mileage': mileage_val}]))
                
                X = np.hstack((cat_features, num_features))
                
                # 2. Forward Pass
                Z1 = np.dot(X, self.nn_weights['W1']) + self.nn_weights['b1']
                A1 = np.maximum(0, Z1) # ReLU
                
                Z2 = np.dot(A1, self.nn_weights['W2']) + self.nn_weights['b2']
                A2 = np.maximum(0, Z2) # ReLU
                
                Z3 = np.dot(A2, self.nn_weights['W3']) + self.nn_weights['b3']
                predicted_price = float(Z3[0, 0])
                
                # Guardrails
                if predicted_price < (listed_price * 0.5):
                    return int(listed_price * 0.7)
                if predicted_price > (listed_price * 1.3):
                    return int(listed_price)
                    
                return int(predicted_price)
            except Exception as e:
                print(f"NumPy Inference Failed: {e}. Falling back to listed price heuristic.")
                return int(listed_price * 0.85)
                
        # SCENARIO B: TensorFlow Keras Model
        elif self.tf_model and self.tf_preprocessor:
            try:
                features = pd.DataFrame([{
                    'model_name': car_model,
                    'car_age': car_age,
                    'mileage': mileage_val
                }])
                X_processed = self.tf_preprocessor.transform(features)
                predicted_price = float(self.tf_model.predict(X_processed, verbose=0)[0][0])
                
                if predicted_price < (listed_price * 0.5):
                    return int(listed_price * 0.7)
                if predicted_price > (listed_price * 1.3):
                    return int(listed_price)
                    
                return int(predicted_price)
            except Exception as e:
                print(f"TF Inference Failed: {e}. Falling back to heuristic.")
                return int(listed_price * 0.85)

        # SCENARIO C: Scikit-Learn Model
        elif self.model:
            features = pd.DataFrame([{
                'model_name': car_model,
                'car_age': car_age,
                'mileage': mileage_val 
            }])
            
            try:
                predicted_price = self.model.predict(features)[0]
                
                # Safety Guardrails
                if predicted_price < (listed_price * 0.5):
                    return int(listed_price * 0.7)
                if predicted_price > (listed_price * 1.3):
                    return int(listed_price)
                    
                return int(predicted_price)
            except:
                return int(listed_price * 0.85)

        # SCENARIO D: Cold Start
        else:
            return int(listed_price * 0.85)


