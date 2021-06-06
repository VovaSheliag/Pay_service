from flask import Flask, render_template, request, redirect
from flask_wtf import FlaskForm
import wtforms
from flask_sqlalchemy import SQLAlchemy
from hashlib import sha256
from datetime import datetime
import requests
import json
import os


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pay_info.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
secret_key = os.urandom(32)
app.config['SECRET_KEY'] = secret_key

db = SQLAlchemy(app)

secret_key_for_sign = 'SecretKey01'
shop_id = '5'
payway = 'advcash_rub'
shop_order_id = 101


class PayInfo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    currency = db.Column(db.String(3), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    post_time = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)


class ServiceFrom(FlaskForm):
    amount = wtforms.DecimalField()
    currency = wtforms.SelectField(choices=[('978', 'EUR'), ('840', 'USD'), ('643', 'RUB')])
    description = wtforms.TextAreaField()
    submit = wtforms.SubmitField('Оплатить')


@app.route('/', methods=['POST', 'GET'])
def service_form():
    '''

    :return: Page for form input
    '''
    form = ServiceFrom(request.form)
    if form.validate_on_submit():
        add_db_session(request.form['currency'], request.form['amount'], datetime.now(), request.form['description'])  #Add new row to database
        if request.form['currency'] == '978':  # EUR
            return eur_case(request.form)
        elif request.form['currency'] == '840':     # USD
            return usd_case(request.form)
        elif request.form['currency'] == '643':     # RUB
            return rub_case(request.form)
    return render_template('pay.html', form=form)


def add_db_session(*args):
    '''

    :param args: [currency, amount, datetime, description]
    :return: None
    '''
    pay_info = PayInfo(currency=args[0], amount=args[1],
                       post_time=args[2], description=args[3])
    try:
        db.session.add(pay_info)
        db.session.commit()
    except:
        redirect('<h1>DB error</h1>')


def get_hex_sign(keys):
    '''
    :param keys: required parameters
    :return: Hash row, which was encoded with required parameters
    '''
    sign = ':'.join([key for key in keys]) + secret_key_for_sign
    return sha256(sign.encode('utf-8')).hexdigest()


def eur_case(form):
    '''
    :param form: request.form
    :return: HTML form with method='POST' to URL='https://pay.piastrix.com/ru/pay'
    '''
    keys = [form['amount'], form['currency'], shop_id, str(shop_order_id)]
    return f'''             </html>

                            <html lang="en">
                            <head>
                                <meta charset="UTF-8">
                                <meta http-equiv="X-UA-Compatible" content="IE=edge">
                                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                                <title>Payment</title>
                            </head>
                            <body>

                            <form name="Pay" method="post" action="https://pay.piastrix.com/ru/pay" accept-charset="UTF-8"> 
                            <input type="hidden" name="amount" value="{form['amount']}"/> 
                            <input type="hidden" name="currency" value="978"/> 
                            <input type="hidden" name="shop_id" value="5"/> 
                            <input type="hidden" name="sign" value="{get_hex_sign(keys)}"/> 
                            <input type="hidden" name="shop_order_id" value="101"/>
                            <input type="submit" value  =''/>
                            <input type="hidden" name="description" value="{form['description']}"/> 
                            </form>
                            <script type="text/javascript">
                                document.Pay.submit();
                            </script>

                            </body>
                            </html>'''


def usd_case(form):
    '''
    :param form: request.from
    :return: URL to which the user can be redirected to pay the bill
    '''
    url = 'https://core.piastrix.com/bill/create'
    keys = [form['currency'], form['amount'], form['currency'], shop_id, str(shop_order_id)]
    get_hex_sign(keys)
    request_json = {                            # data
        "description": form['description'],
        "payer_currency": 840,
        "shop_amount": str(form['amount']),
        "shop_currency": 840,
        "shop_id": shop_id,
        "shop_order_id": shop_order_id,
        "sign": get_hex_sign(keys)
    }
    headers = {'Content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(request_json), headers=headers)   # method='POST' to URL="https://core.piastrix.com/bill/create"
    return redirect(json.loads(response.text)['data']['url'])


def rub_case(form):
    '''
    :param form: request.form
    :return: URL to redirect a client to pay an invoice
    '''
    url = 'https://core.piastrix.com/invoice/create'
    keys = [form['amount'], form['currency'], payway, shop_id, str(shop_order_id)]
    request_json = {                    #data
        "currency": form['currency'],
        "payway": payway,
        "amount": form['amount'],
        "shop_id": shop_id,
        "shop_order_id": str(shop_order_id),
        "description": form['description'],
        "sign": get_hex_sign(keys)
    }
    headers = {'Content-type': 'application/json'}
    response = requests.post(url, data=json.dumps(request_json), headers=headers)   # method='POST' to URL='https://core.piastrix.com/invoice/create'
    return f'''<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Document</title>
</head>
<body>
<form method="{json.loads(response.text)['data']['method']}" action="{json.loads(response.text)['data']['url']}" name="Pay">
    <input type='hidden' name="lang" value="ru" />
    <input type="hidden" name="ac_account_email" value="{json.loads(response.text)['data']['data']['ac_account_email']}"/>
    <input type="hidden" name="ac_sci_name" value="{json.loads(response.text)['data']['data']['ac_sci_name']}"/>
    <input type="hidden" name="ac_amount" value="{json.loads(response.text)['data']['data']['ac_amount']}"/>
    <input type="hidden" name="ac_currency" value="{json.loads(response.text)['data']['data']['ac_currency']}"/>
    <input type="hidden" name="ac_order_id" value="{json.loads(response.text)['data']['data']['ac_order_id']}"/> 
    <input type="hidden" name="ac_sub_merchant_url" value="{json.loads(response.text)['data']['data']['ac_sub_merchant_url']}"/> 
    <input type="hidden" name="ac_sign" value="{json.loads(response.text)['data']['data']['ac_sign']}"/> 
    <input type="hidden" value  =''/>
    </form>
    <script type="text/javascript">
        document.Pay.submit();
    </script>
    
</body>
</html>
'''


app.run(debug=True)