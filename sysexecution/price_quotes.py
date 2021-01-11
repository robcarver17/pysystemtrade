
class quotePrice(list):
    def __init__(self, quote_price):
        if quote_price is None:
            quote_price =[]
        elif isinstance(quote_price, quotePrice):
            quote_price = list(quote_price)
        elif (isinstance(quote_price, float)) or (isinstance(quote_price, int)):
            quote_price = [quote_price]

        super().__init__(quote_price)

    def is_none(self):
        return len(self)==0

    def first_price(self):
        return self[0]