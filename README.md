# arabs-dataset


This repository contains the code and the data collected from a large database of Arabic journals (https://asjp.cerist.dz/en). 

The folder `src` contains the script used to scrape the website in a file called `scrape.py`.

The folder `notebooks` contains the notebook `explore_and_extract.ipynb` that filters and collects the statistics of the collected papers. The following statistics are taken from this file:

- The collected papers from the range of 2010 to 2020 is around 134k papers.
- Out of these papers, the number of accepted papers after filteratoin is around 105k papers.
- Out of these filtered papers, 101k papers have arabic abstracts and 48.7k papers have a paired Arabic and English abstracts.

The folder `articles` contains the scraped articles grouped by their journal, followed by their volume number and year, followed by their issue number and date. It contains boths, the json metadata file and the paper pdf.