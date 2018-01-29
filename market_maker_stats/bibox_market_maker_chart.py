# This file is part of Maker Keeper Framework.
#
# Copyright (C) 2017-2018 reverendus
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import argparse
import datetime
import logging
import sys
import time
from typing import List

from market_maker_stats.util import amount_in_usd_to_size, get_gdax_prices, Price, amount_to_size, get_file_prices, \
    get_block_timestamp, to_seconds, timestamp_to_x
from pyexchange.bibox import BiboxApi, Trade


class BiboxMarketMakerChart:
    """Tool to generate a chart displaying the Bibox market maker keeper trades."""

    def __init__(self, args: list):
        parser = argparse.ArgumentParser(prog='bibox-market-maker-chart')
        parser.add_argument("--bibox-api-server", help="Address of the Bibox API server (default: 'https://api.bibox.com')", default="https://api.bibox.com", type=str)
        parser.add_argument("--bibox-api-key", help="API key for the Bibox API", required=True, type=str)
        parser.add_argument("--bibox-secret", help="Secret for the Bibox API", required=True, type=str)
        parser.add_argument("--bibox-timeout", help="Timeout for accessing the Bibox API", default=9.5, type=float)
        parser.add_argument("--bibox-retry-count", help="Retry count for accessing the Bibox API (default: 20)", default=20, type=int)
        parser.add_argument("--price-history-file", help="File to use as the price history source", type=str)
        parser.add_argument("--alternative-price-history-file", help="File to use as the alternative price history source", type=str)
        parser.add_argument("--pair", help="Token pair to draw the chart for", required=True, type=str)
        parser.add_argument("--past", help="Past period of time for which to draw the chart for (e.g. 3d)", required=True, type=str)
        parser.add_argument("-o", "--output", help="Name of the filename to save to chart to."
                                                   " Will get displayed on-screen if empty", required=False, type=str)
        self.arguments = parser.parse_args(args)

        self.bibox_api = BiboxApi(api_server=self.arguments.bibox_api_server,
                                  api_key=self.arguments.bibox_api_key,
                                  secret=self.arguments.bibox_secret,
                                  timeout=self.arguments.bibox_timeout)

        if self.arguments.output:
            import matplotlib
            matplotlib.use('Agg')

        logging.basicConfig(format='%(asctime)-15s %(levelname)-8s %(message)s', level=logging.INFO)
        logging.getLogger("filelock").setLevel(logging.WARNING)

    def main(self):
        start_timestamp = int(time.time() - to_seconds(self.arguments.past))
        end_timestamp = int(time.time())

        trades = self.bibox_api.get_trades(pair=self.arguments.pair,
                                           retry=True,
                                           retry_count=self.arguments.bibox_retry_count,
                                           from_timestamp=start_timestamp,
                                           to_timestamp=end_timestamp)

        if self.arguments.price_history_file:
            prices = get_file_prices(self.arguments.price_history_file, start_timestamp, end_timestamp)
        else:
            prices = get_gdax_prices(start_timestamp, end_timestamp)

        if self.arguments.alternative_price_history_file:
            alternative_prices = get_file_prices(self.arguments.alternative_price_history_file, start_timestamp, end_timestamp)
        else:
            alternative_prices = []

        self.draw(start_timestamp, end_timestamp, prices, alternative_prices, trades)

    def to_timestamp(self, price_or_trade):
        return timestamp_to_x(price_or_trade.timestamp)

    def to_price(self, trade: Trade):
        return trade.price

    def to_size(self, trade: Trade):
        return amount_to_size(trade.money_symbol, trade.money)

    def draw(self, start_timestamp: int, end_timestamp: int, prices: List[Price], alternative_prices: List[Price], trades: List[Trade]):
        import matplotlib.dates as md
        import matplotlib.pyplot as plt

        plt.subplots_adjust(bottom=0.2)
        plt.xticks(rotation=25)
        ax=plt.gca()
        ax.set_xlim(left=timestamp_to_x(start_timestamp), right=timestamp_to_x(end_timestamp))
        ax.xaxis.set_major_formatter(md.DateFormatter('%Y-%m-%d %H:%M:%S'))

        if len(prices) > 0:
            timestamps = list(map(self.to_timestamp, prices))
            market_prices = list(map(lambda price: price.market_price, prices))
            plt.plot_date(timestamps, market_prices, 'r-', zorder=2)

        if len(alternative_prices) > 0:
            timestamps = list(map(self.to_timestamp, alternative_prices))
            market_prices = list(map(lambda price: price.market_price, alternative_prices))
            plt.plot_date(timestamps, market_prices, 'y-', zorder=1)

        if False:
            market_prices_min = list(map(lambda price: price.market_price_min, prices))
            market_prices_max = list(map(lambda price: price.market_price_max, prices))
            plt.plot_date(timestamps, market_prices_min, 'y-', zorder=1)
            plt.plot_date(timestamps, market_prices_max, 'y-', zorder=1)

        sell_trades = list(filter(lambda trade: trade.is_sell, trades))
        sell_x = list(map(self.to_timestamp, sell_trades))
        sell_y = list(map(self.to_price, sell_trades))
        sell_s = list(map(self.to_size, sell_trades))
        plt.scatter(x=sell_x, y=sell_y, s=sell_s, c='blue', zorder=3)

        buy_trades = list(filter(lambda trade: not trade.is_sell, trades))
        buy_x = list(map(self.to_timestamp, buy_trades))
        buy_y = list(map(self.to_price, buy_trades))
        buy_s = list(map(self.to_size, buy_trades))
        plt.scatter(x=buy_x, y=buy_y, s=buy_s, c='green', zorder=3)

        if self.arguments.output:
            plt.savefig(fname=self.arguments.output, dpi=300, bbox_inches='tight', pad_inches=0)
        else:
            plt.show()


if __name__ == '__main__':
    BiboxMarketMakerChart(sys.argv[1:]).main()
