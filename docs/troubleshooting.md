# Troubleshooting

## Reset the database volume
```
docker compose down -v
```

## Re-run migrations
```
docker compose exec -T api sh -lc 'alembic -c backend_api/alembic.ini upgrade head'
```

## Verify extensions
```
docker compose exec -T db sh -lc "psql -U \"$POSTGRES_USER\" -d \"$POSTGRES_DB\" -c \"SELECT extname FROM pg_extension WHERE extname IN ('postgis','vector');\""
```
