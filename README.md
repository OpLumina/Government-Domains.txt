# government-domains.txt 
A dataset of Approximately 13.5 Million government domains from over 220 countries, international organizations, and other government-adjacent domains/subdomains seperated by ccltd/country/organization
Includes a heatmap and all domains found so far
Last Update: 5/15/2026



## Data/Attribution:
Subdomain Data in `./outputs` is from the Amazing People at thc.org (The Hacker's Choice), and can be found at https://ip.thc.org/docs/bulk-data-access

Chile root domains are from @pdelteil: https://github.com/pdelteil/

German root domains: are from @robbi5 https://github.com/robbi5/german-gov-domains/

## ./domains 
contains txt files of each country/organization structure by ccltd (e.g. dk.txt --> denmark)

## countries.csv:
A list of the root domains and relevant data I used to scrape the parquet file

## heatmap.py:
A python script used to generate the world heat map

## extract.py
A python script I used to extract the data from the parquet file using countries.csv


## Additions and changes:
* 12 added .gl (Greenland) root domains in countries.csv (5/12/2026)
* Added ~2000 More Domains to countries.csv and indexed into ./domains (5/15/2026)
