from bs4 import BeautifulSoup
import requests
import re
import os
import pandas as pd


class ScheduleScraper:
    def __init__(self, season=None):
        self.season = season
        self.scrape_target = os.environ["SCRAPE_TARGET"]

    @property
    def season_schedule(self):
        """Season schedule as a dataframe"""
        req = requests.get(f"{self.scrape_target}/years/{self.season}/games.htm")
        soup = BeautifulSoup(req.text, "lxml")
        schedule_div = soup.find("table", id="games")
        game_urls = []
        game_ids = []
        for link in schedule_div.find_all("a"):
            if link.text == "boxscore" or link.text == "preview":
                game_url = link.get("href")
                game_urls.append(self.scrape_target + game_url)
                game_id = re.findall("\d{9}\D{3}", game_url)[0]
                game_ids.append(game_id)

        schedule = pd.read_html(str(schedule_div))[0]
        schedule = schedule[schedule["Day"].isin("Mon Tue Wed Thu Fri Sat Sun".split())]
        schedule = schedule.copy().reset_index(drop=True)
        schedule.columns = (
            "week day date time away at home url ptsw ptsl ydsw tow ydsl tol".split()
        )
        schedule["has_data"] = [
            True if row == "boxscore" else False for row in schedule["url"]
        ]
        schedule["has_been_scraped"] = [False] * len(schedule)
        for index, row in schedule.iterrows():
            if all([row["has_data"], row["at"] != "@"]):
                schedule.at[index, "away"] = row["home"]
                schedule.at[index, "home"] = row["away"]

        schedule["url"] = game_urls
        schedule["season"] = [str(self.season)] * len(schedule)
        schedule["id"] = game_ids

        return schedule[
            "id season week day date time away home url has_data has_been_scraped".split()
        ].copy()

    @property
    def seasons_at_source(self):
        req = requests.get(f"{self.scrape_target}/years")
        soup = BeautifulSoup(req.text, "lxml")
        years_div = soup.find("table", id="years")
        years_df = pd.read_html(str(years_div))[0]
        years = years_df["Year"].drop_duplicates().to_list()
        return sorted(list(set([n for n in years])))
