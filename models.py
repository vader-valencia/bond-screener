from fastapi import File, Form
from pydantic import BaseModel


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