"""
grant_tracker_dag.py
Place this file in your Airflow dags/ folder. Assumes the rest of the
pipeline (config.py, scraper.py, extract.py, storage.py, progress.py,
process.py, daily_scrape.py) is importable — copy them into the same
dags/ folder, or add their location to PYTHONPATH.

Runs once daily, scraping the previous day's posts.
"""

import sys
import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

sys.path.append(os.path.dirname(__file__))

from daily_scrape import run_daily_scrape

default_args = {
    "owner": "moussaab",
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}


def task_daily_scrape(**kwargs):
    run_daily_scrape()


with DAG(
    dag_id="grant_announcement_daily_scrape",
    schedule="@daily",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["grant-tracker", "facebook"],
) as dag:

    daily_scrape_task = PythonOperator(
        task_id="daily_scrape",
        python_callable=task_daily_scrape,
    )
