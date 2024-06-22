import pandas as pd
import mysql.connector

# MySQL connection details
username = 'root'
password = 'teton123'
host = 'localhost'
database = 'asthma_db'

# Create a MySQL connection
conn = mysql.connector.connect(
    host=host,
    user=username,
    password=password,
    database=database
)

# Function to handle outliers using IQR method
def handle_outliers(df, columns):
    for column in columns:
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        df[column] = df[column].apply(lambda x: lower_bound if x < lower_bound else upper_bound if x > upper_bound else x)
    return df

# Load the dataset
file_path = 'C:/dataset/asthma_disease_data.csv'
asthma_data = pd.read_csv(file_path)

# List of numerical columns to check for outliers
numerical_columns = asthma_data.select_dtypes(include=['float64', 'int64']).columns

# Handle outliers in numerical columns
asthma_data_cleaned = handle_outliers(asthma_data, numerical_columns)

# Drop the 'DoctorInCharge' column as it has only one unique value
asthma_data_cleaned.drop(columns=['DoctorInCharge'], inplace=True)

# Ensure consistency in categorical variables (if needed)
# Example: Replace missing values or standardize categories
categorical_columns = asthma_data_cleaned.select_dtypes(include=['object', 'int64']).columns
for column in categorical_columns:
    asthma_data_cleaned[column] = asthma_data_cleaned[column].fillna(asthma_data_cleaned[column].mode()[0])

# Insert cleaned data into MySQL table
cursor = conn.cursor()

# Create table if it does not exist
create_table_query = """
CREATE TABLE IF NOT EXISTS asthma_cleaned_data (
    PatientID INT,
    Age INT,
    Gender INT,
    Ethnicity INT,
    EducationLevel INT,
    BMI FLOAT,
    Smoking INT,
    PhysicalActivity FLOAT,
    DietQuality FLOAT,
    SleepQuality FLOAT,
    PollutionExposure FLOAT,
    PollenExposure FLOAT,
    DustExposure FLOAT,
    PetAllergy INT,
    FamilyHistoryAsthma INT,
    HistoryOfAllergies INT,
    Eczema INT,
    HayFever INT,
    GastroesophagealReflux INT,
    LungFunctionFEV1 FLOAT,
    LungFunctionFVC FLOAT,
    Wheezing INT,
    ShortnessOfBreath INT,
    ChestTightness INT,
    Coughing INT,
    NighttimeSymptoms INT,
    ExerciseInduced INT,
    Diagnosis INT
);
"""
cursor.execute(create_table_query)

# Insert cleaned data
insert_query = """
INSERT INTO asthma_cleaned_data (
    PatientID, Age, Gender, Ethnicity, EducationLevel, BMI, Smoking, PhysicalActivity, DietQuality, SleepQuality,
    PollutionExposure, PollenExposure, DustExposure, PetAllergy, FamilyHistoryAsthma, HistoryOfAllergies, Eczema,
    HayFever, GastroesophagealReflux, LungFunctionFEV1, LungFunctionFVC, Wheezing, ShortnessOfBreath, ChestTightness,
    Coughing, NighttimeSymptoms, ExerciseInduced, Diagnosis
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

for i, row in asthma_data_cleaned.iterrows():
    cursor.execute(insert_query, tuple(row))

conn.commit()
cursor.close()
conn.close()

print(f"Data successfully inserted into asthma_cleaned_data table in {database} database.")
