import requests
import json
import os
import time
from tqdm import tqdm
from bs4 import BeautifulSoup


class Scraper:
    """
    Scrape data from PCPartPicker from given product `endpoints`.

    Note that requests may hang for a while depending on how many
    endpoints there are, and how many pages each of those endpoints
    have.

    Example: `/video-card`, `/cpu`, etc.
    """
    _BASE_URL = "https://pcpartpicker.com/products"
    _bs4 = lambda self, html: BeautifulSoup(html, "html.parser")

    _unescape = lambda self, text: text.replace("\\", "")
    _json_safe = lambda self, text: text.lower().replace(" ", "_")

    _out = lambda self, *args: print(*args) if self.console else None

    _chunker = lambda self, seq, size: (seq[pos:pos + size] for pos in range(0, len(seq), size))

    def __init__(self, *endpoints, output_dir="./data", console=True):
        self.endpoints = endpoints
        self.output_dir = output_dir
        self.console = console

        self._abs_endpoints = [self._BASE_URL + e + "/fetch" for e in self.endpoints]
        self._scrape_queue = None

    def _create_scrape_queue(self):
        """
        Validate the endpoint, create a dictionary for each endpoint
        with its own text, page count (so we know know how many
        pages to scrape), and categories, and finally append to
        the scrape queue.
        """
        self._scrape_queue = []

        self._out("Creating scrape queue...\n")

        for url in tqdm(self._abs_endpoints):
            req = requests.get(url)

            if not req.ok:
                self._out(f"Failed to GET {url}. ({str(req.status_code)})")
                continue

            # Since we are accessing the generated (escaped) HTML of each
            # endpoint, we need to unescape it using a helper which replaces
            # the backslashes in order to to parse it with BeautifulSoup.
            html_unescaped = self._unescape(req.text)

            bs4 = self._bs4(html_unescaped)

            page_count = bs4.find("ul", class_="pagination").find_all("li")[-1].string

            categories = [self._json_safe(c.find("h6", class_="specLabel").string) for c in bs4.find("td", class_="td--nowrap").find_all_previous("td", class_="td__spec")]

            self._scrape_queue.append({"url": url, "categories": [c for c in reversed(categories)], "page_count": int(page_count)})

    def _scrape(self):
        """
        Get the data from our generated scrape queue, scrape the
        HTML and output it.
        """
        # We need a queue in order to scrape!
        assert self._scrape_queue, "Scrape queue does not exist. Have any valid endpoints been specified?"

        start_all_time = time.time()

        for scrapee in self._scrape_queue:
            self._out(f"\nScraping {scrapee['url']}")
            start_time = time.time()

            current_page = 1
            items = []

            _progress = tqdm(total=scrapee["page_count"])

            while current_page <= scrapee["page_count"]:
                page_items = []

                _progress.update(1)

                req = requests.get(scrapee["url"], params={"page": current_page})
                bs4 = self._bs4(self._unescape(req.text))

                values = [l.find_next_sibling(text=True) for l in bs4.find_all("h6", class_="specLabel")]

                categories = scrapee["categories"]

                for val_group in self._chunker(values, len(categories)):
                    page_items.append(dict(zip(categories, val_group)))

                # We have all of the category values, but still don't
                # have the name and price.
                names = [w.find("p").string for w in bs4.find_all(class_="td__nameWrapper")]
                prices = [w.find(text=True) for w in bs4.find_all(class_="td__price")]

                for i, item in enumerate(page_items):
                    # If there isn't a price to show, it will be "Add".
                    # We don't want to show that.
                    price = prices[i] if prices[i] != "Add" else None

                    item.update({"name": names[i], "price": price})

                # Don't append; page_items is a list
                items += page_items

                current_page += 1

            _progress.close()

            end_time = time.time() - start_time

            self._out(f"Finished scraping {str(len(items))} items from {scrapee['url']} in {str(round(end_time, 3))}s")

            if not os.path.exists(self.output_dir):
                self._out(f"Output directory '{self.output_dir}' does not exist.", "Creating it...")
                os.mkdir(self.output_dir)

            json_out = json.dumps(items)

            # Omit "https://" from the URL and get the endpoint
            file_name = scrapee["url"][8:].split("/")[-2] + ".json"
            file_path = os.path.join(self.output_dir, file_name)

            with open(file_path, "w") as f:
                f.write(json_out)

            self._out(f"Saved data to {file_path}")

        end_all_time = time.time() - start_all_time

        self._out(f"Finished scraping {str(len(self.endpoints))} endpoint(s) in {str(end_all_time // 60)}m ({str(round(end_all_time, 3))}s)")

    def run(self):
        """
        Run the scraper.
        """
        self._create_scrape_queue()
        self._scrape()


if __name__ == "__main__":
    targets = [
        "/cpu",
        "/cpu-cooler",
        "/motherboard",
        "/memory",
        "/internal-hard-drive",
        "/video-card",
        "/case",
        "/power-supply",
        "/optical-drive",
        "/os",
        "/software",
        "/monitor",
        "/external-hard-drive",
        "/laptop",
        "/case-accessory",
        "/case-fan",
        "/fan-controller",
        "/thermal-paste",
        "/ups",
        "/sound-card",
        "/wired-network-card",
        "/wireless-network-card",
        "/headphones",
        "/keyboard",
        "/mouse",
        "/speakers"
    ]

    scraper = Scraper(*targets)
    scraper.run()
