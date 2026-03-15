# HW4 API Testing

## Подробный отчет доступен в папке `htmlcov/index.html`. 

## Запуск проекта и тестов

### 1. Установка зависимостей
```bash
- pip install -r requirements.txt
- python -m pytest --cov=app --cov-report=html tests/
- locust -f tests/locustfile.py
```
### Структура

- tests/test_unit.py — проверка генерации кодов и логики очистки базы.
- tests/test_api.py — функциональные тесты CRUD-операций и авторизации.
- tests/conftest.py — конфигурация тестовой базы данных и фикстур.
- tests/locustfile.py — сценарий для имитации нагрузки на API.