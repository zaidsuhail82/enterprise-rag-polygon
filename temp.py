from google import genai
from src.utils.config import settings

client = genai.Client(api_key=settings.gemini_api_key)

models = client.models.list()

for m in models:
    print(m.name)
