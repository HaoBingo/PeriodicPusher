import requests
import json
import sys
import time
sys.path.append('../')
from PeriodicPusher import PeriodicPusher, Message
import Log
import traceback
from exchange import *

if __name__ != '__main__':
    exit()

if len(sys.argv[1]) < 2:
    Log.log('Missing config file.', True)

pp = PeriodicPusher(sys.argv[1])
price_dict = dict()
cny_exchange_rate = [0, 0]

def get_cny_exchange_rate():
    now = time.time()
    # Update CNY exchange rate per hour.
    if now - cny_exchange_rate[1] < 3600:
        return cny_exchange_rate[0]
    Log.log('Update CNY exchange rate...')
    rate = get_exchange_rate()
    if rate >= -1:
        cny_exchange_rate[0] = rate
        cny_exchange_rate[1] = now
    Log.log('USD:CNY = {}'.format(cny_exchange_rate[0]))
    return cny_exchange_rate[0]


def need_report(p1, p2, delta):
    high = p2 * (100 + delta) /100
    low = p2 * (100 - delta) /100
    if p1 > high or p1 < low:
        return True
    else:
        return False

def get_price(url):
    try:
        r = requests.get(url)
        if r.status_code != 200:
            Log.log('Request failed, status code: {}'.format(r.status_code), True)
            return -1
        result = json.loads(r.text)
        if result['result'] != "true":
            Log.log('Request failed, error message: {}'.format(result['message']), True)
            return -1
        return result['last']
    except Exception:
        Log.log(traceback.format_exc(), True)
        return -1

@pp.prepare
def init_price_dict(config):
    global price_dict
    Log.log('Price init...')
    msg = ''
    for currency_pair in config['CURRENCY']:
        desc = currency_pair['desc']
        api = config['API_BASE'] + currency_pair['api']
        price = get_price(api)
        msg += '{} {} '.format(desc, price)
        price_dict.update({ desc : { 'api' : api, 'last_report' : price } })
    Log.log(msg)
    get_cny_exchange_rate()
    Log.log('Price init finished.')



@pp.notification_register
def check_price(config):
    msg = ''
    log_msg = ''
    global price_dict
    Log.log('Check price...')
    rate = get_cny_exchange_rate()
    for currency in price_dict:
        price = get_price(price_dict[currency]['api'])
        if price >= 0:
            log_msg += '{} {} '.format(currency, price)
            if need_report(price, price_dict[currency]['last_report'], config['THRESHOLD']):
                msg += '\n\n{} current ${} \xa5{}, last report ${} \xa5{}\n\n'.format(
                        currency, price, price * rate,
                        price_dict[currency]['last_report'], price_dict[currency]['last_report'] * rate)
                price_dict[currency]['last_report'] = price
    Log.log(log_msg)
    if msg == '':
        return None
    return Message(msg)

if __name__ == '__main__':
    pp.run()
