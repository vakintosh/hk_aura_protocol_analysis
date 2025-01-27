import os
import aiohttp
import asyncio
from dotenv import load_dotenv
import sys
import logging
from pydantic import BaseModel, field_validator, ValidationError, IPvAnyAddress
import typer
from string import Template

# Load env file
load_dotenv()

HK_IP_ADDRESS = os.getenv('HK_IP_ADDRESS')
HK_PORT = int(os.getenv('HK_PORT'))
TIMEOUT = 2

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Dictionary mapping actions to their parameters
ACTIONS = {
    'set_system_volume': {'name': 'set_system_volume', 'para_range': (0, 100)},
    'set_bass_level': {'name': 'set_bass_level', 'para_range': (0, 100)},
    'set_EQ_mode': {'name': 'set_EQ_mode', 'para_options': ['on', 'off']},
    'heart-alive': {'name': 'heart-alive'},
    'power-off': {'name': 'power-off'},
    'mute-off': {'name': 'mute-off'},
    'mute-on': {'name': 'mute-on'},
}

try:
    with open('hk_request_template.xml') as f:
        XML_TEMPLATE = f.read()
except FileNotFoundError:
    logging.error('XML template file not found.')
    sys.exit(1)

class Config(BaseModel):
    HK_IP_ADDRESS: IPvAnyAddress
    HK_PORT: int

    @field_validator('HK_PORT')
    def validate_port(cls, value: int) -> int:
        if value != 10025:
            raise ValueError("The 'HK_PORT' must be exactly 10025.")
        return value

try:
    config = Config(HK_IP_ADDRESS=HK_IP_ADDRESS, HK_PORT=HK_PORT)
except ValidationError as e:
    logging.error(f"Configuration error: {e}")
    sys.exit(1)

HK_IP_ADDRESS = str(config.HK_IP_ADDRESS)
HK_PORT = config.HK_PORT

async def send_request(action: str, zone: str = 'Main Zone', para: str = None) -> None:
    """
    Send an HTTP request to the Harman Kardon Aura speaker.
    """
    xml_data = Template(XML_TEMPLATE).substitute(action=action, zone=zone, para=para if para is not None else '')

    url = f'http://{HK_IP_ADDRESS}:{HK_PORT}'
    headers = {'Content-Type': 'application/xml', 'Connection': 'close'}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=xml_data, headers=headers, timeout=TIMEOUT) as response:
                # Log only successful responses or handle specific status codes
                if response.status == 200:
                    logging.info(f"Request sent: {action}, zone: {zone}, para: {para}")
                else:
                    logging.warning(f"Failed to send request: {response.status}, message={await response.text()}")
    except asyncio.TimeoutError:
        logging.warning('Request timed out. This is expected for some actions where no response is sent.')
    except Exception as e:
        # Ignore error specifically for 'set_EQ_mode' action
        if action == 'set_EQ_mode':
            logging.warning(f"Ignoring error for action {action}: {e}")
        else:
            logging.error(f"Failed to send request for {action}: {e}")
            raise


def validate_para(action: str, para: str) -> str:
    """
    Validate and map the 'para' argument based on the action.
    """
    if action in ['set_system_volume', 'set_bass_level']:
        if isinstance(para, str) and not para.isdigit():
            raise ValueError(f"The 'para' value for {action} must be a valid integer.")
        elif isinstance(para, (int, str)) and not (0 <= int(para) <= 100):
            raise ValueError(f"The 'para' value for {action} must be an integer between 0 and 100.")
    elif action == 'set_EQ_mode':
        if para == 'off':
            return 'Basic'
        elif para == 'on':
            return 'Stereo Widening'
        else:
            raise ValueError("The 'para' value for set_EQ_mode must be 'on' or 'off'.")

    return para

app = typer.Typer()

@app.command()
def run(action: str, para: str = None) -> None:
    """
    Control the Harman Kardon Aura Speaker by sending commands.
    """
    if action == 'mute':
        action = 'mute-on'
    elif action == 'unmute':
        action = 'mute-off'

    if action in ['set_system_volume', 'set_bass_level', 'set_EQ_mode'] and para is None:
        raise ValueError(f"The '{action}' action requires the 'para' argument.")

    try:
        if action in ['set_system_volume', 'set_bass_level'] and isinstance(para, str):
            para = int(para)

        para = validate_para(action, para)

        asyncio.run(send_request(ACTIONS[action]['name'], 'Main Zone', para))

        print(f"Command '{action}' sent successfully.")

    except ValueError as e:
        logging.error(e)
        sys.exit(1)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        print('Failed to send the command. Check logs for details.')
        sys.exit(1)


if __name__ == '__main__':
    app()
