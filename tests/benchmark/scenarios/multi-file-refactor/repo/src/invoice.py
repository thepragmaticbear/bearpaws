def _fmt(amount, currency):
    symbol = {"USD": "$", "EUR": "€", "JPY": "¥"}[currency]
    if currency == "JPY":
        return f"{symbol}{int(round(amount)):,}"
    return f"{symbol}{amount:,.2f}"


def invoice_line(item, amount, currency):
    return f"{item}: {_fmt(amount, currency)}"
