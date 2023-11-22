import requests
from bs4 import BeautifulSoup
from enum import Enum


class MoodyRating(Enum):
    Aaa = 1
    Aa1 = 2
    Aa2 = 3
    Aa3 = 4
    A1 = 5
    A2 = 6
    A3 = 7
    Baa1 = 8
    Baa2 = 9
    Baa3 = 10
    Ba1 = 11
    Ba2 = 12
    Ba3 = 13
    B1 = 14
    B2 = 15
    B3 = 16
    Caa1 = 17
    Caa2 = 18
    Caa3 = 19
    Ca = 20
    C = 21
    NR = 22
    WR = 23

    def __str__(self):
        return self.value

    def __lt__(self, other):
        return self.value < other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __ge__(self, other):
        return self.value >= other.value


class Maturity(Enum):
    ShortTerm = "shortterm"
    MidTerm = "midterm"
    LongTerm = "longterm"


class Yield(Enum):
    Zero = "0"
    Five = "5"
    Ten = "10"
    Twenty = "20"


class Bond:
    def __init__(
        self,
        issuer,
        url,
        currency,
        coupon,
        yield_,
        moodys_MoodyRating,
        maturity_date,
        bid,
        ask,
    ):
        self.issuer = issuer
        self.url = url
        self.currency = currency
        self.coupon = coupon
        self.yield_ = yield_
        self.moodys_MoodyRating = moodys_MoodyRating
        self.maturity_date = maturity_date
        self.bid = bid
        self.ask = ask


def get_bonds_from_page(response):
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
                bond = Bond(
                    issuer=columns[0].text.strip().split("\n")[0],
                    url=f"https://markets.businessinsider.com{columns[0].find('a')['href']}",
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


def get_all_bonds_for_combination(MoodyRating, maturity, yield_value):
    url = f"https://markets.businessinsider.com/bonds/finder?borrower=&maturity={maturity.value}&yield={yield_value.value}&bondtype=&coupon=&currency=&MoodyRating={MoodyRating.value}&country=18"
    print(url)
    response = requests.get(url)

    if response.status_code == 200:
        bond_list = get_bonds_from_page(response)
        return bond_list
    else:
        print(
            f"Failed to retrieve the webpage for {MoodyRating.value}, {maturity.value}, {yield_value.value}. Status code: {response.status_code}"
        )
        return []


def main():
    all_results = []

    for rating in MoodyRating:
        if rating >= MoodyRating.Baa3:
            for maturity in Maturity:
                for yield_value in Yield:
                    print("made another call")
                    bonds = get_all_bonds_for_combination(
                        str(rating), maturity, yield_value
                    )
                    all_results.extend(bonds)

    # Print the extracted data (you can also store it or process further)
    for bond in all_results:
        print(vars(bond))


if __name__ == "__main__":
    main()
