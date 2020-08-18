import sys             # библиотека системных функций
import datetime        # библиотека для работы с датой и временем
import configparser    # библиотека разбора конфигурационных файлов
import re              # библиотека работы с регулярными выражениями
import telnetlib       # библиотека подключения по telnet к удаленым хостам
import multiprocessing # библиотека запуска параллельных процессов
import threading
import json
import pyexcel         # библиотека для работы с файлами excel

class HardwareHealthChecker:
     
    def __init__(self, config_file_name = ''):
        
        self.jobs_limit = 25 # Ограничение на количество одновременно запущенных процессов
        self.config_file_name = config_file_name # полное название конфигурационного файла
        
        self.jobs=[] # Список запущенных процессов
        self.config = None #Здесь будут храниться конфигурационные настройки
        
        self.result_data = [['hostname', 'ip', 'status(ok/unreachable)', 'оборудование', 'время выполнения']]
        
        self.event = threading.Event()
 
        
    def start_checkig(self):
        
        multiqueue = multiprocessing.Queue()
        
        # Чтение конфигурационного файла
        try:
            self.config = configparser.ConfigParser()  # передача в парсер конфигурационного файла
            self.config.read(self.config_file_name)  # читаем конфиг
            print(f'Прочитан конфигурационный файл {self.config_file_name}. '
                  f'Данные для анализа находятся в {self.config["hhc"]["source_file"]}.')
        except KeyError as error:
            print(f'Конфигурационный файл {self.config_file_name} не может быть прочитан. Или в нем нет нужных настроек')
            print(error)
            return None
        
        self.jobs_limit = int(self.config["hhc"]["jobs_limit"]) 
        
        print()
        print(f'\033[30mPLAY RECAP {"*" * 50}\033[00m')

        # Чтение исходных данных из файла
        with open(self.config["hhc"]["source_file"], 'r', encoding='utf-8') as file_obj:
            username = self.config["hhc"]["username"]
            password = self.config["hhc"]["password"]
            
            for host in self.cat_file_generator(file_obj):
                if host is not None:
                    while len(self.jobs) >= self.jobs_limit:
                        print(f'{datetime.datetime.now()}: достигнут лимит одновременно запущенных процессов ({self.jobs_limit})')
                        print(f'Текущий пулл заданий: {self.jobs}')
                        self.event.wait(1)
                        while not multiqueue.empty():
                            current_message = multiqueue.get()
                            current_result = json.loads(current_message)
                            print(f'\033[36m{current_result.get("host")}\033[00m :',
                                   f'\033[33m{current_result.get("alias")}\033[00m',
                                   f'\033[{32 if current_result.get("ok")== 1 else 31}mok={current_result.get("ok")}\033[00m',
                                   f'\033[{32 if current_result.get("change")== 1 else 31}mchange={current_result.get("change")}\033[00m',
                                   f'\033[{31 if current_result.get("unreachable")== 1 else 97}munreachable={current_result.get("unreachable")}\033[00m',
                                   f'\033[{31 if current_result.get("failed")== 1 else 97}mfailed={current_result.get("failed")}\033[00m'
                                   )
                            status_text = "ok" if current_result.get("ok") == 1 else "unreachable" if current_result.get("unreachable")== 1 else "failed"     
                            self.result_data.append([current_result.get("alias"), current_result.get("host"), status_text, current_result.get("inventory"), current_result.get("clock")])       
                            p_name = current_result.get('p_name')
                            if self.jobs.count(p_name) > 0:
                                self.jobs.remove(p_name)
                                print(f'Текущий пулл заданий: {self.jobs}')
                             
                        

                    print(f'{datetime.datetime.now()}: \033[33m {host} - started \033[00m')
                    p = multiprocessing.Process(name = host, target=self.check_hardware_health, args=(host, username, password, multiqueue))
                    self.jobs.append(p.name)
                    p.start()
                    print(f'Текущий пулл заданий: {self.jobs}')
            
            # Дождаться завершения запущенных процессов
            while len(self.jobs) > 0:
                self.event.wait(1)
                while not multiqueue.empty():
                    current_message = multiqueue.get()
                    current_result = json.loads(current_message)
                    print(f'\033[36m{current_result.get("host")}\033[00m :',
                           f'\033[33m{current_result.get("alias")}\033[00m',
                           f'\033[{32 if current_result.get("ok")== 1 else 31}mok={current_result.get("ok")}\033[00m',
                           f'\033[{32 if current_result.get("change")== 1 else 31}mchange={current_result.get("change")}\033[00m',
                           f'\033[{31 if current_result.get("unreachable")== 1 else 97}munreachable={current_result.get("unreachable")}\033[00m',
                           f'\033[{31 if current_result.get("failed")== 1 else 97}mfailed={current_result.get("failed")}\033[00m'
                           )
                    status_text = "ok" if current_result.get("ok") == 1 else "unreachable" if current_result.get("unreachable")== 1 else "failed"     
                    self.result_data.append([current_result.get("alias"), current_result.get("host"), status_text, current_result.get("inventory"), current_result.get("clock")])       
                    p_name = current_result.get('p_name')
                    if self.jobs.count(p_name) > 0:
                        self.jobs.remove(p_name)
                        print(f'Текущий пулл заданий: {self.jobs}')
        
        result_file_name = f'check_hardware_health_result_{str(datetime.datetime.timestamp(datetime.datetime.now()))}.xls'
        pyexcel.save_as(array=self.result_data, dest_file_name=result_file_name)
        print()
        print(f'Результат записан в файл: {result_file_name}')

    def cat_file_generator(self, file_object):
        # Генератор, который считыват строки и рассчитывает финансовый результат

        for line in file_object:
            
            #print(line)
            result = re.findall(r'\d\d*\.\d\d*\.\d\d*\.\d\d*\s', line)
            #print(result)
            ip_address = None
            if len(result) > 1:
                ip_address = result[1].strip() if result is not None else None

            yield ip_address


    def execute_tn_command(self, tn, command):
        
        begin_command = b"echo \'_begin_python_command_\'\n"
        end_command = b"echo \'_end_python_command_\'\n"
        
        tn.write(begin_command)
        alltext = tn.read_until(b"\n_begin_python_command_").decode('utf-8')
            
        result = ''
        tn.write(command)
        tn.write(end_command)
        result = tn.read_until(b"echo \'_end_python_command_\'\r\n_end_python_command_").decode('utf-8')
        alltext = alltext + result
    
        return alltext, result
        

    def check_hardware_health(self, c_host, c_username, c_password, multiqueue):
        
        p_name = multiprocessing.current_process().name
        result = {'p_name':p_name, 'host':c_host, 'alias':'**********', 'inventory':'', 'clock':'', 'ok':1, 'change':1, 'unreachable':0, 'failed':0}
        
        with open(f'log_{c_host}.txt', 'w', encoding='utf-8') as log_file_obj:
            # Начало записи в лог-файл
            log_file_obj.write(f'telnet {c_host}')
                        
            try:
                tn = telnetlib.Telnet(c_host)
            except TimeoutError:
                result['unreachable'] = 1
                result['ok'] = 0
                result['change'] = 0
             
            if result.get("unreachable")== 0:    
                # Ввод имени и пароля
                log_file_obj.write(tn.read_until(b"Username: ").decode("utf-8"))
                tn.write(c_username.encode('ascii') + b"\n")
                log_file_obj.write(tn.read_until(b"Password: ").decode("utf-8"))
                tn.write(c_password.encode('ascii') + b"\n")

               # tn.write(b"show inv\n")
               # tn.write(b"logout\n")
                
                # Проверка аутентификации
                list_of_answers = [b"### Welcome Cisco Configuration ####", b"Authentication failed"]            
                authentification = tn.expect(list_of_answers)
                
                if authentification[0] == 0:
                    # В случае успешной аутентификации специальные команды
                    log_file_obj.write(authentification[2].decode('utf-8')) 
                    #tn.write(b"show ver | i uptime\n")
                    tn.write(b"term shell\n")
                    while 1:
                        piece = tn.read_eager().decode('utf-8')
                        if piece == '':
                            break
                        log_file_obj.write(piece)                    
                    
                    # -----------------------------------------------------------------
                    # Получении информации о названии (алиаса) подключенного устройства
                    # -----------------------------------------------------------------
                    alltext, local_result = self.execute_tn_command(tn, b"show ver | i uptime\n")
                    result['alias'] = re.search(r'\n.* uptime ', local_result).group(0)
                    result['alias'] = result['alias'].replace('\n', '')
                    result['alias'] = result['alias'].replace(' uptime ', '').strip()
                    #print(f'Алиас :{result["alias"]}')                    
                    log_file_obj.write(alltext)
                    
                    # -----------------------------------------------------------------
                    # Получении информации о составе оборудования
                    # -----------------------------------------------------------------

                    alltext, local_result = self.execute_tn_command(tn, b"show inv | i MC\n")
                    left_part = re.search(r'\n.*show inv \| i MC.*', local_result)
                    if left_part is not None:
                        left_part = left_part.group(0)
                    else:
                        left_part = ''
                        
                    right_part = re.search(r"\n.*echo \'_end_python_command_\'\r\n.*_end_python_command_", local_result)
                    if right_part is not None:
                        right_part = right_part.group(0)
                    else:
                        right_part = ''
                    
                    result['inventory'] = local_result.replace(left_part, '')
                    result['inventory'] = result['inventory'].replace(right_part, '').strip()
                    #print(f'inventory :{result["inventory"]}')                    
                    log_file_obj.write(alltext)

                    # -----------------------------------------------------------------
                    # Получении информации о времени
                    # -----------------------------------------------------------------
                    alltext, local_result = self.execute_tn_command(tn, b"sh clock\n")
                    left_part = re.search(r'\n.*sh clock.*', local_result)
                    if left_part is not None:
                        left_part = left_part.group(0)
                    else:
                        left_part = ''
                        
                    right_part = re.search(r"\n.*echo \'_end_python_command_\'\r\n.*_end_python_command_", local_result)
                    if right_part is not None:
                        right_part = right_part.group(0)
                    else:
                        right_part = ''
                    result['clock'] = local_result.replace(left_part, '')
                    result['clock'] = result['clock'].replace(right_part, '').strip()
                    #print(f'clock :{result["clock"]}') 
                    log_file_obj.write(alltext)
                    
                    # -----------------------------------------------------------------
                    # Завершение сеанса
                    # -----------------------------------------------------------------
                    tn.write(b"logout\n")
                    
                elif authentification[0] == 1:
                    #print(authentification[2])
                    log_file_obj.write(authentification[2].decode('utf-8'))
                    result['failed'] = 1
                    result['ok'] = 0
                    result['change'] = 0
                    
                else:    
                    result['unreachable'] = 1
                    result['ok'] = 0
                    result['change'] = 0
                    
                log_file_obj.write(tn.read_all().decode('utf-8'))
            
        print(f'{datetime.datetime.now()}: \033[33m {c_host} - fifnished \033[00m')
        #print(f'Пытаюсь завершить процесс с именем: {p_name}')
        
        json_string = json.dumps(result)
        multiqueue.put(json_string)


def check_hardware_health_test():

    check_hardware_health('192.168.0.3', 'max-python-test', 'EUXutp1v')


if __name__ == "__main__":
   
    # Анализ агрументов командной строки
    config_file_name = sys.argv[1] if sys.argv[1] != '' else 'descr\hhc_cfg.ini'
    print(config_file_name)

    hhc = HardwareHealthChecker(config_file_name)
    hhc.start_checkig()

