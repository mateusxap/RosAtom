#!/bin/bash


printf "\n\n\n\n\n"
printf "\033[1;32m|----------------------- \033[0m\n"
printf "\033[1;32m| \033[1;97mНачинается установка зависимостей... \033[0m\n"
printf "\033[1;32m| \033[0m\n"
printf "\033[1;32m| \033[1;30mpip install -r req.txt \033[0m\n"
printf "\033[1;32m|----------------------- \033[0m\n"
printf "\n\n\n\n"

sleep 3s

pip install -r req.txt --upgrade pip





printf "\n\n\n\n\n"
printf "\033[1;32m|----------------------- \033[0m\n"
printf "\033[1;32m| 1 из 2 - Установлены зависимости \033[0m\n"
printf "\033[1;32m| \033[0m\n"
printf "\033[1;32m| \033[1;97mПереход к запуску скрипта... \033[0m\n"
printf "\033[1;32m| \033[0m\n"
printf "\033[1;32m| \033[1;30mpython main.py \033[0m\n"
printf "\033[1;32m|----------------------- \033[0m\n"
printf "\n\n\n\n"

python main.py






printf "\n\n\n\n\n"
printf "\033[1;32m|----------------------- \033[0m\n"
printf "\033[1;32m| 2 из 2 - Построена разметка \033[0m\n"
printf "\033[1;32m| \033[0m\n"
printf "\033[1;32m| \033[1;97mМожно проверять результат выполнения в папке output/images_annotated и output/json_annotations \033[0m\n"
printf "\033[1;32m| \033[0m\n"
printf "\033[1;32m| \033[1;97m:) \033[0m\n"
printf "\033[1;32m|----------------------- \033[0m\n"
printf "\n\n\n\n"


chmod 777 -R *