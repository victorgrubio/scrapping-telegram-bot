import asyncio
import scrapy
from scrapy import signals
import json
import os
from telegram import Bot
from telegram.constants import ParseMode
import nest_asyncio

nest_asyncio.apply()


class ColegioPsicologosSpider(scrapy.Spider):
    name = "colegio_psicologos"
    start_urls = ["https://www.copmadrid.org/web/empleo/ofertas-empleo-privado"]
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
    # https://stackoverflow.com/questions/32423837/telegram-bot-how-to-get-a-group-chat-id
    # TELEGRAM_CHAT_ID = "-4013378421"
    TELEGRAM_CHAT_ID = "176888054"
    current_data = []
    new_data = False

    def parse(self, response):
        # Select all list items within the specified XPath
        list_items = response.css(
            "body > div.container > div > div.col-sm-9 > div.fake-table-striped > div.item-striped"
        )

        for item in list_items:
            link_selector = list_items.css("p:nth-child(1) > a")

            job_item = {
                "title": item.css("strong::text").get(),
                "description": item.css("p:nth-child(2)::text").get(),
                "location": item.css("p:nth-child(3)::text").get(),
                "dates": item.css("p:nth-child(4)::text").get(),
                # Extract the 'href' attribute
                "link": link_selector.css("::attr(href)").get(),
            }

            self.current_data.append(job_item)
            yield job_item

        # Load previously stored data
        previous_data = self.load_previous_data()

        # Compare current data with previous data
        if self.data_changed(previous_data, self.current_data):
            # Data has changed; send a notification
            self.log("Data has changed!")
            # Update the stored data
            self.save_current_data(self.current_data)
        else:
            self.log("Data has not changed.")

    def load_previous_data(self):
        try:
            with open("previous_data.json", "r") as file:
                return json.load(file)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_current_data(self, current_data):
        with open("previous_data.json", "w", encoding="utf-8") as file:
            json.dump(current_data, file, indent=2, ensure_ascii=False)

    def data_changed(self, previous_data, current_data):
        # Compare the two lists; you may implement more sophisticated logic here
        self.new_data = previous_data != current_data
        return self.new_data

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super(ColegioPsicologosSpider, cls).from_crawler(
            crawler, *args, **kwargs
        )
        crawler.signals.connect(spider.spider_closed, signal=signals.spider_closed)
        return spider

    async def spider_closed(self, spider):
        spider.logger.info("Spider closed. Sending message: %s", spider.name)
        if self.current_data and self.new_data:
            asyncio.run(self.send_telegram_notification())

    async def send_telegram_notification(self):
        # Create the final message with Markdown or HTML formatting
        final_message = f"*Nuevas Ofertas:*\n```\n{self.current_data}\n```"

        bot = Bot(token=self.TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=self.TELEGRAM_CHAT_ID,
            text=final_message,
            parse_mode=ParseMode.MARKDOWN,
        )
