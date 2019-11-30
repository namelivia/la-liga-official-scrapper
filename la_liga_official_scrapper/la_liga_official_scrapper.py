#!/usr/bin/python
# -*- coding: utf-8 -*-
from lxml import html
from lxml import etree
from lxml.etree import tostring
from unidecode import unidecode
import requests
import json
import logging
import time
import os
from datetime import datetime
import dateutil.parser
from pymongo import MongoClient
from bson.objectid import ObjectId
import sys


class LaLigaOfficialScrapper:

    # Prints the global results of the execution
    def print_results(self, counters):
        logger = logging.getLogger("scrapperLaLigaOficial")
        logger.info("{0} new teams added".format(counters["newTeamsCounter"]))
        logger.info("{0} new matches added".format(counters["newMatchesCounter"]))
        logger.info(
            "{0} existing matches updated".format(counters["updatedMatchesCounter"])
        )
        logger.info("{0} matches had no link".format(counters["matchesWithoutLink"]))
        logger.info(
            "{0} matches had no hashtag".format(counters["matchesWithoutHashtag"])
        )

    # Initializes the loggers
    def init_logger(self):
        stderrLogger = logging.StreamHandler()
        logging.getLogger().addHandler(stderrLogger)
        stderrLogger.setLevel(logging.INFO)
        logging.getLogger("requests").setLevel(logging.WARNING)
        logger = logging.getLogger("scrapperLaLigaOficial")
        execPath = os.path.dirname(os.path.realpath(__file__))
        handler = logging.FileHandler(
            execPath + "/../logs/scrapperLaLigaOficial-{0}.log".format(int(time.time()))
        )
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger

    # Insert a new match in the database
    def insert_a_new_match(self, matchesCollection, match, newMatchesCounter):
        matchesCollection.insert(match)
        return newMatchesCounter + 1

    # Update the match if needed
    def update_match_if_needed(
        self,
        matchesCollection,
        foundMatch,
        match,
        updatedMatchesCounter,
        poolsCollection,
    ):
        if (
            foundMatch["score1"] == match["score1"]
            and foundMatch["score2"] == match["score2"]
            and foundMatch["status"] == match["status"]
        ):
            return updatedMatchesCounter
        foundMatch["score1"] = match["score1"]
        foundMatch["score2"] = match["score2"]
        foundMatch["status"] = match["status"]
        matchesCollection.update({"_id": foundMatch["_id"]}, {"$set": foundMatch})
        self.update_match_pools(foundMatch["_id"], match["score1"], match["score2"])
        return updatedMatchesCounter + 1

    # Updates the pending pools for the updated match
    def update_match_pools(self, matchId, score1, score2):
        pools = poolsCollection.find({"match_id": matchId})
        print(pools)
        exit()

    # Extracts the match date
    def extract_match_date(self, match):
        hour = match.xpath('.//span[@class="fecha left"]//span[@class="hora"]')[0].text
        if hour is not None:
            hour = hour[2:].strip(" ")
        day = match.xpath('.//span[@class="fecha left"]//span[@class="dia"]')[
            0
        ].text.strip(" ")
        splittedDate = day.split("-")
        result = splittedDate[2] + "-" + splittedDate[1] + "-" + splittedDate[0]
        if hour is not None:
            result = result + "T" + hour
        return dateutil.parser.parse(result)

    # Extracts the referee
    def extract_referee(self, match):
        referee = match.xpath('.//span[@class="arbitro last"]')
        if len(referee) > 0:
            return referee[0].text

    # Extracts a team
    def extract_team(self, match, isLocal, teamsCollection, newTeamsCounter):
        divKey = "local" if isLocal else "visitante"
        teamDiv = match.xpath('.//span[@class="equipo left ' + divKey + '"]')
        team = teamDiv[0].xpath('.//span[@class="team"]')
        foundTeam = teamsCollection.find_one({"name": team[0].text})
        if foundTeam is None:
            # Insert a new team
            logger = logging.getLogger("scrapperLaLigaOficial")
            logger.debug("Inserting a new team")
            snake_case = unidecode(
                str(team[0].text)
                .lower()
                .replace("r. ", "real ")
                .replace(" ", "_")
                .replace(".", "")
            )
            newTeam = {"name": team[0].text, "tag": snake_case}
            newTeamId = teamsCollection.insert(newTeam)
            result = (newTeamsCounter + 1, newTeamId)
        else:
            result = (newTeamsCounter, foundTeam["_id"])
        return result

    # main
    def start_scrapping(self, dateRange):

        # if something breaks try changing this
        ANNOYING_LENGTH = -2
        # ANNOYING_LENGTH = -1
        db = MongoClient("localhost", 3001).meteor
        # init logging
        logger = self.init_logger()

        # start scrapping
        logger.info("Scrapping the official La Liga page")
        startTime = time.time()

        # load existing data
        logger.debug("Loading existing teams")
        teamsCollection = db.teams
        logger.debug("Loading exsiting matches")
        matchesCollection = db.matches
        logger.debug("Loading exsiting pools")
        poolsCollection = db.pools
        logger.debug("Loading already feched links")
        execPath = os.path.dirname(os.path.realpath(__file__))
        lines = tuple(open(execPath + "/../fetchedLinks", "r"))
        lines = [line[:-1] for line in lines]

        # Initializing counters
        counters = {
            "newMatchesCounter": 0,
            "newTeamsCounter": 0,
            "updatedMatchesCounter": 0,
            "matchesWithoutHashtag": 0,
            "matchesWithoutLink": 0,
        }

        # Start fetching information
        logger.debug("Fetching information")
        # Fecthing the calendar
        logger.debug("Fetching the calendar")
        page = requests.get("http://www.laliga.es/calendario-horario/")
        tree = html.fromstring(page.text)
        scripts = tree.xpath("//script")
        # Ugly!
        longestScriptIndex = 8
        for key, script in enumerate(scripts):
            if script.text is not None and len(script.text) > 1000:
                longestScriptIndex = key
        for key, content in enumerate(scripts[longestScriptIndex].text.split("\n")):
            if content is not None and len(content) > 10000:
                longestContentIndex = key
        data = scripts[longestScriptIndex].text.split("\n")[longestContentIndex][
            20:ANNOYING_LENGTH
        ]
        parsedData = json.loads(data)

        # Start fetching the events
        logger.debug("Fetching events")
        fh = open("fetchedLinks", "a")

        for event in parsedData:
            # check if I've already have it
            # TODO: Check the updating range time
            splittedEvents = event["url"].split("_")
            eventDate = dateutil.parser.parse(
                splittedEvents[5] + "-" + splittedEvents[4] + "-" + splittedEvents[3]
            )
            delta = datetime.now() - eventDate
            if (
                event["url"] in lines
                and dateRange is not None
                and abs(delta).days > dateRange
            ):
                logger.debug("I already have the " + event["url"] + " event")
                continue

            # Fetch one event
            logger.debug("Fetching an event")
            eventUrl = (
                "http://www.laliga.es/includes/ajax.php?action=ver_evento_calendario"
            )
            queryData = {"filtro": event["url"]}
            page = requests.post(eventUrl, data=queryData)
            tree = html.fromstring(page.text)

            # Find the matches in the event
            logger.debug("Fetching the matches")
            matches = tree.xpath('//div[contains(@class,"partido")]')[2:]

            for idx, match in enumerate(matches):
                # Fetch one match
                logger.debug("Fetching a match")
                prelink = match.xpath(".//a")
                # Check if the match does not have a link
                if len(prelink) == 0:
                    counters["matchesWithoutLink"] += 1
                    continue

                # start retrieving a match info
                newMatch = {}
                link = prelink[0].get("href")
                detailsPage = requests.post(link)
                detailsTree = html.fromstring(detailsPage.text)

                # get the hastag
                prehashtag = detailsTree.xpath('.//div[@id="hashtag"]')
                if len(prehashtag) > 0:
                    hashtag = prehashtag[0].text
                else:
                    counters["matchesWithoutHashtag"] += 1
                newMatch["hashtag"] = hashtag

                # set the referee
                newMatch["arbitro"] = self.extract_referee(match)

                # try to locate the local team
                (counters["newTeamsCounter"], newMatch["player1"]) = self.extract_team(
                    match, True, teamsCollection, counters["newTeamsCounter"]
                )

                # try to locate the visitant team
                (counters["newTeamsCounter"], newMatch["player2"]) = self.extract_team(
                    match, False, teamsCollection, counters["newTeamsCounter"]
                )

                # process the date
                newMatch["date"] = self.extract_match_date(match)

                # process the score
                horaResultadoDiv = match.xpath('.//span[@class="hora-resultado left"]')
                horaResultado = horaResultadoDiv[0].xpath(
                    './/span[@class="horario-partido hora"]'
                )
                newMatch["score1"] = horaResultado[0].text.split("-")[0]
                newMatch["score2"] = horaResultado[0].text.split("-")[1]
                if newMatch["score1"] == "" and newMatch["score2"] == "":
                    newMatch["status"] = 0
                else:
                    newMatch["status"] = 1

                # Try to find if the match is already in the database, and has to be updated or inserted
                foundMatch = matchesCollection.find_one(
                    {
                        "player1": ObjectId(newMatch["player1"]),
                        "player2": ObjectId(newMatch["player2"]),
                        "date": newMatch["date"],
                    }
                )
                if foundMatch is None:
                    logger.debug("Inserting a new match")
                    counters["newMatchesCounter"] = self.insert_a_new_match(
                        matchesCollection, newMatch, counters["newMatchesCounter"]
                    )
                else:
                    logger.debug("Updating an existing match if needed")
                    counters["updatedMatchesCounter"] = self.update_match_if_needed(
                        matchesCollection,
                        foundMatch,
                        newMatch,
                        counters["updatedMatchesCounter"],
                        poolsCollection,
                    )

            # write it in the already fetched links
            fh.write(event["url"] + "\n")
        fh.close()

        # print the results and exit
        self.print_results(counters)
        endTime = time.time()
        executionTime = endTime - startTime
        logger.info("The execution took " + str(executionTime) + " seconds")
        logger.info("Done")
