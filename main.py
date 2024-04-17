import json
import os
from typing import List
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

from models import EmbeddableDocument, UrlDocument
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
import httpx
import requests
from dotenv import load_dotenv
from database import get_db, SECData, init_db
import uvicorn

from sec_service import SECService

#from sec_service import get_and_embed_all_latest_documents, get_cik_str_by_title, get_sec_headers

load_dotenv()
app = FastAPI()

secService = SECService()

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
@app.put("/fetch-sec-data")
async def fetch_and_store_sec_data(database=Depends(get_db)):
    try:
        # Fetch data from SEC endpoint using httpx
        sec_endpoint = "https://www.sec.gov/files/company_tickers.json"
        async with httpx.AsyncClient() as client:
            response = await client.get(sec_endpoint, headers=get_sec_headers())
            response.raise_for_status()  # Raise an exception for non-2xx responses
            sec_data = response.json()

        # Convert sec_data to a list of dictionaries
        data_list = [v for v in sec_data.values()]

        # Store data in the database with upsert based on the 'title' column
        for data in data_list:
            stmt = insert(SECData).values(data)
            stmt = stmt.on_conflict_do_update(
                constraint='uq_sec_data_title',
                set_=dict([(col.name, col) for col in stmt.excluded]),
            )
            database.execute(stmt)
        database.commit()

    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error fetching and storing SEC data: {e}")

    return {"message": "SEC data stored successfully"}
    
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