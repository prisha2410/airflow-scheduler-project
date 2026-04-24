airflow-scheduler-project/
├── README.md
├── experiment1_results.txt        ← Raw latency measurements (13 runs)
├── dags/
│   ├── latency_experiment.py      ← Experiment 1: scheduling lag measurement
│   ├── zombie_experiment.py       ← Experiment 2: crash detection (SIGKILL)
│   ├── test_timeout_double.py     ← Timeout behavior test
│   └── generated/
│       ├── dag_0.py               ← Experiment 3: scale test (51 DAGs)
│       ├── dag_1.py
│       └── ... dag_49.py
└── logs/
    ├── dag_id=latency_experiment/ ← Experiment 1 task logs
    ├── dag_id=zombie_experiment/  ← Experiment 2 crash logs
    ├── dag_id=test_timeout_double/← Timeout experiment logs
    └── scheduler/                 ← Scheduler parse-time logs (Experiment 3)
