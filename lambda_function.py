"""
Task 3 - Simulated serverless function (Azure Function style) using Azurite.

Flow:  All_Diets.csv in Azurite Blob Storage  ->  this function  ->  simulated_nosql/results.json

Usage:
    python lambda_function.py --upload data/All_Diets.csv   # upload, then process
    python lambda_function.py                               # process what is already in Azurite
"""
import argparse
import io
import json
import os
from datetime import datetime, timezone

import pandas as pd
from azure.storage.blob import BlobServiceClient

from data_analysis import clean_data, average_macros, top_protein_recipes, most_common_cuisines, add_ratios

# Azurite's PUBLIC, well-known development key (safe to commit - it only works on the local emulator).
AZURITE_CONN_STR = (
    "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;"
    "AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;"
    "BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
)
CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING", AZURITE_CONN_STR)
CONTAINER = os.getenv("BLOB_CONTAINER", "datasets")
BLOB_NAME = os.getenv("BLOB_NAME", "All_Diets.csv")
NOSQL_DIR = os.getenv("NOSQL_DIR", "simulated_nosql")

_blob_service = None  # cached client = reused on "warm" invocations


def get_blob_service() -> BlobServiceClient:
    global _blob_service
    if _blob_service is None:
        _blob_service = BlobServiceClient.from_connection_string(CONN_STR)
    return _blob_service


def upload_csv(local_path: str, container: str = CONTAINER, blob_name: str = BLOB_NAME) -> None:
    container_client = get_blob_service().get_container_client(container)
    if not container_client.exists():
        container_client.create_container()
        print(f"[INFO] Created container '{container}'")
    with open(local_path, "rb") as f:
        container_client.upload_blob(blob_name, f, overwrite=True)
    print(f"[INFO] Uploaded {local_path} -> {container}/{blob_name}")


def build_results(df: pd.DataFrame, source: str) -> dict:
    """Pure function: DataFrame -> NoSQL-style document. Easy to unit test."""
    df = add_ratios(clean_data(df))
    avg = average_macros(df)
    return {
        "id": f"run-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}",
        "source_blob": source,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": int(len(df)),
        "avg_macros_by_diet": avg.reset_index().to_dict(orient="records"),
        "highest_protein_diet": avg["Protein(g)"].idxmax(),
        "top5_protein_recipes": top_protein_recipes(df).to_dict(orient="records"),
        "most_common_cuisine_by_diet": most_common_cuisines(df).to_dict(orient="records"),
    }


def save_to_nosql(document: dict, out_dir: str = NOSQL_DIR) -> str:
    """Simulated NoSQL: one JSON 'document' per run + results.json (latest)."""
    os.makedirs(out_dir, exist_ok=True)
    for name in (f"{document['id']}.json", "results.json"):
        with open(os.path.join(out_dir, name), "w") as f:
            json.dump(document, f, indent=2, default=str)
    return os.path.join(out_dir, "results.json")


def process_nutritional_data_from_azurite(container: str = CONTAINER, blob_name: str = BLOB_NAME) -> str:
    blob_client = get_blob_service().get_blob_client(container=container, blob=blob_name)
    raw = blob_client.download_blob().readall()
    df = pd.read_csv(io.BytesIO(raw))
    print(f"[INFO] Downloaded {container}/{blob_name} ({len(raw):,} bytes, {len(df):,} rows) from Azurite")

    doc = build_results(df, f"{container}/{blob_name}")
    path = save_to_nosql(doc)
    print(f"[INFO] Highest-protein diet: {doc['highest_protein_diet']}")
    print(json.dumps(doc["avg_macros_by_diet"], indent=2))
    return f"Data processed and stored successfully in {path}"


def main(event: dict | None = None) -> dict:
    """Entry point shaped like a cloud function handler (event in, response out)."""
    event = event or {}
    started = datetime.now()
    print(f"[TRIGGER] Function invoked at {started:%Y-%m-%d %H:%M:%S}  event={event}")
    msg = process_nutritional_data_from_azurite(event.get("container", CONTAINER), event.get("blob", BLOB_NAME))
    elapsed = (datetime.now() - started).total_seconds()
    print(f"[DONE] {msg}  (took {elapsed:.2f}s)")
    return {"status": 200, "message": msg, "duration_s": elapsed}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--upload", help="local CSV to upload to Azurite before processing")
    args = parser.parse_args()
    if args.upload:
        upload_csv(args.upload)
    main({"container": CONTAINER, "blob": BLOB_NAME})
