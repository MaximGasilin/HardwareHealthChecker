import configparser  # библиотека разбора конфигурационных файлов
import re
import sys
import telnetlib


def cat_file_generator(file_object):
    # Генератор, который считыват строки и рассчитывает финансовый результат

    for line in file_object:
        # print(line)
        result = re.search(r'192\.168\.0\.\d[\s|\d\s|\d\d\s]', line)
        # print(result.start())
        # print(result.end())

        ip_address = result.group(0).strip() if result is not None else None

        yield ip_address


def check_hardware_health(c_host, c_username, c_password):

    with open(f'log_{c_host}.txt', 'w', encoding='utf-8') as log_file_obj:
        log_file_obj.write(f'telnet {c_host}')
        tn = telnetlib.Telnet('192.168.0.3')

        log_file_obj.write(tn.read_until(b"Username: ").decode("utf-8"))
        tn.write(c_username.encode('ascii') + b"\n")
        log_file_obj.write(tn.read_until(b"Password: ").decode("utf-8"))
        tn.write(c_password.encode('ascii') + b"\n")

        tn.write(b"show inv\n")
        tn.write(b"logout\n")

        log_file_obj.write(tn.read_all().decode('utf-8'))


def check_hardware_health_test():

    check_hardware_health('192.168.0.3', 'max-python-test', 'EUXutp1v')


if __name__ == "__main__":

    # Анализ агрументов командной строки
    config_file_name = sys.argv[1] if sys.argv[1] != '' else 'descr\hhc_cfg.ini'
    print(config_file_name)

    # Чтение конфигурационного файла
    try:
        config = configparser.ConfigParser()  # передача в парсер конфигурационного файла
        config.read(config_file_name)  # читаем конфиг
        print(f'Прочитан конфигурационный файл {config_file_name}. '
              f'Данные для анализа находятся в {config["hhc"]["source_file"]}.')
    except KeyError as error:
        print(f'Конфигурационный файл {config_file_name} не может быть прочитан. Или в нем нет нужных настроек')
        print(error)

    print()
    print(f'\033[30mPLAY RECAP {"*" * 50}\033[00m')

    # Чтение исходных данных из файла
    with open(config["hhc"]["source_file"], 'r', encoding='utf-8') as file_obj:
        username = config["hhc"]["username"]
        password = config["hhc"]["password"]
        for host in cat_file_generator(file_obj):
            if host is not None:
                print(f'\033[33m {host}\033[00m')
                check_hardware_health(host, username, password)
