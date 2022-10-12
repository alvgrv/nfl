"""Scraper functions for season schedule and individual games."""
import datetime as dt
import re
import math
import os

from bs4 import BeautifulSoup
import pandas as pd
import requests

from .table import DataTable
from . import LOGGER


class ScheduleScraper:
    """Functions for scraping a season schedule from source.

    Args:
        season (str): season to scrape schedule of

    """

    def __init__(self, season=None):
        """Initialise the class."""
        self.season = season
        self.scrape_target = os.environ["SCRAPE_TARGET"]

    @staticmethod
    def get_current_season():
        """Get the current NFL season.

        Returns:
            current_season (int)
        """
        if dt.datetime.now().month >= 7:
            return dt.datetime.now().year
        return dt.datetime.now().year - 1

    @property
    def schedule_div(self):
        """Get the main div from the current season schedule page at source.

        Returns:
            div (PageElement)

        """
        req = requests.get(f"{self.scrape_target}/years/{self.season}/games.htm")
        soup = BeautifulSoup(req.text, "lxml")
        return soup.find("table", id="games")

    @property
    def games_with_data(self):
        """Get game_ids that have stats published at source.

        Returns:
            game_ids (list): list of game_ids as strings

        """
        game_ids = []
        for link in self.schedule_div.find_all("a"):
            if link.text == "boxscore":
                game_id = re.findall(r"\d{9}\D{3}", link.get("href"))[0]
                game_ids.append(game_id)
        return game_ids


class GameScraper:
    """Scraper module for getting game stats and computing fun index.

    Args:
        game_id (str): the game id to scrape

    """

    def __init__(self, game_id):
        """Initialise the scraper class."""
        self.scrape_target = os.environ["SCRAPE_TARGET"]
        self.game_id = game_id
        self.game_url = f"{self.scrape_target}/boxscores/{self.game_id}.htm"

    @property
    def game_dict(self):
        """Dict containing game stats including fun index.

        Returns:
            game_dict (dict): dict containing game stats

        """
        res = requests.get(self.game_url)
        # use re to escape html comments
        comm = re.compile("<!--|-->")
        soup = BeautifulSoup(comm.sub("", res.text), "lxml")
        # get content div, holds all body content
        divs = soup.findAll("div", id="content")
        # table for points by quarter
        linescore_div = soup.find_all("div", class_="linescore_wrap")
        points = pd.read_html(str(linescore_div))[0]
        # table for scoring stats
        stats = pd.read_html(
            str(
                divs[0]
                .findAll("div", id=re.compile("^all_team_stats"))[0]
                .findAll("table")[0]
            )
        )[0]
        # length of drives table = number of drives
        # error handling added 20.9.21 to deal with
        # cases with no data for home drives, return drives or returns
        try:
            home_drives = len(
                pd.read_html(str(divs[0].findAll("table", id="home_drives")))[0].index
            )
        except:
            home_drives = 0

        try:
            away_drives = len(
                pd.read_html(str(divs[0].findAll("table", id="vis_drives")))[0].index
            )
        except:
            away_drives = 0

        # get datetime object for the dict
        date_ = (
            divs[0]
            .findAll("div", class_="scorebox")[0]
            .findAll("div", class_="scorebox_meta")[0]
            .findAll("div")[0]
            .text
        )
        time_ = (
            divs[0]
            .findAll("div", class_="scorebox")[0]
            .findAll("div", class_="scorebox_meta")[0]
            .findAll("div")[1]
            .text.replace("Start Time: ", "")
        )
        datestr = date_ + " " + time_
        dateobj = dt.datetime.strptime(datestr, "%A %b %d, %Y %I:%M%p")

        # get week number, all of the playoffs is called week 18
        if soup.findAll("h2")[0].text.endswith("Playoffs"):
            week_ = "18"
        else:
            week_ = soup.findAll("h2")[0].text.replace("NFL Scores — Week ", "")

        if dateobj.month >= 7:
            season_ = dateobj.year
        else:
            season_ = dateobj.year - 1

        # kick and punt returns
        try:
            returns = pd.read_html(str(divs[0].findAll("table", id="returns")))[0]

            split_row = None
            try:
                math.isnan(returns.iloc[0, 0])
                split_row = 0
            except:
                pass
            try:
                math.isnan(returns.iloc[1, 0])
                split_row = 1
            except:
                pass
            try:
                math.isnan(returns.iloc[2, 0])
                split_row = 2
            except:
                pass
            try:
                math.isnan(returns.iloc[3, 0])
                split_row = 3
            except:
                pass
            try:
                math.isnan(returns.iloc[4, 0])
                split_row = 4
            except:
                pass

            if split_row is not None:
                returns.columns = returns.columns.droplevel()
                away_returns = returns.copy().loc[: split_row - 1]
                away_returns.columns = [
                    "Player",
                    "Tm",
                    "Rt",
                    "Yds",
                    "Y/Rt",
                    "TD-kick",
                    "Lng",
                    "Ret",
                    "Yds",
                    "Y/R",
                    "TD-punt",
                    "Lng",
                ]
                home_returns = returns.copy().loc[split_row + 2 :]
                home_returns.columns = [
                    "Player",
                    "Tm",
                    "Rt",
                    "Yds",
                    "Y/Rt",
                    "TD-kick",
                    "Lng",
                    "Ret",
                    "Yds",
                    "Y/R",
                    "TD-punt",
                    "Lng",
                ]
                away_rtn_td = (
                    away_returns["TD-kick"].astype(int).sum()
                    + away_returns["TD-punt"].astype(int).sum()
                )
                home_rtn_td = (
                    home_returns["TD-kick"].astype(int).sum()
                    + home_returns["TD-punt"].astype(int).sum()
                )
            # ** imperfect hack alert **
            else:
                away_rtn_td = 0
                home_rtn_td = 0
        except:
            away_rtn_td = 0
            home_rtn_td = 0

        overtime = 0
        if points.shape == (2, 8):
            overtime = 1

        game_dict = {}

        game_dict.update(
            {
                "match_id": self.game_url[49:61],  # NOT INT
                "date": dateobj.date().strftime("%Y-%m-%d"),  # NOT INT
                "time": dateobj.time().strftime("%H:%M:%S"),  # NOT INT
                "week": int(week_),
                "season": int(season_),
                "ot": overtime,
                "teama_name": points.iloc[0, 1],  # NOT INTPcurrent
                "teama_pts": int(points.iloc[0, -1]),
                "teama_pts_q4": int(points.iloc[0, 5]),
                "teama_yds": int(stats.iloc[5, 1]),
                "teama_tds": int(stats.iloc[1, 1].split("-")[2])
                + int(stats.iloc[2, 1].split("-")[3]),
                "teama_tos": int(stats.iloc[7, 1]),
                "teama_4d_att": int(stats.iloc[10, 1].split("-")[1]),
                "teama_4d_comp": int(stats.iloc[10, 1].split("-")[0]),
                "teama_sacks": int(stats.iloc[3, 2].split("-")[0]),
                "teama_sack_yds": int(stats.iloc[3, 2].split("-")[1]),
                "teama_rtn_td": int(away_rtn_td),
                "teama_drives": int(away_drives),
                "teamh_name": points.iloc[1, 1],  # NOT INT
                "teamh_pts": int(points.iloc[1, -1]),
                "teamh_pts_q4": int(points.iloc[1, 5]),
                "teamh_yds": int(stats.iloc[5, 2]),
                "teamh_tds": int(stats.iloc[1, 2].split("-")[2])
                + int(stats.iloc[2, 2].split("-")[3]),
                "teamh_tos": int(stats.iloc[7, 2]),
                "teamh_4d_att": int(stats.iloc[10, 2].split("-")[1]),
                "teamh_4d_comp": int(stats.iloc[10, 2].split("-")[0]),
                "teamh_sacks": int(stats.iloc[3, 1].split("-")[0]),
                "teamh_sack_yds": int(stats.iloc[3, 1].split("-")[1]),
                "teamh_rtn_td": int(home_rtn_td),
                "teamh_drives": int(home_drives),
            }
        )

        pts = game_dict["teama_pts"] + game_dict["teamh_pts"]
        pts_q4 = game_dict["teama_pts_q4"] + game_dict["teamh_pts_q4"]
        q4_close = (
            1
            if (
                (game_dict["teama_pts"] - game_dict["teama_pts_q4"])
                - (game_dict["teamh_pts"] - game_dict["teamh_pts_q4"])
            )
            <= 7
            else 0
        )
        close = 1 if game_dict["teama_pts"] - game_dict["teamh_pts"] <= 7 else 0
        close_q4 = pts_q4 * 0.04 if q4_close == 1 else 0.02
        yds = game_dict["teama_yds"] + game_dict["teamh_yds"]
        tds = game_dict["teama_tds"] + game_dict["teamh_tds"]
        tos = game_dict["teama_tos"] + game_dict["teamh_tos"]
        sacks = game_dict["teama_sacks"] + game_dict["teamh_sacks"]
        sack_yds = game_dict["teama_sack_yds"] + game_dict["teamh_sack_yds"]
        rtns = game_dict["teama_rtn_td"] + game_dict["teamh_rtn_td"]
        ot = game_dict["ot"] * 0.15

        game_dict = {
            "id": game_dict["match_id"],
            "date": dateobj.strftime("%Y-%m-%d"),
            "time": dateobj.strftime("%H:%M"),
            "season": str(season_),
            "week": str(week_),
            "away_team": game_dict["teama_name"],
            "home_team": game_dict["teamh_name"],
            "fun_index": str(
                round(
                    pts * 0.04
                    + close_q4
                    + yds * 0.0008
                    + tds * 0.15
                    + tos * 0.08
                    + q4_close * 0.2
                    + close * 0.1
                    + sacks * 0.015
                    + sack_yds * 0.011
                    + rtns * 0.3
                    + ot,
                    2,
                )
            ),
        }

        return game_dict


class GameScraperDirector:
    """Director pattern class for executing GameScraper.

    Arg

    """

    def __init__(self, data_table: DataTable, game_scraper: GameScraper):
        """Initialise the class with dependency injection of DataTable and GameScraper."""
        self.game_scraper = game_scraper
        self.game_id = game_scraper.game_id
        self.data_table = data_table

    def run(self):
        """Execute command."""
        LOGGER.info("Event received, scraping game %s", self.game_id)
        self.data_table.table.put_item(Item=self.game_scraper.game_dict)
        LOGGER.info("Complete")
