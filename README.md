# IE221-BikeStore

Backend API cho đồ án BikeStore, tập trung vào Django REST Framework, service layer,
JWT/OAuth2 auth, PostgreSQL, Redis cache và Celery local. Repo này **không nhắm tới
production deploy**, nên các phần Nginx/Gunicorn/Sentry/Prometheus/Elasticsearch đã
được bỏ để giữ scope gọn và dễ demo.

## Stack giữ lại

- Django 5 + Django REST Framework
- PostgreSQL
- Redis cache/broker
- Celery worker local
- JWT auth với `djangorestframework-simplejwt`
- Google OAuth2 qua `django-allauth`/`dj-rest-auth`
- Swagger/OpenAPI qua `drf-spectacular`
- `django-filter`, pagination, permissions
- `pytest`, `factory-boy`, `ruff`

## Chạy bằng Docker Compose

1. Copy `.env.example` thành `.env` nếu chưa có.
2. Điền `SECRET_KEY`, `DB_PASSWORD` và Google OAuth credentials nếu cần test OAuth.
   File `.env` đã được ignore, không commit; repo chỉ commit `.env.example` làm template.
   `docker-compose.yml` chỉ tham chiếu biến qua `${...}`, không chứa password thật.
3. Chạy stack local:

```powershell
docker compose up --build
```

API sẽ chạy tại:

- `http://localhost:8000/health/`
- `http://localhost:8000/api/docs/`
- `http://localhost:8000/api/v1/products/`
- `http://localhost:8000/api/v1/orders/`

PostgreSQL trong container dùng `DOCKER_DB_HOST=db`, `DOCKER_DB_PORT=5432`.
Khi chạy `python manage.py runserver` trực tiếp trên máy host hoặc kết nối từ pgAdmin,
dùng `DB_HOST=localhost` với `DB_PORT`/`POSTGRES_HOST_PORT` trong `.env`.
Redis cũng được publish local qua `REDIS_HOST_PORT` để host runserver dùng được cache.

## Chạy Django trên host, DB/Redis trong Docker

Chạy PostgreSQL/Redis bằng Docker Compose, sau đó chạy Django trực tiếp trên máy host:

```powershell
python -m pip install -e ".[dev]"
python manage.py migrate
python manage.py runserver
```

## Kiểm tra chất lượng

```powershell
ruff format .
ruff check .
python manage.py check --settings=config.settings.dev
pytest
```

## Scope đã bỏ vì không deploy

- Nginx reverse proxy
- Gunicorn/Uvicorn production server
- Flower dashboard
- Celery Beat scheduler
- Elasticsearch indexing
- Sentry, Prometheus, Grafana
- pghistory/pgtrigger audit trail
- Trivy scan, image push, zero-downtime deploy

## Rule kiến trúc vẫn giữ

- Business logic nằm trong `services.py`
- Query/read logic nằm trong `selectors.py`
- Views không gọi `.objects.` trực tiếp
- `create_order()` chạy atomic transaction và kiểm tra stock
- API được document bằng Swagger ở `/api/docs/`
