"""Sanity checks for OrderBook reconstruction.

Run from the project root with: python -m tests.test_orderbook
"""

from src.ofi_study.orderbook import OrderBook


def make_book():
    book = OrderBook()
    book.apply_snapshot(
        bids=[["100.0", "2"], ["99.0", "5"], ["98.0", "1"]],
        asks=[["101.0", "3"], ["102.0", "4"], ["103.0", "1"]],
    )
    return book


def test_snapshot_and_top_n():
    bids, asks = make_book().top_n(2)
    assert bids == [(100.0, 2.0), (99.0, 5.0)]
    assert asks == [(101.0, 3.0), (102.0, 4.0)]


def test_update_add_and_delete():
    book = make_book()
    book.apply_update([
        ["buy", "100.0", "9"],      # update existing level
        ["buy", "100.5", "1"],      # add a new, better bid
        ["sell", "101.0", "0"],     # delete the best ask
    ])
    bids, asks = book.top_n(2)
    assert bids == [(100.5, 1.0), (100.0, 9.0)]
    assert asks == [(102.0, 4.0), (103.0, 1.0)]


if __name__ == "__main__":
    test_snapshot_and_top_n()
    test_update_add_and_delete()
    print("All order book tests passed")
