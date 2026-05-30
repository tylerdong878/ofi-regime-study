from sortedcontainers import SortedDict


class OrderBook:
    """A local replica of one product's L2 order book.

    Seeded from a Coinbase `snapshot` message, then kept in sync by
    applying each `l2update` delta in the order received.
    """

    def __init__(self):
        # price -> total size at that level. Both kept sorted ascending by price
        self.bids = SortedDict()
        self.asks = SortedDict()

    def apply_snapshot(self, bids, asks):
        """Reset the book to the full state from a snapshot message."""
        self.bids.clear()
        self.asks.clear()
        for price, size in bids:
            self.bids[float(price)] = float(size)
        for price, size in asks:
            self.asks[float(price)] = float(size)

    def apply_update(self, changes):
        """Apply one l2update message's list of [side, price, size] changes."""
        for side, price, size in changes:
            book = self.bids if side == "buy" else self.asks
            price = float(price)
            size = float(size)
            if size == 0.0:
                book.pop(price, None)
            else:
                book[price] = size

    def top_n(self, n=5):
        """Return the best n levels per side as (price, size) tuples, best first.
        
        Best bid = highest price, best ask = lowest price
        """
        n_bids = min(n, len(self.bids))
        n_asks = min(n, len(self.asks))
        bids = [self.bids.peekitem(-1 - i) for i in range(n_bids)]
        asks = [self.asks.peekitem(i) for i in range(n_asks)]
        return bids, asks
    
