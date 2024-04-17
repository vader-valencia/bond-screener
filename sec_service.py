
from datetime import datetime
from enum import Enum
from typing import List
from bs4 import BeautifulSoup
from fastapi import HTTPException, status
from models import EmbeddableDocument, UrlDocument
from sqlalchemy import select, func, insert
import httpx
from sqlalchemy.orm import session, Session
from databases import Database

from database import DocumentMetadata, SECData
from embedding_manager import EmbeddingManager

class FilingDocuments(Enum):
    EightK = "8-K"
    EightKA = "8-K/A"
    TenK = "10-K"
    TenQ = "10-Q"

class SECService:
    def __init__(self):
        self.embeddingManager = EmbeddingManager()
        self.headers = {"User-Agent": "Mozilla/5.0"}

    async def get_filings(self, cik_str: str):
        # Add leading zeros to cik_str
        cik_str = str(cik_str).zfill(10)

        # Make a request to the SEC endpoint for filings
        filings_endpoint = f"https://data.sec.gov/submissions/CIK{cik_str}.json"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(filings_endpoint, headers=self.headers)
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
        

    def get_sec_filing_document(self, cik_str: int, accession_number: str, primary_document: str):
        # Construct the SEC document URL
        formatted_accession_number = accession_number.replace("-", "")
        document_url = f"https://www.sec.gov/Archives/edgar/data/{cik_str}/{formatted_accession_number}/{primary_document}"
        print(f"document url: {document_url}")
        return (document_url, accession_number, primary_document)


    async def fetch_filing_document(self, document_url):   #Fetch the document in HTML format
        async with httpx.AsyncClient() as client:
            response = await client.get(document_url, headers=self.headers)

            # Check if the request was successful (status code 200)
            if response.status_code == 200:
                return response.text
            else:
                # Raise an HTTPException if the request was not successful
                raise HTTPException(status_code=response.status_code, detail=f"Failed to fetch document. Status code: {response.status_code}")

    def get_latest_documents(self, cik_str, form_type: FilingDocuments, filings_list):
        most_recent_index = min((index for index, form in enumerate(filings_list["filings"]["filings"]["recent"]["form"]) if form == form_type.value), default=None)
        print(f"most_recent_index: {most_recent_index}")
        if most_recent_index is not None:
            accession_number = filings_list["filings"]["filings"]["recent"]["accessionNumber"][most_recent_index]
            primary_document = filings_list["filings"]["filings"]["recent"]["primaryDocument"][most_recent_index]
            return self.get_sec_filing_document(cik_str=cik_str, accession_number=accession_number, primary_document=primary_document)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"No filing available for cik:{cik_str}, form_type:{form_type}")
    from datetime import datetime

    async def get_all_latest_documents(self, company_name, database) -> List[UrlDocument]:
        cik_str = await self.get_cik_str_by_title(company_name, database)
        filings_list = await self.get_filings(cik_str)

        documents: List[UrlDocument] = []

        for form_type in FilingDocuments:
            try:
                print("going through the form tpes")
                # Get the latest document information
                (document_url, accession_number, primary_document_type) = self.get_latest_documents(cik_str, form_type, filings_list)
                documents.append(UrlDocument(
                    cik_str = cik_str,
                    accession_number = accession_number,
                    primary_document_type = str(form_type.value) ,
                    url = document_url 
                ))

            except HTTPException as e:
                print(f"Error: {e.detail}")
        return documents

    def document_already_exists_in_db(self, document: UrlDocument, database: Session) -> bool:
        # Build a query that matches all relevant fields except the timestamp
        query = select(DocumentMetadata).where(
            (DocumentMetadata.cik_str == document.cik_str) &
            (DocumentMetadata.accession_number == document.accession_number) &
            (DocumentMetadata.document_type == document.primary_document_type)
        )
        
        # Execute the query and fetch the first result
        result = database.execute(query).scalar_one_or_none()

        # Check if any result was found
        return result is not None

    async def get_filing_documents(self, documents: List[UrlDocument],  database: Session, overwrite=False) -> List[EmbeddableDocument]:
        documents_with_files = []
        for document in documents:
            document_preexists = self.document_already_exists_in_db(document, database)
            print("doc exists search done")
            if not(document_preexists) or (document_preexists and overwrite):
                document_text = await self.fetch_filing_document(document.url)
                print("fetched filing document")
                embeddableDocument = EmbeddableDocument(
                    cik_str = document.cik_str,
                    accession_number = document.accession_number,
                    primary_document = document_text,
                    primary_document_type = document.primary_document_type
                )
                documents_with_files.append(embeddableDocument)
        return documents_with_files

    async def store_company_documents(self, cik_str, documents: List[EmbeddableDocument], database):
        embedding_type = self.embeddingManager.get_embedding_type()
        model_name = self.embeddingManager.get_model_name()

        for document in documents:
            try:
                document_text = BeautifulSoup(document.primary_document, "lxml").getText()

                # Split the document text into chunks
                docs = self.embeddingManager.split_text(text=document_text, chunk_size=1500, overlap=150)
                
                # Save document metadata in the document_metadata table
                document_metadata_id = await self.save_document_metadata(database, 
                                                                    document.cik_str, 
                                                                    document.accession_number, 
                                                                    document.primary_document, 
                                                                    document.primary_document_type,
                                                                    embedding_type,
                                                                    model_name
                                                                    )                                                

                print("metadata saved")
                # Embed the document chunks and store them in the database
                metadata_list = [
                    {
                        "document_metadata_id": document_metadata_id,
                        "cik_str": cik_str,
                    }
                    for _ in docs
                ]
                self.embeddingManager.embed_documents(texts=docs, metadatas=metadata_list)
                print("document embedded")

            except HTTPException as e:
                print(f"Error: {e.detail}")

    async def get_cik_str_by_title(self, title: str, database: Session):
        # Create a SQLAlchemy select statement
        query = select([SECData.cik_str]).where(func.lower(SECData.title).ilike(func.lower(f"{title}")))

        # Execute the query and fetch the result
        result = database.execute(query)
        cik_result = result.scalar()

        return cik_result

    async def save_document_metadata(self, database: Session, cik_str, accession_number, primary_document, document_type, embedding_type, model_name):
        # Create a DocumentMetadata object
        print("made it to saving doc metadata")
        document_metadata = DocumentMetadata(
            cik_str=cik_str,
            accession_number=accession_number,
            primary_document=primary_document,
            document_type=document_type,  # Assuming FilingDocuments is an Enum
            timestamp=datetime.now()
        )
        
        # Add the DocumentMetadata object to the session
        try:
            database.add(document_metadata)
            database.commit()  # Commit the transaction to save changes to the database
            database.refresh(document_metadata)  # Refresh the object to get its updated ID
            print("refreshed db")
        except Exception as e:
            # Rollback the transaction in case of an error
            database.rollback()
            raise e

        return document_metadata.id  # Return the ID of the inserted record