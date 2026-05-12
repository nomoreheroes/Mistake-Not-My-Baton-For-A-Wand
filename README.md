# 1.Mistake Not My Baton For A Wand

## Pipeline Overview

This project implements a software workflow pipeline for managing project bootstrap and execution.

## Bootstrap Structure

The project has been bootstrapped using P0.1 and P0.2 agents, creating the necessary directory structure, scripts, and database schema.

## Directory Layout

- `artifacts/`: Stores all artifacts (machine-readable, human-readable, snapshots, audits, meta)
- `pipeline/`: Pipeline configuration, prompts, schemas, tests, generated files
- `pipeline_state/`: SQLite database and event logs
- `scripts/`: Bootstrap and utility scripts
- `logs/`: Log files

## Pipeline Graph

The pipeline graph is defined in `pipeline/pipeline_graph.yaml`.

## SQLite State Database

The project uses SQLite for state management. Database located at `pipeline_state/pipeline.db` with schema in `pipeline/schemas/sqlite_schema.sql`.

## Bootstrap Scripts

- `scripts/bootstrap_project.py`: Main bootstrap script
- `scripts/init_sqlite.py`: SQLite initialization
- `scripts/validate_pipeline_graph.py`: Graph validation

## How to Validate Bootstrap

Run `python scripts/bootstrap_project.py` to ensure all components are in place.