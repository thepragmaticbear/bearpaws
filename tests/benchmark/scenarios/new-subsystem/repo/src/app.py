"""Tiny service entry point. Nothing caches yet."""


def lookup_price(sku, fetch):
    return fetch(sku)
