from lxml import html
from lxml.html import fromstring
import requests
from time import sleep
import time
import schedule
import argparse
import locale
import random
import sys
import csv
from pathlib import Path
import datetime
import os
import configparser
from bs4 import BeautifulSoup as bs
from fp.fp import FreeProxy

# Email id for who want to check availability
receiver_email_id = "EMAIL_ID_OF_USER"

LOG_FILE_PATH = os.path.dirname(os.path.realpath(__file__))

config = configparser.ConfigParser(defaults=None, strict=False)

smtp_toaddr = []
smtp_fromaddr = ''
smtp_ccaddr = ''
smtp_server = ''
smtp_port = ''
smtp_useSSL = ''
smtp_username = ''
smtp_passwd = ''

proxy_list = []

logfile = False
timeframe = 30


def setup_ini(inifile='config.ini'):

    global smtp_server
    global smtp_username
    global smtp_passwd
    global smtp_port
    global smtp_toaddr
    global smtp_fromaddr
    global PREFIXO_TAMANHO

    my_file = Path(inifile)

    if not my_file.is_file():

        txt = "[EMAIL]\nemail_admin = xxx@gmail.com\nsmtp_host = smtp.email.sa-saopaulo-1.oci.oraclecloud.com\nsmtp_user = \nsmtp_pass = \nsmtp_port = 587\nsmtp_from = no-reply@xxx.com"
        with open(inifile, 'w') as configfile:  # save

            configfile.write(txt)

        tslog("Entre com os parametros de configuração no arquivo config.ini e rode novamente")

        sys.exit()
    else:
        tslog("Lendo configurações do arquivo: " + inifile)

        config.read(inifile)

        smtp_toaddr.append(config.get('EMAIL', 'email_admin').replace(" ", ""))

        smtp_server = config.get('EMAIL', 'smtp_host').replace(" ", "")
        smtp_username = config.get('EMAIL', 'smtp_user').replace(" ", "")
        smtp_passwd = config.get('EMAIL', 'smtp_pass').replace(" ", "")
        smtp_port = config.get('EMAIL', 'smtp_port').replace(" ", "")
        smtp_fromaddr = config.get('EMAIL', 'smtp_from').replace(" ", "")


def tslog(msg, logtofile=False, logfilesufix="_log.txt", path=""):

    global LOG_FILE_PATH
    global logfile

    if LOG_FILE_PATH:
        path = LOG_FILE_PATH

    dateTimeObj = datetime.datetime.now()

    timestampStr = dateTimeObj.strftime("%Y-%m-%d")

    if path:
        timestampStr = timestampStr

    if logfile or logtofile:
        f = open(os.path.join(path, timestampStr + logfilesufix), "a")

        f.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z ") + ";" + msg + "\n")
        f.close()

    print(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S%z ") + " - " + msg)


def send_email(subject='Alarme', body='Alarme', attach=''):

    global smtp_server
    global smtp_port
    global smtp_username
    global smtp_passwd
    global smtp_fromaddr
    global smtp_toaddr

    recipient = smtp_toaddr

    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage

    global LOG_FILE_PATH

    user = smtp_username
    pwd = smtp_passwd
    str_from = smtp_fromaddr

    msgRoot = MIMEMultipart("related")

    msgRoot['Subject'] = subject
    msgRoot['From'] = smtp_fromaddr

    if not isinstance(recipient, list):
        recipient = recipient.split(",")

    str_to = recipient if isinstance(recipient, list) else [recipient]

    msgRoot['To'] = ', '.join(recipient)

    # msgRoot['To'] = recipient if isinstance(recipient, list) else [recipient]
    msgRoot.preamble = 'This is a multi-part message in MIME format.'

    # Encapsulate the plain and HTML versions of the message body in an
    # 'alternative' part, so message agents can decide which they want to display.
    msgAlternative = MIMEMultipart('alternative')
    msgRoot.attach(msgAlternative)

    msgText = MIMEText('This is the alternative plain text message.')
    msgAlternative.attach(msgText)

    # We reference the image in the IMG SRC attribute by the ID we give it below
    msg = '<html><header><meta http-equiv="Content-Type" content="text/html; charset=utf-8">' \
          '<title>SGPC Monitor</title></header><body>' + body + '<br/><img src="cid:image1"><br/></body></html>'

    msg = body + '<br/><img src="cid:image1"><br/>Nifty!'
    msgText = MIMEText(msg, 'html')

    msgAlternative.attach(msgText)

    if attach:
        try:
            # This example assumes the image is in the current directory

            fp = open(attach, 'rb')
            msgImage = MIMEImage(fp.read())
            fp.close()

            # Define the image's ID as referenced above
            msgImage.add_header('Content-ID', '<image1>')
            msgRoot.attach(msgImage)

        except FileNotFoundError:
            print("File not found: " + attach)

    # Prepare actual message
    # message = """From: %s\nTo: %s\nSubject: %s\n\n%s
    # """ % (FROM, ", ".join(TO), SUBJECT, TEXT)

    agora = datetime.datetime.now()

    try:

        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_server, smtp_port)
            server.ehlo()  # optional, called by login()
            server.login(user, pwd)
        else:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.ehlo()
            server.starttls()
            server.login(user, pwd)

        server.sendmail(str_from, str_to, msgRoot.as_string())
        server.close()

        agora = datetime.datetime.now()

        print(agora.strftime('%d-%m-%Y %H:%M') + ' : Email enviado com suceso')

    except Exception as e:

        tslog(" : Email com ERRO: " + str(e) + " \n")


def check_if_proxy_is_working(proxies, timeout=1):
    try:
        with requests.get('https://www.google.com', proxies=proxies, timeout=timeout, stream=True) as r:
            if r.raw.connection.sock:
                if r.raw.connection.sock.getpeername()[0] == proxies['https'].split(':')[1][2:]:
                    tslog("Proxy %s OK!" % proxies['https'])
                    return True
            else:
                tslog("Proxy %s não OK - Peer: %s" % (proxies['https'], r.raw.connection.sock.getpeername()[0]))
                return False
    except (requests.exceptions.ConnectTimeout, requests.exceptions.ReadTimeout, requests.exceptions.ProxyError, requests.exceptions.SSLError) as e:
        tslog("Proxy %s não OK - Error: %s" % (proxies['https'], e))


def get_proxies():

    url = 'https://free-proxy-list.net/'
    tslog("Loading proxy list from: %s" % url)

    # url = 'https://www.sslproxies.org'

    country_id = ['BR','US','CA', 'DE', 'ID', 'JP','IN','RU','MX', 'GB', 'AR']
    anonym = False
    ssl = True

    try:
        response = requests.get(url)
        parser = fromstring(response.content)
    except requests.exceptions.RequestException as e:
        tslog("Error getting proxies - connection error # %s " % e)
        return None

    proxies = []

    tr_elements = parser.xpath('//*[@id="proxylisttable"]//tr')
    # tr_elements = parser.xpath('//tbody/tr')[:20]
    '''
    for i in tr_elements:
        if i.xpath('.//td[7][contains(text(),"yes")]'):
            proxy = ":".join([i.xpath('.//td[1]/text()')[0], i.xpath('.//td[2]/text()')[0]])
            proxies.append(proxy)
    '''
    for i in range(1, 101):
        if tr_elements[i][2].text_content() in country_id and ((tr_elements[i][4].text_content()) == 'anonymous' if anonym else True) and ((tr_elements[i][6].text_content()) == 'yes' if ssl else True):
            proxy =  {'https': "http://" + tr_elements[i][0].text_content() + ":" + tr_elements[i][1].text_content(),}

            if check_if_proxy_is_working(proxy) :
                proxies.append(tr_elements[i][0].text_content() + ":" + tr_elements[i][1].text_content())

    '''
    proxies = [f'{tr_elements[i][0].text_content()}:{tr_elements[i][1].text_content()}' for i in
               range(1, 101)
               if tr_elements[i][2].text_content() in country_id
               and ((tr_elements[i][4].text_content()) == 'anonymous' if anonym else True)
               and ((tr_elements[i][6].text_content()) == 'yes' if ssl else True)]  # check the 5th column for `anonymous` if needed
    '''

    return proxies


def get_user_agent():

    user_agent_list = [
        # Chrome
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 5.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.90 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36',
        # Firefox
        'Mozilla/4.0 (compatible; MSIE 9.0; Windows NT 6.1)',
        'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; WOW64; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.0; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.3; WOW64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)',
        'Mozilla/5.0 (Windows NT 6.1; Win64; x64; Trident/7.0; rv:11.0) like Gecko',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; WOW64; Trident/6.0)',
        'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.1; Trident/6.0)',
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; .NET CLR 2.0.50727; .NET CLR 3.0.4506.2152; .NET CLR 3.5.30729)'
    ]
    user_agent = random.choice(user_agent_list)
    return user_agent


def connect(url, proxy, headers):

    r1 = None

    try:
        if proxy:
            tslog("Using proxy: " + proxy)
            r1 = requests.get(url, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)

        else:
            tslog("No proxie connection...")
            r1 = requests.get(url, headers=headers)

    except requests.exceptions.RequestException as e:

        tslog("Main: Erro de conexão... Tentando novamente %s" % e)

    if r1:
        # check for error http
        if not 200 <= r1.status_code < 300:
            tslog("Error while browsing in, code: %d" % r1.status_code)

    return r1


def mk_float(s):
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
    s = s.replace("R$", "")
    s = locale.atof(s)
    return float(s) if s else 0


def amazoncheck(url):

    availabiliy = ''
    title = ''
    proxy = ''
    global proxy_list
    # adding headers to pretend being a regular browser

    tslog("Open url: " + url)

    user_agent = get_user_agent()

    headers = {"User-Agent": user_agent,
            "Accept-Encoding": "gzip, deflate",
            'Accept-Language': 'pt-BR,en-GB,en-US;q=0.9,en;q=0.8',
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "DNT": "1",
            'Host': 'httpbin.org',
            "Connection": "close",
            "Upgrade-Insecure-Requests": "1"}

    # proxy_list = FreeProxy(country_id=['US', 'BR']).get()

    page = False

    i = 0

    while not page:
        if proxy_list:
            proxy = random.choice(proxy_list)

            page = connect(url, proxy, headers)
        i += 1
        sleep(3)

        if i > 5:
            break

    if not page:
        tslog("Connection error... Proxy: %s" % proxy)
        return '', '', ''

    sleep(1)

    soup = bs(page.content, 'html.parser')

    try:
        if soup.select_one('input[id="captchacharacters"]'):
            tslog("Página de captcha, reconectando...")
            return '', '', ''

        title = soup.select_one('h1[id="title"]').text
        title = ''.join(title).strip() if title else ''
        tslog("Título: %s" % title)

        availabiliy = soup.select_one('div[id="availability"]').text
        availabiliy = ''.join(availabiliy).strip() if availabiliy else ''

    except AttributeError as err:
        tslog("Erro na leitura da página: %s" % err)
        price = 0

    try:
        price = soup.select_one('div[id="priceInsideBuyBox_feature_div"]').text

        price = ''.join(price).strip() if price else 0
        if price == '' and 'Em estoque' in availabiliy:
            # priceblock_ourprice
            price = soup.select_one('span[id="priceblock_ourprice"]').text
            price = ''.join(price).strip() if price else 0

        price = mk_float(price.replace("R$", ""))
    except AttributeError as err1:
        price = 0

    return availabiliy, price, title


def readAsin(asin='B077PWK5BT', price=0.0):

    # Asin Id is the product Id which
    # needs to be provided by the user

    url = "https://www.amazon.com.br/dp/" + asin
    tslog("Processing: " + url)

    ans, price_real, title = amazoncheck(url)

    if not title:
        return

    arr = [
        'Only 1 left in stock.',
        'Only 2 left in stock.',
        'Em estoque.']
    if ans in arr:
        tslog("Produto %s - Preço: R$%s" % (title, price_real))
    else:
        tslog("Produto %s Indisponível" % title)
    # print(ans)

    if ans in arr and price == 0:
        subject = "[ALARME] Produto em estoque: %s" % title
        body = "[ALARME] Produto em estoque: %s" % title

        send_email(subject, body, '')

    if ans in arr and price > 0 and price_real < price:
        subject = "[ALARME] Preço menor para %s" % title
        body = "Preço menor para"

        send_email(subject, body, '')


def job():

    global proxy_list

    CLI = argparse.ArgumentParser(add_help=False)

    CLI.add_argument(
        "-f", "--file", help='Prices CSV File', default='products.csv'
    )

    args = CLI.parse_args()

    # print(args)

    if args.file:
        csv_file = args.file

        my_file = Path(csv_file)
        if not my_file.is_file():
            tslog("DB file does NOT exists, no products to browse, correct it!", True)
            sys.exit()

        with open(csv_file) as csv_file:
            csv_reader = csv.reader(csv_file, delimiter=';')
            line_count = 0

            proxy_list = get_proxies()

            for row in csv_reader:
                if line_count == 0:
                    line_count += 1
                else:
                    asin = row[0]
                    price = float(row[1])
                    line_count += 1

                    tslog("Tracking: %s - Price checking = %s" % (asin, price))
                    readAsin(asin, price)
        tslog("Fim do processo - aguardar timer")


if __name__ == '__main__':
    setup_ini()

    tslog("Initiating... Tracking every %s minutes" % timeframe, True)

    schedule.every(timeframe).minutes.do(job)

    while True:
        # running all pending tasks/jobs
        schedule.run_pending()
        time.sleep(1)
