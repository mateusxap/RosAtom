#### Как запустить разметку
1. Положить изображения в папку 
2. Выполнить команду
```bash
docker compose up -d && docker compose exec app sh -c ". ./run.sh"
```