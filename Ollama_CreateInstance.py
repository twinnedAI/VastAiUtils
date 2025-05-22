#!/usr/bin/python3

#!pip install vastai
#!pip install ollama
import json
import time
import logging
import vastai_utils
from ollama import Client as Ollama_Client

log_format = "%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"
logging.basicConfig(filename="ollama.log", filemode='w', level=logging.INFO, format=log_format)

logger = logging.getLogger(__name__)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(stream_handler)
# some search params
min_dph = 0.1           # min price per hour
max_dph = 1.5           # max price per hour
cpu_ram = 64            
gpu_total_ram = 48      # gpu ram depends also on num_gpus and gpu_names
min_num_gpus = 1
max_num_gpus = 8
min_cpu_ghz = 3
total_flops = 10
gpu_names= "[\"RTX_4090\", \"RTX_3090\", \"RTX_A4000\"]"              
inet_down=5000          # download speed is importatnt for large models
disk_space=120          # ensure having enough disk space
query = F'dph>={min_dph} dph<={max_dph} gpu_total_ram>={gpu_total_ram} total_flops>={total_flops} inet_down>={inet_down} reliability>0.8 verified=true cpu_ram>={cpu_ram} disk_space>={disk_space} cpu_ghz>={min_cpu_ghz}'
image='ghcr.io/open-webui/open-webui:ollama'
env=f'-p 11434:11434 -p 8080:8080 --gpus=all -e OLLAMA_HOST=0.0.0.0:11434 -e OLLAMA_BASE_URL=http://0.0.0.0:11434'
onstart_cmd="env >> /etc/environment; cd /app/backend && ./start.sh &"

active_instance = None
models_default = ["gemma3:27b"]
models_codestral = []
models = models_codestral

def wait_and_get_ollama_client(instance):
    instance = vastai_utils.wait_for_ready(instance)
    webui_url = vastai_utils.get_server_url_for_port(instance, '8080')
    ollama_url = vastai_utils.get_server_url_for_port(instance, '11434')
    logger.info(F"Instance {instance.get('id')} is ready! Web UI: {webui_url}")
    logger.info(F"Ollama server url: {ollama_url}")
    return Ollama_Client(host=ollama_url, headers={'x-some-header': 'some-value'})

def pull_models(ollama_client: Ollama_Client, models):
    logger.info(f"Pulling models: {models}")
    for model in models:
        model_available = is_available(ollama_client, model)
        if model_available:
            logger.info(f"Model '{model}' already available!")
        else:
            ollama_client.pull(model=model)
            while not model_available:
                time.sleep(10)
                model_available = is_available(ollama_client, model)
                logger.info(f"Pulling model {model} {ollama_client.pull(model=model)}")
            logger.info(f"Model '{model}' has been successfully pulled!")

def is_available(ollama_client: Ollama_Client, m: str):
    models = ollama_client.list().get('models')
    return any(model['model'] == m for model in models)

def create_instance(models: list) -> Ollama_Client:
    start = time.time()
    logger.info(f"Creating instance and loading models: {models}")
    global active_instance
    active_instance = vastai_utils.get_existing_instance()
    if active_instance:
        logger.info(F"Existing instance with id: {active_instance.get('id')} available.")
    else:
        logger.info(F"No existing instance available. Creating new contract...")
        contract = vastai_utils.search_offer_and_create_instance(query=query, image=image, env=env, onstart_cmd=onstart_cmd)
        if contract and contract.get('success') == True:
            instance_id = contract.get('new_contract')
            logger.info(f"Created contract and instance with id {instance_id}")
            active_instance = vastai_utils.loadInstanceById(instance_id=instance_id)
        else:
            logger.error(json.dumps(contract, indent=2))
            raise vastai_utils.InstanceCreationFailedException("Failed to create instance!")
    active_instance = vastai_utils.wait_for_ready(instance=active_instance)
    logger.info(f"Done creating vastai ollama instance: {time.time() - start} seconds")
    ollama_client = wait_and_get_ollama_client(instance=active_instance)
    if models:
        pull_models(ollama_client, models=models)
    logger.info(f"Done creating vastai ollama instance and pulling models: {time.time() - start} seconds")
    return ollama_client

if __name__ == '__main__':
    try:
        active_instance = vastai_utils.get_existing_instance()
        while 1:
            user_command = input('Enter command: create, get_url, destroy or exit: (default: create)')
            if not user_command.strip():
                print(f"using default: create")
                user_command = 'create'
            if user_command == 'get_url':
                print("Your Ollama URL is:", vastai_utils.get_server_url_for_port(vastai_utils.loadInstanceById(instance_id=active_instance.get('id')), '11434'))
            elif user_command == 'destroy':
                vastai_utils.destroy_instance(active_instance.get('id'))
            elif user_command == 'exit':
                exit()
            elif user_command == 'create':
                user_input = input(f"Enter a list of models to pull (comma-separated, default: {models_default}): ")
                models= [model.strip() for model in user_input.split(",")] if user_input else models_default
                client = create_instance(models=models)
    except KeyboardInterrupt as k:
        vastai_utils.destroy_instance(active_instance.get('id'))
        logger.info(f"Destroed instance and quit program because of keyboard interrupt")
        exit()
    except Exception as e:
        vastai_utils.destroy_instance(active_instance.get('id'))
        logger.info(f"Destroed instance and  program because of error: {repr(e)}")
        exit()