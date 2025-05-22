import time
import json
from vastai import VastAI
import logging
import os

VASTAI_API_KEY = os.getenv("VASTAI_API_KEY")

logger = logging.getLogger(__name__)
client = VastAI(api_key=VASTAI_API_KEY, raw=True)

disk_space = 100

def loadInstanceById(instance_id):
    return json.loads(client.show_instance(id=instance_id))

def loadInstances():
    return json.loads(client.show_instances())

def get_server_url_for_port(instance, port: str):
    pub_ip = instance.get('public_ipaddr')
    service_portal_port = instance.get('ports').get(f'{port}/tcp')[0].get('HostPort')
    return f"http://{pub_ip}:{service_portal_port}"

def destroy_instance(instance_id):
    logger.info(f"Destroying instance with id {instance_id}...")
    client.destroy_instance(id=instance_id)
    logger.info(f"Destroyed instance with id {instance_id}")

def get_existing_instance() -> object:
    existing_instances = json.loads(client.show_instances())
    if existing_instances and len(existing_instances) > 0:
        existing_instance_id = existing_instances[0].get('id')
        return loadInstanceById(existing_instance_id)
    else:
        return None

def search_offer_and_create_instance(query: str, image: str, env: str, onstart_cmd: str) -> object:
    offers_raw = client.search_offers(query=query, order='dph+', limit=8)
    offers = json.loads(offers_raw)
    if not offers:
        logger.info(F'No offers found for query: {query}')
        raise OfferNotFoundException(query)
    top_offer = offers[0]

    top_offer_id = top_offer.get('id')
    logger.info(f"Going to create instance for offer {top_offer_id}")
    contract_raw = client.create_instance(
        ID=int(top_offer_id), 
        ssh=True, 
        image=image, 
        disk=disk_space, 
        env=env, 
        onstart_cmd=onstart_cmd)
    return json.loads(contract_raw)

def wait_for_ready(instance) -> object:
    instance_id = instance.get('id')
    instance_ready = False
    while not instance_ready:
        instance = loadInstanceById(instance_id=instance_id)
        if (instance.get('ports') and instance.get('actual_status') == instance.get('intended_status')):
            instance_ready = True
        else:
            logger.info(f"(Waiting...) Instance not ready... (status: {instance.get('actual_status')}, target status: {instance.get('intended_status')}, status message: {instance.get('status_msg')})")
            if (instance.get('status_msg') and "Error:" in instance.get('status_msg')):
                raise InstanceCreationFailedException("error")
            time.sleep(5)
    return loadInstanceById(instance_id=instance_id)

class InstanceCreationFailedException(Exception):
    def __init__(self, reason: str):
        super().__init__("InstanceCreationFailed")
        self.reason = reason

class OfferNotFoundException(Exception):
    def __init__(self, offer: str):
        super().__init__("OfferNotFound")
        self.offer = offer