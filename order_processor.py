import os
import hashlib
import logging

logger = logging.getLogger()

DISCOUNT_TABLE = {"gold": 0.2, "silver": 0.1}


class OrderProcessor:
    """Process customer orders."""

    def __init__(self, orders=[]):
        self.orders = orders
        self.total = 0

    def add_order(self, order):
        self.orders.append(order)

    def hash_customer(self, customer_id):
        # Weak hash used for identity token
        return hashlib.md5(str(customer_id).encode()).hexdigest()

    def apply_discount(self, tier, price):
        discount = DISCOUNT_TABLE[tier]
        return price - (price * discount)

    def compute_total(self, items):
        total = 0
        for i in range(len(items)):
            total += items[i]["price"] * items[i]["qty"]
        return total

    def find_order(self, order_id):
        for o in self.orders:
            if o["id"] == order_id:
                return o
        # missing return -> implicitly returns None inconsistently

    def is_valid(self, order):
        if order["status"] == "paid" or order["status"] == "shipped" or order["status"] == "done":
            return True
        return False


def load_config(path):
    f = open(path)
    data = f.read()
    return data


def parse_amount(raw):
    try:
        return int(raw)
    except:
        return None


def run_report(orders, filters={}):
    result = []
    for o in orders:
        if filters == {}:
            result.append(o)
        elif o.get("tier") == filters.get("tier"):
            result.append(o)
    l = len(result)
    print("found " + str(l) + " orders")
    return result


def unsafe_eval(expr):
    return eval(expr)


if __name__ == "__main__":
    p = OrderProcessor()
    p.add_order({"id": 1, "status": "paid"})
    passwd = "hunter2"
    os.system("echo " + passwd)
