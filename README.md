# Cloud-Native Nutritional Insights

![CI/CD](https://github.com/Jayraj-sinh/nutritional-insights/actions/workflows/deploy.yml/badge.svg)

Analyses `All_Diets.csv` (protein/carbs/fat by diet type and cuisine) with Pandas, containerised with Docker, processed by a simulated Azure Function reading from Azurite Blob Storage, and deployed through a GitHub Actions CI/CD pipeline.

```bash
pip install -r requirements.txt
python data_analysis.py                              # Task 1
docker build -t diet-analysis . && docker run --rm diet-analysis   # Task 2
docker compose up --build                            # full simulated stack
python lambda_function.py --upload data/All_Diets.csv  # Task 3 (Azurite running)
pytest tests/                                        # tests
```

See **GUIDE.md** for the full walkthrough.

## Docker image
Published on Docker Hub: https://hub.docker.com/r/jayrajsinhgohil/diet-analysis

    docker pull jayrajsinhgohil/diet-analysis:latest
    docker run --rm jayrajsinhgohil/diet-analysis

## Serverless function with Azurite (Task 3)
1. Start Azurite: `docker run --rm -p 10000:10000 -v ~/azurite-data:/data mcr.microsoft.com/azure-storage/azurite azurite-blob --blobHost 0.0.0.0 --location /data --skipApiVersionCheck --loose`
2. Upload All_Diets.csv to the `datasets` container (Azure Storage Explorer or `python lambda_function.py --upload data/All_Diets.csv`)
3. Run the function: `python lambda_function.py` → results in `simulated_nosql/`
4. Simulated blob trigger: `python watcher.py`, then copy a CSV into `incoming/`
