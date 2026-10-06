# Project 1 – Cloud-Native Nutritional Insights: Step-by-Step Guide

Everything here runs in your **Ubuntu VM from Lab 1/2**. Work through the tasks in order — each one builds on the last.

> **Screenshot rule for the whole project:** the date and time must be visible in every screenshot. Easiest way: keep the Ubuntu top bar (clock) in the frame, **and** run `date` in the terminal right before each command you screenshot. The scripts also print timestamps and stamp them on the charts.

---

## 0. One-time setup

```bash
# Tools (most are already in the lab VM)
sudo apt update
sudo apt install -y python3-pip python3-venv git docker.io docker-compose-v2 nodejs npm
sudo usermod -aG docker $USER && newgrp docker      # run docker without sudo

# Get the project folder into your home dir, then:
cd ~/nutri
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Get the real dataset:** download `All_Diets.csv` from Kaggle (or Course Resources) and put it at `data/All_Diets.csv`. Check it:

```bash
head -3 data/All_Diets.csv
wc -l data/All_Diets.csv
```

### Project structure

```
nutri/
├── data_analysis.py            # Task 1
├── Dockerfile                  # Task 2
├── docker-compose.yml          # Task 2 step 5 + Task 3
├── lambda_function.py          # Task 3 (serverless function)
├── watcher.py                  # Task 3 step 3 (simulated event trigger)
├── Dockerfile.optimized        # Task 5 (multi-stage build)
├── .github/workflows/deploy.yml# Task 4
├── tests/test_analysis.py      # Task 4 "run tests"
├── requirements.txt
└── data/All_Diets.csv          # you add this
```

---

## Task 1 – Dataset Analysis & Insights (20 marks)

**1. Run the analysis**

```bash
date
python data_analysis.py
```

The script covers every bullet in the brief:

| Requirement | Function in `data_analysis.py` |
|---|---|
| Handle missing values | `clean_data()` – coerces numbers, fills NaN with the column mean, normalises `Paleo`/`paleo` |
| Average macros per diet | `average_macros()` |
| Top 5 protein recipes per diet | `top_protein_recipes()` |
| Diet with highest protein | `highest_protein_diet()` |
| Most common cuisine per diet | `most_common_cuisines()` |
| Protein:Carbs and Carbs:Fat ratios | `add_ratios()` (zero denominators → NaN, not infinity) |
| Bar chart, heatmap, scatter plot | `make_charts()` → `outputs/*.png` |

**Two things worth mentioning in your report (shows understanding):**
- The provided pseudocode `df.fillna(df.mean())` **crashes in pandas 2.x** because `mean()` can't run on text columns. We only take the mean of the numeric columns.
- The dataset has inconsistent casing (`Paleo` vs `paleo` in the sample table). Without lower-casing, the same diet is counted as two groups.

**2. Look at the charts:** `xdg-open outputs/bar_avg_macros.png` (also `heatmap_macros.png`, `scatter_top_protein.png`).

**Screenshots (with date/time):**
- [ ] VS Code showing `data_analysis.py`
- [ ] Terminal output: averages, top 5, highest-protein diet, common cuisines, ratios
- [ ] Each of the 3 charts (bar, heatmap, scatter)

---

## Task 2 – Dockerize (20 marks)

**1. Build**
```bash
date
docker build -t diet-analysis .
docker images | grep diet-analysis
```

**2. Run & verify it processes data**
```bash
date
docker run -it --rm -v "$PWD/outputs:/app/outputs" diet-analysis
ls -l outputs/          # charts were created by the container
```
(The `-v` mount lets you see the charts the container produced.)

**3. Push to Docker Hub** (create a free account at hub.docker.com first)
```bash
docker login
docker tag diet-analysis YOURUSERNAME/diet-analysis:latest
docker push YOURUSERNAME/diet-analysis:latest
```
Screenshot the terminal **and** the repo page on hub.docker.com.

**4. Simulated deployment with Docker Compose**
```bash
date
docker compose up --build
```
This starts three containers together: **azurite** (fake Blob Storage), **diet-analysis** (Task 1 batch job), and **serverless-function** (Task 3). Then:
```bash
docker compose ps -a
cat simulated_nosql/results.json | head -30
docker compose down
```

**Screenshots:**
- [ ] `docker build` success
- [ ] `docker run` output showing the analysis results
- [ ] `docker push` + Docker Hub page
- [ ] `docker compose up` logs with all services

---

## Task 3 – Serverless Processing with Azurite (20 marks)

**1. Start Azurite** (pick one, in a separate terminal)

```bash
# Option A – npm
sudo npm install -g azurite
azurite-blob --silent --skipApiVersionCheck --location ~/azurite-data

# Option B – Docker
docker run -p 10000:10000 mcr.microsoft.com/azure-storage/azurite \
  azurite-blob --blobHost 0.0.0.0 --skipApiVersionCheck --loose
```

> ⚠️ **Why `--skipApiVersionCheck`?** New versions of the `azure-storage-blob` Python SDK send an API version that Azurite may not know yet, giving: *"The API version … is not supported by Azurite"*. This flag fixes it. (We hit this while testing — worth a line in your report.)

You should see: `Azurite Blob service successfully listens on http://127.0.0.1:10000`

**2. Upload the CSV** — either way works:
- **Azure Storage Explorer** (the brief asks for this): install from Microsoft → *Connect* → *Local storage emulator* → Blob Containers → create `datasets` → Upload `All_Diets.csv`. **Screenshot this** — it's your proof the file is in Azurite.
- **Or via the script:** `python lambda_function.py --upload data/All_Diets.csv`

**3. Run the function**
```bash
date
python lambda_function.py
cat simulated_nosql/results.json | head -40
ls simulated_nosql/
```

What it does: connects to Azurite with the Blob SDK → downloads `All_Diets.csv` → cleans + calculates averages per diet → saves a NoSQL-style JSON **document** (one file per run plus `results.json` for the latest), like a Cosmos DB record.

**4. Simulate an event trigger (step 3 of the brief)**
```bash
# terminal 1
python watcher.py
# terminal 2
cp data/All_Diets.csv incoming/new_batch.csv
```
Terminal 1 shows `[EVENT ...] New file detected` → uploads to Azurite → runs the function automatically. This mimics an Azure **Blob Trigger**.

**Screenshots:**
- [ ] Azurite running
- [ ] Storage Explorer with `All_Diets.csv` in the `datasets` container
- [ ] Function output in terminal
- [ ] `results.json` contents
- [ ] watcher.py auto-triggering

**Explanation to write in the report (adapt in your own words):**
> Azurite emulates Azure Blob Storage locally on port 10000 using the same REST API as real Azure, so our code uses the official `azure-storage-blob` SDK unchanged — only the connection string differs (read from `AZURE_STORAGE_CONNECTION_STRING`). `lambda_function.py` follows the serverless pattern: a stateless `main(event)` handler that is invoked, reads input from blob storage, processes it, writes output to a NoSQL store, and returns a status. Because Azurite has no event triggers, `watcher.py` uses the watchdog library to watch a folder and invoke the function when a new CSV arrives, simulating an Azure Blob Trigger. Results are saved as JSON documents, simulating Cosmos DB.

---

## Task 4 – CI/CD with GitHub Actions (20 marks)

**1. Create the repo** on GitHub (e.g. `nutritional-insights`), add **all team members as collaborators** (Settings → Collaborators) — this matters for the contribution marks.

**2. Commit the real dataset** so the pipeline can use it (it's small enough), then push:
```bash
git init
git add .
git commit -m "Initial project: analysis, Docker, serverless function"
git branch -M main
git remote add origin https://github.com/YOURNAME/nutritional-insights.git
git push -u origin main
```

**3. Add Docker Hub secrets** (Repo → Settings → Secrets and variables → Actions → New repository secret):
- `DOCKERHUB_USERNAME` = your Docker Hub username
- `DOCKERHUB_TOKEN` = an access token (Docker Hub → Account settings → Personal access tokens)

**4. The pipeline** (`.github/workflows/deploy.yml`) runs on every push to `main`:

| Job | What it does | Brief requirement |
|---|---|---|
| `test` | flake8 lint + 6 pytest unit tests | "Run tests or checks" |
| `integration` | starts Azurite in CI, uploads CSV, runs the function | tests the serverless simulation |
| `build-and-deploy` | builds image, **runs the container** (simulated deploy), uploads charts as an artifact, pushes to Docker Hub | "Build", "Push", "Evidence of simulated deployment" |

**5. Trigger it:**
```bash
git add .
git commit -m "Setup CI/CD pipeline simulation"
git push origin main
```
Go to the **Actions** tab, watch the run turn green.

**Screenshots:**
- [ ] Actions run summary with all 3 jobs green + timestamp
- [ ] Expanded log of "Run unit tests" (6 passed)
- [ ] Expanded log of "Simulated deployment – run the container"
- [ ] The `analysis-outputs` artifact and the new tag on Docker Hub

Tip: show a deliberately failing test once (break something, push, screenshot the red ❌, fix it). It's a nice demonstration that the pipeline actually guards your code.

---

## Task 5 – Enhancement (5 marks)

Recommended picks: **Option 1 (multi-stage Docker)** and **Option 2 (cold start)** — both are already implemented, so you just measure and report.

**Measure Option 1:**
```bash
docker build -t diet-analysis:basic .
docker build -f Dockerfile.optimized -t diet-analysis:optimized .
docker images | grep diet-analysis          # compare SIZE column
time docker run --rm diet-analysis:optimized
```

**Measure Option 2:**
```bash
python -X importtime -c "import lambda_function" 2>&1 | tail -3
python -X importtime -c "import matplotlib.pyplot, seaborn" 2>&1 | tail -3
```

### Draft 1-page report (fill in YOUR measured numbers)

**Enhancement Report – Options Chosen: (1) Multi-stage Docker builds, (2) Reducing serverless cold-start latency**

**Research conducted.** We reviewed Docker's documentation on multi-stage builds and build caching best practices, and Microsoft's Azure Functions guidance on cold starts (keeping packages small, lazy loading, and reusing client connections across invocations).

**Improvement 1 – Multi-stage build (`Dockerfile.optimized`).** A builder stage compiles dependency wheels; the final stage starts from a fresh `python:3.11-slim` and installs only those wheels, so pip caches and build artifacts never reach the final image. We also copy only the files the app needs (not tests, docs, or `.git`, enforced by `.dockerignore`), install `requirements.txt` before copying code so the dependency layer is cached between builds, and run as a non-root user. Result: image size went from ___ MB to ___ MB.

**Improvement 2 – Cold-start reduction (`lambda_function.py`).** (a) *Lazy imports:* matplotlib and seaborn are imported only inside `make_charts()`, so the function, which never draws charts, no longer loads them. Import time dropped from ___ ms to ___ ms. (b) *Client reuse:* the `BlobServiceClient` is cached in a module-level variable, so warm invocations reuse the connection instead of rebuilding it. (c) *Pure processing function:* `build_results()` is separated from I/O, making it fast to test and reuse.

**Impact.** Smaller images mean faster pushes/pulls in CI and faster container startup at deployment, and lower registry storage cost. Faster cold starts mean lower latency on the first request after idle and less billed execution time on a consumption plan, since Azure Functions charges per execution time and memory.

---

## Video Presentation (10 marks)

Every member must appear on camera presenting their own part (record in MS Teams). Suggested split for a 4-person team, ~3 min each:

1. Intro + Task 1 (dataset, cleaning, charts)
2. Task 2 (Dockerfile walkthrough, build/run/push, Compose)
3. Task 3 (Azurite, Storage Explorer, function, watcher demo)
4. Task 4 + 5 (pipeline run live, image size comparison, wrap-up)

Make sure each person can explain *why* the code works, not just show it — that's what "confidently" in the rubric means.

---

## Contribution Report (5 marks) – template

| Member | Tasks & steps completed | Commits / PRs (count + examples) | Meetings attended | Hours |
|---|---|---|---|---|
| Name 1 | | | | |
| Name 2 | | | | |

Also include: **task distribution agreement** (who owns what, date agreed), **communication** (e.g. weekly Teams meeting Mondays, GitHub Issues for tasks, group chat daily), and a **meeting log** (date, attendees, decisions).

To get genuine GitHub evidence: each person works on a branch (`git checkout -b task3-azurite`), opens a pull request, and a teammate reviews and merges it. Screenshot the Insights → Contributors graph and the closed PRs list.

---

## Final submission checklist (zip everything)

- [ ] `data_analysis.py`
- [ ] `lambda_function.py`
- [ ] `Dockerfile`
- [ ] `.github/workflows/deploy.yml`
- [ ] PDF report: all screenshots with date/time, Task 3 explanation, 1-page Task 5 report
- [ ] Team video (every face visible)
- [ ] Contribution report
