import pandas as pd
import os

# On lit un de tes vrais fichiers Parquet
df = pd.read_parquet('data/raw/Tanger/2024.parquet')

# On garde seulement les 500 premières lignes (environ 20 jours de données)
df_sample = df.head(500)

# On crée le dossier de test et on sauvegarde l'échantillon
os.makedirs('tests/data/Tanger', exist_ok=True)
df_sample.to_parquet('tests/data/Tanger/2024.parquet')

print("✅ Échantillon réel créé : tests/data/Tanger/2024.parquet")