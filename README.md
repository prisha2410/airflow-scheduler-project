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
├── dags/                          ← All Airflow DAG files
│   ├── latency_experiment.py      ← Experiment 1: scheduling lag measurement
│   ├── zombie_experiment.py       ← Experiment 2: crash detection (SIGKILL)
│   ├── test_timeout_double.py     ← Timeout behavior test
│   └── generated/                 ← Experiment 3: scale test
│       ├── dag_0.py
│       ├── dag_1.py
│       └── ... dag_49.py          ← 51 DAGs total
├── results/                       ← Raw experiment output
│   ├── experiment1_results.txt    ← Latency measurements (13 runs)
│   ├── experiment2_results.txt    ← Zombie crash log evidence
│   └── experiment3_results.txt    ← Parse time degradation data
└── logs/                          ← Full Airflow execution logs
    ├── dag_id=latency_experiment/ ← Experiment 1 task logs
    ├── dag_id=zombie_experiment/  ← Experiment 2 crash logs
    ├── dag_id=test_timeout_double/← Timeout experiment logs
    └── scheduler/                 ← Scheduler parse-time logs (Experiment 3)
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
- **DAG:** `dags/latency_experiment.py`
- **Hypothesis:** Lag ≈ 2 × parse_interval + executor overhead (~61s)
- **Result:** Mean lag = 63.1s, σ = 0.33s — structurally deterministic
- **Key insight:** Changing heartbeat 5s → 30s had zero effect. Real bottleneck is `min_file_process_interval=30s` + SQLite single-thread (`manager.py:406`)
- **Raw data:** `results/experiment1_results.txt`

### Experiment 2 — Zombie Task Detection
- **DAG:** `dags/zombie_experiment.py`
- **Hypothesis:** SIGKILL triggers fast path at `local_task_job_runner.py:266`
- **Result:** Crash detected in 535ms, return code -9 confirmed
- **Key insight:** Fast path (535ms) vs slow path (300s) — 580x difference
- **Raw data:** `results/experiment2_results.txt`

### Experiment 3 — DAG Scale Stress Test
- **DAGs:** `dags/generated/dag_0.py` ... `dag_49.py`
- **Hypothesis:** 51 DAGs will degrade parse time (single-threaded processor)
- **Result:** +297% parse time increase, 245s starvation gap
- **Key insight:** SQLite forces parallelism=1 — confirmed at `manager.py:406`
- **Raw data:** `results/experiment3_results.txt`

---

## 🏗️ Key Design Decisions

| Decision | Code Location | Problem Solved | Tradeoff |
|----------|--------------|----------------|----------|
| Polling loop (not event-driven) | `scheduler_job_runner.py:1057` | Self-healing, no event infrastructure needed | ~63s structural latency |
| DB as single source of truth | `dagrun.py:760` | All components share state, crash recovery | DB is bottleneck at scale |
| Pluggable executor abstraction | `base_executor.py` | Same scheduler works with Local/Celery/K8s | Scheduler can't inspect worker health directly |
| Two-tier zombie detection | `local_task_job_runner.py:266` | Handles both common and catastrophic failures | 535ms fast vs 300s slow — 580x difference |

---

## 🧠 Concept Mapping

| CS Concept | Where in Airflow | Code Reference |
|------------|-----------------|----------------|
| DAG / Topological execution | Tasks are nodes, dependencies are edges | `dagrun.py`, `dag.py` |
| Fault tolerance | Retries, zombie detection, DB-based recovery | `scheduler_job_runner.py`, `taskinstance.py` |
| B-tree storage indexes | B-tree indexes on task_id, dag_id, state | `dagrun.py:1026` |
| Partitioning | Pools and max_active_tasks partition resources | executor config, pools |
| Streaming ingestion | DAG file processor — continuous parsing loop | `dag_processing/manager.py` |
| Concurrency control | SELECT FOR UPDATE prevents double-scheduling | `scheduler_job_runner.py` |

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

## 🔥 Failure Analysis

### What happens when data size increases significantly?
Adding 51 DAGs caused +297% parse time increase and a 245-second starvation gap. The `get_task_instances()` query at `dagrun.py:1026` also degrades as TaskInstance rows accumulate into millions.

### What happens under skew?
A single slow DAG file blocks the entire parse queue. The 245-second spike in Experiment 3 shows this pattern. In task execution, a slow task holds a pool slot and blocks downstream tasks.

### What happens if a component fails?

| Failed Component | Consequence |
|-----------------|-------------|
| Scheduler | No new tasks scheduled. On restart, reads DB and resumes — no lost work. |
| Worker (SIGKILL) | Fast path at line 266 → FAILED in 535ms |
| Worker node (full crash) | Zombie sweep → FAILED after up to 300 seconds |
| Metadata DB | Everything stops. No scheduling, no state updates. |

### What assumptions does the system rely on?
- DAG files are idempotent — parsed every ~30s
- Metadata DB is always available — no offline fallback
- Tasks are independent between DagRuns
- System clocks are synchronized across workers

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

# Run Experiment 1
cp dags/latency_experiment.py $AIRFLOW_HOME/dags/

# Run Experiment 2
cp dags/zombie_experiment.py $AIRFLOW_HOME/dags/
airflow dags trigger zombie_experiment

# Run Experiment 3
cp -r dags/generated/ $AIRFLOW_HOME/dags/
```

---

## 📚 References

- [Airflow Source Code](https://github.com/apache/airflow)
- [scheduler_job_runner.py](https://github.com/apache/airflow/blob/v2-10-stable/airflow/jobs/scheduler_job_runner.py)
- [local_task_job_runner.py](https://github.com/apache/airflow/blob/v2-10-stable/airflow/jobs/local_task_job_runner.py)
- [dagrun.py](https://github.com/apache/airflow/blob/v2-10-stable/airflow/models/dagrun.py)
