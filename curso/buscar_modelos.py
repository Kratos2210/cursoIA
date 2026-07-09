import os
import requests
from dotenv import load_dotenv

# Cargamos tu clave
load_dotenv()
api_key = os.environ.get("GOOGLE_API_KEY")

# Le preguntamos directamente a la API de Google
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
print("Consultando a los servidores de Google...\n")

respuesta = requests.get(url).json()

print("Modelos de Embedding exactos que tu cuenta puede usar:")
print("-" * 50)

# Filtramos solo los que sirven para convertir texto a vectores
modelos_encontrados = False
for modelo in respuesta.get("models", []):
    if "embedContent" in modelo.get("supportedGenerationMethods", []):
        print(f"Nombre exacto a usar: {modelo.get('name')}")
        modelos_encontrados = True

if not modelos_encontrados:
    print("No se encontraron modelos de embedding habilitados para tu API Key.")