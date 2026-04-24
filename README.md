# Apache Airflow Scheduler — Systems Engineering Analysis

![Airflow](https://img.shields.io/badge/Apache%20Airflow-2.10.3-017CEE?logo=apacheairflow)
![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![Ubuntu](https://img.shields.io/badge/Ubuntu-24.04-E95420?logo=ubuntu)

## 📌 Project Overview

A deep-dive systems engineering analysis of the **Apache Airflow Scheduler**. We reverse-engineered the scheduler by reading actual source code, tracing the complete execution path, identifying key design decisions, and running three controlled experiments to measure real-world behavior.

> **Key Finding:** A structural 63-second scheduling lag exists as a direct, quantifiable consequence of the polling architecture — not a bug, but a deliberate tradeoff between simplicity and latency.

---

## 👥 Team

| Name | Role |
|------|------|
| Prisha Khalasi | Source code analysis, Experiments 1 & 2 |
| Aman Choudhary | Architecture tracing, Experiment 3, Report |

---

## 🔍 System Studied

| Property | Value |
|----------|-------|
| System | Apache Airflow Scheduler |
| Version | v2.10.3 |
| Source Code | https://github.com/apache/airflow/tree/v2-10-stable |
| Environment | Ubuntu 24.04, Python 3.11, SQLite |

---

## 📁 Repository Structure

```
airflow-scheduler-project/
├── README.md                             
├── dags/
│   ├── latency_experiment.py          ← Experiment 1 DAG
│   ├── zombie_experiment.py           ← Experiment 2 DAG
│   └── generated/dag_0.py            ← Experiment 3 sample
├── experiments/
│   ├── experiment1_latency_results.txt
│   ├── experiment2_zombie_results.txt
│   └── experiment3_parse_results.txt
└── screenshots/                       ← All 19 evidence screenshots
```

---

## 🗺️ Execution Path Traced

```
scheduler_job_runner.py:1057  _run_scheduler_loop()
        ↓
scheduler_job_runner.py:1211  _do_scheduling()
        ↓
scheduler_job_runner.py:1626  _schedule_dag_run()
        ↓
dagrun.py:760                 dag_run.update_state()
        ↓
dagrun.py:1026                _get_ready_tis()
        ↓
taskinstance.py               are_dependencies_met()
        ↓
base_executor.py              executor.queue_task_instance()
        ↓
local_task_job_runner.py:266  return code → SUCCESS / FAILED
```

---

## 🔬 Experiments

### Experiment 1 — Scheduling Latency
- **Hypothesis:** Lag ≈ 2 × parse_interval + executor overhead (~61s)
- **Result:** Mean lag = 63.1s, σ = 0.33s — structurally deterministic
- **Key insight:** Changing heartbeat from 5s → 30s had zero effect — parse interval dominates
- **Code:** `dags/latency_experiment.py`

### Experiment 2 — Zombie Task Detection
- **Hypothesis:** SIGKILL triggers fast path at `local_task_job_runner.py:266`
- **Result:** Crash detected in 535ms, return code -9 confirmed
- **Key insight:** Fast path (535ms) vs slow path (300s) — 580x difference
- **Code:** `dags/zombie_experiment.py`

### Experiment 3 — DAG Scale Stress Test
- **Hypothesis:** 51 DAGs will degrade parse time due to single-threaded processor
- **Result:** +297% parse time increase, 245s starvation gap
- **Key insight:** SQLite forces parallelism=1 — confirmed at `manager.py:406`
- **Code:** `dags/generated/dag_0.py`

---

## 🏗️ Key Design Decisions

| Decision | Code Location | Tradeoff |
|----------|--------------|----------|
| Polling loop (not event-driven) | `scheduler_job_runner.py:1057` | Simple & reliable vs ~63s latency |
| DB as single source of truth | `dagrun.py:760` | Crash recovery vs DB bottleneck |
| Pluggable executor abstraction | `base_executor.py` | Flexibility vs opacity |
| Two-tier zombie detection | `local_task_job_runner.py:266` | 535ms fast vs 300s slow path |

---

## 🧠 Concept Mapping

| CS Concept | Where in Airflow |
|------------|-----------------|
| DAG / Topological execution | `dagrun.py`, `dag.py` |
| Fault tolerance | Retries, zombie detection, DB recovery |
| B-tree storage indexes | TaskInstance queries in `dagrun.py:1026` |
| Partitioning | Pools, `max_active_tasks`, Celery workers |
| Streaming ingestion | `dag_processing/manager.py` continuous loop |
| Concurrency control | SELECT FOR UPDATE locking in scheduler |

---

## 📊 Results Summary

| Metric | Value |
|--------|-------|
| Scheduling lag mean | 63.1 seconds |
| Scheduling lag σ | 0.33 seconds |
| Cold start lag | 108.02 seconds |
| Zombie detection fast path | 535 milliseconds |
| Zombie detection slow path | up to 300 seconds |
| Parse time increase (51 DAGs) | +297% |
| Peak starvation gap | 245 seconds |

---

## ⚙️ How to Reproduce

```bash
# Install
conda create -n airflow-env python=3.11 -y
conda activate airflow-env
pip install "apache-airflow==2.10.3" \
  --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.3/constraints-3.11.txt"

# Initialize
export AIRFLOW_HOME=~/airflow
airflow db init
airflow users create --username admin --password admin \
  --firstname Admin --lastname User --role Admin \
  --email admin@example.com

# Start
airflow webserver --port 8080 &
airflow scheduler &

# Run experiments
cp dags/latency_experiment.py $AIRFLOW_HOME/dags/
cp dags/zombie_experiment.py $AIRFLOW_HOME/dags/
airflow dags trigger zombie_experiment
```

---

## 📚 References

- [Airflow Source Code](https://github.com/apache/airflow)
- [scheduler_job_runner.py](https://github.com/apache/airflow/blob/v2-10-stable/airflow/jobs/scheduler_job_runner.py)
- [local_task_job_runner.py](https://github.com/apache/airflow/blob/v2-10-stable/airflow/jobs/local_task_job_runner.py)
- [dagrun.py](https://github.com/apache/airflow/blob/v2-10-stable/airflow/models/dagrun.py)
