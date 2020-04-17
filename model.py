import sys
import time
from urllib.parse import urljoin

class Challenge():
    def __init__(self, c_info):
        print(c_info)
        self.id = c_info["id"]
        self.rated = c_info["rated"]
        self.variant = c_info["variant"]["key"]
        self.perf_name = c_info["perf"]["name"]
        self.speed = c_info["speed"]
        self.increment = c_info.get("timeControl", {}).get("increment", -1)
        self.challenger = c_info.get("challenger")
        self.destUser = c_info.get("destUser")
        self.challenger_title = self.challenger.get("title") if self.challenger else None
        self.challenger_is_bot = self.challenger_title == "BOT"
        self.challenger_master_title = self.challenger_title if not self.challenger_is_bot else None
        self.challenger_name = self.challenger["name"] if self.challenger else "Anonymous"
        self.challenger_rating_int = self.challenger["rating"] if self.challenger else 0
        self.challenger_rating = self.challenger_rating_int or "?"
        self.challenger_provisional = self.challenger.get("provisional") or False 

    def is_supported_variant(self, supported):
        return self.variant in supported

    def is_supported_time_control(self, supported_speed, supported_increment_max, supported_increment_min):
        if self.increment < 0:
            return self.speed in supported_speed
        return self.speed in supported_speed and self.increment <= supported_increment_max and self.increment >= supported_increment_min

    def is_supported_mode(self, supported):
        return "rated" in supported if self.rated else "casual" in supported

    def is_supported(self, config):
        blacklist = config["blacklist"]
        if self.challenger_name in blacklist:
            return False
        if not config.get("accept_bot", False) and self.challenger_is_bot:
            return False
        variants = config["variants"]
        tc = config["time_controls"]
        inc_max = config.get("max_increment", 180)
        inc_min = config.get("min_increment", 0)
        modes = config["modes"].copy()
        if (not config.get("accept_bot_rated", False) and self.challenger_is_bot) or self.challenger_provisional:
            if "rated" in modes:
                modes.remove("rated")
        return self.is_supported_time_control(tc, inc_max, inc_min) and self.is_supported_variant(variants) and self.is_supported_mode(modes)

    def score(self):
        rated_bonus = 200 if self.rated else 0
        titled_bonus = 200 if self.challenger_master_title else 0
        return self.challenger_rating_int + rated_bonus + titled_bonus

    def mode(self):
        return "rated" if self.rated else "casual"

    def challenger_full_name(self):
        return "{}{}".format(self.challenger_title + " " if self.challenger_title else "", self.challenger_name)

    def __str__(self):
        return "{} {} challenge from {}({})".format(self.perf_name, self.mode(), self.challenger_full_name(), self.challenger_rating)

    def __repr__(self):
        return self.__str__()

class Game():
    def __init__(self, json, username, base_url, abort_time):
        self.username = username
        self.id = json.get("id")
        self.speed = json.get("speed")
        clock = json.get("clock", {}) or {}
        self.clock_initial = clock.get("initial", 1000 * 3600 * 24 * 365 * 10) # unlimited = 10 years
        self.clock_increment = clock.get("increment", 0)
        self.perf_name = json.get("perf").get("name") if json.get("perf") else "{perf?}"
        self.variant_name = json.get("variant")["name"]
        self.white = Player(json.get("white"))
        self.black = Player(json.get("black"))
        self.initial_fen = json.get("initialFen")
        self.state = json.get("state")
        self.is_white = bool(self.white.name and self.white.name == username)
        self.my_color = "white" if self.is_white else "black"
        self.opponent_color = "black" if self.is_white else "white"
        self.me = self.white if self.is_white else self.black
        self.opponent = self.black if self.is_white else self.white
        self.base_url = base_url
        self.white_starts = self.initial_fen == "startpos" or self.initial_fen.split()[1] == "w"
        self.abort_at = time.time() + abort_time

    def url(self):
        return urljoin(self.base_url, "{}/{}".format(self.id, self.my_color))

    def is_abortable(self):
        return len(self.state["moves"]) < 6

    def abort_in(self, seconds):
        if (self.is_abortable()):
            self.abort_at = time.time() + seconds

    def should_abort_now(self):
        return self.is_abortable() and time.time() > self.abort_at

    def my_remaining_seconds(self):
        return (self.state["wtime"] if self.is_white else self.state["btime"]) / 1000

    def __str__(self):
        return "{} {} vs {}".format(self.url(), self.perf_name, self.opponent.__str__())

    def __repr__(self):
        return self.__str__()


class Player():
    def __init__(self, json):
        self.id = json.get("id")
        self.name = json.get("name")
        self.title = json.get("title")
        self.rating = json.get("rating")
        self.provisional = json.get("provisional")
        self.aiLevel = json.get("aiLevel")

    def __str__(self):
        if self.aiLevel:
            return "AI level {}".format(self.aiLevel)
        else:
            rating = "{}{}".format(self.rating, "?" if self.provisional else "")
            return "{}{}({})".format(self.title + " " if self.title else "", self.name, rating)

    def __repr__(self):
        return self.__str__()
