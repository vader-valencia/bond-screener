from ast import Yield
from typing import List
import requests
from bs4 import BeautifulSoup
from itertools import product

from models import Maturity, MoodyRating, Bond


class BondService:
    def __init__(self):
        pass

    def get_bonds_from_page(self, response):
        soup = BeautifulSoup(response.text, "lxml")

        # Locate the table containing bond information
        table = soup.find("table", {"class": "table"})

        # Check if the table is found
        if table:
            # Extract data from the table
            rows = table.find_all("tr")

            # Define a list to store Bond objects for each row
            bond_list = []

            if "No results found" in response.text:
                print("No results found.")
                return bond_list

            # Iterate through rows and extract data
            for row in rows:
                # Check if the row contains the header element, indicating it's a header row
                if row.find("th"):
                    continue

                columns = row.find_all(["td", "th"])

                try:
                    # Extract data from each column and create a Bond object
                    direct_url = f"https://markets.businessinsider.com{columns[0].find('a')['href']}"
                    bond = Bond(
                        issuer=columns[0].text.strip().split("\n")[0],
                        url=direct_url,
                        isin=direct_url.rsplit('-', 1)[-1],
                        currency=columns[1].text.strip(),
                        coupon=columns[2].text.strip(),
                        yield_=columns[3].text.strip(),
                        moodys_MoodyRating=columns[4].text.strip(),
                        maturity_date=columns[5].text.strip(),
                        bid=columns[6].text.strip(),
                        ask=columns[7].text.strip(),
                    )

                    # Append the Bond object to the list
                    bond_list.append(bond)

                except (AttributeError, IndexError) as e:
                    # Handle the case where the expected elements are not found
                    print(f"Skipping row: {row}")

            return bond_list

        else:
            print("Table not found on the webpage.")
            return []


    def get_all_bonds_for_combination(self, MoodyRating, maturity, yield_value):
        url = f"https://markets.businessinsider.com/bonds/finder?borrower=&maturity={maturity.value}&yield={yield_value.value}&bondtype=&coupon=&currency=&MoodyRating={MoodyRating.value}&country=18"
        print(f"url is: {url}")
        response = requests.get(url)

        if response.status_code == 200:
            bond_list = self.get_bonds_from_page(response)
            return bond_list
        else:
            print(
                f"Failed to retrieve the webpage for {MoodyRating.value}, {maturity.value}, {yield_value.value}. Status code: {response.status_code}"
            )
            return []

    def get_bonds_within_criteria(self, ratings: List[MoodyRating], maturity: List[Maturity], yield_values: List[Yield]):
        # Use itertools.product to generate all combinations of ratings, maturity, and yield_values
        all_combinations = product(ratings, maturity, yield_values)
        print(f"ratings: {ratings}")
        
        # List comprehension to process each combination
        all_bonds = [
            bond 
            for rating, mat, yld in all_combinations 
            for bond in self.get_all_bonds_for_combination(rating, mat, yld)
        ]
        
        return set(all_bonds)