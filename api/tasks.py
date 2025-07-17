from django.conf import settings
from django.core.files.base import ContentFile
from .models import TattooDesign
import requests
import time
import os

HF_API_TOKEN = os.environ.get("HF_API_TOKEN")
API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-schnell"

def generate_tattoo_from_prompt(design_id, final_prompt):
    """
    Background task to generate a tattoo image asynchronously.
    """
    print(f"--- [WORKER LOG] Starting task for design ID: {design_id} ---")
    
    try:
        # --- 1. Log the Environment Variables the Worker Sees ---
        print("[WORKER LOG] Verifying environment variables...")
        
        # We use os.environ.get() here because settings might cache old values.
        # This reads the live environment variable from the container.
        account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        access_key = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
        secret_key = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
        bucket_name = os.environ.get('CLOUDFLARE_BUCKET_NAME')
        public_domain = os.environ.get('CLOUDFLARE_PUBLIC_DOMAIN')

        print(f"[WORKER LOG]   ACCOUNT_ID: {account_id}")
        print(f"[WORK_LOG]   ACCESS_KEY_ID: {'******' if access_key else 'Not Set'}") # Don't log the full key
        print(f"[WORK_LOG]   SECRET_ACCESS_KEY: {'******' if secret_key else 'Not Set'}") # Don't log the secret
        print(f"[WORKER LOG]   BUCKET_NAME: {bucket_name}")
        print(f"[WORKER LOG]   PUBLIC_DOMAIN: {public_domain}")

        if not all([account_id, access_key, secret_key, bucket_name, public_domain]):
            print("[WORKER LOG] 🔴 ERROR: One or more Cloudflare variables are missing in the worker environment!")
            # Mark the task as failed
            design = TattooDesign.objects.get(id=design_id)
            design.status = 'failed'
            design.save()
            return # Stop execution here

        print("[WORKER LOG] ✅ All variables seem to be present.")

        # --- The rest of your task logic ---
        design = TattooDesign.objects.get(id=design_id)
        start_time = time.time()
        
        print("[WORKER LOG] Calling Hugging Face API...")
        headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": final_prompt})
        print(f"[WORKER LOG] Hugging Face API responded with status: {response.status_code}")

        if response.status_code == 200:
            image_bytes = response.content
            print(f"[WORKER LOG] Received {len(image_bytes)} bytes from AI model.")
            print("[WORKER LOG] Attempting to save image to R2 via django-storages...")
            
            # This is the critical line where the upload happens
            design.generated_image.save(f'{design_id}.png', ContentFile(image_bytes), save=False)
            
            print("[WORKER LOG] ✅ design.generated_image.save() command executed without crashing.")
            design.status = 'completed'
        else:
            print(f"[WORKER LOG] 🔴 AI Model failed. Status: {response.status_code}, Text: {response.text}")
            design.status = 'failed'

        end_time = time.time()
        design.processing_time = end_time - start_time
        design.ai_model_used = API_URL.split('/')[-1]
        
        print(f"[WORKER LOG] Saving final design status to database: '{design.status}'")
        design.save()
        print(f"--- [WORKER LOG] Task for design ID {design_id} finished. ---")

    except Exception as e:
        print(f"[WORKER LOG] 🔴 An unexpected exception occurred in the task: {e}")
        # Try to mark the task as failed if an exception happens
        try:
            design_fail = TattooDesign.objects.get(id=design_id)
            design_fail.status = 'failed'
            design_fail.save()
        except TattooDesign.DoesNotExist:
            pass # The design was not even created, nothing to do.