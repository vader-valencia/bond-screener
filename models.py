from fastapi import File, Form
from pydantic import BaseModel
from enum import Enum


class UrlDocument(BaseModel):
    cik_str: str
    accession_number: str
    primary_document_type: str 
    url: str 

class EmbeddableDocument(BaseModel):
    cik_str: str
    accession_number: str
    primary_document: str 
    primary_document_type: str

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
        isin,
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
        self.isin = isin
        self.currency = currency
        self.coupon = coupon
        self.yield_ = yield_
        self.moodys_MoodyRating = moodys_MoodyRating
        self.maturity_date = maturity_date
        self.bid = bid
        self.ask = ask