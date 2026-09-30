def format_amount(amount, currency):
    return f"{currency} {round(amount, 2)}"


def report_row(name, amount, currency):
    return f"{name:<10}{format_amount(amount, currency)}"
