# Sends list of batch files to SGLang server for processing
import argparse
import datetime
import json
import os
import time
import requests
from tqdm import tqdm
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


SGLANG_ENDPOINT = "http://localhost:30000/v1/chat/completions"
UPLOAD_STATE_FILENAME = "SENDSILVER_DATA"
REQUEST_TIMEOUT = 30  # Seconds

def process_sglang_request(messages):
    """Send request to SGLang server"""
    try:
        response = requests.post(
            SGLANG_ENDPOINT,
            json={
                "model": "default",
                "messages": messages,
                "temperature": 0.7
            },
            timeout=REQUEST_TIMEOUT
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Request failed: {str(e)}")
        return None

def _json_datetime_decoder(obj):
    if "last_checked" in obj:
        try:
            obj["last_checked"] = datetime.datetime.fromisoformat(obj["last_checked"])
        except (TypeError, ValueError):
            pass
    return obj

def _json_datetime_encoder(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

def get_state(folder_path: str) -> dict:
    state_file = os.path.join(folder_path, UPLOAD_STATE_FILENAME)
    try:
        with open(state_file, "r") as f:
            return json.load(f, object_hook=_json_datetime_decoder)
    except (json.JSONDecodeError, FileNotFoundError):
        jsonl_files = [f for f in os.listdir(folder_path) if f.endswith(".jsonl")]
        if not jsonl_files:
            raise Exception("No JSONL files found to process")

        state = {
            f: {
                "filename": f,
                "state": "init",
                "last_checked": datetime.datetime.now(),
                "processed_lines": 0,
                "total_lines": sum(1 for _ in open(os.path.join(folder_path, f)))
            }
            for f in jsonl_files
        }

        with open(state_file, "w") as f:
            json.dump(state, f, default=_json_datetime_encoder)
        return state

def update_state(folder_path: str, filename: str, **kwargs):
    all_state = get_state(folder_path)
    for kwarg_name, kwarg_value in kwargs.items():
        all_state[filename][kwarg_name] = kwarg_value

    all_state[filename]["last_checked"] = datetime.datetime.now()

    state_file = os.path.join(folder_path, UPLOAD_STATE_FILENAME)
    temp_file = state_file + ".tmp"

    with open(temp_file, "w") as f:
        json.dump(all_state, f, default=_json_datetime_encoder)
        f.flush()
        os.fsync(f.fileno())

    os.replace(temp_file, state_file)
    return all_state

def get_next_file(folder_path):
    state = get_state(folder_path)
    for filename, data in state.items():
        if data["state"] == "init":
            return data
    return None

def process_file(folder_path, file_info):
    input_path = os.path.join(folder_path, file_info["filename"])
    output_folder = f"{folder_path.rstrip('/')}_done"
    os.makedirs(output_folder, exist_ok=True)
    output_path = os.path.join(output_folder, file_info["filename"])

    try:
        update_state(folder_path, file_info["filename"], state="processing")
        
        with open(input_path, "r") as infile, open(output_path, "w") as outfile:
            for line in tqdm(infile, total=file_info["total_lines"], desc=file_info["filename"]):
                try:
                    data = json.loads(line)
                    result = process_sglang_request(data["messages"])
                    if result:
                        outfile.write(json.dumps(result) + "\n")
                        update_state(folder_path, file_info["filename"], 
                                   processed_lines=file_info["processed_lines"] + 1)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON in line: {line.strip()}")
                except KeyError:
                    logger.error(f"Missing 'messages' field in line: {line.strip()}")

        update_state(folder_path, file_info["filename"], state="completed")
    except Exception as e:
        logger.error(f"Failed to process {file_info['filename']}: {str(e)}")
        update_state(folder_path, file_info["filename"], state="errored_out")

def process_folder(folder_path: str):
    logger.info(f"Starting processing of folder: {folder_path}")
    
    while True:
        next_file = get_next_file(folder_path)
        if not next_file:
            logger.info("All files processed")
            break

        logger.info(f"Processing file: {next_file['filename']}")
        process_file(folder_path, next_file)
        time.sleep(1)  # Brief pause between files

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process JSONL files using SGLang server")
    parser.add_argument("folder", type=str, help="Path to folder containing JSONL files")
    args = parser.parse_args()

    try:
        process_folder(args.folder)
    except KeyboardInterrupt:
        logger.info("Processing interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}")