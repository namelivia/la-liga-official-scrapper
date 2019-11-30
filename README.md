# La Liga Official Scrapper [![Build Status](https://travis-ci.org/namelivia/la-liga-official-scrapper.svg?branch=master)](https://travis-ci.org/namelivia/la-liga-official-scrapper)

## Warning
I wrote this scrapper some years ago so it is outdated, I'm currently checking if it works or if the page it was getting the info from still stays the same.

## What is this?
This is a scrapper I wrote some years ago for a side-project called Cryptopool related with cryptocurrencies and soccer pools. Due to time constrains the project was abandoned but I had already wrote significant pieces on my spare time like this scapper and I've decided to publish and revamp some of the code that may be useful for somebody else.

This scrapper goal was to populate the MongoDB database that contained information about teams, games, results and players. It was meant to be incremental so it could run every day and get new matches and scores, but also it should be able to repopulate the whole database if necessary. The information source was La Liga Official website.

## Requeriments

* python => 3.5
* pip3

## Installation

Clone the project, navigate to its root folder and execute `pip3 install - e . --user` for installing it's dependencies.

## Testing

For executing the tests just execute `python3 -m unittest discover` on the project's root folder.
