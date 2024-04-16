
from enum import Enum
from typing import List
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from models import UrlDocument
from sqlalchemy import select, func, insert
import httpx
from sqlalchemy.orm import session, Session
from databases import Database



from database import DocumentMetadata, SECData
from embedding_manager import EmbeddingManager

def get_sec_headers():
    return {"User-Agent": "Mozilla/5.0"}

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
    formatted_accession_number = accession_number.replace("-", "")
    document_url = f"https://www.sec.gov/Archives/edgar/data/{cik_str}/{formatted_accession_number}/{primary_document}"
    print(f"document url: {document_url}")
    return (document_url, accession_number, primary_document)

    # # Fetch the document in HTML format
    # async with httpx.AsyncClient() as client:
    #     response = await client.get(document_url, headers=get_sec_headers())

    #     # Check if the request was successful (status code 200)
    #     if response.status_code == 200:
    #         return (response.text, accession_number, primary_document)
    #     else:
    #         # Raise an HTTPException if the request was not successful
    #         raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch document. Status code: {response.status_code}")

class FilingDocuments(Enum):
    EightK = "8-K"
    EightKA = "8-K/A"
    TenK = "10-K"
    TenQ = "10-Q"

async def get_latest_documents(cik_str, form_type: FilingDocuments, filings_list):
    most_recent_index = min((index for index, form in enumerate(filings_list["filings"]["filings"]["recent"]["form"]) if form == form_type.value), default=None)
    print(f"most_recent_index: {most_recent_index}")
    if most_recent_index is not None:
        accession_number = filings_list["filings"]["filings"]["recent"]["accessionNumber"][most_recent_index]
        primary_document = filings_list["filings"]["filings"]["recent"]["primaryDocument"][most_recent_index]
        return await get_sec_filing_document(cik_str=cik_str, accession_number=accession_number, primary_document=primary_document)
    else:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No filing available for cik:{cik_str}, form_type:{form_type}")
from datetime import datetime

async def get_all_latest_documents(company_name, database) -> List[UrlDocument]:
    cik_str = await get_cik_str_by_title(company_name, database)
    print(f"cik_str is {cik_str}, company name is {company_name}")
    filings_list = await get_filings(cik_str)

    documents: List[UrlDocument] = []

    for form_type in FilingDocuments:
        try:
            # Get the latest document information
            (document_url, accession_number, primary_document_type) = await get_latest_documents(cik_str, form_type, filings_list)
            documents.append(UrlDocument(
                cik_str = cik_str,
                accession_number = accession_number,
                primary_document_type = primary_document_type ,
                url = document_url 
            ))

        except HTTPException as e:
            print(f"Error: {e.detail}")
    return documents

async def store_company_documents(company_name, documents, database):
    manager = EmbeddingManager()

    for document in documents:
        try:
            document_text = BeautifulSoup(document, "lxml").getText()

            # Split the document text into chunks
            docs = manager.split_text(text=document_text, chunk_size=1500, overlap=150)
            
            # Save document metadata in the document_metadata table
            document_metadata_id = await save_document_metadata(database, document.cik_str, document.accession_number, document.primary_document, document.form_type)

            # Embed the document chunks and store them in the database
            metadata_list = [
                {
                    "document_metadata_id": document_metadata_id,
                    "cik_str": cik_str,
                }
                for _ in docs
            ]
            manager.embed_documents(texts=docs, metadatas=metadata_list)

            item = BeautifulSoup(document, "lxml").find("FORM 10")
            print(f"item: {item}")
        except HTTPException as e:
            print(f"Error: {e.detail}")

async def get_cik_str_by_title(title: str, database: Session):
    # Create a SQLAlchemy select statement
    print(f"title is {title}")
    query = select([SECData.cik_str]).where(func.lower(SECData.title).ilike(func.lower(f"{title}")))
    #query = select([SECData.cik_str])

    # Execute the query and fetch the result
    result = database.execute(query)
    print(result)
    cik_result = result.scalar()

    return cik_result

async def save_document_metadata(database: Session, cik_str, accession_number, primary_document, document_type):
    # Create a DocumentMetadata object
    document_metadata = DocumentMetadata(
        cik_str=cik_str,
        accession_number=accession_number,
        primary_document=primary_document,
        document_type=document_type.value,  # Assuming FilingDocuments is an Enum
        timestamp=datetime.now()
    )
    
    # Add the DocumentMetadata object to the session
    try:
        database.add(document_metadata)
        database.commit()  # Commit the transaction to save changes to the database
        database.refresh(document_metadata)  # Refresh the object to get its updated ID
    except Exception as e:
        # Rollback the transaction in case of an error
        database.rollback()
        raise e

    return document_metadata.id  # Return the ID of the inserted record

    # Create a DocumentMetadata object
    document_metadata = DocumentMetadata(
        cik_str=cik_str,
        accession_number=accession_number,
        primary_document=primary_document,
        document_type=document_type.value,  # Assuming FilingDocuments is an Enum
        timestamp=datetime.now()
    )
    
    # Add the DocumentMetadata object to the session
    async with database() as session:
        session.add(document_metadata)
        session.commit()  # Commit the transaction to save changes to the database

    return document_metadata.id  # Return the ID of the inserted record