import http.client
import argparse
import sys

# Define the IP address as a variable
HK_IP_ADDRESS = '172.16.1.68'

def send_request(action, zone='Main Zone', para=None):
    conn = http.client.HTTPConnection(HK_IP_ADDRESS, 10025, timeout=2)
    headers = {
        'Content-Type': 'application/xml',
        'Connection': 'close'
    }
    data = f'''<?xml version="1.0" encoding="UTF-8"?>
<harman>
  <mm>
    <common>
      <control>
        <name>{action}</name>
        <zone>{zone}</zone>
        <para>{para if para is not None else ''}</para>
      </control>
    </common>
  </mm>
</harman>'''
    conn.request('POST', '/', body=data, headers=headers)
    try:
        response = conn.getresponse()
        print(response.read().decode())
    except http.client.BadStatusLine:
        print('Received a bad status line, which is expected for HTTP/0.9 responses.')
    except TimeoutError:
        print('Request timed out, but this is expected for some actions.')
    finally:
        conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Control Harman Kardon Aura Speaker')
    parser.add_argument('action', choices=['set_system_volume', 'set_bass_level', 'set_EQ_mode', 'heart-alive', 'power-off'], help='Action to perform')
    parser.add_argument('--zone', default='Main Zone', help='Zone to control (default: Main Zone)')
    parser.add_argument('--para', help='Parameter for the action (e.g., volume level, bass level, EQ mode)')

    args = parser.parse_args()

    if args.action in ['set_system_volume', 'set_bass_level']:
        if args.para is None or not args.para.isdigit() or not (0 <= int(args.para) <= 100):
            print("Error: The 'para' value for set_system_volume and set_bass_level must be an integer between 0 and 100.")
            sys.exit(1)

    if args.action == 'set_EQ_mode':
        if args.para == 'on':
            args.para = 'Stereo Widening'
        elif args.para == 'off':
            args.para = 'Basic'
        else:
            print("Error: The 'para' value for set_EQ_mode must be 'on' or 'off'.")
            sys.exit(1)

    send_request(args.action, args.zone, args.para)
