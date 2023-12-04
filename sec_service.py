
from enum import Enum
from fastapi import HTTPException, status
from sqlalchemy import select, func
import httpx
from sqlalchemy.orm import Session


from database import sec_table

def get_sec_headers():
    return {"User-Agent": "Mozilla/5.0"}

async def get_cik_str_by_title(title: str, database: Session):
    # Create a SQLAlchemy select statement
    query = select([sec_table.c.cik_str]).where(func.lower(sec_table.c.title).ilike(func.lower(f"%{title}%")))

    # Execute the query and fetch the result
    result = database.execute(query)
    cik_result = result.scalar()

    return cik_result

async def get_filings(cik_str: str):
    # Add leading zeros to cik_str
    cik_str = str(cik_str).zfill(10)

    # Make a request to the SEC endpoint for filings
    filings_endpoint = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(filings_endpoint, headers=get_sec_headers())
            response.raise_for_status()  # Raise an exception for non-2xx responses
            filings_data = response.json()
            
            # Assuming filings_data is a JSON response containing filing information
            return {"filings": filings_data}

    except httpx.HTTPError as e:
        # Handle HTTP errors, for example, return a 404 if CIK is not found
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="CIK not found")

        # Raise an HTTPException with the actual error message
        raise HTTPException(status_code=e.response.status_code, detail=str(e))

    except Exception as e:
        # Handle other exceptions
        raise HTTPException(status_code=500, detail=str(e))


async def get_sec_filing_document(cik_str: int, accession_number: str, primary_document: str):
    # Construct the SEC document URL
    document_url = f"https://www.sec.gov/ix?doc=/Archives/edgar/data/{cik_str}/{accession_number}/{primary_document}"

    # Fetch the document in HTML format
    async with httpx.AsyncClient() as client:
        response = await client.get(document_url, headers=get_sec_headers())

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            print(response.text[0:10])
            return response.text
        else:
            # Raise an HTTPException if the request was not successful
            raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch document. Status code: {response.status_code}")

class FilingDocuments(Enum):
    EightK = "8-K"
    EightKA = "8-K/A"
    TenK = "10-K"
    TenQ = "10-Q"

async def get_latest_documents(cik_str, form_type: FilingDocuments, filings_list):
    most_recent_index = min((index for index, form in enumerate(filings_list["filings"]["filings"]["recent"]["form"]) if form == form_type.value), default=None)
    print(f"most_recent_index: {most_recent_index}")
    if most_recent_index is not None:
        accession_number = filings_list["filings"]["filings"]["recent"]["accessionNumber"][most_recent_index].replace("-", "")
        primary_document = filings_list["filings"]["filings"]["recent"]["primaryDocument"][most_recent_index]
        return await get_sec_filing_document(cik_str=cik_str, accession_number=accession_number, primary_document=primary_document)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No filing available for cik:{cik_str}, form_type:{form_type}")

async def test_documents_get(company_name, database):
    cik_str = await get_cik_str_by_title(company_name, database)
    filings_list = await get_filings(cik_str)

    for form_type in FilingDocuments:
        try:
            document = await get_latest_documents(cik_str, form_type, filings_list)
            print(f"First 10 lines of {form_type.value} document:")
            print(document[:10])
        except HTTPException as e:
            print(f"Error: {e.detail}")