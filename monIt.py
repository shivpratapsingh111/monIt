import argparse
import json
import requests
import os
import asyncio
from telegram import Bot
import warnings
from urllib3.exceptions import InsecureRequestWarning

# Suppress only InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)


# Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = ''
TELEGRAM_CHAT_ID = ''

async def notify_telegram(message):

    '''
    - Send provided message to telegram, via BotFather "https://t.me/BotFather"
    - Return:
        Nothing
    '''

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        params = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message
        }

        response = requests.get(url, params=params, verify=False)
        if response.status_code == 200:
            pass
        else:
            print(f"Failed to send message. Status code: {response.status_code}")
    except Exception as e:
        print(f"[!] System threw: {e}")


def fetch_status(url):

    '''
    - Return HTTP status code of provided subdomain.
    - Return: 
        200
    '''

    try:
        print(f"[-] Fetching status: {url}")
        response = requests.get(url)
        return response.status_code # return status code
    except (requests.RequestException, ConnectionError, requests.Timeout) as e:
        if "Failed to resolve" in str(e):
            pass
        elif "Max retries exceeded" in str(e):
            pass
        else:
            print(f"[!] System threw: {e} for {url}")
        return None


def load_subdomains(subdomain_file):

    '''
    - Load subdomains from provided file.
    - Return: 
        ['google.com\n', 'evil.com\n']
    '''

    try:
        if os.path.exists(subdomain_file): # Checking if file exists
            with open(subdomain_file, 'r') as file:
                lines = file.readlines() # Read lines in list format. Ex: ['google.com\n', 'youtube.in\n', 'labs.withsecure.com']
            return lines
        else:
            print(f"[!] File doesn't exists: {subdomain_file}") 
            return None
    except Exception as e:
        print(f"[!] System threw: {e}") # Printing error such as "[Errno 13] Permission denied: 'a.txt'"
        return None     


def load_previous_result(result_file): # Load previous result

    '''
    - Load result from previous run.
    - Structure of json file (from which data is getting loaded):
        {
            "google.com": 200,
            "youtube.com": 302
        }
    - Return:
        {'youtube.com': 200, 'evil.com': 302}
    '''

    try:
        if os.path.exists(result_file):
            with open(result_file, 'r') as file:
                data = json.load(file) # Loading json data
            return data
        else:
            print("[-] Results from previous run not found")
            return None
    except Exception as e:
        print(f"[!] System threw: {e}")
        return None

    
def load_log_file(result_file): # Load previous result

    '''
    - Load result from previous run.
    - Structure of json file (from which data is getting loaded):
        {
            "google.com": 200,
            "youtube.com": 302
        }
    - Return:
        {'youtube.com': [200, 302], 'evil.com': [302, 403, 500]}    
    '''

    try:
        if os.path.exists(result_file):
            with open(result_file, 'r') as file:
                data = json.load(file)
            return data
        else:
            print("[-] Log file not found")
            return None
    except Exception as e:
        print(f"[!] System threw: {e}")
        return None


def save_log(log_file, subdomain, subdomain_status):

    '''
    - Append the changes in the http status code to a json file. (Creates new file if doesn't exists)
    - Structure of json file saved:
        {
            "google.com": [200],
            "youtube.com": [302, 403]
        }
    - Return:
        Nothing
    '''

    try:
        if os.path.exists(log_file):
            with open(log_file, 'r') as json_file: 
                data = json.load(json_file) # Load json content 
            # json_file.close() # Close the stream
        else:
            data = {}
        
        if subdomain not in data:
            data[subdomain] = []
        try:
            if not subdomain_status == None: 
                data[subdomain].append(int(subdomain_status)) # It appends the status code in and json array only. Converting status code to int before appending
                with open(log_file, 'w') as json_file:
                    json.dump(data, json_file, indent=4)
        except Exception as e:
            print(f"[!] System threw: {e}")
            return None 
    except Exception as e:
        print(f"[!] System threw: {e}")
        return None 


def save_result(result_file, subdomain, subdomain_status):

    '''
    - Save/Update the subdomain and it's status code in a json file. (Creates new file if doesn't exists)
    - Structure of json file saved:
        {
            "google.com": 200,
            "youtube.com": 302
        }
    - Return:
        Nothing
    '''

    try:
        if os.path.exists(result_file):
            with open(result_file, 'r') as json_file:
                data = json.load(json_file)
        else:
            data = {}
        try:
            if not subdomain_status == None: 
                data[subdomain] = int(subdomain_status) # Update/Save the data in json file. Converting status code to int before appending
                with open(result_file, 'w') as json_file:
                    json.dump(data, json_file, indent=4)
        except Exception as e:
            print(f"[!] System threw: {e}")  
            return None 
    except Exception as e:
        print(f"[!] System threw: {e}")    
        return None 

        
async def if_result_present(subdomain_list, result_file, previous_log, log_file):

    '''
    - Fetch current status and if subdomain is present in log file (from previous run), and it's last status from log file is same as it's current status 
    then do nothing. But if status is different from the log file (It means status is changed) then notify the user about the change, update the status in log file and if status is 200 OK then update the status in result file too.
    - Return:
        Nothing
    '''

    for subdomain in subdomain_list:
        subdomain = subdomain.strip() # striping trailing newlines (\n)
        subdomain_status = fetch_status(subdomain)
        if subdomain in previous_log.keys() and subdomain_status == previous_log[subdomain]: # If subdomain is present in previous result and status code is same, Do nothing
            pass
        else:
            if subdomain in previous_log.keys():
                if previous_log.get(subdomain)[-1] != subdomain_status:
                    status_change_message = f"[{subdomain}]: [{previous_log.get(subdomain)[-1]}] ---> [{subdomain_status}]" # Notify message. Getting last value from log file as it will return an array
                    await notify_telegram(status_change_message)
                    save_log(log_file, subdomain, subdomain_status) 
                if subdomain_status == 200: # saving it to result file if status is 200
                    subdomain_200_message = f"[{subdomain}] : [{subdomain_status}]" # Notify message
                    await notify_telegram(subdomain_200_message)
                    save_result(result_file, subdomain, subdomain_status)


async def if_result_not_present(subdomain_list, log_file, result_file):

    '''
    - Fetch current status, save the status in log file and if status is 200 OK then notify user and save in result file.
    - Return:
        Nothing
    '''

    for subdomain in subdomain_list: 
        subdomain = subdomain.strip() # striping trailing newlines (\n)
        subdomain_status = fetch_status(subdomain)
        save_log(log_file, subdomain, subdomain_status)
        if subdomain_status == 200: # saving it to result file and notifying if status is 200
            subdomain_200_message = f"[{subdomain}] : [{subdomain_status}]" # Notify message
            await notify_telegram(subdomain_200_message) 
            save_result(result_file, subdomain, subdomain_status) 




async def process_subdomain(subdomain_file, result_file, log_file):

    '''
    - Sort of main function, It calls other function based on a condition, If result from previous run are present or not. 
    - Return:
        Nothing
    '''

    subdomain_list = load_subdomains(subdomain_file)
    previous_result = load_previous_result(result_file)
    previous_log = load_log_file(log_file)

    cleaned_subdomains = [
        url.replace("https://", "").replace("http://", "") for url in subdomain_list # Removing any leading http:// or https://
        ]

    http_urls = [
        f"http://{url}" for url in cleaned_subdomains # Adding http:// as prefix
        ]

    https_urls = [
        f"https://{url}" for url in cleaned_subdomains # Adding https:// as prefix
        ]

# Running for http:// urls
    print("[-] Running with http as protocol")
    if previous_result:
        await if_result_present(http_urls, result_file, previous_log, log_file) # Function responsible for further handling, If result from previous run is present 
    else:
        pass
        await if_result_not_present(http_urls, log_file, result_file) # Function responsible for further handling, If result from previous run not present 

# Running for https:// urls
    print("[-] Running with https as protocol")
    if previous_result:
        await if_result_present(https_urls, result_file, previous_log, log_file) # Function responsible for further handling, If result from previous run is present 
    else:
        pass
        await if_result_not_present(https_urls, log_file, result_file) # Function responsible for further handling, If result from previous run not present 


    
async def main():

    '''
    - Definetly main function
    - Return:
        Nothing
    '''

    result_file = 'result.json'
    subdomain_file = 'subdomains.txt'
    log_file = 'log.json'

    await process_subdomain(subdomain_file, result_file, log_file)


if __name__ == "__main__":
    asyncio.run(main())

