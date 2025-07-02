# General info

We use Celery
We use docker compose. If code changed, the related containers must be restarted.
We use .env (specifically .env.development.local). If env changed, the related containers need to be rebuilt.

## Pipeline/worker related info

If you need to do any worker/pipeline related work, search for "Pipeline" classes and their "create" or "build" methods to find the main processor sequence. Look for task orchestration patterns (like "chord", "group", or "chain") to identify the post-processing flow with parallel
execution chains. This will give you abstract vision on how processing pipeling is organized.