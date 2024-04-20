import json
import os
import sys
from typing import List
from fastapi import FastAPI, File, Query, UploadFile, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.routing import Match

from bond_service import BondService
from models import EmbeddableDocument, MoodyRating, Yield, Maturity, UrlDocument
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
import httpx
import requests
from dotenv import load_dotenv
from database import get_db, SECData, init_db
import uvicorn
from loguru import logger

from sec_service import SECService

#from sec_service import get_and_embed_all_latest_documents, get_cik_str_by_title, get_sec_headers

load_dotenv()


logger.remove()
logger.add(sys.stdout, colorize=True, format="<green>{time:HH:mm:ss}</green> | {level} | <level>{message}</level>")
app = FastAPI()


@app.middleware("http")
async def log_middle(request: Request, call_next):
    logger.debug(f"{request.method} {request.url}")
    routes = request.app.router.routes
    logger.debug("Params:")
    for route in routes:
        match, scope = route.matches(request)
        if match == Match.FULL:
            for name, value in scope["path_params"].items():
                logger.debug(f"\t{name}: {value}")
    logger.debug("Headers:")
    for name, value in request.headers.items():
        logger.debug(f"\t{name}: {value}")

    response = await call_next(request)
    return response


secService = SECService()
bondService = BondService()

origins = ["*"]
    # "http://localhost:5000",  # Adjust to match the URL of your frontend
    # "http://127.0.0.1:5000",


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of origins that are allowed to make requests
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)

# Define the endpoint to fetch and store SEC data
@app.put("/store-sec-data")
async def store_sec_data(database=Depends(get_db)):
    try:
        secService.store_sec_data(database)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching and storing SEC data: {e}")
    return {"message": "SEC data stored successfully"}

import re

def normalize_name(name):
    return re.sub(r'[^a-zA-Z0-9]', '', name).lower()

def combine_data(sec_data, bond_data):
    normalized_sec = {normalize_name(item.title): item for item in sec_data}
    combined_results = []

    for bond in bond_data:
        norm_name = normalize_name(bond.issuer)
        if norm_name in normalized_sec:
            sec_item = normalized_sec[norm_name]
            # Flatten attributes from both objects into a single dictionary
            combined_result = {
                "cik_str": sec_item.cik_str,
                "ticker": sec_item.ticker,
                "issuer": bond.issuer,
                "url": bond.url,
                "currency": bond.currency,
                "coupon": bond.coupon,
                "yield": bond.yield_,
                "moody_rating": bond.moodys_MoodyRating,
                "maturity_date": bond.maturity_date,
                "bid": bond.bid,
                "ask": bond.ask
            }
            combined_results.append(combined_result)

    # Sorting results based on the normalized name of the SEC title
    combined_results.sort(key=lambda x: normalize_name(x['issuer']))
    return combined_results

def parse_moody_ratings(ratings: List[int] = Query(...)):
    try:
        # Convert each integer value to the corresponding MoodyRating enum
        return [MoodyRating(value) for value in ratings]
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid rating value provided")


@app.get("/get-sec-data")
async def get_sec_data(
    database=Depends(get_db),
    ratings: List[MoodyRating] = Depends(parse_moody_ratings),
    maturities: List[Maturity] = Query([Maturity.MidTerm], description="List of maturities"),
    yields: List[Yield] = Query([Yield.Ten], description="List of yield values")
):
    try:
        sec_data = secService.get_all_sec_data(database)
        bond_data = bondService.get_bonds_within_criteria(ratings, maturities, yields)
        combined_data = combine_data(sec_data, bond_data)
        return combined_data
    except HTTPException as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")
    
@app.get("/get-company-documents/{company_name}")
async def get_company_documents(company_name: str, database=Depends(get_db)):
    try:
        documents: List[UrlDocument] = await secService.get_all_latest_documents(company_name, database)
        if not documents:
            raise HTTPException(status_code=404, detail="No documents found for the company")
        return documents #{"company_name": company_name, "documents": documents}
    except Exception as e:
        return {"error": str(e)}
    

@app.put("/store-company-documents")
async def store_company_documents(documents: List[UrlDocument], database=Depends(get_db)):
    try:
        cik_str = documents[0].cik_str
        documents_with_files = await secService.get_filing_documents(documents, database)
        print("got filing docs")
        await secService.store_company_documents(cik_str, documents_with_files, database)
        return {"message": f"Successfully created documents for cik: {cik_str}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
async def on_startup():
    await init_db()

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        debug=True
    )