# The AI will rewrite this file to improve accuracy
from prepare import get_clean_data
from sklearn.linear_model import LinearRegression

X_train, X_test, y_train, y_test = get_clean_data()
model = LinearRegression()
model.fit(X_train, y_train)
print(f"SCORE: {model.score(X_test, y_test)}")
