# bond-screener
Screening tool for bonds

# Dependencies
- postgres 15

# Running the Simple Web App
`python -m flask --app web-app/run.py run`

# Running the FastAPI instance alone
`python -m main.py`

# Running Postgres 15
- `psql -U <postgres> -h localhost -p 5432 -W`
    - replace <postgres> with the usename of the postgres installation

# Preferred method -- running with Docker
1. `docker build -t postgres_pgvector_image .`
2. `docker run --name container_name -d postgres_pgvector_image`