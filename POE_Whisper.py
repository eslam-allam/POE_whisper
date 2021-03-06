import logging
from watchfiles import run_process
import requests
import os
import threading
import time
import sys
import msvcrt as m
from watchfiles import Change, DefaultFilter

logging.getLogger("watchfiles").setLevel(logging.CRITICAL)

mylogs = logging.getLogger(__name__)
mylogs.setLevel(logging.DEBUG)

file = logging.FileHandler("program_logs.log",encoding='utf-8')
file.setLevel(logging.INFO)
fileformat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
file.setFormatter(fileformat)
mylogs.addHandler(file)

stream = logging.StreamHandler()
stream.setLevel(logging.INFO)
streamformat = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s',datefmt='%Y-%m-%d %H:%M:%S')
stream.setFormatter(streamformat)


mylogs.addHandler(stream)

mode = 0o777
flags = os.O_RDONLY
setup_file_path = './setup.txt'
client_log_file = ''
client_log_folder = ''
program_count_file = './lastlength.txt'
telegram_bot_token = ''
telegram_chatID = ''
kill_thread = False


def wait():
        m.getch()

class textFilter(DefaultFilter):
    allowed_extensions = '.txt'

    def __call__(self, change: Change, path: str) -> bool:
        return super().__call__(change, path) and path.endswith(self.allowed_extensions)

def startup():

    global client_log_file
    global client_log_folder
    global program_count_file
    global telegram_bot_token
    global telegram_chatID
    if os.path.exists(setup_file_path):
        try:
            with open(setup_file_path,'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            mylogs.error('COULD NOT LOCATE SETUP FILE')  
            sys.exit(0)

        client_log_file = lines[0][lines[0].find('=')+1:].strip()
        client_log_folder = client_log_file[:-11]
        telegram_bot_token = lines[1][lines[1].find('=')+1:].strip()
        telegram_chatID = lines[2][lines[2].find('=')+1:].strip()
    else:
        mylogs.warning('SETUP FILE DOES NOT EXIST! CREATING SETUP FILE')
        client_log_file = input('ENTER CLIENT LOG FILE ABSOLUTE PATH: ')
        client_log_folder = client_log_file[:-11]
        telegram_bot_token = input('ENTER TELEGRAM BOT TOKEN: ')
        telegram_chatID = input('ENTER TELEGRAM CHAT ID: ')

        setup_text = 'client_log_file = {}\ntelegram_bot_token = {}\ntelegram_chatID = {}'.format(client_log_file, telegram_bot_token, telegram_chatID)
        mylogs.info('CREATING SETUP FILE')
        with open(setup_file_path,'w', encoding='utf-8') as f:
                f.write(setup_text)
        
        mylogs.info('SETUP FILE CREATED SUCCESSFULLY')
    mylogs.info('OPENING PROGRAM COUNTER AND CLIENT LOG')

    try:
        with open(client_log_file, 'r', encoding='utf-8') as f:
            count = f.readlines()
    except FileNotFoundError:
        mylogs.error('COULD NOT LOCATE LOG FILE ---- MAKE SURE LOG FILE PATH IS SET CORRECTLY E.G...../logs/Client.txt')  
        sys.exit(0)

    length = len(count)


    with open(program_count_file,'w+',encoding='utf-8') as f:
            f.write(str(length))

def refresh():
    mylogs.info('THREAD STARTED')
    denied = False
    global kill_thread
    while not kill_thread:
        try:
            file= os.open(client_log_file, flags, mode)
            if denied == True:
                mylogs.info('ACCESS RECOVERED!')
                denied = False
            os.close(file)
            time.sleep(1)
        except Exception:
                mylogs.warning('ACCESS TO LOGS DENIED ----- RETRYING ----- PRESS (CTRL + C) TO END')
                denied = True
                time.sleep(5)
    mylogs.info('THREAD CLOSED')
    sys.exit(0)


def  whisper(client_log_file, program_count_file, telegram_bot_token, telegram_chatID):
    global th
    try:
        with open(program_count_file,'r',encoding='utf-8') as f:
            last_length = int(f.readline())
        content = ''
        whispers = ''
        with open(client_log_file,'r',encoding='utf-8') as f:
            lines = f.readlines()
            
            if lines:
                
                if last_length != 0:
                    if last_length != len(lines):
                        diffirence = len(lines) - last_length
                        content = lines[-diffirence:]
                        
                else: 
                    last_length = len(lines)
                    if lines:
                        content = lines[-10:]
                        
                
            if lines: last_length = len(lines)
        if content:
            for line in content:
                if '@From' in line:
                    whispers += line[line.find('@From'):] + '\n'
            
            if whispers:
                response = requests.get('https://api.telegram.org/bot{}/sendMessage'.format(telegram_bot_token),params={'text':whispers,'chat_id': '{}'.format(telegram_chatID)})
                status = response.json()
                if status['ok']:
                    mylogs.info('**********************STATUS:OK**********************')
                    sender = status['result']['from']
                    chat = status['result']['chat']
                    mylogs.info('MESSAGE SENT THROUGH {} TO {} {}'.format(sender['first_name'],chat['first_name'], chat['last_name']))
                    mylogs.info('MESSAGE: {}'.format(whispers))
                else:
                    mylogs.warning('**********************STATUS:NO OK**********************')
                    mylogs.warning('MESSAGE NOT SENT!! PLEASE CHECK BOT PARAMETERS OR CHAT ID')

        with open(program_count_file,'w',encoding='utf-8') as f:
            f.write(str(last_length))
    except Exception:
        mylogs.error('UNABLE TO ACCESS CLIENT LOG!!')

def catch(arg):
    for change in arg:
        if str(change[0]) == 'Change.deleted':
            mylogs.warning('{} HAS BEEN DELETED!'.format(change[1]))
        


def main():
    mylogs.info('PROGRAM RUNNING --------- PRESS (CTRL + C) TO EXIT')
    run_process(client_log_folder, target=whisper, watch_filter=textFilter(), args=(client_log_file, program_count_file, telegram_bot_token, telegram_chatID), callback=catch)

if __name__ == '__main__':
    
    try:
        th = threading.Thread(target=refresh, daemon=False, name='refreshThread')
        mylogs.info('LOADING SETUP PREFERENCES')
        startup()
        mylogs.info('PREFERENCES LOADED SUCCESSFULLY')
        mylogs.info('STARTING REFRESH THREAD')
        th.start()
        main()
        
        
    except KeyboardInterrupt:
        kill_thread = True
        if th: 
            if th.is_alive():
                th.join()
        mylogs.info('PROGRAM TERMINATED')
        
        
    except Exception as e:
        kill_thread = True
        if th: 
            if th.is_alive():
                th.join()
        
        mylogs.error('PROGRAM TERMINATED WITHOUT INTERRUPT ' + str(e))

    finally:
        kill_thread = True
        if th: 
            if th.is_alive():
                th.join()
        
        mylogs.info('PROGRAM ABOUT TO CLOSE - PRESS ANY KEY TO CONTINUE')
        wait()
        mylogs.info('PROGRAM TERMINATED')
        