import requests
import os

# Create a dummy file to summarize
with open("test.text", "w") as f:
    f.write("This is a test sentence for the summarization API. The goal of this test is to ensure that the backend is correctly calling the summarization script and returning the result. The summarization script itself is a black box for the purposes of this test; we are only concerned with the integration between the frontend, backend, and the script.")

# Read the content of the file
with open("test.text", "r") as f:
    text_to_summarize = f.read()

# Make the request to the backend
response = requests.post("http://localhost:5000/api/summarize", json={"text": text_to_summarize})

# Print the response
print(response.json())

# Clean up the dummy file
os.remove("test.text")
