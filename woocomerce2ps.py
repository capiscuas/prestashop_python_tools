import oauth2
import os
import io
import time
import requests
import urllib.request
import json
from pprint import pprint
from prestapyt import PrestaShopWebServiceDict
from django.utils.text import slugify


def get_woocomerce_products(api_url, api_key, api_secret):
    params = {
        'oauth_version': "1.0",
        'oauth_nonce': oauth2.generate_nonce(),
        'oauth_timestamp': int(time.time())
    }
    method = 'GET'
    consumer = oauth2.Consumer(key=api_key,
                               secret=api_secret)
    params['oauth_consumer_key'] = consumer.key

    req = oauth2.Request(method=method, url=api_url, parameters=params)
    signature_method = oauth2.SignatureMethod_HMAC_SHA1()
    req.sign_request(signature_method, consumer, None)

    with urllib.request.urlopen(req.to_url()) as f:
        json_output = f.read().decode('utf-8')

    return json.loads(json_output)


#Woocomerce EXPORT
api_url = 'http://woocomercedomain.com/wp-json/wc/v1/products'
api_key = 'ck_xxxx'
api_secret = 'cs_xxxxxx'
products = get_woocomerce_products(api_url, api_key, api_secret)
# pprint(products)


# PRESTASHOP IMPORT


# For production PS
ps_token = 'XXXX'
protocol_url = 'https://'
ps_url_api = 'yourdomain.com/api'

prestashop = PrestaShopWebServiceDict('{}{}'.format(protocol_url, ps_url_api), ps_token)

seller_id = 4  # Particular Knowband Marketplace seller id
# Todo: insert the right categories matching from a table
category_id = 43  # Art and culture
id_shop = 1  # Prestashop shop general id


for p in products:
    url_img = ''

    if 'images' in p:
        for im in p['images']:
            if im['src']:
                url_img = im['src']

    # pprint(p)
    print('name', p['name'])

    blank_product = {'product': {
                        'active': 1,
                        'additional_shipping_cost': '',
                        'advanced_stock_management': '',
                        'description': {'language': {'attrs': {'id': '1'}, 'value': p['description']}},
                        'description_short': {'language': {'attrs': {'id': '1'},
                                                           'value': p['short_description']}},
                        'id_category_default': category_id,
                        'name': {'language': {'attrs': {'id': '1'}, 'value': p['name']}},
                        'new': 1,
                        'state': 1,
                        'show_price': 1,
                        'low_stock_alert': 0,
                    }
    }
    if p['slug']:
        slug = p['slug'][:32]
    else:
        slug = slugify(p['name'])
    blank_product['product'].update({'reference': slug})

    if p['regular_price']:
        blank_product['product'].update({'price': float(p['regular_price'])})

    pprint(blank_product)
    result = prestashop.add('products', blank_product)
    new_product_id = result['prestashop']['product']['id']

    seller_product = {'kbsellerproduct':
                      {
                          "id_seller": seller_id,
                          "id_product": new_product_id,
                          "id_shop": id_shop,
                          "approved": 1,
                          "deleted": 0,
                           }
                      }
    result = prestashop.add('kbsellerproducts', seller_product)
    if url_img:
        print('Downloading image', url_img)
        path = urllib.parse.urlparse(url_img).path
        ext = os.path.splitext(path)[1]
        file_name = '/tmp/woocomerce{}'.format(ext)
        urllib.request.urlretrieve(url_img, file_name)

        fd = io.open(file_name, "rb")
        content = fd.read()
        fd.close()
        ps_image_url_api = '{}{}/images/products/{}'.format(protocol_url, ps_url_api, new_product_id)
        #TODO: import the legend of the image
        files = {'image': ("filename.jpg", open(file_name, 'rb'), 'image/jpg')}

        client = requests.Session()
        client.auth = (ps_token, '')
        r = client.post(ps_image_url_api, files=files)
        print(r)
