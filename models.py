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
    form_type: str

class EmbeddableDocumentForm(BaseModel):
    cik_str: str = Form(...)
    accession_number: str = Form(...)
    primary_document: str = Form(...)
    form_type: str = Form(...)