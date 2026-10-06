# Cloud-Native Nutritional Insights

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
