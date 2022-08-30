
import time
import os

import json

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import ElementClickInterceptedException

from dotenv import load_dotenv
from bs4 import BeautifulSoup

load_dotenv()

FILE_URLS = ''


def get_urls():
    with open(FILE_URLS, encoding='utf-8') as file:
        return file.readlines()


def validate_symbol(item):
    return item.replace('₽', 'руб.') if '₽' in item else item


def get_product_name(soup):
    try:
        product_name = soup.find('h1').text
        return product_name
    except AttributeError:
        product_name = soup.find(class_='app__crumbs').find_all(class_='crumbs__item')[-1].get_text(strip=True)
        return product_name


def get_price_and_currency(soup):
    try:
        data = soup.find(class_='price__value notranslate').get_text(strip=True)
        price = ''.join(data[:-1].split())
        currency = data.replace('&nbsp;', '')[-1]
        if currency == '₽':
            currency = 'руб.'
    except AttributeError:
        pass
    try:
        price = soup.find(class_='price price_novalue p_price gray').get_text(strip=True)
        currency = 'NA'
    except AttributeError:
        pass
    return price, currency


def get_img_url(soup):
    data = ('https:', soup.find(class_='goods-card__imgs-wrap').find('img').get('src'))
    return ''.join(data)


def get_crumbs_and_category(soup):
    data = soup.find(class_='app__crumbs').find_all(class_='crumbs__item')
    category = data[-2].get_text(strip=True)
    breadcrumbs = ''
    for breadcrumb in data[1:-1]:
        temp = breadcrumb.get_text(strip=True)
        breadcrumbs += f'{temp}* '
    return category, breadcrumbs


def get_description(soup):
    data = soup.find(class_='goods-desc')
    try:
        table = str(data.find('table').text)
        text = str(soup.find(class_='goods-desc').text)
        text = text.replace(table, '').replace('\nРазвернуть описаниеСвернуть описание', '')
    except AttributeError:
        try:
            text = data.find(class_='mb10-not-last overtext text').text
        except AttributeError:
            text = 'NA'
    try:
        list_table = []
        dict_table = {}
        all_cols = []
        for row in soup.find(class_='goods-desc').find_all('table'):
            table_cols = row.find_all('td')
            all_cols.extend(table_cols)
        for i in all_cols:
            list_table.append(i.text)
        if len(list_table) % 2 != 0:
            index = 1
            while len(list_table) > index + 1:
                dict_table[list_table[index]] = list_table[index + 1]
                index += 2
        else:
            index = 0
            while len(list_table) > index + 1:
                dict_table[list_table[index]] = list_table[index + 1]
                index += 2

    except AttributeError:
        dict_table = 'NA'

    if not dict_table:
        dict_table = 'NA'

    description = {
        'table': dict_table,
        'text':  text
    }

    return description


def get_description_product_raw(soup):
    return str(soup.find(class_='goods-desc'))


def get_сontact_details(soup):
    data = soup.find(class_='modal__content')
    phones = data.find_all(class_='lnk phone__number-link')
    if len(phones) == 1:
        phone_1 = phones[0].get_text(strip=True)
        phone_2 = 'NA'
    elif len(phones) > 1:
        phone_1 = phones[0].get_text(strip=True)
        phone_2 = phones[1].get_text(strip=True)
    elif len(phones) == 0:
        phone_1 = 'NA'
        phone_2 = 'NA'
    city = data.find(class_='lnk firm-map-link').get_text(strip=True)
    return phone_1, phone_2, city


def get_сontact_details_v2(soup):
    data = soup.find(class_='phone phone_list')
    phone_1 = data.find(class_='lnk phone__number-link').get_text(strip=True)
    phone_2 = 'NA'
    city = data.find(class_='lnk firm-map-link').get_text(strip=True)
    return phone_1, phone_2, city


def get_сontact_details_v3(soup):
    data = soup.find(class_='phone phone_list').find_all(class_='phone__number')
    phone_1 = data[0].get_text(strip=True)
    phone_2 = data[1].get_text(strip=True)
    
    city = data.find(class_='lnk firm-map-link').get_text(strip=True)
    return phone_1, phone_2, city


def get_sellers_name(soup):
    sellers_name = soup.find(class_='goods-card__cell goods-card__firm-info').get_text(strip=True)
    sellers_name = sellers_name.replace('Продавец', '').strip()
    return sellers_name


def get_sellers_url_satom(soup):
    full_sellers_url_satom = soup.find(class_='goods-card__cell goods-card__firm-info').find('a').get('href')
    sellers_url_satom = full_sellers_url_satom.partition('?')[0]
    return sellers_url_satom, full_sellers_url_satom


def get_legal_name(soup):
    try:
        if soup.find(class_='goods-card__cell goods-card__firm-info').find('a').get('title') is None:
            return 'NA'
        return soup.find(class_='goods-card__cell goods-card__firm-info').find('a').get('title')
    except AttributeError:
        return 'NA'


def get_sellers_address(soup):
    try:
        return soup.find(class_='phone__item phone__item_area').find('span').get('data-modal-subtitle')
    except AttributeError:
        return 'NA'


def get_delivery(soup):
    shipping_methods = []
    data = soup.find(class_='goods-card__delivery goods-card__cell')
    try:
        rule = data.find(class_='order-rules__msg').get_text(strip=True)
    except AttributeError:
        rule = 'NA'
    try:
        temp = data.find(class_='order-rules__items')
    except AttributeError:
        temp = 'NA'
    try:
        for i in temp:
            shipping_methods.append(i.find(class_='order-rules__item-text').get_text(strip=True))
    except TypeError:
        shipping_methods = 'NA'
    return {
        "message": rule,
        "shipping_methods": ', '.join(shipping_methods)
    }


def get_extended_delivery(soup):   
    shipping_methods = {}
    delivery_regions = {}
    temp = []
    list_regions = []
    data = soup.find(class_='modal__content scrolled')
    try:
        header = data.find(class_='mb20').text
    except AttributeError:
        header = 'NA'
    try:
        description = data.find(class_='section section_order-rules').text
    except AttributeError:
        description = 'NA'
    try:
        temp = data.find_all(class_='section section_order-rules section_with-title')
    except AttributeError:
        return {
            "header": 'NA',
            "shipping_methods": 'NA',
            "delivery_regions": 'NA'
        }

    for i in temp:
        title = i.find(class_='title section__title').text
        if title == 'Способы доставки':
            line = i.find_all(class_='order-rule')
            for item in line:
                key = item.find(class_='order-rule__name').text
                value = item.find(class_='order-rule__label').text
                shipping_methods[key] = value
        elif title == 'Регионы доставки':
            line = i.find_all(class_='delivery-regions__item delivery-regions__item_top')
            for item in line:
                key = item.find(class_='delivery-regions__item-name-text').text
                if '(по всем регионам)' in key:
                    key = key.partition(' ')[0]
                    value = 'по всем регионам'
                    delivery_regions[key] = value
                else:
                    data = item.find(class_='delivery-regions__children-dd').find_all(class_='delivery-regions__item delivery-regions__item_child')
                    list_city = []
                    for item in data:
                        list_city.append(item.find(class_='delivery-regions__item-name').find(class_='delivery-regions__item-name-text').get_text(strip=True))
                        delivery_regions[key] = list_city
    list_regions.append(delivery_regions)

    if list_regions == [{}]:
        list_regions = 'NA'

    return {
        "header": list(map(validate_symbol, [header, description])),
        "shipping_methods": list(map(validate_symbol, shipping_methods)),
        "delivery_regions": list_regions
    }


def get_ways_payment(soup):
    payments = []
    try:
        data = soup.find(class_='goods-card__payment goods-card__cell').find_all(class_='order-rules__item')
        for item in data:
            payments.append(''.join(item.find(class_='order-rules__item-text').get_text(strip=True)))
    except AttributeError:
        payments = 'NA'
    return payments


def get_characteristics(soup):
    characteristics = {}
    try:
        data = soup.find(class_='app__product-attrs').find(class_='info-table__table').find_all(class_='info-table__row')
        for item in data:
            key = item.find(class_='info-table__name').get_text(strip=True)
            value = item.find(class_='info-table__value').get_text(strip=True)
            if value == ',':
                value = "NA"
            characteristics[key] = value
    except AttributeError:
        characteristics = 'NA'
    return characteristics


def get_sellers_url_external(soup):
    try:
        sellers_url_external = soup.find(class_='firm-info__link-wrap firm-info__site').find('a').get('href')
        sellers_url_external = sellers_url_external.partition('?')[0]
    except AttributeError:
        sellers_url_external = 'NA'
    return sellers_url_external


def check_card_with_link_shop(soup):
    if soup.find(class_='goods-card__info').find(class_='goods-card__btns goods-card__cell').get_text(strip=True) == 'В магазин':
        return True


def parser_card_with_linK_shop(soup, driver):
    url_item = (driver.current_url).partition('?')[0]
    product_name = get_product_name(soup)
    price, currency = get_price_and_currency(soup)
    availability = soup.find(class_='presence').get_text(strip=True)
    img_url = get_img_url(soup)
    category, breadcrumbs = get_crumbs_and_category(soup)
    description = get_description(soup)
    description_product_raw = get_description_product_raw(soup)
    mail = 'NA'
    sellers_name = get_sellers_name(soup)
    sellers_address = get_sellers_address(soup)
    phone_1, phone_2, city = 'NA', 'NA', 'NA'
    sellers_url_satom, full_sellers_url_satom = 'NA', 'NA'
    sellers_url_external = 'NA'
    legal_name = get_legal_name(soup)
    delivery = get_delivery(soup)
    try:
        element = driver.find_element(By.CLASS_NAME, 'lnk_order-rules-more')
        element.click()
        time.sleep(0.3)
        soup = BeautifulSoup(driver.page_source, 'lxml')
        extended_delivery = get_extended_delivery(soup)

    except NoSuchElementException:
        extended_delivery = 'NA'

    payment = get_ways_payment(soup)
    characteristics = get_characteristics(soup)

    dict = {
                'url_product': url_item,  # indes 0
                'title_product': product_name,  # indes 1
                'price': price,  # index 2
                'currency': currency,  # index 3
                'availability': availability,  # index 4
                'url_photo': img_url,  # index 5
                'category': category,  # index 6
                'full_category_raw': breadcrumbs,  # index 7
                'description_product': description, #  index 8
                'description_product_raw': description_product_raw, # index 9
                'tel_1': phone_1,  # index 10
                'tel_2': phone_2,  # index 11
                'email': mail,  # index 12
                'city': city,  # index 13
                'title_seller': sellers_name,  # index 14
                'url_seller_satom': sellers_url_satom,  # index 15
                'url_seller_external': sellers_url_external,  # index 16
                'legal_name': legal_name,  # index 17
                'address_seller': sellers_address,  # index 18
                'delivery': delivery,  # index 19
                'extended_delivery': extended_delivery,  # index 20
                'payments': payment,  # index 21,
                'characteristics': characteristics,  # index 22  
            }


    # with open('cards', 'a', encoding='utf-8') as file:
        # json.dump(dict, file, ensure_ascii=False)
        # file.write('\n')
    with open('workspace/item_card.json', 'w', encoding='utf-8') as file:
        json.dump(dict, file, indent=4, ensure_ascii=False)


def main():
    service = Service(os.environ['PATH_DRIVER'])
    options = ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--incognito")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(os.environ['URL_START'])
    time.sleep(20)
    for url in get_urls():
        url = url.partition('?')[0]
        driver.get(url)
        action = ActionChains(driver)
        soup = BeautifulSoup(driver.page_source, 'lxml')

        try:
            if soup.find(class_='not-found__title').get_text(strip=True) == 'Страница не найдена : (':
                continue
        except AttributeError:
            pass

        if soup.find(class_='app__crumbs').find_all(class_='crumbs__item')[2].get_text(strip=True) == 'Промышленное оборудование':
            pass
        else:
            continue

        try:
            if soup.find(class_='product-404__content'):
                continue
        except AttributeError:
            pass

        if check_card_with_link_shop(soup):
            parser_card_with_linK_shop(soup, driver)
        phone_1, phone_2, city = 'NA', 'NA', 'NA'
        try:
            element = driver.find_element(By.CLASS_NAME, 'phone_many')
            driver.execute_script("arguments[0].click();", element)
            time.sleep(0.9)
            
            soup = BeautifulSoup(driver.page_source, 'lxml')
            try:
                for i in soup.find_all(class_='msg__content scrolled'):
                    action = ActionChains(driver)
                    if i.find(class_='doc').find('div').get_text(strip=True) == 'В данный момент компания не может быстро обработать заявки, поскольку сегодня выходной день по ее графику работы. Ваша заявка будет обработана в ближайший рабочий день.':
                        element = driver.find_element(By.CLASS_NAME, 'msg__overlay')
                        driver.execute_script("arguments[0].click();", element)
            except AttributeError:
                pass
            element = driver.find_element(By.CLASS_NAME, 'modal')
            driver.execute_script("arguments[0].scrollIntoView();", element)
            try:
                phone_1, phone_2, city = get_сontact_details(soup)
            except AttributeError:
                phone_1, phone_2, city = 'NA', 'NA', 'NA'
        except NoSuchElementException:
            pass
            
        try:
            element = driver.find_element(By.CLASS_NAME, 'phone_one')
            driver.execute_script("arguments[0].click();", element)
            time.sleep(0.9)
            element = driver.find_element(By.CLASS_NAME, 'modal')
            driver.execute_script("arguments[0].scrollIntoView();", element)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            try:
                for i in soup.find_all(class_='msg__content scrolled'):
                    action = ActionChains(driver)
                    if i.find(class_='doc').find('div').get_text(strip=True) == 'В данный момент компания не может быстро обработать заявки, поскольку сегодня выходной день по ее графику работы. Ваша заявка будет обработана в ближайший рабочий день.':
                        element = driver.find_element(By.CLASS_NAME, 'msg__overlay')
                        driver.execute_script("arguments[0].click();", element)
            except AttributeError:
                pass
            try:
                phone_1, phone_2, city = get_сontact_details_v2(soup)
            except AttributeError:
                phone_1, phone_2, city = 'NA', 'NA', 'NA'

        except NoSuchElementException:
            pass

        time.sleep(0.3)
            #  Здесь возникает ошибка, когда открывается карточка со ссылкой на магазин
        try:
            element = driver.find_element(By.CLASS_NAME, 'modal')
            driver.execute_script("arguments[0].click();", element)
        except NoSuchElementException:
            continue
        except ElementClickInterceptedException:
            continue

        soup = BeautifulSoup(driver.page_source, 'lxml')
        url_item = (driver.current_url).partition('?')[0]
        product_name = get_product_name(soup)
        price, currency = get_price_and_currency(soup)
        availability = soup.find(class_='presence').get_text(strip=True)
        img_url = get_img_url(soup)
        category, breadcrumbs = get_crumbs_and_category(soup)
        description = get_description(soup)
        description_product_raw = get_description_product_raw(soup)
        mail = 'NA'
        sellers_name = get_sellers_name(soup)
        sellers_address = get_sellers_address(soup)


        action = ActionChains(driver)
        element = driver.find_element(By.CLASS_NAME, 'modal__close')
        action.move_to_element(element)
        element.click()
        time.sleep(0.2)

        try:
            action = ActionChains(driver)
            element = driver.find_element(By.CLASS_NAME, 'goods-card__minisite-link')
            action.move_to_element(element).perform()
            time.sleep(0.2)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            sellers_url_satom, full_sellers_url_satom = get_sellers_url_satom(soup)
                
        except NoSuchElementException:
            sellers_url_satom, full_sellers_url_satom = 'NA', 'NA'

        except AttributeError:
            sellers_url_satom, full_sellers_url_satom = 'NA', 'NA'

        legal_name = get_legal_name(soup)
        delivery = get_delivery(soup)
        try:
            element = driver.find_element(By.CLASS_NAME, 'lnk_order-rules-more')
            element.click()
            time.sleep(0.2)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            extended_delivery = get_extended_delivery(soup)

        except NoSuchElementException:
            extended_delivery = 'NA'
        except ElementClickInterceptedException:
            extended_delivery = 'NA'

        payment = get_ways_payment(soup)
        characteristics = get_characteristics(soup)
        if full_sellers_url_satom != 'NA':
            driver.get(full_sellers_url_satom)
            soup = BeautifulSoup(driver.page_source, 'lxml')
            sellers_url_external = get_sellers_url_external(soup)
        else:
            sellers_url_external = 'NA'

        dict = {
                'url_product': url_item,  # indes 0
                'title_product': product_name,  # indes 1
                'price': price,  # index 2
                'currency': currency,  # index 3
                'availability': availability,  # index 4
                'url_photo': img_url,  # index 5
                'category': category,  # index 6
                'full_category_raw': breadcrumbs,  # index 7
                'description_product': description, #  index 8
                'description_product_raw': description_product_raw, # index 9
                'tel_1': phone_1,  # index 10
                'tel_2': phone_2,  # index 11
                'email': mail,  # index 12
                'city': city,  # index 13
                'title_seller': sellers_name,  # index 14
                'url_seller_satom': sellers_url_satom,  # index 15
                'url_seller_external': sellers_url_external,  # index 16
                'legal_name': legal_name,  # index 17
                'address_seller': sellers_address,  # index 18
                'delivery': delivery,  # index 19
                'extended_delivery': extended_delivery,  # index 20
                'payments': payment,  # index 21,
                'characteristics': characteristics,  # index 22  
            }

        with open('workspace/item_card.json', 'w', encoding='utf-8') as file:
            json.dump(dict, file, indent=4, ensure_ascii=False)

        #with open('cards', 'a', encoding='utf-8') as file:
            #json.dump(dict, file, ensure_ascii=False)
            #file.write('\n')

    driver.quit()


if __name__ == '__main__':
    main()
