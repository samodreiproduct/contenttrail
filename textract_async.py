
---

### 🧾 5. `textract_async.py`
Here’s the improved version that automatically loads AWS credentials and settings from `.env`:

```python
import os
import time
import json
import boto3
from dotenv import load_dotenv
from collections import defaultdict

# Load environment variables
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
S3_BUCKET = os.getenv("S3_BUCKET")

textract = boto3.client(
    "textract",
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

def start_textract(bucket, key):
    response = textract.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
        FeatureTypes=["TABLES", "FORMS"]
    )
    job_id = response["JobId"]
    print(f"Started Textract job: {job_id}")
    return job_id

def wait_for_job(job_id):
    while True:
        response = textract.get_document_analysis(JobId=job_id)
        status = response["JobStatus"]
        print(f"Job {job_id} status: {status}")
        if status in ["SUCCEEDED", "FAILED"]:
            return status
        time.sleep(5)

def get_all_results(job_id):
    results = []
    next_token = None
    while True:
        if next_token:
            response = textract.get_document_analysis(JobId=job_id, NextToken=next_token)
        else:
            response = textract.get_document_analysis(JobId=job_id)
        results.extend(response["Blocks"])
        next_token = response.get("NextToken")
        if not next_token:
            break
    return results

def extract_text(blocks):
    pages = defaultdict(list)
    for block in blocks:
        if block["BlockType"] == "LINE":
            pages[block["Page"]].append(block["Text"])
    return {p: "\n".join(lines) for p, lines in pages.items()}

def analyze_pdf(key):
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    job_id = start_textract(S3_BUCKET, key)
    if wait_for_job(job_id) != "SUCCEEDED":
        print("Textract job failed.")
        return

    blocks = get_all_results(job_id)
    text_data = extract_text(blocks)
    
    raw_path = os.path.join(output_dir, f"{os.path.basename(key)}_raw.json")
    parsed_path = os.path.join(output_dir, f"{os.path.basename(key)}_parsed.json")

    with open(raw_path, "w") as f:
        json.dump(blocks, f, indent=2)
    with open(parsed_path, "w") as f:
        json.dump(text_data, f, indent=2)

    print(f"Saved results to {output_dir}/")

if __name__ == "__main__":
    pdf_key = input("Enter S3 PDF path (e.g., documents/sample.pdf): ").strip()
    analyze_pdf(pdf_key)
