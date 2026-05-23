import pandas as pd
import pickle
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.naive_bayes import GaussianNB
from sklearn.metrics import r2_score, accuracy_score

# =====================================================
# CROP YIELD MODEL
# Dataset Columns:
# State_Name,District_Name,Crop_Year,Season,
# Crop,Area,Production,cat_crop
# =====================================================

yield_data = pd.read_csv("datasets/crop_yield.csv")
yield_data.dropna(inplace=True)
yield_data.columns = yield_data.columns.str.strip()

# Clean categorical columns
yield_data['State_Name'] = yield_data['State_Name'].str.strip()
yield_data['Season'] = yield_data['Season'].str.strip()
yield_data['Crop'] = yield_data['Crop'].str.strip()

# Label Encoding
le_state = LabelEncoder()
le_season = LabelEncoder()
le_crop = LabelEncoder()

yield_data['State_Name'] = le_state.fit_transform(yield_data['State_Name'])
yield_data['Season'] = le_season.fit_transform(yield_data['Season'])
yield_data['Crop'] = le_crop.fit_transform(yield_data['Crop'])

# Features & Target
X_yield = yield_data[['State_Name', 'Season', 'Crop', 'Area']]
y_yield = yield_data['Production']

X_train, X_test, y_train, y_test = train_test_split(
    X_yield, y_yield, test_size=0.2, random_state=42
)

yield_model = ExtraTreesRegressor(n_estimators=300, random_state=42)
yield_model.fit(X_train, y_train)

print("Yield Model R2 Score:", r2_score(y_test, yield_model.predict(X_test)))

pickle.dump(yield_model, open("models/yield_model.pkl", "wb"))
pickle.dump((le_state, le_season, le_crop), open("models/yield_encoder.pkl", "wb"))


# =====================================================
# FERTILIZER MODEL
# Dataset Columns:
# Temparature,Humidity ,Moisture,Soil Type,
# Crop Type,Nitrogen,Potassium,Phosphorous,Fertilizer Name
# =====================================================

fert_data = pd.read_csv("datasets/fertilizer.csv")
fert_data.dropna(inplace=True)
fert_data.columns = fert_data.columns.str.strip()

# Fix column names with spaces
fert_data.rename(columns={
    "Humidity ": "Humidity"
}, inplace=True)

# Clean categorical columns
fert_data['Soil Type'] = fert_data['Soil Type'].str.strip()
fert_data['Crop Type'] = fert_data['Crop Type'].str.strip()
fert_data['Fertilizer Name'] = fert_data['Fertilizer Name'].str.strip()

# Label Encoding
le_soil = LabelEncoder()
le_crop2 = LabelEncoder()
le_fert = LabelEncoder()

fert_data['Soil Type'] = le_soil.fit_transform(fert_data['Soil Type'])
fert_data['Crop Type'] = le_crop2.fit_transform(fert_data['Crop Type'])
fert_data['Fertilizer Name'] = le_fert.fit_transform(fert_data['Fertilizer Name'])

X_fert = fert_data[['Temparature','Humidity','Moisture',
                    'Soil Type','Crop Type',
                    'Nitrogen','Potassium','Phosphorous']]

y_fert = fert_data['Fertilizer Name']

X_train_f, X_test_f, y_train_f, y_test_f = train_test_split(
    X_fert, y_fert, test_size=0.2, random_state=42
)

fert_model = GaussianNB()
fert_model.fit(X_train_f, y_train_f)

print("Fertilizer Model Accuracy:",
      accuracy_score(y_test_f, fert_model.predict(X_test_f)))

pickle.dump(fert_model, open("models/fert_model.pkl", "wb"))
pickle.dump((le_soil, le_crop2, le_fert), open("models/fert_encoder.pkl", "wb"))

print("Models Saved Successfully ✅")