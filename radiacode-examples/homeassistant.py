import argparse
import asyncio
import time
import json
import aiohttp

from radiacode import RealTimeData, RareData, RadiaCode

# Insert your URL for the webhook sensor
url = 'http://HOME_ASSISTANT_IP:8123/api/webhook/radiacode'

def sensors_data(rc_conn):
    databuf = rc_conn.data_buf()

    last = None
    for v in databuf:
        if isinstance(v, RealTimeData):
            if last is None or last.dt < v.dt:
                last = v

    rare = None
    for r in databuf:
        if isinstance(r, RareData):
            if rare is None or rare.dt < r.dt:
                rare = r

    if last is None:
        return []

    rates = {
        'dose_rate': round(10000 * last.dose_rate, 4),
        'count_rate': round(last.count_rate, 4),
        'dose_rate_err': round(last.dose_rate_err, 4),
        'count_rate_err': round(last.count_rate_err, 4)
    }

    if rare is not None:
        rates['charge_level'] = rare.charge_level

    rates_json = json.dumps(rates)

    return rates_json

async def send_data(d):
    # use aiohttp because we already have it as dependency in webserver.py, don't want add 'requests' here
    headers = {'Content-Type': 'application/json'}
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(url, data=d) as resp:
            return await resp.text()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--bluetooth-mac', type=str, required=False, help='MAC address of radiascan device')
    parser.add_argument('--connection', choices=['usb', 'bluetooth'], default='usb', help='device connection type')
    parser.add_argument('--interval', type=int, required=False, default=10, help='send interval, seconds')
    args = parser.parse_args()

    if args.connection == 'usb':
        print('will use USB connection')
        rc_conn = RadiaCode()
    else:
        print('will use Bluetooth connection')
        rc_conn = RadiaCode(bluetooth_mac=args.bluetooth_mac)

    while True:
        d = sensors_data(rc_conn)
        #print(f'Sending {d}')

        try:
            r = asyncio.run(send_data(d))
            #print(f'HA response: {r}')
        except Exception as ex:
            print(f'HA send error: {ex}')

        time.sleep(args.interval)


if __name__ == '__main__':
    main()
