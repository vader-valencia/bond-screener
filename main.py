import json
import os
from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.declarative import declarative_base
import httpx
import requests
from dotenv import load_dotenv
from database import get_db, sec_table
import uvicorn


from sec_service import get_and_embed_all_latest_documents, get_cik_str_by_title, get_sec_headers

load_dotenv()
app = FastAPI()


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
            stmt = insert(sec_table).values(data)
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
    # You may want to implement the logic to retrieve or validate the company_name
    # For simplicity, let's assume you have a function to get the company's CIK

    try:
        await get_and_embed_all_latest_documents(company_name, database)
        return {"message": "Documents retrieved successfully"}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )