import argparse
import json
import requests
import os
import asyncio
from telegram import Bot
import warnings, aiohttp
from urllib3.exceptions import InsecureRequestWarning
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suppress only InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = '7210871936:AAFoVT4dhSknVIRFKbAhaEoU7W32ysc9-rQ'
TELEGRAM_CHAT_ID = '5403860559'

async def notify_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, ssl=False) as response:
            if response.status != 200:
                print(f"Failed to send message. Status code: {response.status}")

def fetch_status(url):
    return url, 200
    # try:
    #     response = requests.get(url, timeout=10)
    #     return url, response.status_code
    # except (requests.RequestException, ConnectionError, requests.Timeout) as e:
    #     print(f"[!] Error: {e} for {url}")
    #     return url, None

def load_subdomains(subdomain_file):
    if os.path.exists(subdomain_file):
        with open(subdomain_file, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    else:
        print(f"[!] File doesn't exist: {subdomain_file}")
        return []

def load_json_file(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return json.load(file)
    return {}

def save_log(log_file, subdomain, subdomain_status):
    data = load_json_file(log_file)  # Load existing data or return an empty dictionary

    # Ensure that subdomain_status is valid
    if subdomain_status is not None:
        # If the subdomain is not already in the data, initialize it as an empty list
        if subdomain not in data:
            data[subdomain] = []
        
        # Append the new status only if it's different from the last recorded status
        if not data[subdomain] or data[subdomain][-1] != subdomain_status:
            data[subdomain].append(int(subdomain_status))
            
            # Write the updated data back to the log file
            with open(log_file, 'w') as json_file:
                json.dump(data, json_file, indent=4)


def save_result(result_file, subdomain, subdomain_status):
    data = load_json_file(result_file)
    if subdomain_status is not None:
        data[subdomain] = int(subdomain_status)
        with open(result_file, 'w') as json_file:
            json.dump(data, json_file, indent=4)

async def process_subdomains(subdomain_list, result_file, log_file, previous_log, previous_result):
    status_change_message_list = []

    with ThreadPoolExecutor(max_workers=100) as executor:
        futures = {executor.submit(fetch_status, subdomain): subdomain for subdomain in subdomain_list}
        for future in as_completed(futures):
            url, subdomain_status = future.result()

            if url in previous_log and previous_log[url][-1] == subdomain_status:
                continue
            else:
                # Save the log regardless of status change to ensure it is always updated
                save_log(log_file, url, subdomain_status)
                
                if url in previous_log and previous_log[url][-1] != subdomain_status:
                    status_change_message = f"[{url}]: [{previous_log[url][-1]}] ---> [{subdomain_status}]"
                    status_change_message_list.append(status_change_message)
                    
                if subdomain_status == 200:
                    subdomain_200_message = f"[{url}] : [{subdomain_status}]"
                    status_change_message_list.append(subdomain_200_message)
                    save_result(result_file, url, subdomain_status)

            if len(status_change_message_list) >= 15:
                await notify_telegram('\n'.join(status_change_message_list))
                status_change_message_list.clear()

    if status_change_message_list:
        await notify_telegram('\n'.join(status_change_message_list))


async def process_subdomain(subdomain_file, result_file, log_file):
    subdomain_list = load_subdomains(subdomain_file)
    previous_result = load_json_file(result_file)
    previous_log = load_json_file(log_file)

    cleaned_subdomains = [
        url.replace("https://", "").replace("http://", "") for url in subdomain_list
    ]

    http_urls = [f"http://{url}" for url in cleaned_subdomains]
    https_urls = [f"https://{url}" for url in cleaned_subdomains]

    print("[-] Running with HTTP protocol")
    await process_subdomains(http_urls, result_file, log_file, previous_log, previous_result)

    print("[-] Running with HTTPS protocol")
    await process_subdomains(https_urls, result_file, log_file, previous_log, previous_result)

async def main():
    result_file = 'result.json'
    subdomain_file = 'subdomains.txt'
    log_file = 'log.json'

    await process_subdomain(subdomain_file, result_file, log_file)

if __name__ == "__main__":
    asyncio.run(main())
