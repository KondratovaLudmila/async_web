import aiohttp
import asyncio
import platform
from datetime import date, timedelta
from time import time
from sys import argv
from functools import wraps
from pprint import pprint
from typing import Iterable

url = "https://api.privatbank.ua/p24api/exchange_rates?json&date="
base_currency = ["EUR", "USD"]

DATE_FORMAT = "%d.%m.%Y"
MAX_DAYS = 10
API_CURRENCIES = frozenset((
    "AUD", "AZN", "BYN", "CAD", "CHF",
    "CNY", "CZK", "DKK", "EUR", "GBP", "GEL",
    "HUF", "ILS", "JPY", "KZT", "MDL", "NOK",
    "PLN", "SEK", "SGD", "TMT", "TRY", "UAH",
    "USD", "UZS", "XAU", "AUD", "AZN", "BYN",
    "CAD", "CHF", "CNY", "CZK", "DKK", "EUR", 
    "GBP", "GEL", "HUF", "ILS", "JPY", "KZT", 
    "MDL", "NOK", "PLN", "SEK", "SGD", "TMT", 
    "TRY", "USD", "UZS", "XAU"))

def pars_response(response: dict, currency: list) -> dict:
    """Cuts all additional information from response

    Args:
        response (dict): dict of currency exchanges
        currencies (list): additional currency

    Returns:
        dict: dictionary like {date1: 
                                {currency1: 
                                            {"sale": price, "purchase": price},
                                }}....
    """
    exchange_rate = {}
    rates = response.get("exchangeRate")
    if rates is None:
        return exchange_rate
    for curr in rates:
        if curr["currency"] in currency:
            exchange_rate.update({
                    curr["currency"]: 
                        {
                        "sale": curr.get("saleRate", 
                                    curr.get("saleRateNB", "unavailable")),
                        "purchase": curr.get("purchaseRate", 
                                    curr.get("purchaseRateNB", "unavailable"))
                        }
                    })
        
    return {response["date"]: exchange_rate}
            
def response_to_html(response: Iterable) -> str:
    """Converts python dictionaries to html for pretty view"""
    if not isinstance(response, Iterable):
        return response
    html = ""
    for el in response:
        html += str(el).replace("'", "")\
                        .replace("{", "<ul><li>")\
                        .replace(",", "</li><li>")\
                        .replace("}", "</li></ul>")
    
    return html

def connection_errors(func):
    """Connection errors decorator for asynchronic requests

    Returns:
        coroutine
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            result = await func(*args, **kwargs)
        except aiohttp.ClientConnectorError as err:
            result = str(err)
        
        return result
    return wrapper

@connection_errors
async def get_request(url: str, session: aiohttp.ClientSession) -> dict:
    """Sends request using url and session argument

    Args:
        url (str): url to make a request
        session (aiohttp.ClientSession): an opened session to use for request

    Returns:
        dict: exchange rates dictionary like:
            {
                "date": date,
                "bank":"PB",
                "baseCurrency":980,
                "baseCurrencyLit":"UAH",
                "exchangeRate":{
                    "baseCurrency":"UAH",
                    "currency": currency1 ,
                    "saleRateNB": NBprice, 
                    "purchaseRateNB": NBprice,
                    "saleRate": PBprice,
                    "purchaseRate": PBprice},
                                }
            }
    """
    async with session.get(url) as resp:
        if resp.status == 200:
            result = await resp.json()
        else:
            result = f"Error status: {resp.status} for {url}"
        
        return result
    
async def exchange_rates(days: int=1, currency: [str]=[]) -> list[dict]:
    """Creates requests by completting 'url' with date 
    from today date to date today - days.
    One date per request

    Args:
        days (int, optional): The period starting from the current 
            date for which you want to receive exchange rates. Defaults to 1.
        currency (str, optional): Additional currency in result. Defaults to None.
    Returns:
        List of dicts like {currency: {sale: price, purchase: price}} by default return
        EUR and USD as currencies
    """
    
    currency.extend(base_currency)
    if days > MAX_DAYS:
        days = MAX_DAYS
    
    cur_date = date.today()
    requests = []
    result = []
    async with aiohttp.ClientSession() as session:
        for day in range(days):
            request_date = cur_date - timedelta(days=day)
            requests.append(get_request(url + request_date.strftime(DATE_FORMAT), session))
        
        cources = await asyncio.gather(*requests)

        for course in cources:
            result.append(pars_response(course, currency))
        
    return result

def arg_parsing(args: list[str]) -> tuple[bool, str]:
    """Try to parse given arguments from list of strings

    Args:
        args (list): arguments for main function in list of strings

    Returns:
        tuple[bool, str]: True if parsing success and empty message,
            otherwise False and not empty message
    """

    message = ""
    kwargs = {}
    #Try to parse days count
    if len(args) > 1:
        if args[1].isdecimal():
            kwargs["days"] = int(args[1])
        else:
            message = "Invalid days count! It must be numeric value between 1 and 10"
            return (kwargs, message)
    
    #Try to parse additional currencies
    if len(args) > 2:
        currencies = args[2].upper().split(",")
        if API_CURRENCIES.issuperset(currencies):
            kwargs["currency"] = currencies
        else:
            message = "Invalid currency! Use one of available currencies:\n" + ", ".join(API_CURRENCIES)
            return (kwargs, message)
    
    return (kwargs, message)
        
    
if __name__ == '__main__':
    kwargs, message = arg_parsing(argv)
    if not message:
        start = time()
        if platform.system() == 'Windows':
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        result = asyncio.run(exchange_rates(**kwargs))
        fin = time()
        pprint(result, fin - start)
    else:
        pprint(message)