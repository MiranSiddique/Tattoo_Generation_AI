# api/tasks.py
from background_task import background
from django.conf import settings
from django.core.files.base import ContentFile
from .models import TattooDesign
import requests
import time
import os

# Store your Hugging Face API Token securely (e.g., in environment variables)
HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

def generate_tattoo_from_prompt(design_id, final_prompt):
    """
    A plain Python function to generate a tattoo image.
    This will be run in a separate thread by the view.
    """
    try:
        design = TattooDesign.objects.get(id=design_id)
        start_time = time.time()

        # Securely use the token from your settings (this part is the same)
        headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}

        # --- Call the AI Model (this part is the same) ---
        response = requests.post(API_URL, headers=headers, json={"inputs": final_prompt})

        if response.status_code == 200:
            image_bytes = response.content
            design.generated_image.save(f'{design_id}.png', ContentFile(image_bytes), save=False)
            design.status = 'completed'
        else:
            design.status = 'failed'
            print(f"AI Model Error: {response.text}")

        end_time = time.time()
        design.processing_time = end_time - start_time
        design.ai_model_used = API_URL.split('/')[-1]
        design.save()

    except TattooDesign.DoesNotExist:
        pass
    except Exception as e:
        if 'design' in locals():
            design.status = 'failed'
            design.save()
        print(f"An error occurred in background thread: {e}")