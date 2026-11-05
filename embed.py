from dotenv import load_dotenv
from langfuse.openai import OpenAI
from langfuse import observe, propagate_attributes
import os

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OCI_API_KEY_ONE"),
    base_url="https://inference.generativeai.us-phoenix-1.oci.oraclecloud.com/openai/v1",
    project=os.getenv("PROJECT_OCID")
)

response = client.embeddings.create(
    model="cohere.embed-multilingual-v3.0",
    input="Your text string goes here",
    encoding_format="float"
)

print(response)