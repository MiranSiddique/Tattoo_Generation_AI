import boto3
from botocore.client import Config
from botocore.exceptions import ClientError
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
    Background task that now MANUALLY handles the upload to Cloudflare R2,
    bypassing django-storages for the upload step.
    """
    print(f"--- [WORKER LOG] Starting task for design ID: {design_id} ---")

    try:
        design = TattooDesign.objects.get(id=design_id)
        
        print("[WORKER LOG] Calling Hugging Face API...")
        headers = {"Authorization": f"Bearer {settings.HF_API_TOKEN}"}
        response = requests.post(API_URL, headers=headers, json={"inputs": final_prompt})
        print(f"[WORKER LOG] Hugging Face API responded with status: {response.status_code}")

        if response.status_code != 200:
            print(f"[WORKER LOG] 🔴 AI Model failed. Status: {response.status_code}, Text: {response.text}")
            design.status = 'failed'
            design.save()
            return

        image_bytes = response.content
        print(f"[WORKER LOG] Received {len(image_bytes)} bytes from AI model.")

        # --- MANUAL R2 UPLOAD LOGIC STARTS HERE ---
        print("[WORKER LOG] Starting manual upload process to R2...")

        # 1. Get credentials directly from the environment
        account_id = os.environ.get('CLOUDFLARE_ACCOUNT_ID')
        access_key_id = os.environ.get('CLOUDFLARE_ACCESS_KEY_ID')
        secret_access_key = os.environ.get('CLOUDFLARE_SECRET_ACCESS_KEY')
        bucket_name = os.environ.get('CLOUDFLARE_BUCKET_NAME')

        if not all([account_id, access_key_id, secret_access_key, bucket_name]):
            raise Exception("Cloudflare R2 credentials are missing in the environment.")

        # 2. Initialize the boto3 client
        s3_client = boto3.client(
            service_name="s3",
            endpoint_url=f"https://{account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            config=Config(signature_version="s3v4"),
            region_name="auto",
        )
        print("[WORKER LOG]   boto3 client initialized.")

        # 3. Define the object name (the full path in the bucket)
        object_name = f"generated_tattoos/{design_id}.png"
        
        # 4. Upload the image bytes directly from memory
        try:
            # We use `upload_fileobj` because we have bytes in memory, not a local file
            from io import BytesIO
            s3_client.upload_fileobj(
                Fileobj=BytesIO(image_bytes),
                Bucket=bucket_name,
                Key=object_name,
                ExtraArgs={'ContentType': 'image/png'} # Important to set the content type
            )
            print(f"[WORKER LOG] ✅ Successfully uploaded to R2 as '{object_name}'.")

            # 5. Update the Django model field MANUALLY
            # We are not using .save() on the field, we are just setting the text path.
            design.generated_image.name = object_name
            design.status = 'completed'

        except ClientError as e:
            print(f"[WORKER LOG] 🔴 R2 UPLOAD FAILED with ClientError: {e}")
            design.status = 'failed'

        # --- MANUAL R2 UPLOAD LOGIC ENDS HERE ---

        # Save the final state of the design object to the database
        print(f"[WORKER LOG] Saving final design status to database: '{design.status}'")
        design.save()
        print(f"--- [WORKER LOG] Task for design ID {design_id} finished. ---")

    except Exception as e:
        print(f"[WORKER LOG] 🔴 An unexpected exception occurred in the task: {e}")
        try:
            design_fail = TattooDesign.objects.get(id=design_id)
            design_fail.status = 'failed'
            design_fail.save()
        except TattooDesign.DoesNotExist:
            pass