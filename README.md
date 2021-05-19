## API для изменения разрешения квадратных картинок
Можно загрузить картинку и по id задачи следить за ее статусом. После завершения работы картинку можно получить в оригинальном разрешении или в 32x32, 64x64. 


## Create venv:
    make venv

## Run tests:
    make test

## Run linters:
    make lint

## Run formatters:
    make format

### Build container
    make build

### Run app
    make up

## Redis
    address: `redis://redis:6379/0`

## Docker
    docker-compose build app
    docker-compose run --rm app make test
    docker-compose up
    docker-compose up -d
