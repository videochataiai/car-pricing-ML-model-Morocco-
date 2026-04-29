import sqlite3
import pandas as pd
import numpy as np
import os
import joblib
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import OneHotEncoder, MinMaxScaler

# 1. Custom PyTorch Dataset
class CarDataset(Dataset):
    def __init__(self, db_path="research_study.db"):
        conn = sqlite3.connect(db_path)
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
        
        if len(df) == 0:
            raise ValueError("No data found in database.")
            
        # Feature Engineering
        df['car_age'] = 2026 - df['year']
        
        # Preprocessing
        self.cat_encoder = OneHotEncoder(sparse_output=False, handle_unknown='ignore')
        cat_features = self.cat_encoder.fit_transform(df[['model_name']])
        
        self.num_scaler = MinMaxScaler()
        # Fill missing mileage with median
        df['mileage'] = df['mileage'].fillna(df['mileage'].median() if not df['mileage'].isna().all() else 150000)
        num_features = self.num_scaler.fit_transform(df[['car_age', 'mileage']])
        
        # Combine features
        self.X = np.hstack((cat_features, num_features))
        self.y = df['true_value'].values.reshape(-1, 1)
        
        # Save preprocessors for inference
        if not os.path.exists("models"):
            os.makedirs("models")
        joblib.dump(self.cat_encoder, "models/cat_encoder.pkl")
        joblib.dump(self.num_scaler, "models/num_scaler.pkl")

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return torch.tensor(self.X[idx], dtype=torch.float32), torch.tensor(self.y[idx], dtype=torch.float32)

# 2. NumPy Neural Network
class NumPyNeuralNetwork:
    def __init__(self, input_dim, hidden1=16, hidden2=8):
        # He Initialization
        self.W1 = np.random.randn(input_dim, hidden1) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros((1, hidden1))
        
        self.W2 = np.random.randn(hidden1, hidden2) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros((1, hidden2))
        
        self.W3 = np.random.randn(hidden2, 1) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros((1, 1))

    def relu(self, x):
        return np.maximum(0, x)

    def relu_derivative(self, x):
        return (x > 0).astype(float)

    def forward(self, X):
        self.X = X
        self.Z1 = np.dot(X, self.W1) + self.b1
        self.A1 = self.relu(self.Z1)
        
        self.Z2 = np.dot(self.A1, self.W2) + self.b2
        self.A2 = self.relu(self.Z2)
        
        self.Z3 = np.dot(self.A2, self.W3) + self.b3
        self.A3 = self.Z3 
        return self.A3

    def backward(self, y, learning_rate=0.01):
        m = y.shape[0]
        
        # dL/dy_hat (MAE)
        dZ3 = (1.0 / m) * np.sign(self.A3 - y)
        
        dW3 = np.dot(self.A2.T, dZ3)
        db3 = np.sum(dZ3, axis=0, keepdims=True)
        
        dA2 = np.dot(dZ3, self.W3.T)
        dZ2 = dA2 * self.relu_derivative(self.Z2)
        
        dW2 = np.dot(self.A1.T, dZ2)
        db2 = np.sum(dZ2, axis=0, keepdims=True)
        
        dA1 = np.dot(dZ2, self.W2.T)
        dZ1 = dA1 * self.relu_derivative(self.Z1)
        
        dW1 = np.dot(self.X.T, dZ1)
        db1 = np.sum(dZ1, axis=0, keepdims=True)
        
        # Update weights
        self.W3 -= learning_rate * dW3
        self.b3 -= learning_rate * db3
        self.W2 -= learning_rate * dW2
        self.b2 -= learning_rate * db2
        self.W1 -= learning_rate * dW1
        self.b1 -= learning_rate * db1

    def save_weights(self, path="models/numpy_nn_weights.pkl"):
        weights = {
            'W1': self.W1, 'b1': self.b1,
            'W2': self.W2, 'b2': self.b2,
            'W3': self.W3, 'b3': self.b3
        }
        joblib.dump(weights, path)

def train():
    try:
        dataset = CarDataset()
    except ValueError as e:
        print(f"{e}")
        return
        
    dataloader = DataLoader(dataset, batch_size=4, shuffle=True)
    
    input_dim = dataset.X.shape[1]
    model = NumPyNeuralNetwork(input_dim)
    
    epochs = 1000 # Increased for small dataset
    lr = 0.001    # Lowered for stability with MAE
    
    print(f"Training NumPy NN on custom PyTorch DataLoader...")
    
    for epoch in range(epochs):
        epoch_loss = 0
        batches = 0
        
        for batch_X, batch_y in dataloader:
            X_np = batch_X.numpy()
            y_np = batch_y.numpy()
            
            predictions = model.forward(X_np)
            loss = np.mean(np.abs(predictions - y_np))
            epoch_loss += loss
            batches += 1
            
            model.backward(y_np, learning_rate=lr)
            
        if epoch % 100 == 0 or epoch == epochs - 1:
            avg_loss = epoch_loss / batches
            print(f"Epoch {epoch:03d} | Average MAE Loss: {avg_loss:,.2f} DH")
            
    model.save_weights()
    print("NumPy NN Weights Saved.")

if __name__ == "__main__":
    train()
