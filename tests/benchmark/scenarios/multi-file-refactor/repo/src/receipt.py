def money(amount, currency):
    symbol = {"USD": "$", "EUR": "€"}[currency]
    return symbol + "%.2f" % amount


def receipt_total(amounts, currency):
    return "TOTAL " + money(sum(amounts), currency)
