import tkinter as tk
from tkinter import filedialog
import os
import base64
import pandas as pd
import numpy as np
from pandas import json_normalize
import requests
from simple_salesforce import Salesforce
from datetime import datetime
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.utils import formatdate

from configuracion import variable_requerida

# ============================================
# CONECTARME A SALESFORCE
# ============================================

def conectar_salesforce():
    consumer_key = variable_requerida("SF_CLIENT_ID")
    consumer_secret = variable_requerida("SF_CLIENT_SECRET")
    username = variable_requerida("SF_USERNAME")
    password = variable_requerida("SF_PASSWORD")


    login_url = "https://login.salesforce.com/services/oauth2/token"

    params = {
        "grant_type": "password",
        "client_id": consumer_key,
        "client_secret": consumer_secret,
        "username": username,
        "password": password
    }

    response = requests.post(login_url, data=params)
    response.raise_for_status()
    auth_response = response.json()

    access_token = auth_response["access_token"]
    instance_url = auth_response["instance_url"]

    sf = Salesforce(instance_url=instance_url, session_id=access_token)
    return sf


sf = conectar_salesforce()


def safe(val):
    return "" if pd.isna(val) else str(val)


def normalizar_case_number(val):
    s = str(val).strip().lstrip("0")
    return s if s else "0"


# ============================================
# FUNCIÓN API — RIDESHARE T9
# ============================================
def enviar_api_rideshare_t9(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType": "Rideshare - Phillips Law",
        "Key": variable_requerida("API_RIDESHARE_T9_KEY"),
        "dupcheck": "0",
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "custom894": "Rideshare - Phillips Law",
        "custom896": "No",
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "CellPhone": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "dob": safe(row.get("Date of Birth")),
        "Address1": safe(row.get("Address Street")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip Code")),
        "custom697": safe(row.get("Case Number")),
        "custom1016": safe(row.get("Incident Date"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# FUNCIÓN API — RIDESHARE T10
# ============================================
def enviar_api_rideshare_t10(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "29734",
        "lp_supplier_id": "92858",
        "lp_key": variable_requerida("API_RIDESHARE_T10_KEY"),
        "first_name": safe(row.get("First Name")),
        "last_name": safe(row.get("Last Name")),
        "phone": safe(row.get("Phone Number")),
        "email": safe(row.get("Email")),
        "date_of_birth": safe(row.get("Date of Birth")),
        "gender": safe(row.get("Gender")),
        "address": safe(row.get("Address Street")),
        "city": safe(row.get("City")),
        "zip_code": int(row.get("Zip Code")) if row.get("Zip Code") != "NA" else None,
        "ip_address": safe(row.get("IP Address")),
        "landing_page_url": safe(row.get("Landing Page URL")),
        "trustedform_cert_url": safe(row.get("Trusted Form")),
        "abuse_where": safe(row.get("Were You Abused In An Uber Or Lyft Ride")),
        "type_of_abuse": safe(row.get("Type Of Abuse Experienced")),
        "has_attorney": safe(row.get("Attorney")),
        "proof_of_incident": safe(row.get("Got Proof Of The Rideshare Incident")),
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — DOCUMENTO RIDESHARE T10
# ============================================
def enviar_documento_rideshare_t10(lead_id, ruta_pdf):
    url = variable_requerida("API_RIDESHARE_T10_DOCUMENT_URL")

    headers = {
        "Authorization": variable_requerida("API_RIDESHARE_T10_DOCUMENT_AUTHORIZATION")
    }

    data = {
        "lead_id": lead_id
    }

    with open(ruta_pdf, "rb") as fh:
        files = {
            "pdf_name": (os.path.basename(ruta_pdf), fh, "application/pdf")
        }
        response = requests.post(url, headers=headers, data=data, files=files)

    return response



# ============================================
# FUNCIÓN API — RIDESHARE T11
# ============================================
def enviar_api_rs11(row):
    url = variable_requerida("API_SHARED_CAMPAIGNS_URL")

    headers = {
        "Authorization": variable_requerida("API_SHARED_CAMPAIGNS_AUTHORIZATION"),
        "Content-Type": "application/json"
    }

    payload = {
        "campaignId": "1351",
        "tcpaConsent": True,
        "firstName": safe(row.get("First Name")),
        "lastName": safe(row.get("Last Name")),
        "phone": safe(row.get("Phone Number")),
        "zipCode": safe(row.get("Zip Code")),
        "email": safe(row.get("Email")),
        "ipAddress": safe(row.get("IP Address")),
        "abuse_type": safe(row.get("Abuse Type")),
        "receipt": safe(row.get("Receipt")),
        "year": safe(row.get("Incident Year")),
        "suffer_abuse": safe(row.get("Suffer Abuse")),
        "reported": safe(row.get("Reported")),
        "description": safe(row.get("Abuse Details")),
        "lpUrl": safe(row.get("Landing Page")),
        "trustedFormCertUrl": safe(row.get("Trusted Form"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response

# ============================================
# FUNCIÓN API — RIDESHARE T12 & T13 & T14 & T15
# ============================================
def enviar_api_ridehsare_t12_t13_14(row):
    url = variable_requerida("API_RIDESHARE_T12_T14_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
      "Request": {
        "Key": variable_requerida("API_RIDESHARE_T12_T13_14_KEY"),
        "API_Action": "pingPostLead",
        "Mode": "full",
        "SRC": "IMG360",
        "TYPE": "35",
        "Email": safe(row.get("Email")),
        "Primary_Phone": safe(row.get("Phone Number")),
        "First_Name": safe(row.get("First Name")),
        "Last_Name": safe(row.get("Last Name")),
        "Address": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip Code")),
        "DOB": safe(row.get("DOB")),
        "Have_Attorney": safe(row.get("Have Attorney")),
        "Rideshare_Assault": safe(row.get("Rideshare Assault")),
        "Injured_Party": safe(row.get("Passenger or Driver")),
        "Assault_Details": safe(row.get("Assault Details")),
        "Incident_Date": safe(row.get("Incident Date")),
        "Digital_Receipt": safe(row.get("Digital Receipt")),
        "Police_Report": safe(row.get("Police Report")),
        "Reported": safe(row.get("Reported")),
        "Date_Reported": safe(row.get("Date Reported")),
        "When_Reported": safe(row.get("When Reported")),
        "Incident_Details": safe(row.get("Incident Details")),
        "Trusted_Form_URL": safe(row.get("Trusted Form URL")),
        "Landing_Page": safe(row.get("Landing Page")),
        "IP_Address": safe(row.get("IP Address")),
        "Rideshare_Company": safe(row.get("Rideshare Company")),
        "Gender": safe(row.get("Gender")),
        "State_Of_Incident": safe(row.get("State Of Incident")),
        "Comments": safe(row.get("Comments")),
        "Lead_ID": safe(row.get("Case Number")),
        "Reported_To_Name": safe(row.get("Reported To Name")),
        "Reported_To_Relationship": safe(row.get("Reported To Relationship")),
        "Reported_To_Address": safe(row.get("Reported To Address")),
        "Reported_To_Phone": safe(row.get("Reported To Phone")),
        "Reported_To_Date": safe(row.get("Reported To Date")),
        "Permission_To_Contact": safe(row.get("Permission To Contact")),
        "How_Shared": safe(row.get("How Shared"))
      }
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — BARD PORT T2
# ============================================
def enviar_api_bardport_t2(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "33926",
        "lp_supplier_id": "110027",
        "lp_key": variable_requerida("API_BARDPORT_T2_KEY"),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "CellPhone": safe(row.get("Phone Number")),
        "Email": safe(row.get("Email")),
        "have_attorney": safe(row.get("Attorney")),
        "received_port": safe(row.get("Receied an Implanted Port Catheter")),
        "catheter_issues": safe(row.get("Cathther Issues"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response



# ============================================
# FUNCIÓN API — BARD PORT T3
# ============================================

def enviar_api_bardport_t3(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType": "Glassman - Bard Powerport",
        "Key": variable_requerida("API_RIDESHARE_T9_KEY"),
        "dupcheck": "0",
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "custom894": "Glassman - Bard Powerport",
        "custom897": "Glassman",
        "custom896": "No",
        "custom754": "IMG-" + safe(row.get("Case Number")),
        "custom697": safe(row.get("Case Number")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "custom1079": safe(row.get("First Name")),
        "custom1080": safe(row.get("Last Name")),
        "dob": safe(row.get("Date of Birth")),
        "CellPhone": safe(row.get("Phone Number")),
        "custom1081": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "custom1082": safe(row.get("Email")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "custom1083": safe(row.get("Retainer Signed Date")),
        "custom775":safe(row.get("Date of Diagnosis"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for _, ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# CORREO CON DOCUMENTOS ADJUNTOS
# ============================================

def conectar_correo():
    smtp_server = "smtp.office365.com"
    smtp_port   = 587
    from_email  = variable_requerida("SMTP_API_USERNAME")
    email_pass  = variable_requerida("SMTP_PASSWORD")

    server = smtplib.SMTP(smtp_server, smtp_port)
    try:
        server.ehlo()
        server.starttls()
        server.login(from_email, email_pass)
    except Exception:
        server.close()
        raise
    return server, from_email


def enviar_correo_adjuntos_bard_port_t3(row, campaign, archivos):
    TO_EMAILS = ["masstort@jeffreysglassman.com"]
    CC_EMAILS = ["sergio@imgcorp.us", "alonso@imgcorp.us", "vanessa@imgcorp.us", "romina@imgcorp.us", "katherine@imgcorp.us",
                 "manuel@imgcorp.us", "jocelyn@imgcorp.us", "christyjen@imgcorp.us", "bruno@imgcorp.us"]

    case_number = safe(row.get("Case Number"))
    nombre = f"{safe(row.get('First Name'))} {safe(row.get('Last Name'))}".strip()

    msg = MIMEMultipart()
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Cc"] = ", ".join(CC_EMAILS)
    msg["Date"] = formatdate(localtime=True)
    producto = re.sub(r"\s+T\d+\b", "", campaign) 
    msg["Subject"] = f"{producto} – IMG-{case_number} – {nombre}"

    cuerpo = (
        f"Hi team,\n\n"
        f"Please find attached the Intake Questionnaire, HIPAA and Retainer for {nombre}. This has been pushed via API.\n\n"
        f"Let us know if you have any questions or require further clarification.\n\n"
        f"Thanks!\n"
    )
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    for tipo, ruta in archivos:
        with open(ruta, "rb") as fh:
            parte = MIMEApplication(fh.read(), _subtype="pdf")
        parte.add_header("Content-Disposition", "attachment", filename=os.path.basename(ruta))
        msg.attach(parte)

    server, from_email = conectar_correo()
    msg["From"] = from_email
    try:
        server.sendmail(from_email, TO_EMAILS + CC_EMAILS, msg.as_string())
    finally:
        server.quit()

# ============================================
# FUNCIÓN API — BARD PORT T4
# ============================================
def enviar_api_bard_port_t4(row):
    url = variable_requerida("API_BARD_PORT_T4_WEBHOOK_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "uniqueid": safe(row.get("Case Number")),
        "s1-s9": "s1",
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": safe(row.get("Ip Address")),
        "xxTrustedFormCertUrl": safe(row.get("Trusted Form")),
        "fname": safe(row.get("First Name")),
        "lname": safe(row.get("Last Name")),
        "phone": safe(row.get("Phone Number")),
        "email": safe(row.get("Email")),
        "attorney": safe(row.get("Do you have an attorney?")),
        "year": safe(row.get("Was a port implanted in 2013 or later?")),
        "brand": safe(row.get("Do you know the Port-A-Cath brand?")),
        "injury": safe(row.get("Did you experience any of the following complications or injuries?")),
        "implant": safe(row.get("When did the complication first occur after the Port-A-Cath was implanted?")),
        "removed": safe(row.get("Was the Port-A-Cath removed because of the complication or injury?")),
        "state": safe(row.get("In what state did the implant or treatment occur?"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response




# Bard Port T5 no tiene API: solo se envía por correo. Devuelve el asunto para guardarlo en Salesforce.
def enviar_correo_adjuntos_bard_port_t5(row, archivos):
    TO_EMAILS = ["lexie@adreachiq.com"]
    CC_EMAILS = ["sergio@imgcorp.us", "alonso@imgcorp.us", "vanessa@imgcorp.us", "romina@imgcorp.us", "katherine@imgcorp.us",
                 "manuel@imgcorp.us", "jocelyn@imgcorp.us", "christyjen@imgcorp.us", "bruno@imgcorp.us"]

    nombre = f"{safe(row.get('First Name'))} {safe(row.get('Last Name'))}".strip()
    asunto = f"IMG - Bard Port Case - {nombre}"

    msg = MIMEMultipart()
    msg["To"] = ", ".join(TO_EMAILS)
    msg["Cc"] = ", ".join(CC_EMAILS)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = asunto

    cuerpo = (
        f"Hi team,\n\n"
        f"Please find attached the Intake Questionnaire, HIPAA, Retainer and Portal Patient Authorization for {nombre}.\n\n"
        f"Let us know if you have any questions or require further clarification.\n\n"
        f"Thanks!\n"
    )
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    for tipo, ruta in archivos:
        with open(ruta, "rb") as fh:
            parte = MIMEApplication(fh.read(), _subtype="pdf")
        parte.add_header("Content-Disposition", "attachment", filename=os.path.basename(ruta))
        msg.attach(parte)

    server, from_email = conectar_correo()
    msg["From"] = from_email
    try:
        server.sendmail(from_email, TO_EMAILS + CC_EMAILS, msg.as_string())
    finally:
        server.quit()

    return asunto

# ============================================
# FUNCIÓN API — DEPO PROVERA T7 STINAR
# ============================================
def enviar_api_depoprovera_t7_stinar(row, archivos=None):
    url = variable_requerida("API_SHARED_INTAKE_URL")

    payload = {
        "Key": variable_requerida("API_DEPOPROVERA_T7_STINAR_KEY"),
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "CaseType":"Depo - Stinar Lannen Pulaski - IMG",
        "Status":"Signed Contract Intake Complete",
        "Custom4567": "NA",
        "Custom4568": "NA",
        "Custom4569": "NA",
        "Custom4570": "NA",
        "Custom4582": "NA",
        "Custom4583": "NA",
        "Custom4584": "NA",
        "Custom4585": "NA",
        "Custom4547": "NA",
        "CellPhone": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email Address")),
        "FirstName": safe(row.get("Injured Party First Name")),
        "LastName": safe(row.get("Injured Party Last Name")),
        "Address1": safe(row.get("Injured Party Street Address")),
        "City": safe(row.get("Injured Party City")),
        "State": safe(row.get("Injured Party State")),
        "Zip": safe(row.get("Injured Party Zip Code")),
        "DOB": safe(row.get("Injured Party Date of Birth")),
        "Custom4542": safe(row.get("Injured Party Date of Death")),
        "SSN": safe(row.get("Injured Party SSN")),
        "Custom4543": safe(row.get("Injured Party Last Four SSN")),
        "Custom4544": safe(row.get("OBO First Name")),
        "Custom4545": safe(row.get("OBO Last Name")),
        "Custom4546": safe(row.get("OBO Relationship to Injured Party")),
        "Custom4548": safe(row.get("OBO City")),
        "Custom4549": safe(row.get("OBO State")),
        "Custom4550": safe(row.get("OBO Zip Code")),
        "Custom4551": safe(row.get("Start Date")),
        "Custom4552": safe(row.get("Stop Date")),
        "Custom4651": safe(row.get("What were you taking Depo Provera for?")),
        "Custom4553": safe(row.get("Usage 1 Generic?")),
        "Custom4554": safe(row.get("Usage 1 Start Date")),
        "Custom4555": safe(row.get("Usage 1 Stop Date")),
        "Custom4556": safe(row.get("Usage 1 Pharmacy Name")),
        "Custom4557": safe(row.get("Usage 1 Pharmacy Address")),
        "Custom4558": safe(row.get("Usage 1 Pharmacy Phone")),
        "Custom4559": safe(row.get("Usage 2 Generic?")),
        "Custom4560": safe(row.get("Usage 2 Start Date")),
        "Custom4561": safe(row.get("Usage 2 Stop Date")),
        "Custom4562": safe(row.get("Usage 2 Pharmacy Name")),
        "Custom4563": safe(row.get("Usage 2 Pharmacy Address")),
        "Custom4564": safe(row.get("Usage 2 Pharmacy Phone")),
        "Custom4565": safe(row.get("Diagnosed with Meningioma?")),
        "Custom4566": safe(row.get("Diagnosis Date")),
        "Custom4652": safe(row.get("How many meningiomas do you have?")),
        "Custom4653": safe(row.get("Location of your meningioma(s)?")),
        "Custom4654": safe(row.get("What treatment have you undergone for your meningioma(s)")),
        "Custom4571": safe(row.get("Diagnosing Doctor Name")),
        "Custom4572": safe(row.get("Diagnosing Facility Name")),
        "Custom4573": safe(row.get("Diagnosing Facility Address")),
        "Custom4574": safe(row.get("Diagnosing Facility Phone")),
        "Custom4575": safe(row.get("Treating Doctor Name")),
        "Custom4576": safe(row.get("Treating Facility Name")),
        "Custom4577": safe(row.get("Treating Facility Address")),
        "Custom4578": safe(row.get("Treating Facility Phone")),
        "Custom4579": safe(row.get("PCP Name")),
        "Custom4580": safe(row.get("PCP Address")),
        "Custom4581": safe(row.get("PCP Phone")),
        "Custom4586": safe(row.get("Medical Notes")),
        "Custom4587": safe(row.get("Notes")),
        "Custom4588": safe(row.get("Emergency Contact Name")),
        "Custom4589": safe(row.get("Emergency Contact Relationship")),
        "Custom4590": safe(row.get("Emergency Contact Address")),
        "Custom4591": safe(row.get("Emergency Contact Phone")),
        "Custom4592": safe(row.get("Emergency Contact Email"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("File", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response

# ============================================
# FUNCIÓN API — DEPO PROVERA T7 HICKORY
# ============================================
def enviar_api_depoprovera_t7_hickory(row, archivos=None):
    url = variable_requerida("API_SHARED_INTAKE_URL")

    payload = {
        "Key": variable_requerida("API_DEPOPROVERA_T7_STINAR_KEY"),
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "CaseType":"Depo - BD Hickory - IMG",
        "Status":"Signed Contract Intake Complete",
        "Custom4567": "NA",
        "Custom4568": "NA",
        "Custom4569": "NA",
        "Custom4570": "NA",
        "Custom4582": "NA",
        "Custom4583": "NA",
        "Custom4584": "NA",
        "Custom4585": "NA",
        "Custom4547": "NA",
        "CellPhone": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email Address")),
        "FirstName": safe(row.get("Injured Party First Name")),
        "LastName": safe(row.get("Injured Party Last Name")),
        "Address1": safe(row.get("Injured Party Street Address")),
        "City": safe(row.get("Injured Party City")),
        "State": safe(row.get("Injured Party State")),
        "Zip": safe(row.get("Injured Party Zip Code")),
        "DOB": safe(row.get("Injured Party Date of Birth")),
        "Custom4542": safe(row.get("Injured Party Date of Death")),
        "SSN": safe(row.get("Injured Party SSN")),
        "Custom4543": safe(row.get("Injured Party Last Four SSN")),
        "Custom4544": safe(row.get("OBO First Name")),
        "Custom4545": safe(row.get("OBO Last Name")),
        "Custom4546": safe(row.get("OBO Relationship to Injured Party")),
        "Custom4548": safe(row.get("OBO City")),
        "Custom4549": safe(row.get("OBO State")),
        "Custom4550": safe(row.get("OBO Zip Code")),
        "Custom4551": safe(row.get("Start Date")),
        "Custom4552": safe(row.get("Stop Date")),
        "Custom4651": safe(row.get("What were you taking Depo Provera for?")),
        "Custom4553": safe(row.get("Usage 1 Generic?")),
        "Custom4554": safe(row.get("Usage 1 Start Date")),
        "Custom4555": safe(row.get("Usage 1 Stop Date")),
        "Custom4556": safe(row.get("Usage 1 Pharmacy Name")),
        "Custom4557": safe(row.get("Usage 1 Pharmacy Address")),
        "Custom4558": safe(row.get("Usage 1 Pharmacy Phone")),
        "Custom4559": safe(row.get("Usage 2 Generic?")),
        "Custom4560": safe(row.get("Usage 2 Start Date")),
        "Custom4561": safe(row.get("Usage 2 Stop Date")),
        "Custom4562": safe(row.get("Usage 2 Pharmacy Name")),
        "Custom4563": safe(row.get("Usage 2 Pharmacy Address")),
        "Custom4564": safe(row.get("Usage 2 Pharmacy Phone")),
        "Custom4565": safe(row.get("Diagnosed with Meningioma?")),
        "Custom4566": safe(row.get("Diagnosis Date")),
        "Custom4652": safe(row.get("How many meningiomas do you have?")),
        "Custom4653": safe(row.get("Location of your meningioma(s)?")),
        "Custom4654": safe(row.get("What treatment have you undergone for your meningioma(s)")),
        "Custom4571": safe(row.get("Diagnosing Doctor Name")),
        "Custom4572": safe(row.get("Diagnosing Facility Name")),
        "Custom4573": safe(row.get("Diagnosing Facility Address")),
        "Custom4574": safe(row.get("Diagnosing Facility Phone")),
        "Custom4575": safe(row.get("Treating Doctor Name")),
        "Custom4576": safe(row.get("Treating Facility Name")),
        "Custom4577": safe(row.get("Treating Facility Address")),
        "Custom4578": safe(row.get("Treating Facility Phone")),
        "Custom4579": safe(row.get("PCP Name")),
        "Custom4580": safe(row.get("PCP Address")),
        "Custom4581": safe(row.get("PCP Phone")),
        "Custom4586": safe(row.get("Medical Notes")),
        "Custom4587": safe(row.get("Notes")),
        "Custom4588": safe(row.get("Emergency Contact Name")),
        "Custom4589": safe(row.get("Emergency Contact Relationship")),
        "Custom4590": safe(row.get("Emergency Contact Address")),
        "Custom4591": safe(row.get("Emergency Contact Phone")),
        "Custom4592": safe(row.get("Emergency Contact Email"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("File", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response



# ============================================
# FUNCIÓN API — DEPO PROVERA T8
# ============================================
def enviar_api_depoprovera_t8(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "32464",
        "lp_supplier_id": "110026",
        "lp_key": variable_requerida("API_DEPOPROVERA_T8_KEY"),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "CellPhone": safe(row.get("Phone Number")),
        "Email": safe(row.get("Email")),
        "have_attorney": safe(row.get("Attorney")),
        "use_depo": safe(row.get("Used Depo")),
        "tumor": safe(row.get("Diagnosed with Meningioma"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — TALCUM T15
# ============================================
def enviar_api_talcum_t15(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "19002",
        "lp_supplier_id": "108899",
        "lp_key": variable_requerida("API_TALCUM_T15_KEY"),
        "lp_subid2":"00a1",
        "first_name": safe(row.get("First Name")),
        "last_name": safe(row.get("Last Name")),
        "phone": safe(row.get("Phone Number")),
        "email": safe(row.get("Email")),
        "date_of_birth": safe(row.get("Date of Birth")),
        "gender": safe(row.get("Gender")),
        "address": safe(row.get("Address Street")),
        "city": safe(row.get("City")),
        "state": safe(row.get("State")),
        "zip_code": safe(row.get("Zip Code")),
        "ip_address": safe(row.get("IP Address")),
        "landing_page_url": safe(row.get("Landing Page URL")),
        "trustedform_cert_url": safe(row.get("Trusted Form")),
        "cancer_after_using_talc": safe(row.get("Used J&J Shower Talcum Last 5 Years")),
        "diagnosed_cancer": safe(row.get("Diagnosis")),
        "have_attorney": safe(row.get("Attorney")),
        "diagnosed_year": safe(row.get("Diagnosis Year")),
    }

    response = requests.post(url, json=payload, headers=headers)
    return response

# ============================================
# FUNCIÓN API — WOMENS PRISIONER ABUSE T1
# ============================================
def enviar_api_womens_prisioner_abuse_t1(row, archivos=None):
    url = variable_requerida("API_SHARED_INTAKE_URL")

    payload = {
        "Key": variable_requerida("API_DEPOPROVERA_T7_STINAR_KEY"),
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "CaseType":"WDC - BD Hickory - IMG",
        "Status":"Signed Contract Intake Complete",
        "Custom4910": "Womens Detention Center",
        "Custom4896":"NA",
        "SSN":"NA",
        "Custom4897": "NA",
        "Custom4898": "NA",
        "Custom4899":"NA",
        "Custom4900":"NA",
        "Custom4901":"NA",
        "Custom4902":"NA",
        "Custom4903":"NA",
        "Custom4904":"NA",
        "Email1": safe(row.get("Email")),
        "CellPhone": safe(row.get("Cell Phone")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "DOB": safe(row.get("DOB")),
        "Custom4911": safe(row.get("Perpetrator Name")),
        "Custom4912": safe(row.get("Perpetrator Title")),
        "Custom4913": safe(row.get("Juvenile Detention Center Name")),
        "Custom4914": safe(row.get("What years were you at the center?")),
        "Custom4915": safe(row.get("How did you end up being sent to the center?")),
        "Custom4916": safe(row.get("What City/State were you sent from?")),
        "Custom4917": safe(row.get("Date of Abuse")),
        "Custom4918": safe(row.get("How did you first come into contact with them?")),
        "Custom4919": safe(row.get("Abuse Details")),
        "Custom4920": safe(row.get("Abuse Location")),
        "Custom4923": safe(row.get("Number of Times You Were Abused")),
        "Custom4924": safe(row.get("Were they ever subjected to any physical abuse?")),
        "Custom4925": safe(row.get("Physical Abuse Details")),
        "Custom4926": safe(row.get("Heared of others abused")),
        "Custom4927": safe(row.get("Did you report the abuse")),
        "Custom4928": safe(row.get("Who did you report this to?")),
        "Custom4929": safe(row.get("When did you report this?")),
        "Custom4930": safe(row.get("Outcome after reporting the abuse")),
        "Custom4931": safe(row.get("Issues from Abuse")),
        "Custom4932": safe(row.get("Treatment Details")),
        "Custom4933": safe(row.get("Additional Notes")),
        "Custom4934": safe(row.get("Best Contact Method")),
        "Custom4905": safe(row.get("Emergency Contact Name")),
        "Custom4906": safe(row.get("Emergency Contact Relationship")),
        "Custom4907": safe(row.get("Emergency Contact Address")),
        "Custom4908": safe(row.get("Emergency Contact Phone")),
        "Custom4909": safe(row.get("Emergency Contact Email")),
        "Custom4942": safe(row.get("Prision ID"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("File", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# FUNCIÓN API — WOMENS PRISIONER ABUSE T2
# ============================================
def enviar_api_womens_prisioner_abuse_t2(row):
    url = variable_requerida("API_LEAD_PORTAL_CAMPAIGNS_URL")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {
        "lp_campaign_id": "6a4ea0914bbac",
        "lp_campaign_key": variable_requerida("API_WOMENS_PRISIONER_ABUSE_T2_KEY"),
        "country": "US",
        "first_name": safe(row.get("First Name")),
        "last_name": safe(row.get("Last Name")),
        "phone_home": safe(row.get("Phone Number")),
        "email_address": safe(row.get("Email")),
        "ip_address": safe(row.get("IP Address")),
        "trusted_form_cert_id": safe(row.get("Trusted Form Id")),
        "experienced_sex_abuse": safe(row.get("Were you or a loved one sexually abused at a Womens Detention Center?")),
        "abuse_from": safe(row.get("Was the abuse from another inmate or Law Enforcement/Corrections Officer/Guard?"))
    }

    response = requests.post(url, data=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — WOMENS PRISIONER ABUSE T3
# ============================================

def enviar_api_womens_prisioner_abuse_t3(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType": "ARC Law - WDC Abuse",
        "Key": variable_requerida("API_RIDESHARE_T9_KEY"),
        "dupcheck": "0",
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "custom894": "ARC Law - WDC Abuse",
        "custom897": "ARC Law",
        "custom896": "No",
        "custom754": "IMG-" + safe(row.get("Case Number")),
        "custom697": safe(row.get("Case Number")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "custom1079": safe(row.get("First Name")),
        "custom1080": safe(row.get("Last Name")),
        "dob": safe(row.get("Date of Birth")),
        "CellPhone": safe(row.get("Phone Number")),
        "custom1081": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "custom1082": safe(row.get("Email")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "custom1083": safe(row.get("Retainer Signed Date")),
        "custom1016":safe(row.get("Date of Abuse"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for _, ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response




# ============================================
# FUNCIÓN API — CHLORPYRIFOS T1
# ============================================
def enviar_api_chlorpyrifos_t1(row, archivos=None):
    url = variable_requerida("API_CHLORPYRIFOS_T1_URL")

    payload = {
        "LeadProvider": "International Media Group",
        "Hear": "International Media Group",
        "Key": variable_requerida("API_CHLORPYRIFOS_T1_KEY"),
        "Status":"Signed Retainer Contract",
        "CaseType":"Chlorpyrifos",
        "dupcheck":"0",
        "custom796":"Wagstaff",
        "custom797":"IMG",
        "WhenToContact":"Anytime",
        "FullName": safe(row.get("Full Name")),
        "CellPhone": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "DOB": safe(row.get("DOB")),
        "custom792": safe(row.get("First Name")),
        "custom793": safe(row.get("Last Name")),
        "custom794": safe(row.get("First Name")),
        "custom795": safe(row.get("Last Name")),
        "custom798": safe(row.get("Code"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("File", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# FUNCIÓN API — CHLORPYRIFOS T2
# ============================================
def enviar_api_chlorpyrifos_t2(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "35550",
        "lp_supplier_id": "119203",
        "lp_key": variable_requerida("API_CHLORPYRIFOS_T2_KEY"),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "CellPhone": safe(row.get("Phone Number")),
        "Email": safe(row.get("Email")),
        "injured_party_full_name": safe(row.get("Full Name")),
        "State": safe(row.get("State")),
        "ip_address": safe(row.get("IP Address")),
        "landing_page_url": safe(row.get("Landing Page")),
        "trustedform_cert_url": safe(row.get("Trusted Form URL")),
        "tcpa_text": safe(row.get("Trusted Form ID")),
        "have_attorney": safe(row.get("Do you have an attorney?")),
        "parkinsons": safe(row.get("Parkinson's disease after being exposed?")),
        "farm_land": safe(row.get("Did you live or work near CPF?")),
        "chlorpyrifos": safe(row.get("Did you use CPF?"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — ASBESTOS T1
# ============================================
def enviar_api_asbestos_t1(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "35424",
        "lp_supplier_id": "117798",
        "lp_key": variable_requerida("API_ASBESTOS_T1_KEY"),
        "lp_subid1": "NA",
        "lp_subid2": "NA",
        "user_agent":"WordPress/7.0.1; https://campaigns.legalhelpadvisor.com",
        "first_name": safe(row.get("First Name")),
        "last_name": safe(row.get("Last Name")),
        "email": safe(row.get("Email")),
        "phone": safe(row.get("Phone Number")),
        "date_of_birth": safe(row.get("DOB")),
        "gender": safe(row.get("Gender")),
        "address": safe(row.get("Address")),
        "city": safe(row.get("City")),
        "state": safe(row.get("State")),
        "zip_code": int(row.get("Zip")) if pd.notna(row.get("Zip")) else None,
        "ip_address": safe(row.get("IP Address")),
        "landing_page_url": safe(row.get("Landing Page")),
        "trustedform_cert_url": safe(row.get("Trusted Form URL")),
        "tcpa_text": safe(row.get("Trusted Form ID")),
        "diagnosed": safe(row.get("Diagnosed")),
        "exposed": safe(row.get("Exposed")),
        "has_attorney": safe(row.get("Do you have an attorney?")),
        "deceased": safe(row.get("Deceased")),
        "diagnosis_year": safe(row.get("When was the injured party diagnosed?")),
        "death_year": safe(row.get("When did the injured party pass away?"))  
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — ASBESTOS T1 - TURNDOWNCASES
# ============================================
def enviar_api_asbestos_t1_turndowncases(row):
    url = variable_requerida("API_LEAD_PORTAL_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "lp_campaign_id": "35424",
        "lp_supplier_id": "117798",
        "lp_key": variable_requerida("API_ASBESTOS_T1_KEY"),
        "lp_subid1": "NA",
        "lp_subid2": "b0987767",
        "ip_address":"11.111.111.11",
        "zip_code": 55555,
        "state":"NY",
        "exposed":"5+ years",
        "diagnosed":"Lung cancer",
        "has_attorney":"No",
        "deceased":"No",
        "diagnosis_year":"Less than 1 year ago",
        "landing_page_url":"landingpage.com",
        "user_agent":"WordPress/7.0.1; https://campaigns.legalhelpadvisor.com",
        "first_name": safe(row.get("First Name")),
        "last_name": safe(row.get("Last Name")),
        "email": safe(row.get("Email")),
        "phone": safe(row.get("Phone Number")),
        "date_of_birth": safe(row.get("DOB")),
        "gender": safe(row.get("Gender")),
        "address": safe(row.get("Address")),
        "city": safe(row.get("City")),
        "trustedform_cert_url": safe(row.get("Trusted Form URL")),
        "tcpa_text": safe(row.get("Trusted Form ID"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response



# ============================================
# FUNCIÓN API — JUVENILE DETENTION CENTER T3
# ============================================
def enviar_api_juvenile_detention_center_t3(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType":"CA JDC Abuse - Phillips Law",
        "Key":variable_requerida("API_RIDESHARE_T9_KEY"),
        "LeadProvider":"IMG",
        "Hear":"IMG",
        "custom894":"CA JDC Abuse - Phillips Law",
        "custom897":"Phillips Law",
        "custom699":"NA",
        "custom700":"NA",


        "Email1": safe(row.get("Email")),
        "CellPhone": safe(row.get("Phone Number")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "dob": safe(row.get("Date of Birth")),
        "custom697": safe(row.get("Case Number")),
        "custom1016": safe(row.get("Date of Abuse"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response

# ============================================
# FUNCIÓN API — JUVENILE DETENTION CENTER T4
# ============================================
def enviar_api_juvenile_detention_center_t4(row):
    url = variable_requerida("API_LEAD_PORTAL_CAMPAIGNS_URL")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    payload = {
        "lp_campaign_id": "6a4e9f4f4873c",
        "lp_campaign_key": variable_requerida("API_JUVENILE_DETENTION_CENTER_T4_KEY"),
        "country": "US",
        "first_name": safe(row.get("First Name")),
        "last_name": safe(row.get("Last Name")),
        "phone_home": safe(row.get("Phone Number")),
        "email_address": safe(row.get("Email")),
        "ip_address": safe(row.get("IP Address")),
        "trusted_form_cert_id": safe(row.get("Trusted Form Id")),
        "experienced_sex_abuse_gov_institute": safe(row.get("Were you victim of harassment or abuse?")),
        "under_18": safe(row.get("Were you or your loved one under the age of 18 at the time of the sexual abuse?")),
        "subcategory": safe(row.get("Where did the abuse take place?"))
    }

    response = requests.post(url, data=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — JUVENILE DETENTION CENTER T5
# ============================================

def enviar_api_juvenile_detention_center_t5(row):
    url = variable_requerida("API_SHARED_CAMPAIGNS_URL")

    headers = {
        "Authorization": variable_requerida("API_SHARED_CAMPAIGNS_AUTHORIZATION"),
        "Content-Type": "application/json"
    }

    payload = {
        "campaignId": "3230",
        "tcpaConsent": True,
        "firstName": safe(row.get("First Name")),
        "lastName": safe(row.get("Last Name")),
        "email": safe(row.get("Email")),
        "phone": safe(row.get("Phone Number")),
        "zipCode": safe(row.get("Zip Code")),
        "description": safe(row.get("Abuse Details")),
        "ipAddress": safe(row.get("Ip Address")),
        "lpUrl": safe(row.get("Landing Page")),
        "facility": safe(row.get("Juvenile Detention Center Name")),
        "abuse_minor": safe(row.get("Minor underage at the time?")),
        "abuse_role": safe(row.get("What was their position at the facility?")),
        "abuse_type": safe(row.get("Were they ever physically abused?")),
        "can_name_abuser": safe(row.get("Do you know the name of the person?")),
        "trustedFormCertUrl": safe(row.get("Trusted Form")),
        "attorney": safe(row.get("Do you have an attorney?"))
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — JUVENILE DETENTION CENTER T6
# ============================================

def enviar_api_juvenile_detention_center_t6(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType": "Stinar Lannen - JDC Abuse",
        "Key": variable_requerida("API_RIDESHARE_T9_KEY"),
        "dupcheck": "0",
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "custom894": "Stinar Lannen - JDC Abuse",
        "custom897": "Stinar Lannen",
        "custom896": "No",
        "custom1077": "LPC-V_PAJDC_IMG",
        "custom754": "IMG-" + safe(row.get("Case Number")),
        "custom697": safe(row.get("Case Number")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "custom1079": safe(row.get("First Name")),
        "custom1080": safe(row.get("Last Name")),
        "dob": safe(row.get("Date of Birth")),
        "CellPhone": safe(row.get("Phone Number")),
        "custom1081": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "custom1082": safe(row.get("Email")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "custom1083": safe(row.get("Retainer Signed Date")),
        "custom1016": safe(row.get("Date of Abuse"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for _, ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# FUNCIÓN API — OLYMPUS T1
# ============================================
def enviar_api_olympus_t1(row):
    url = variable_requerida("API_OLYMPUS_T1_WEBHOOK_URL")

    headers = {
        "Content-Type": "application/json"
    }

    payload = {
        "s1-s9": "s1",
        "user_agent": "WordPress/7.0.1; https://campaigns.legalhelpadvisor.com",
        "date": safe(row.get("Current Date/Time")),
        "uniqueid": safe(row.get("Case Number")),
        "ip": safe(row.get("IP Address")),
        "xxTrustedFormCertUrl": safe(row.get("Trusted Form")),
        "fname": safe(row.get("First Name")),
        "lname": safe(row.get("Last Name")),
        "phone": safe(row.get("Phone Number")),
        "email": safe(row.get("Email")),
        "qualify": safe(row.get("Did you have a scope or endoscopic procedure from the list below?")),
        "procedure": safe(row.get("Did the infection occur within 1 year after the procedure?")),
        "after": safe(row.get("Was the infection after 2015?")),
        "medical": safe(row.get("Did you experience any of the following infections?")),
        "hospital": safe(row.get("Were you hospitalized and given IV antibiotics?")),
        "state": safe(row.get("What state did you get the procedure in?")),
        "records": safe(row.get("Are you able to obtain your medical records?")),
        "attorney": safe(row.get("Are you currently working with an attorney?")),
    }

    response = requests.post(url, json=payload, headers=headers)
    return response


# ============================================
# FUNCIÓN API — OLYMPUS T2
# ============================================

def enviar_api_olympus_t2(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType": "Stinar Lannen - Olympus Scopes",
        "Key": variable_requerida("API_RIDESHARE_T9_KEY"),
        "dupcheck": "0",
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "custom894": "Stinar Lannen - Olympus Scopes",
        "custom897": "Stinar Lannen",
        "custom896": "No",
        "custom1077": "LPC-V_SCOPES_IMG",
        "custom754": "IMG-" + safe(row.get("Case Number")),
        "custom697": safe(row.get("Case Number")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "custom1079": safe(row.get("First Name")),
        "custom1080": safe(row.get("Last Name")),
        "dob": safe(row.get("Date of Birth")),
        "CellPhone": safe(row.get("Phone Number")),
        "custom1081": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "custom1082": safe(row.get("Email")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "custom1083": safe(row.get("Retainer Signed Date")),
        "custom1016": safe(row.get("Date of Abuse"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for _, ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# FUNCIÓN API — SEX TRAFFICKING T1
# ============================================

def enviar_api_sex_trafficking_t1(row):

    url = variable_requerida("API_SHARED_CAMPAIGNS_URL")
    headers = {
        "Authorization": variable_requerida("API_SHARED_CAMPAIGNS_AUTHORIZATION"),
        "Content-Type": "application/json"
    }
    payload = {
        "campaignId": "3202",
        "tcpaConsent": True,
        "firstName": safe(row.get("First Name")),
        "lastName": safe(row.get("Last Name")),
        "email": safe(row.get("Email")),
        "phone": safe(row.get("Phone Number")),
        "zipCode": safe(row.get("Zip Code")),
        "ipAddress": safe(row.get("Ip Address")),
        "lpUrl": safe(row.get("Landing Page")),
        "hotel_g6_chain": safe(row.get("Did the trafficking occur at a Motel 6, Studio 6, or Studio 6 Plus?")),
        "trafficking_minor": safe(row.get("Were you a minor when the incident occurred?")),
        "incident_before_2019": safe(row.get("Did this happen in 2018 or earlier?")),
        "knows_trafficker_name": safe(row.get("Do you know the name of the trafficker or pimp involved?")),
        "trustedFormCertUrl": safe(row.get("Trusted Form"))
    }
    response = requests.post(url, json=payload, headers=headers)
    return response



# ============================================
# FUNCIÓN API — HERNIA MESH T1
# ============================================

def enviar_api_hernia_mesh_t1(row, archivos=None):
    host = variable_requerida("API_HERNIA_MESH_HOST")
    url = f"{host}/services/apexrest/dclegal/intake/v1"

    token = requests.post(
        f"{host}/services/oauth2/token",
        data={
            "grant_type": "client_credentials",
            "client_id": variable_requerida("API_HERNIA_MESH_CLIENT_ID"),
            "client_secret": variable_requerida("API_HERNIA_MESH_CLIENT_SECRET"),
        },
    ).json()["access_token"]

    payload = {
        "partner_intake_id": "IMG-" + safe(row.get("Case Number")),
        "harms": [h.strip() for h in safe(row.get("Hernia Mesh Harms")).split(";") if h.strip()],

        "contact": {
            "Email": safe(row.get("Email")),
            "Phone": safe(row.get("Phone Number")),
            "FirstName": safe(row.get("First Name")),
            "LastName": safe(row.get("Last Name")),
            "MailingStreet": safe(row.get("Address")),
            "MailingCity": safe(row.get("City")),
            "MailingStateCode": safe(row.get("State")),
            "MailingCountryCode": "US",
            "MailingPostalCode": safe(row.get("Zip")),
            "Birthdate": safe(row.get("Date of Birth")),
            "SSN_Last_Four__c": safe(row.get("SSN Last Four"))
        },

        "case": {
            "Marketer__c": "IMG",
            "Mass_Tort__c": "Hernia Mesh",
            "Law_Firm__c": "Lanier Law Firm",
            "Firm_Status__c": "Pending",

            "Retainer_Signed_Date__c": safe(row.get("Retainer Signed Date")),
            "State_of_Occurrence__c": safe(row.get("State of Incident")),
            "Date_of_Incident__c": safe(row.get("Incident Date")),
            "Case_Summary__c": safe(row.get("Additional Notes"))
        }
    }

    # archivos: [("Retainer", "r.pdf"), ("HIPAA", "h.pdf"), ("Intake Questionnaire", "q.pdf")]
    if archivos:
        files_data = []
        for tipo, ruta in archivos:
            with open(ruta, "rb") as fh:
                files_data.append({
                    "type": tipo,
                    "name": os.path.basename(ruta),
                    "content_base64": base64.b64encode(fh.read()).decode("ascii"),
                    "mime_type": "application/pdf"
                })
        payload["files"] = files_data

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)

    return response


# ============================================
# FUNCIÓN API — HERNIA MESH T1 SMART REVIEWS
# ============================================

def enviar_api_hernia_mesh_t1_smart_reviews(row, archivos=None):
    url = variable_requerida("API_RIDESHARE_T9_URL")

    payload = {
        "CaseType": "Hernia Mesh - Lanier Law Firm",
        "Key": variable_requerida("API_RIDESHARE_T9_KEY"),
        "dupcheck": "0",
        "LeadProvider": "IMG",
        "Hear": "IMG",
        "custom894": "Hernia Mesh - Lanier Law Firm",
        "custom897": "Lanier Law Firm",
        "custom896": "No",
        "custom1077": "DC Legal Advisory Group",
        "custom754": "IMG-" + safe(row.get("Case Number")),
        "custom697": safe(row.get("Case Number")),
        "FirstName": safe(row.get("First Name")),
        "LastName": safe(row.get("Last Name")),
        "custom1079": safe(row.get("First Name")),
        "custom1080": safe(row.get("Last Name")),
        "dob": safe(row.get("Date of Birth")),
        "CellPhone": safe(row.get("Phone Number")),
        "custom1081": safe(row.get("Phone Number")),
        "Email1": safe(row.get("Email")),
        "custom1082": safe(row.get("Email")),
        "Address1": safe(row.get("Address")),
        "City": safe(row.get("City")),
        "State": safe(row.get("State")),
        "Zip": safe(row.get("Zip")),
        "custom1083": safe(row.get("Retainer Signed Date")),
        "custom775":safe(row.get("Date of Diagnosis"))
    }

    if archivos:
        handles = []
        files_data = []
        try:
            for _, ruta in archivos:
                fh = open(ruta, "rb")
                handles.append(fh)
                files_data.append(("file", (os.path.basename(ruta), fh)))
            response = requests.post(url, data=payload, files=files_data)
        finally:
            for fh in handles:
                fh.close()
    else:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

    return response



# Social Media Addiction no tiene API: solo se envía por correo. Se mandan dos correos separados:
#   - Ventura Law: los 4 documentos (ID, Retainer, Intake Questionnaire, Audio)
#   - AWKO: todo menos el Audio

def enviar_correo_adjuntos_social_media_addiction_t1_full(row, archivos):
    return _enviar_correo_social_media_addiction_t1(row, archivos, ["nicole@venturalaw.com"])


def enviar_correo_adjuntos_social_media_addiction_t1_no_mp3(row, archivos):
    archivos = [(tipo, ruta) for tipo, ruta in archivos if tipo != "Audio"]
    return _enviar_correo_social_media_addiction_t1(row, archivos, ["awkonewreferrals@awkolaw.com"])


# Envía el correo y devuelve el asunto para guardarlo en Salesforce.
def _enviar_correo_social_media_addiction_t1(row, archivos, to_emails):
    CC_EMAILS = ["sergio@imgcorp.us", "alonso@imgcorp.us", "vanessa@imgcorp.us", "romina@imgcorp.us", "katherine@imgcorp.us",
                 "manuel@imgcorp.us", "jocelyn@imgcorp.us", "christyjen@imgcorp.us", "bruno@imgcorp.us"]

    nombre = f"{safe(row.get('First Name'))} {safe(row.get('Last Name'))}".strip()
    asunto = f"IMG - Social Media Addiction Case - {nombre}"

    msg = MIMEMultipart()
    msg["To"] = ", ".join(to_emails)
    msg["Cc"] = ", ".join(CC_EMAILS)
    msg["Date"] = formatdate(localtime=True)
    msg["Subject"] = asunto

    # El cuerpo nombra solo los documentos realmente adjuntos
    tipos = [tipo for tipo, _ in archivos]
    if len(tipos) > 1:
        lista = ", ".join(tipos[:-1]) + " and " + tipos[-1]
    else:
        lista = tipos[0] if tipos else "documents"
    cuerpo = (
        f"Hi team,\n\n"
        f"Please find attached the {lista} for {nombre}.\n\n"
        f"Let us know if you have any questions or require further clarification.\n\n"
        f"Thanks!\n"
    )
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    for tipo, ruta in archivos:
        with open(ruta, "rb") as fh:
            if ruta.lower().endswith(".mp3"):
                parte = MIMEAudio(fh.read(), _subtype="mpeg")
            else:
                parte = MIMEApplication(fh.read(), _subtype="pdf")
        parte.add_header("Content-Disposition", "attachment", filename=os.path.basename(ruta))
        msg.attach(parte)

    server, from_email = conectar_correo()
    msg["From"] = from_email
    try:
        server.sendmail(from_email, to_emails + CC_EMAILS, msg.as_string())
    finally:
        server.quit()

    return asunto



# ============================================
# MOSTRAR RESPUESTA API
# ============================================
def mostrar_respuesta_api(response, titulo="Respuesta API"):
    ventana = tk.Toplevel()
    ventana.title(titulo)
    ventana.geometry("700x400")

    frame = tk.Frame(ventana)
    frame.pack(fill="both", expand=True, padx=10, pady=10)

    scrollbar = tk.Scrollbar(frame)
    scrollbar.pack(side="right", fill="y")

    text = tk.Text(frame, wrap="word", yscrollcommand=scrollbar.set)
    text.pack(fill="both", expand=True)

    scrollbar.config(command=text.yview)

    contenido = f"""STATUS CODE:
{response.status_code}

RESPONSE BODY:
{response.text}
"""

    text.insert("1.0", contenido)
    text.config(state="disabled")


# ============================================
# VENTANA — SUBIR DOCUMENTO RIDESHARE T10
# ============================================
def mostrar_ventana_documento_rideshare_t10(lead_id, sf_case_id, post_response_text):
    ventana = tk.Toplevel()
    ventana.title("Subir Documento - Rideshare T10")
    ventana.configure(bg=BG)
    ventana.resizable(False, False)
    ventana.grab_set()

    ancho, alto = 480, 430
    ventana.update_idletasks()
    x = (ventana.winfo_screenwidth() // 2) - (ancho // 2)
    y = (ventana.winfo_screenheight() // 2) - (alto // 2)
    ventana.geometry(f"{ancho}x{alto}+{x}+{y}")

    hdr = tk.Frame(ventana, bg="#1E293B")
    hdr.pack(fill="x")
    tk.Label(hdr, text="Subir Documento", font=("Segoe UI", 13, "bold"),
             bg="#1E293B", fg="white", padx=16).pack(anchor="w", pady=(12, 2))
    tk.Label(hdr, text="El lead ya fue enviado. Falta adjuntar el documento firmado.",
             font=("Segoe UI", 9), bg="#1E293B", fg="#94A3B8", padx=16
             ).pack(anchor="w", pady=(0, 12))

    tk.Frame(ventana, bg=PRIMARY, height=3).pack(fill="x")

    # --- Botón fijo abajo: se empaqueta ANTES que el área de contenido para
    # reservar su espacio (si no, el body con expand=True se lo come todo) ---
    btn_frame = tk.Frame(ventana, bg=BG, padx=16, pady=12)
    btn_frame.pack(fill="x", side="bottom")
    tk.Frame(btn_frame, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))

    btn_subir = tk.Button(
        btn_frame, text="Subir documento",
        bg=DIS_BG, fg=DIS_FG, activebackground=PRIMARY_HV, activeforeground="white",
        font=("Segoe UI", 11, "bold"), relief="flat", bd=0, cursor="arrow", pady=10,
        state="disabled",
    )
    btn_subir.pack(fill="x")

    body = tk.Frame(ventana, bg=BG, padx=20, pady=18)
    body.pack(fill="both", expand=True)

    # --- Lead ID ---
    tk.Label(body, text="LEAD ID", font=("Segoe UI", 9, "bold"),
             bg=BG, fg=TEXT_MUTED, anchor="w").pack(fill="x")

    lead_box = tk.Frame(body, bg="white", highlightbackground=BORDER, highlightthickness=1)
    lead_box.pack(fill="x", pady=(4, 18))
    tk.Label(lead_box, text=lead_id, font=("Consolas", 11), bg="white",
             fg=TEXT_DARK, anchor="w", padx=10, pady=8).pack(fill="x")

    # --- Documento PDF ---
    tk.Label(body, text="DOCUMENTO PDF", font=("Segoe UI", 9, "bold"),
             bg=BG, fg=TEXT_MUTED, anchor="w").pack(fill="x")

    doc_box = tk.Frame(body, bg="white", highlightbackground=BORDER, highlightthickness=1)
    doc_box.pack(fill="x", pady=(4, 4))

    doc_inner = tk.Frame(doc_box, bg="white", padx=10, pady=10)
    doc_inner.pack(fill="x")

    ruta_seleccionada = {"path": None}

    lbl_archivo = tk.Label(doc_inner, text="Ningún archivo seleccionado", font=("Segoe UI", 9),
                            bg="white", fg=TEXT_MUTED, anchor="w")
    lbl_archivo.pack(side="left", fill="x", expand=True)

    def actualizar_estado_boton():
        if ruta_seleccionada["path"]:
            btn_subir.config(state="normal", bg=PRIMARY, fg="white", cursor="hand2")
        else:
            btn_subir.config(state="disabled", bg=DIS_BG, fg=DIS_FG, cursor="arrow")

    def quitar_archivo():
        ruta_seleccionada["path"] = None
        lbl_archivo.config(text="Ningún archivo seleccionado", fg=TEXT_MUTED)
        btn_quitar.pack_forget()
        actualizar_estado_boton()

    btn_quitar = tk.Button(
        doc_inner, text="✕", command=quitar_archivo, font=("Segoe UI", 8, "bold"),
        fg="#EF4444", bg="white", bd=0, cursor="hand2", padx=4,
    )

    def seleccionar_pdf():
        ruta = filedialog.askopenfilename(
            title="Seleccionar PDF",
            filetypes=[("Archivos PDF", "*.pdf")]
        )
        if ruta:
            ruta_seleccionada["path"] = ruta
            lbl_archivo.config(text=os.path.basename(ruta), fg=TEXT_DARK)
            btn_quitar.pack(side="right")
            actualizar_estado_boton()

    tk.Button(
        body, text="+ Seleccionar PDF", command=seleccionar_pdf,
        font=("Segoe UI", 9), bg=DIS_BG, fg=TEXT_DARK,
        activebackground="#E2E8F0", relief="flat", bd=0,
        cursor="hand2", padx=10, pady=6,
    ).pack(anchor="w", pady=(8, 0))

    lbl_estado = tk.Label(body, text="", font=("Segoe UI", 9), bg=BG, fg=TEXT_MUTED, anchor="w")
    lbl_estado.pack(fill="x", pady=(14, 0))

    def subir_documento():
        ruta = ruta_seleccionada["path"]
        if not ruta:
            return
        btn_subir.config(state="disabled", text="Subiendo...", bg=DIS_BG, fg=DIS_FG, cursor="arrow")
        lbl_estado.config(text="Subiendo documento, espera un momento...", fg=TEXT_MUTED)
        ventana.update_idletasks()
        try:
            response = enviar_documento_rideshare_t10(lead_id, ruta)
            mostrar_respuesta_api(response)
            if response.status_code in [200, 201]:
                sf_status = enviar_api_resultado(sf_case_id, post_response_text)
                print("Actualización Salesforce (PDF):", sf_status)
                ventana.destroy()
            else:
                lbl_estado.config(text="El servidor respondió con un error, revisa el detalle.", fg="#EF4444")
                btn_subir.config(state="normal", text="Subir documento", bg=PRIMARY, fg="white", cursor="hand2")
        except Exception as e:
            lbl_estado.config(text="", fg=TEXT_MUTED)
            btn_subir.config(state="normal", text="Subir documento", bg=PRIMARY, fg="white", cursor="hand2")
            mostrar_error(str(e))

    btn_subir.config(command=subir_documento)


# ============================================
# FUNCIÓN OBTENER DATOS — RIDESHARE T9
# ============================================
def obtener_datos_rideshare_t9(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Incident_Date__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000fksnQYAQ' AND Lead__r.Status ='Sent' AND Lead__r.Type='Rideshare'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.FirstName__c','Lead__r.Last_Name__c','Lead__r.Email__c','Lead__r.Phone_Numbercontact__c','Lead__r.Date_of_Birth__c','Lead__r.Address_Street__c',
        'Lead__r.City__c','Lead__r.StateUS__c','Lead__r.Area_Code__c','Lead__r.Incident_Date__c','Lead__r.CaseNumber'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Address_Street__c': 'Address Street',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.CaseNumber':'Case Number',
        'Lead__r.Incident_Date__c':'Incident Date'
    })

    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    df_sent["Date of Birth"] = pd.to_datetime(df_sent["Date of Birth"]).dt.strftime("%m/%d/%Y")
    df_sent["Incident Date"] = pd.to_datetime(df_sent["Incident Date"]).dt.strftime("%m/%d/%Y")

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent

# ============================================
# FUNCIÓN OBTENER DATOS — RIDESHARE T10
# ============================================
def obtener_datos_rideshare_t10(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Area_Code__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.Email__c,
            Lead__r.Gender__c,
            Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c,
            Lead__r.Do_you_have_an_attorney__c,
            Lead__r.What_type_of_abuse_did_you_experience__c,
            Lead__r.Got_proof_of_the_rideshare_incident__c,
            Lead__r.Trusted_Form__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.ip_address__c,
            Lead__r.Date_of_Birth__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000igX9ZYAU' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Rideshare'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.Area_Code__c', 'Lead__r.Address_Street__c',
        'Lead__r.City__c', 'Lead__r.Email__c', 'Lead__r.Gender__c', 'Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c', 'Lead__r.Do_you_have_an_attorney__c',
        'Lead__r.What_type_of_abuse_did_you_experience__c', 'Lead__r.Got_proof_of_the_rideshare_incident__c', 'Lead__r.Trusted_Form__c', 'Lead__r.Landing_Page_URL__c',
        'Lead__r.ip_address__c', 'Lead__r.Date_of_Birth__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.Address_Street__c': 'Address Street',
        'Lead__r.City__c': 'City',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Gender__c': 'Gender',
        'Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c': 'Were You Abused In An Uber Or Lyft Ride',
        'Lead__r.Do_you_have_an_attorney__c': 'Attorney',
        'Lead__r.What_type_of_abuse_did_you_experience__c': 'Type Of Abuse Experienced',
        'Lead__r.Got_proof_of_the_rideshare_incident__c': 'Got Proof Of The Rideshare Incident',
        'Lead__r.Trusted_Form__c': 'Trusted Form',
        'Lead__r.Landing_Page_URL__c': 'Landing Page URL',
        'Lead__r.ip_address__c': 'IP Address',
        'Lead__r.Date_of_Birth__c': 'Date of Birth'
    })

    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    date_columns = ["Date of Birth"]

    df_sent[date_columns] = df_sent[date_columns].apply(
        lambda col: pd.to_datetime(col, errors="coerce").dt.strftime("%Y-%m-%d")
    )

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — RIDESHARE T11
# ============================================
def obtener_datos_rs11(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
        SELECT
        Lead__r.Id,
        Lead__r.FirstName__c,
        Lead__r.Last_Name__c,
        Lead__r.Phone_Numbercontact__c,
        Lead__r.Area_Code__c,
        Lead__r.Email__c,
        Lead__r.ip_address__c,
        Lead__r.What_describes_the_misconduct__c,
        Lead__r.Have_a_Receipt__c,
        Lead__r.Incident_Date__c,
        Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c,
        Lead__r.Reported_to_any_of_the_following__c,
        Lead__r.Abuse_Details__c,
        Lead__r.Landing_Page_URL__c,
        Lead__r.Trusted_Form__c,
        Lead__r.CaseNumber
        FROM Lead_de_oportunidad__c
        WHERE Oportunidad__r.AccountId='001TR00000LRBBNYA5'
        AND Lead__r.Substatus__c='Transferred'
        AND Lead__r.Type='Rideshare'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c',
        'Lead__r.Phone_Numbercontact__c', 'Lead__r.Area_Code__c',
        'Lead__r.Email__c', 'Lead__r.ip_address__c',
        'Lead__r.What_describes_the_misconduct__c',
        'Lead__r.Have_a_Receipt__c', 'Lead__r.Incident_Date__c',
        'Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c',
        'Lead__r.Reported_to_any_of_the_following__c',
        'Lead__r.Abuse_Details__c',
        'Lead__r.Landing_Page_URL__c',
        'Lead__r.Trusted_Form__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.Email__c': 'Email',
        'Lead__r.ip_address__c': 'IP Address',
        'Lead__r.What_describes_the_misconduct__c': 'Abuse Type',
        'Lead__r.Have_a_Receipt__c': 'Receipt',
        'Lead__r.Incident_Date__c': 'Incident Year',
        'Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c': 'Suffer Abuse',
        'Lead__r.Reported_to_any_of_the_following__c': 'Reported',
        'Lead__r.Abuse_Details__c': 'Abuse Details',
        'Lead__r.Landing_Page_URL__c': 'Landing Page',
        'Lead__r.Trusted_Form__c': 'Trusted Form'
    })

    df_sent['Receipt'] = df_sent['Receipt'].str.lower()
    df_sent['Suffer Abuse'] = df_sent['Suffer Abuse'].str.lower()

    mapping_reported = {
        "Rideshare Company": "rideshare_company",
        "Therapist": "therapist",
        "Physician": "physician",
        "Police Department": "police_dept",
        "Friend or Family Member": "friend_or_family_member",
        "No": "didnt_report"
    }

    df_sent['Reported'] = df_sent['Reported'].map(mapping_reported).fillna("NA")

    df_sent['Incident Year'] = pd.to_datetime(df_sent['Incident Year'], errors='coerce').dt.year
    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    return df_sent



# =================================================
# FUNCIÓN OBTENER DATOS — RIDESHARE T12 | T13 | 14
# =================================================
def obtener_datos_rideshare_t12_t13_t14(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Date_of_Death__c,
            Lead__r.Signer_SSN__c,
            Lead__r.Signer_Last_4_SSN__c,
            Lead__r.VictimName__c,
            Lead__r.VictimLName__c,
            Lead__r.Victim_Mailing_Address__c,
            Lead__r.Victim_City__c,
            Lead__r.Victim_State__c,
            Lead__r.Victim_Zipcode__c,
            Lead__r.Relationship_to_the_victim__c,
            Lead__r.Do_you_have_an_attorney__c,
            Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c,
            Lead__r.Passenger_or_Driver__c,
            Lead__r.What_type_of_abuse_did_you_experience__c,
            Lead__r.Incident_Date__c,
            Lead__r.Have_a_Receipt__c,
            Lead__r.Is_there_a_police_report__c,
            Lead__r.Reported_to_any_of_the_following__c,
            Lead__r.When_was_the_abuse_reported__c,
            Lead__r.Abuse_Details__c,
            Lead__r.Trusted_Form__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.ip_address__c,
            Lead__r.Uber_or_Lyft__c,
            Lead__r.Gender__c,
            Lead__r.State_of_Incident__c,
            Lead__r.Additional_Notes__c,
            Lead__r.What_is_this_person_s_full_name__c,
            Lead__r.What_s_your_relationship_to_this_person__c,
            Lead__r.What_is_this_person_s_address__c,
            Lead__r.What_s_this_person_s_phone_number__c,
            Lead__r.When_did_you_tell_them__c,
            Lead__r.May_the_attorneys_contact_this_person__c,
            Lead__r.How_did_you_share_the_information__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000pGZ66YAG' AND Lead__r.Status='Sent' AND Lead__r.Type='Rideshare'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.CaseNumber','Lead__r.Email__c','Lead__r.Phone_Numbercontact__c','Lead__r.FirstName__c','Lead__r.Last_Name__c','Lead__r.Address_Street__c','Lead__r.City__c',
        'Lead__r.StateUS__c', 'Lead__r.Area_Code__c','Lead__r.Date_of_Birth__c','Lead__r.Do_you_have_an_attorney__c',
        'Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c','Lead__r.Passenger_or_Driver__c','Lead__r.What_type_of_abuse_did_you_experience__c',
        'Lead__r.Incident_Date__c','Lead__r.Have_a_Receipt__c','Lead__r.Is_there_a_police_report__c','Lead__r.Reported_to_any_of_the_following__c',
        'Lead__r.When_was_the_abuse_reported__c','Lead__r.Abuse_Details__c','Lead__r.Trusted_Form__c',
        'Lead__r.Landing_Page_URL__c','Lead__r.ip_address__c','Lead__r.Uber_or_Lyft__c','Lead__r.Gender__c','Lead__r.State_of_Incident__c','Lead__r.Additional_Notes__c',
        'Lead__r.What_is_this_person_s_full_name__c','Lead__r.What_s_your_relationship_to_this_person__c','Lead__r.What_is_this_person_s_address__c','Lead__r.What_s_this_person_s_phone_number__c',
        'Lead__r.When_did_you_tell_them__c','Lead__r.May_the_attorneys_contact_this_person__c','Lead__r.How_did_you_share_the_information__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Address_Street__c': 'Address',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.Date_of_Birth__c': 'DOB', 
        'Lead__r.Do_you_have_an_attorney__c': 'Have Attorney',
        'Lead__r.Were_you_abused_in_an_Uber_or_Lyft_ride__c': 'Rideshare Assault',
        'Lead__r.Passenger_or_Driver__c': 'Passenger or Driver',
        'Lead__r.What_type_of_abuse_did_you_experience__c': 'Assault Details',
        'Lead__r.Incident_Date__c': 'Incident Date',
        'Lead__r.Have_a_Receipt__c': 'Digital Receipt',
        'Lead__r.Is_there_a_police_report__c': 'Police Report',
        'Lead__r.Reported_to_any_of_the_following__c': 'Reported',
        'Lead__r.When_was_the_abuse_reported__c': 'Date Reported',

        'Lead__r.Abuse_Details__c': 'Incident Details',

        'Lead__r.Uber_or_Lyft__c': 'Rideshare Company',
        'Lead__r.Gender__c': 'Gender',
        'Lead__r.State_of_Incident__c': 'State Of Incident',
        'Lead__r.Additional_Notes__c': 'Comments',

        'Lead__r.What_is_this_person_s_full_name__c': 'Reported To Name',
        'Lead__r.What_s_your_relationship_to_this_person__c': 'Reported To Relationship',
        'Lead__r.What_is_this_person_s_address__c': 'Reported To Address',
        'Lead__r.What_s_this_person_s_phone_number__c': 'Reported To Phone',
        'Lead__r.When_did_you_tell_them__c': 'Reported To Date',

        'Lead__r.May_the_attorneys_contact_this_person__c': 'Permission To Contact',
        'Lead__r.How_did_you_share_the_information__c': 'How Shared',

        'Lead__r.Landing_Page_URL__c': 'Landing Page',
        'Lead__r.ip_address__c': 'IP Address',
        'Lead__r.Trusted_Form__c': 'Trusted Form URL'
    })

    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    df_sent["DOB"] = pd.to_datetime(df_sent["DOB"], errors='coerce').dt.strftime("%m/%d/%Y")
    df_sent["Incident Date"] = pd.to_datetime(df_sent["Incident Date"], errors='coerce').dt.strftime("%m/%d/%Y")

    # Convertir fechas
    incident_dt = pd.to_datetime(df_sent["Incident Date"], errors="coerce")
    date_reported_dt = pd.to_datetime(df_sent["Date Reported"], errors="coerce")

    # Formatear fechas
    df_sent["Incident Date"] = incident_dt.dt.strftime("%m/%d/%Y")
    df_sent["Date Reported"] = date_reported_dt.dt.strftime("%m/%d/%Y")
    df_sent["Reported To Date"] = pd.to_datetime(
        df_sent["Reported To Date"], errors="coerce"
    ).dt.strftime("%m/%d/%Y")

    # Calcular diferencia en días entre incidente y reporte
    df_sent["When Reported Number"] = (date_reported_dt - incident_dt).dt.days

    # Clasificar When Reported
    df_sent["When Reported"] = np.select(
        [
            df_sent["When Reported Number"].isna(),
            df_sent["When Reported Number"] == 0,
            (df_sent["When Reported Number"] >= 1) & (df_sent["When Reported Number"] <= 7),
            df_sent["When Reported Number"] > 7
        ],
        [
            "NA",
            "Same day of Incident",
            "Within week of Incident",
            "Other/Several weeks after incident"
        ],
        default="NA"
    )


    df_sent['Rideshare Company'] = np.where(
        df_sent['Rideshare Company'].isna() | (df_sent['Rideshare Company'].astype(str).str.strip() == ''),
        'NA',
        df_sent['Rideshare Company'].astype(str).str.strip() + ' Rideshare'
    )

    df_sent = df_sent.drop(columns=['When Reported Number'], errors='ignore')


    df_sent['Digital Receipt'] = np.where(
    df_sent['Digital Receipt'].astype(str).str.strip().str.lower() == 'yes',
    'Yes - has receipt and can provide copy',
    df_sent['Digital Receipt'])
    
    
    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — BARD PORT T2
# ============================================
def obtener_datos_bardport_t2(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
        SELECT
        Lead__r.Id,
        Lead__r.Email__c,
        Lead__r.Phone_Numbercontact__c,
        Lead__r.FirstName__c,
        Lead__r.Last_Name__c,
        Lead__r.Do_you_have_an_attorney__c,
        Lead__r.Receive_an_Implanted_Port_Catheter__c,
        Lead__r.Implanted_Port_Catheter_infection__c,
        Lead__r.CaseNumber
        FROM Lead_de_oportunidad__c
        WHERE Oportunidad__r.AccountId='001TR00000YhtYmYAJ'
        AND Lead__r.Status='Sent'
        AND Lead__r.Type='Bard Port'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c',
        'Lead__r.Phone_Numbercontact__c',
        'Lead__r.Email__c',
        'Lead__r.Do_you_have_an_attorney__c',
        'Lead__r.Receive_an_Implanted_Port_Catheter__c',
        'Lead__r.Implanted_Port_Catheter_infection__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Do_you_have_an_attorney__c': 'Attorney',
        'Lead__r.Receive_an_Implanted_Port_Catheter__c': 'Receied an Implanted Port Catheter',
        'Lead__r.Implanted_Port_Catheter_infection__c': 'Cathther Issues'
    })

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — BARD PORT T3
# ============================================

def obtener_datos_bardport_t3(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.DiagnosisYear__c
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR00001AMawEYAT' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Bard Port'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Date_of_Birth__c',
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.Address_Street__c', 'Lead__r.City__c',
                       'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.DiagnosisYear__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Address_Street__c': 'Address',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip',
        "Lead__r.DiagnosisYear__c":"Date of Diagnosis"
    })

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    # Smart Reviews pide fechas mm/dd/yyyy
    df_sent['Retainer Signed Date'] = datetime.today().strftime('%m/%d/%Y')

    df_sent['Date of Birth'] = pd.to_datetime(df_sent['Date of Birth'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent['Date of Diagnosis'] = pd.to_datetime(df_sent['Date of Diagnosis'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — BARD PORT T5
# ============================================

def obtener_datos_bard_port_t5(case_number):
    global sf
    accounts_sent = sf.query_all(
        f"""
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000pGZ66YAG' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Bard Port'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c',
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
    })

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — SOCIAL MEDIA ADDICTION T1
# ============================================

def obtener_datos_social_media_addiction_t1(case_number):
    global sf
    accounts_sent = sf.query_all(
        f"""
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00001Amh7kYAB' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Social Media Addiction'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c',
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
    })

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — BARD PORT T4
# ============================================

def obtener_datos_bard_port_t4(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.Trusted_Form__c,
            Lead__r.ip_address__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Date_of_Implant__c,
            Lead__r.Brand_Name__c,
            Lead__r.Diagnosis__c,
            Lead__r.Incident_Date__c,
            Lead__r.Was_the_port_removed_due_to_the_injury__c,
            Lead__r.State_of_Incident__c,
            Lead__r.Do_you_have_an_attorney__c 
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR000000wRPiYAM' AND Lead__r.Substatus__c='Posted' AND Lead__r.Type='Bard Port'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.Trusted_Form__c', 'Lead__r.ip_address__c', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.Date_of_Implant__c', 'Lead__r.Brand_Name__c', 'Lead__r.Diagnosis__c', 
                       'Lead__r.Incident_Date__c', 'Lead__r.Was_the_port_removed_due_to_the_injury__c', 'Lead__r.State_of_Incident__c',
                       'Lead__r.Do_you_have_an_attorney__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.Trusted_Form__c': 'Trusted Form',
        'Lead__r.ip_address__c': 'Ip Address',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Date_of_Implant__c': 'Was a port implanted in 2013 or later?',
        'Lead__r.Brand_Name__c': 'Do you know the Port-A-Cath brand?',
        'Lead__r.Diagnosis__c': 'Did you experience any of the following complications or injuries?',
        'Lead__r.Incident_Date__c': 'When did the complication first occur after the Port-A-Cath was implanted?',
        'Lead__r.Was_the_port_removed_due_to_the_injury__c': 'Was the Port-A-Cath removed because of the complication or injury?',
        'Lead__r.State_of_Incident__c': 'In what state did the implant or treatment occur?',
        'Lead__r.Do_you_have_an_attorney__c':'Do you have an attorney?'
    })

    fecha_implante = pd.to_datetime(df_sent["Was a port implanted in 2013 or later?"], errors="coerce")

    fecha_incidente = pd.to_datetime(df_sent["When did the complication first occur after the Port-A-Cath was implanted?"], errors="coerce")

    dias = (fecha_incidente - fecha_implante).dt.days

    df_sent["When did the complication first occur after the Port-A-Cath was implanted?"] = np.select(
        [
            dias.isna() | (dias < 0),
            dias < 14,
            dias <= 90,
            dias > 90
        ],
        [
            "NA",
            "Under 14 days",
            "14 days to 3 months",
            "Over 3 months"
        ],
        default="NA"
    )

    df_sent["Was a port implanted in 2013 or later?"] = np.where(
        fecha_implante.dt.year >= 2013,
        "Yes",
        "No"
    )

    col = "Do you know the Port-A-Cath brand?"
    df_sent[col] = np.where(
    df_sent[col].str.strip().str.lower() == "bard port",
    "Bard Port",
    "Unknown"
    )


    df_sent["Did you experience any of the following complications or injuries?"] = df_sent["Did you experience any of the following complications or injuries?"].apply(lambda x: {
    "Catheter Breakage": "Catheter Breakage",
    "Blood Clots": "Blood clots",
    "Fracture": "Fracture",
    "Infection of port": "Infection",
    "Thrombosis": "Thrombosis / Thromboembolic event",
    "Migration (port shifted)": "Migration with complication"
    }.get(x, "Other"))






    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — TALCUM T15
# ============================================
def obtener_datos_talcum_t15(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Gender__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.ip_address__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.Trusted_Form__c,
            Lead__r.Used_J_J_Shower_talcum_last_5_years__c,
            Lead__r.Diagnosis__c,
            Lead__r.Do_you_have_an_attorney__c,
            Lead__r.DiagnosisYear__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000igX9ZYAU' AND Lead__r.Substatus__c='Posted' AND Lead__r.Type='Talcum'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.FirstName__c','Lead__r.Last_Name__c','Lead__r.Email__c','Lead__r.Phone_Numbercontact__c','Lead__r.Date_of_Birth__c','Lead__r.Gender__c','Lead__r.Address_Street__c',
        'Lead__r.City__c','Lead__r.StateUS__c','Lead__r.Area_Code__c','Lead__r.ip_address__c','Lead__r.Landing_Page_URL__c','Lead__r.Trusted_Form__c','Lead__r.Used_J_J_Shower_talcum_last_5_years__c',
        'Lead__r.Diagnosis__c','Lead__r.Do_you_have_an_attorney__c','Lead__r.DiagnosisYear__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Gender__c': 'Gender',
        'Lead__r.Address_Street__c': 'Address Street',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.ip_address__c': 'IP Address',
        'Lead__r.Landing_Page_URL__c': 'Landing Page URL',
        'Lead__r.Trusted_Form__c': 'Trusted Form',
        'Lead__r.Used_J_J_Shower_talcum_last_5_years__c': 'Used J&J Shower Talcum Last 5 Years',
        'Lead__r.Diagnosis__c': 'Diagnosis',
        'Lead__r.Do_you_have_an_attorney__c': 'Attorney',
        'Lead__r.DiagnosisYear__c': 'Diagnosis Year'
    })

    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    # Asegurar que la columna sea fecha
    df_sent["Diagnosis Year"] = pd.to_datetime(df_sent["Diagnosis Year"], errors="coerce")

    # Aplicar lógica equivalente al IFS de Excel
    df_sent["Diagnosis Year"] = np.select(
        [
            df_sent["Diagnosis Year"].isna(),
            df_sent["Diagnosis Year"].dt.year >= 2023,
            df_sent["Diagnosis Year"].dt.year >= 2016,
            df_sent["Diagnosis Year"].dt.year >= 2011,
            df_sent["Diagnosis Year"].dt.year < 2011
        ],
        [
            "NA",
            "2023 - 2026",
            "2016 - 2022",
            "2011 - 2015",
            "Before 2010"
        ],
        default="NA"
    )

    return df_sent

# ============================================
# FUNCIÓN OBTENER DATOS — DEPO PROVERA T7
# ============================================
def obtener_datos_depo_provera_t7(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Date_of_Death__c,
            Lead__r.Signer_SSN__c,
            Lead__r.Signer_Last_4_SSN__c,
            Lead__r.VictimName__c,
            Lead__r.VictimLName__c,
            Lead__r.Relationship_to_the_victim__c,
            Lead__r.Victim_City__c,
            Lead__r.Victim_State__c,
            Lead__r.Victim_Zipcode__c,
            Lead__r.Date_First_Exposure__c,
            Lead__r.Date_Last_Exposure__c,
            Lead__r.What_were_you_taking_Depo_Provera_for__c,
            Lead__r.Usage_1_Generic__c,
            Lead__r.Usage_1_Start_Date__c,
            Lead__r.Usage_1_Stop_Date__c,
            Lead__r.Usage_1_Pharmacy_Name__c,
            Lead__r.Usage_1_Pharmacy_Address__c,
            Lead__r.Usage_1_Pharmacy_Phone__c,
            Lead__r.Usage_2_Generic__c,
            Lead__r.Usage_2_Start_Date__c,
            Lead__r.Usage_2_Stop_Date__c,
            Lead__r.Usage_2_Pharmacy_Name__c,
            Lead__r.Usage_2_Pharmacy_Address__c,
            Lead__r.Usage_2_Pharmacy_Phone__c,
            Lead__r.Diagnosed_with_Meningioma__c,
            Lead__r.DiagnosisYear__c,
            Lead__r.How_many_meningiomas_do_you_have__c,
            Lead__r.Location_of_your_meningioma_s__c,
            Lead__r.Treatment__c,
            Lead__r.Diagnosing_Doctor_s_name__c,
            Lead__r.Diagnosing_Hospital_s_name__c,
            Lead__r.Diagnosing_Hospital_s_address__c,
            Lead__r.Diagnosing_facility_phone_number__c,
            Lead__r.Treating_Doctor_s_name__c,
            Lead__r.Treating_Facility_name__c,
            Lead__r.Treating_facility_address__c,
            Lead__r.Treating_facility_phone_number__c,
            Lead__r.PCP_Name__c,
            Lead__r.PCP_Address__c,
            Lead__r.PCP_Phone__c,
            Lead__r.Medical_Notes__c,
            Lead__r.Additional_Notes__c,
            Lead__r.Emergency_Contact_Name__c,
            Lead__r.Relationship_to_Emergency_Contact__c,
            Lead__r.Emergency_Mailing_Address__c,
            Lead__r.Emergency_Contact_Phone_Number__c,
            Lead__r.Emergency_Contact_Email__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR000000uKX8YAM' AND Lead__r.Status ='Sent' AND Lead__r.Type='Depo Provera'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.Phone_Numbercontact__c','Lead__r.Email__c','Lead__r.FirstName__c','Lead__r.Last_Name__c','Lead__r.Address_Street__c','Lead__r.City__c','Lead__r.StateUS__c','Lead__r.Area_Code__c',
        'Lead__r.Date_of_Birth__c','Lead__r.Date_of_Death__c','Lead__r.Signer_SSN__c','Lead__r.Signer_Last_4_SSN__c','Lead__r.VictimName__c','Lead__r.VictimLName__c','Lead__r.Relationship_to_the_victim__c',
        'Lead__r.Victim_City__c','Lead__r.Victim_State__c','Lead__r.Victim_Zipcode__c','Lead__r.Date_First_Exposure__c','Lead__r.Date_Last_Exposure__c','Lead__r.What_were_you_taking_Depo_Provera_for__c',
        'Lead__r.Usage_1_Generic__c','Lead__r.Usage_1_Start_Date__c','Lead__r.Usage_1_Stop_Date__c','Lead__r.Usage_1_Pharmacy_Name__c','Lead__r.Usage_1_Pharmacy_Address__c','Lead__r.Usage_1_Pharmacy_Phone__c',
        'Lead__r.Usage_2_Generic__c','Lead__r.Usage_2_Start_Date__c','Lead__r.Usage_2_Stop_Date__c','Lead__r.Usage_2_Pharmacy_Name__c','Lead__r.Usage_2_Pharmacy_Address__c','Lead__r.Usage_2_Pharmacy_Phone__c',
        'Lead__r.Diagnosed_with_Meningioma__c','Lead__r.DiagnosisYear__c','Lead__r.How_many_meningiomas_do_you_have__c','Lead__r.Location_of_your_meningioma_s__c','Lead__r.Treatment__c',
        'Lead__r.Diagnosing_Doctor_s_name__c','Lead__r.Diagnosing_Hospital_s_name__c','Lead__r.Diagnosing_Hospital_s_address__c','Lead__r.Diagnosing_facility_phone_number__c','Lead__r.Treating_Doctor_s_name__c',
        'Lead__r.Treating_Facility_name__c','Lead__r.Treating_facility_address__c','Lead__r.Treating_facility_phone_number__c','Lead__r.PCP_Name__c','Lead__r.PCP_Address__c','Lead__r.PCP_Phone__c',
        'Lead__r.Medical_Notes__c','Lead__r.Additional_Notes__c','Lead__r.Emergency_Contact_Name__c','Lead__r.Relationship_to_Emergency_Contact__c','Lead__r.Emergency_Mailing_Address__c',
        'Lead__r.Emergency_Contact_Phone_Number__c','Lead__r.Emergency_Contact_Email__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Id",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.Email__c": "Email Address",
        "Lead__r.FirstName__c": "Injured Party First Name",
        "Lead__r.Last_Name__c": "Injured Party Last Name",
        "Lead__r.Address_Street__c": "Injured Party Street Address",
        "Lead__r.City__c": "Injured Party City",
        "Lead__r.StateUS__c": "Injured Party State",
        "Lead__r.Area_Code__c": "Injured Party Zip Code",
        "Lead__r.Date_of_Birth__c": "Injured Party Date of Birth",
        "Lead__r.Date_of_Death__c": "Injured Party Date of Death",
        "Lead__r.Signer_SSN__c": "Injured Party SSN",
        "Lead__r.Signer_Last_4_SSN__c": "Injured Party Last Four SSN",

        "Lead__r.VictimName__c": "OBO First Name",
        "Lead__r.VictimLName__c": "OBO Last Name",
        "Lead__r.Relationship_to_the_victim__c": "OBO Relationship to Injured Party",
        "Lead__r.Victim_City__c": "OBO City",
        "Lead__r.Victim_State__c": "OBO State",
        "Lead__r.Victim_Zipcode__c": "OBO Zip Code",

        "Lead__r.Date_First_Exposure__c": "Start Date",
        "Lead__r.Date_Last_Exposure__c": "Stop Date",
        "Lead__r.What_were_you_taking_Depo_Provera_for__c": "What were you taking Depo Provera for?",

        "Lead__r.Usage_1_Generic__c": "Usage 1 Generic?",
        "Lead__r.Usage_1_Start_Date__c": "Usage 1 Start Date",
        "Lead__r.Usage_1_Stop_Date__c": "Usage 1 Stop Date",
        "Lead__r.Usage_1_Pharmacy_Name__c": "Usage 1 Pharmacy Name",
        "Lead__r.Usage_1_Pharmacy_Address__c": "Usage 1 Pharmacy Address",
        "Lead__r.Usage_1_Pharmacy_Phone__c": "Usage 1 Pharmacy Phone",

        "Lead__r.Usage_2_Generic__c": "Usage 2 Generic?",
        "Lead__r.Usage_2_Start_Date__c": "Usage 2 Start Date",
        "Lead__r.Usage_2_Stop_Date__c": "Usage 2 Stop Date",
        "Lead__r.Usage_2_Pharmacy_Name__c": "Usage 2 Pharmacy Name",
        "Lead__r.Usage_2_Pharmacy_Address__c": "Usage 2 Pharmacy Address",
        "Lead__r.Usage_2_Pharmacy_Phone__c": "Usage 2 Pharmacy Phone",

        "Lead__r.Diagnosed_with_Meningioma__c": "Diagnosed with Meningioma?",
        "Lead__r.DiagnosisYear__c": "Diagnosis Date",
        "Lead__r.How_many_meningiomas_do_you_have__c": "How many meningiomas do you have?",
        "Lead__r.Location_of_your_meningioma_s__c": "Location of your meningioma(s)?",
        "Lead__r.Treatment__c": "What treatment have you undergone for your meningioma(s)",

        "Lead__r.Diagnosing_Doctor_s_name__c": "Diagnosing Doctor Name",
        "Lead__r.Diagnosing_Hospital_s_name__c": "Diagnosing Facility Name",
        "Lead__r.Diagnosing_Hospital_s_address__c": "Diagnosing Facility Address",
        "Lead__r.Diagnosing_facility_phone_number__c": "Diagnosing Facility Phone",

        "Lead__r.Treating_Doctor_s_name__c": "Treating Doctor Name",
        "Lead__r.Treating_Facility_name__c": "Treating Facility Name",
        "Lead__r.Treating_facility_address__c": "Treating Facility Address",
        "Lead__r.Treating_facility_phone_number__c": "Treating Facility Phone",

        "Lead__r.PCP_Name__c": "PCP Name",
        "Lead__r.PCP_Address__c": "PCP Address",
        "Lead__r.PCP_Phone__c": "PCP Phone",

        "Lead__r.Medical_Notes__c": "Medical Notes",
        "Lead__r.Additional_Notes__c": "Notes",

        "Lead__r.Emergency_Contact_Name__c": "Emergency Contact Name",
        "Lead__r.Relationship_to_Emergency_Contact__c": "Emergency Contact Relationship",
        "Lead__r.Emergency_Mailing_Address__c": "Emergency Contact Address",
        "Lead__r.Emergency_Contact_Phone_Number__c": "Emergency Contact Phone",
        "Lead__r.Emergency_Contact_Email__c": "Emergency Contact Email"
    })

    df_sent['Injured Party Zip Code'] = pd.to_numeric(df_sent['Injured Party Zip Code'], errors='coerce').astype('Int64')

    date_columns = [
        "Injured Party Date of Birth",
        "Injured Party Date of Death",
        "Start Date",
        "Stop Date",
        "Usage 1 Start Date",
        "Usage 1 Stop Date",
        "Usage 2 Start Date",
        "Usage 2 Stop Date",
        "Diagnosis Date"
    ]

    for col in date_columns:
        df_sent[col] = pd.to_datetime(df_sent[col], errors="coerce").dt.strftime("%m/%d/%Y")
        df_sent[col] = df_sent[col].fillna("NA")

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — DEPO PROVERA T8
# ============================================
def obtener_datos_depoprovera_t8(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
        SELECT
        Lead__r.Id,
        Lead__r.Email__c,
        Lead__r.Phone_Numbercontact__c,
        Lead__r.FirstName__c,
        Lead__r.Last_Name__c,
        Lead__r.Do_you_have_an_attorney__c,
        Lead__r.Used_Depo_Provera_for_at_least_1_year__c,
        Lead__r.Diagnosed_with_Meningioma__c,
        Lead__r.CaseNumber
        FROM Lead_de_oportunidad__c
        WHERE Oportunidad__r.AccountId='001TR00000YhtYmYAJ'
        AND Lead__r.Status='Sent'
        AND Lead__r.Type='Depo Provera'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c',
        'Lead__r.Phone_Numbercontact__c',
        'Lead__r.Email__c',
        'Lead__r.Do_you_have_an_attorney__c',
        'Lead__r.Used_Depo_Provera_for_at_least_1_year__c',
        'Lead__r.Diagnosed_with_Meningioma__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Do_you_have_an_attorney__c': 'Attorney',
        'Lead__r.Used_Depo_Provera_for_at_least_1_year__c': 'Used Depo',
        'Lead__r.Diagnosed_with_Meningioma__c': 'Diagnosed with Meningioma'
    })

    return df_sent

# ============================================
# FUNCIÓN OBTENER DATOS — WOMENS PRISIONER ABUSE T1
# ============================================
def obtener_datos_womens_prisioner_abuse_t1(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Perpetrator_Name__c,
            Lead__r.Perpetrator_Title__c,
            Lead__r.Womens_Detention_Center_Name__c,
            Lead__r.What_years_were_you_at_the_center__c,
            Lead__r.Why_were_you_sent_to_the_center__c,
            Lead__r.What_City_State_were_you_sent_from__c,
            Lead__r.Date_of_Abuse__c,
            Lead__r.How_did_you_first_meet_them__c,
            Lead__r.Abuse_Details__c,
            Lead__r.Location_1__c,
            Lead__r.Number_of_times_you_were_abused__c,
            Lead__r.Were_they_ever_physically_abused__c,
            Lead__r.Physical_abuse_details__c,
            Lead__r.Witnessed_or_heard_of_others_abused__c,
            Lead__r.Was_the_abuse_reported__c,
            Lead__r.Reported_to_any_of_the_following__c,
            Lead__r.When_was_the_abuse_reported__c,
            Lead__r.Outcome_after_reporting_the_abuse__c,
            Lead__r.Issues_from_Abuse__c,
            Lead__r.Treatment_details__c,
            Lead__r.Additional_Notes__c,
            Lead__r.Best_Contact_Method__c,
            Lead__r.Emergency_Contact_Name__c,
            Lead__r.Relationship_to_Emergency_Contact__c,
            Lead__r.Emergency_Mailing_Address__c,
            Lead__r.Emergency_Contact_Phone_Number__c,
            Lead__r.Emergency_Contact_Email__c,
            Lead__r.Prison_ID__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR000000uKX8YAM' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Women’s Prisoner Abuse'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.Email__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Address_Street__c', 'Lead__r.City__c',
        'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.Date_of_Birth__c', 'Lead__r.Perpetrator_Name__c', 'Lead__r.Perpetrator_Title__c',
        'Lead__r.Womens_Detention_Center_Name__c', 'Lead__r.What_years_were_you_at_the_center__c', 'Lead__r.Why_were_you_sent_to_the_center__c',
        'Lead__r.What_City_State_were_you_sent_from__c', 'Lead__r.Date_of_Abuse__c', 'Lead__r.How_did_you_first_meet_them__c', 'Lead__r.Abuse_Details__c',
        'Lead__r.Location_1__c', 'Lead__r.Number_of_times_you_were_abused__c', 'Lead__r.Were_they_ever_physically_abused__c', 'Lead__r.Physical_abuse_details__c',
        'Lead__r.Witnessed_or_heard_of_others_abused__c', 'Lead__r.Was_the_abuse_reported__c', 'Lead__r.Reported_to_any_of_the_following__c',
        'Lead__r.When_was_the_abuse_reported__c', 'Lead__r.Outcome_after_reporting_the_abuse__c', 'Lead__r.Issues_from_Abuse__c', 'Lead__r.Treatment_details__c',
        'Lead__r.Additional_Notes__c', 'Lead__r.Best_Contact_Method__c', 'Lead__r.Emergency_Contact_Name__c', 'Lead__r.Relationship_to_Emergency_Contact__c',
        'Lead__r.Emergency_Mailing_Address__c', 'Lead__r.Emergency_Contact_Phone_Number__c', 'Lead__r.Emergency_Contact_Email__c', 'Lead__r.Prison_ID__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Id",
        "Lead__r.Email__c": "Email",
        "Lead__r.Phone_Numbercontact__c": "Cell Phone",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name",
        "Lead__r.Address_Street__c": "Address",
        "Lead__r.City__c": "City",
        "Lead__r.StateUS__c": "State",
        "Lead__r.Area_Code__c": "Zip",
        "Lead__r.Date_of_Birth__c": "DOB",
        "Lead__r.Perpetrator_Name__c": "Perpetrator Name",
        "Lead__r.Perpetrator_Title__c": "Perpetrator Title",
        "Lead__r.Womens_Detention_Center_Name__c": "Juvenile Detention Center Name",
        "Lead__r.What_years_were_you_at_the_center__c": "What years were you at the center?",
        "Lead__r.Why_were_you_sent_to_the_center__c": "How did you end up being sent to the center?",
        "Lead__r.What_City_State_were_you_sent_from__c": "What City/State were you sent from?",
        "Lead__r.Date_of_Abuse__c": "Date of Abuse",
        "Lead__r.How_did_you_first_meet_them__c": "How did you first come into contact with them?",
        "Lead__r.Abuse_Details__c": "Abuse Details",
        "Lead__r.Location_1__c": "Abuse Location",
        "Lead__r.Number_of_times_you_were_abused__c": "Number of Times You Were Abused",
        "Lead__r.Were_they_ever_physically_abused__c": "Were they ever subjected to any physical abuse?",
        "Lead__r.Physical_abuse_details__c": "Physical Abuse Details",
        "Lead__r.Witnessed_or_heard_of_others_abused__c": "Heared of others abused",
        "Lead__r.Was_the_abuse_reported__c": "Did you report the abuse",
        "Lead__r.Reported_to_any_of_the_following__c": "Who did you report this to?",
        "Lead__r.When_was_the_abuse_reported__c": "When did you report this?",
        "Lead__r.Outcome_after_reporting_the_abuse__c": "Outcome after reporting the abuse",
        "Lead__r.Issues_from_Abuse__c": "Issues from Abuse",
        "Lead__r.Treatment_details__c": "Treatment Details",
        "Lead__r.Additional_Notes__c": "Additional Notes",
        "Lead__r.Best_Contact_Method__c": "Best Contact Method",
        "Lead__r.Emergency_Contact_Name__c": "Emergency Contact Name",
        "Lead__r.Relationship_to_Emergency_Contact__c": "Emergency Contact Relationship",
        "Lead__r.Emergency_Mailing_Address__c": "Emergency Contact Address",
        "Lead__r.Emergency_Contact_Phone_Number__c": "Emergency Contact Phone",
        "Lead__r.Emergency_Contact_Email__c": "Emergency Contact Email",
        "Lead__r.Prison_ID__c": "Prision ID"
    })

    yn_map = {"yes": "Y", "no": "N"}
    for col in ["Were they ever subjected to any physical abuse?", "Did you report the abuse"]:
        df_sent[col] = df_sent[col].apply(lambda v: yn_map.get(str(v).strip().lower(), v))

    date_columns = ["DOB", "Date of Abuse", "When did you report this?"]

    for col in date_columns:
        df_sent[col] = pd.to_datetime(df_sent[col], errors="coerce").dt.strftime("%m/%d/%Y")
        df_sent[col] = df_sent[col].fillna("NA")

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    return df_sent

# ============================================
# FUNCIÓN OBTENER DATOS — WOMENS PRISIONER ABUSE T2
# ============================================
def obtener_datos_womens_prisioner_abuse_t2(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.ip_address__c, 
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Trusted_Form_Id__c,
            Lead__r.Were_they_ever_physically_abused__c,
            Lead__r.Who_committed_the_abuse__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000KzBRFYA3' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Women’s Prisoner Abuse'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.ip_address__c', 
        'Lead__r.Trusted_Form_Id__c', 'Lead__r.Were_they_ever_physically_abused__c', 'Lead__r.Who_committed_the_abuse__c'
    ]]

    df_sent = df_sent.rename(columns={
    "Lead__r.Id": "Id",
    "Lead__r.FirstName__c": "First Name",
    "Lead__r.Last_Name__c": "Last Name",
    "Lead__r.Phone_Numbercontact__c": "Phone Number",
    "Lead__r.Email__c": "Email",
    "Lead__r.ip_address__c": "IP Address",
    "Lead__r.Trusted_Form_Id__c":"Trusted Form Id",
    "Lead__r.Were_they_ever_physically_abused__c": "Were you or a loved one sexually abused at a Womens Detention Center?",
    "Lead__r.Who_committed_the_abuse__c": "Was the abuse from another inmate or Law Enforcement/Corrections Officer/Guard?"
    })


    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    return df_sent



# ============================================
# FUNCIÓN OBTENER DATOS — WOMENS PRISIONER ABUSE T3
# ============================================

def obtener_datos_womens_prisioner_abuse_t3(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Abuse__c
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR00001BN9qBYAT' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Women’s Prisoner Abuse'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Date_of_Birth__c',
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.Address_Street__c', 'Lead__r.City__c',
                       'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.Date_of_Abuse__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Address_Street__c': 'Address',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip',
        "Lead__r.Date_of_Abuse__c":"Date of Abuse"
    })

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    # Smart Reviews pide fechas mm/dd/yyyy
    df_sent['Retainer Signed Date'] = datetime.today().strftime('%m/%d/%Y')

    df_sent['Date of Birth'] = pd.to_datetime(df_sent['Date of Birth'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent['Date of Abuse'] = pd.to_datetime(df_sent['Date of Abuse'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — CHLORPYRIFOS T1
# ============================================
def obtener_datos_chlorpyrifos_t1(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FullName__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR000010ORjJYAW' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Chlorpyrifos'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FullName__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.Address_Street__c',
        'Lead__r.City__c', 'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.Date_of_Birth__c', 'Lead__r.FirstName__c',
        'Lead__r.Last_Name__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Id",
        "Lead__r.CaseNumber": "Case Number",
        "Lead__r.FullName__c": "Full Name",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.Email__c": "Email",
        "Lead__r.Address_Street__c": "Address",
        "Lead__r.City__c": "City",
        "Lead__r.StateUS__c": "State",
        "Lead__r.Area_Code__c": "Zip",
        "Lead__r.Date_of_Birth__c": "DOB",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name"
    })

    date_columns = ["DOB"]

    for col in date_columns:
        df_sent[col] = pd.to_datetime(df_sent[col], errors="coerce").dt.strftime("%m/%d/%Y")
        df_sent[col] = df_sent[col].fillna("NA")

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    df_sent["Code"] = "IMG-" + df_sent["Case Number"].astype(str)

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — CHLORPYRIFOS T2
# ============================================
def obtener_datos_chlorpyrifos_t2(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.StateUS__c,
            Lead__r.ip_address__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.Trusted_Form__c,
            Lead__r.Trusted_Form_Id__c,
            Lead__r.Do_you_have_an_attorney__c,
            Lead__r.Parkinson_s_Disease_After_Being_Exposed__c,
            Lead__r.Did_you_live_or_work_near_chlorpyrifos__c,
            Lead__r.Did_you_use_Chlorpyrifos__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000YhtYmYAJ' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Chlorpyrifos'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Email__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.StateUS__c', 'Lead__r.ip_address__c', 
        'Lead__r.Landing_Page_URL__c', 'Lead__r.Trusted_Form__c', 'Lead__r.Trusted_Form_Id__c', 'Lead__r.Do_you_have_an_attorney__c', 'Lead__r.Parkinson_s_Disease_After_Being_Exposed__c', 
        'Lead__r.Did_you_live_or_work_near_chlorpyrifos__c', 'Lead__r.Did_you_use_Chlorpyrifos__c'

    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Id",
        "Lead__r.CaseNumber": "Case Number",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name",
        "Lead__r.Email__c": "Email",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.StateUS__c": "State",
        "Lead__r.ip_address__c": "IP Address",
        "Lead__r.Landing_Page_URL__c": "Landing Page",
        "Lead__r.Trusted_Form__c": "Trusted Form URL",
        "Lead__r.Trusted_Form_Id__c": "Trusted Form ID",
        "Lead__r.Do_you_have_an_attorney__c": "Do you have an attorney?",
        "Lead__r.Parkinson_s_Disease_After_Being_Exposed__c": "Parkinson's disease after being exposed?",
        "Lead__r.Did_you_live_or_work_near_chlorpyrifos__c": "Did you live or work near CPF?",
        "Lead__r.Did_you_use_Chlorpyrifos__c": "Did you use CPF?"
    })

    df_sent["Full Name"] = (
        df_sent["First Name"].fillna("").str.strip()
        + " "
        + df_sent["Last Name"].fillna("").str.strip()
    ).str.strip()

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — ASBESTOS T1
# ============================================
def obtener_datos_asbestos_t1(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Gender__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.ip_address__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.Trusted_Form__c,
            Lead__r.Trusted_Form_Id__c,
            Lead__r.Diagnosis__c,
            Lead__r.How_long_were_you_exposed__c,
            Lead__r.Do_you_have_an_attorney__c,
            Lead__r.Date_of_Death__c,
            Lead__r.DiagnosisYear__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000igX9ZYAU' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Asbestos'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Email__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.Date_of_Birth__c', 'Lead__r.Gender__c', 
        'Lead__r.Address_Street__c', 'Lead__r.City__c', 'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.ip_address__c', 'Lead__r.Landing_Page_URL__c', 'Lead__r.Trusted_Form__c', 
        'Lead__r.Trusted_Form_Id__c', 'Lead__r.Diagnosis__c', 'Lead__r.How_long_were_you_exposed__c', 'Lead__r.Do_you_have_an_attorney__c',
        'Lead__r.Date_of_Death__c', 'Lead__r.DiagnosisYear__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Id",
        "Lead__r.CaseNumber": "Case Number",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name",
        "Lead__r.Email__c": "Email",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.Date_of_Birth__c": "DOB",
        "Lead__r.Gender__c": "Gender",
        "Lead__r.Address_Street__c": "Address",
        "Lead__r.City__c": "City",
        "Lead__r.StateUS__c": "State",
        "Lead__r.Area_Code__c": "Zip",
        "Lead__r.ip_address__c": "IP Address",
        "Lead__r.Landing_Page_URL__c": "Landing Page",
        "Lead__r.Trusted_Form__c": "Trusted Form URL",
        "Lead__r.Trusted_Form_Id__c": "Trusted Form ID",
        "Lead__r.Diagnosis__c": "Diagnosed",
        "Lead__r.How_long_were_you_exposed__c": "Exposed",
        "Lead__r.Do_you_have_an_attorney__c": "Do you have an attorney?",
        "Lead__r.Date_of_Death__c":"Date of Death",
        "Lead__r.DiagnosisYear__c":"Date of Diagnosis"
    })

    date_columns = ["DOB","Date of Death", "Date of Diagnosis"]

    for col in date_columns:
        df_sent[col] = pd.to_datetime(df_sent[col], errors="coerce").dt.strftime("%Y-%m-%d")
        df_sent[col] = df_sent[col].fillna("NA")

    df_sent["Deceased"] = np.where(
        df_sent["Date of Death"].isna() | (df_sent["Date of Death"].astype(str).str.strip() == "NA"),
        "No",
        "Yes"
    )
    
    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')


    def anos_completos_desde(fecha_col):
        now = pd.Timestamp.now()
        fechas = pd.to_datetime(fecha_col, errors="coerce")
        aun_no_cumple = (fechas.dt.month > now.month) | (
            (fechas.dt.month == now.month) & (fechas.dt.day > now.day)
        )
        return (now.year - fechas.dt.year) - aun_no_cumple.astype(int)

    # Aplicar lógica equivalente al IFS de Excel, usando años completos (no diferencia de año calendario)
    anos_diagnostico = anos_completos_desde(df_sent["Date of Diagnosis"])
    df_sent["When was the injured party diagnosed?"]  = np.select(
        [
            pd.to_datetime(df_sent["Date of Diagnosis"], errors="coerce").isna(),
            anos_diagnostico >= 5,
            anos_diagnostico >= 3,
            anos_diagnostico >= 1,
            anos_diagnostico < 1
        ],
        [
            "NA",
            "More than 5 years ago",
            "3–5 years ago",
            "1–3 years ago",
            "Less than 1 year ago"
        ],
        default="NA"
    )

    # Aplicar lógica equivalente al IFS de Excel, usando años completos (no diferencia de año calendario)
    anos_fallecimiento = anos_completos_desde(df_sent["Date of Death"])
    df_sent["When did the injured party pass away?"]  = np.select(
        [
            pd.to_datetime(df_sent["Date of Death"], errors="coerce").isna(),
            anos_fallecimiento >= 5,
            anos_fallecimiento >= 3,
            anos_fallecimiento >= 1,
            anos_fallecimiento < 1
        ],
        [
            "NA",
            "More than 5 years ago",
            "3–5 years ago",
            "1–3 years ago",
            "Less than 1 year ago"
        ],
        default="NA"
    )

    df_sent["When did the injured party pass away?"] = (df_sent["When did the injured party pass away?"].astype(str).str.strip().replace("NA", ""))

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — ASBESTOS T1 TURNDOWNCASES
# ============================================
def obtener_datos_asbestos_t1_turndowncases(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Id,
            CaseNumber,
            FirstName__c,
            Last_Name__c,
            Email__c,
            Phone_Numbercontact__c,
            Date_of_Birth__c,
            Gender__c,
            Address_Street__c,
            City__c,
            Trusted_Form__c,
            Trusted_Form_Id__c
            FROM Case
            WHERE Substatus__c = 'Disqualified' AND Type ='Asbestos' AND TDC__c = FALSE
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Id', 'CaseNumber', 'FirstName__c', 'Last_Name__c', 'Email__c', 'Phone_Numbercontact__c', 'Date_of_Birth__c', 'Gender__c', 'Address_Street__c', 'City__c', 'Trusted_Form__c', 'Trusted_Form_Id__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Id": "Id",
        "CaseNumber": "Case Number",
        "FirstName__c": "First Name",
        "Last_Name__c": "Last Name",
        "Email__c": "Email",
        "Phone_Numbercontact__c": "Phone Number",
        "Date_of_Birth__c": "DOB",
        "Gender__c": "Gender",
        "Address_Street__c": "Address",
        "City__c": "City",
        "Trusted_Form__c": "Trusted Form URL",
        "Trusted_Form_Id__c": "Trusted Form ID"
    })

    date_columns = ["DOB"]

    for col in date_columns:
        df_sent[col] = pd.to_datetime(df_sent[col], errors="coerce").dt.strftime("%Y-%m-%d")
        df_sent[col] = df_sent[col].fillna("NA")


    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    return df_sent

# ============================================
# FUNCIÓN OBTENER DATOS — JUVENILE DETENTION CENTER T3
# ============================================
def obtener_datos_juvenile_detention_center_t3(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Date_of_Abuse__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000fksnQYAQ' AND Lead__r.Status='Sent' AND Lead__r.Type='Juvenile Detention Center'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.Email__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 
        'Lead__r.Address_Street__c', 'Lead__r.City__c', 'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.Date_of_Birth__c', 'Lead__r.Date_of_Abuse__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id":"Id",
        "Lead__r.CaseNumber": "Case Number",
        "Lead__r.Email__c": "Email",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name",
        "Lead__r.Address_Street__c": "Address",
        "Lead__r.City__c": "City",
        "Lead__r.StateUS__c": "State",
        "Lead__r.Area_Code__c": "Zip",
        "Lead__r.Date_of_Birth__c": "Date of Birth",
        "Lead__r.Date_of_Abuse__c": "Date of Abuse"
    })

    date_columns = ["Date of Birth","Date of Abuse"]

    for col in date_columns:
        df_sent[col] = pd.to_datetime(df_sent[col], errors="coerce").dt.strftime("%m/%d/%Y")
        df_sent[col] = df_sent[col].fillna("NA")

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    return df_sent




# ============================================
# FUNCIÓN OBTENER DATOS — JUVENILE DETENTION CENTER T4
# ============================================
def obtener_datos_juvenile_detention_center_t4(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.ip_address__c, 
            Lead__r.Were_they_ever_physically_abused__c,
            Lead__r.Minor_underage_at_the_time__c,
            Lead__r.Where_did_the_abuse_take_place__c,
            Lead__r.Trusted_Form_Id__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000KzBRFYA3' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Juvenile Detention Center'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 
        'Lead__r.ip_address__c', 'Lead__r.Were_they_ever_physically_abused__c', 'Lead__r.Minor_underage_at_the_time__c', 'Lead__r.Where_did_the_abuse_take_place__c', 
        'Lead__r.Trusted_Form_Id__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Id",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.Email__c": "Email",
        "Lead__r.ip_address__c": "IP Address",
        "Lead__r.Trusted_Form_Id__c": "Trusted Form Id",
        "Lead__r.Were_they_ever_physically_abused__c": "Were you victim of harassment or abuse?",
        "Lead__r.Minor_underage_at_the_time__c": "Were you or your loved one under the age of 18 at the time of the sexual abuse?",
        "Lead__r.Where_did_the_abuse_take_place__c": "Where did the abuse take place?"

    })

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — JUVENILE DETENTION CENTER T5
# ============================================
def obtener_datos_juvenile_detention_center_t5(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Area_Code__c,
            Lead__r.Abuse_Details__c,
            Lead__r.ip_address__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.Juvenile_Detention_Center_Name__c,
            Lead__r.Minor_underage_at_the_time__c,
            Lead__r.What_was_their_position_at_the_facility__c,
            Lead__r.Were_they_ever_physically_abused__c,
            Lead__r.Do_you_know_the_name_of_the_person__c,
            Lead__r.Trusted_Form__c,
            Lead__r.Do_you_have_an_attorney__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR00000LRBBNYA5' AND Lead__r.Substatus__c='Posted' AND Lead__r.Type='Juvenile Detention Center'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.FirstName__c','Lead__r.Last_Name__c','Lead__r.Email__c','Lead__r.Phone_Numbercontact__c','Lead__r.Area_Code__c','Lead__r.Abuse_Details__c','Lead__r.ip_address__c','Lead__r.Landing_Page_URL__c','Lead__r.Juvenile_Detention_Center_Name__c','Lead__r.Minor_underage_at_the_time__c','Lead__r.What_was_their_position_at_the_facility__c','Lead__r.Were_they_ever_physically_abused__c','Lead__r.Do_you_know_the_name_of_the_person__c','Lead__r.Trusted_Form__c','Lead__r.Do_you_have_an_attorney__c'
    ]]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.Abuse_Details__c': 'Abuse Details',
        'Lead__r.ip_address__c': 'Ip Address',
        'Lead__r.Landing_Page_URL__c': 'Landing Page',
        'Lead__r.Juvenile_Detention_Center_Name__c': 'Juvenile Detention Center Name',
        'Lead__r.Minor_underage_at_the_time__c': 'Minor underage at the time?',
        'Lead__r.What_was_their_position_at_the_facility__c':'What was their position at the facility?',
        'Lead__r.Were_they_ever_physically_abused__c':'Were they ever physically abused?',
        'Lead__r.Do_you_know_the_name_of_the_person__c': 'Do you know the name of the person?',
        'Lead__r.Trusted_Form__c':'Trusted Form',
        'Lead__r.Do_you_have_an_attorney__c':'Do you have an attorney?'
    })

    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    # Facility Mapping
    facility_mapping = {
        "Crossroads Juvenile Center": "crossroads",
        "Horizon Juvenile Center": "horizon",
        "Spofford Juvenile Center": "spofford",
        "Rikers Island Juvenile Detention": "rikers",
        "St. John’s Residence/School/Treatment Center for Boys": "st_john",
        "Non-Secure Detention Residence": "non_secure_richmond_hill",
        "Residential Treatment Center": "rtc_rockaway",
        "NYC Board of Education – PS256Q": "ps256q",
        "Limited Secure Placement Programs": "limited_secure_placement",
        "Rising Ground": "rising_ground",
        "Children’s Learning Center": "childrens_learning_center",
        "Abbott House": "abbot_house",
        "Lutheran Social Services": "lutheran_social",
        "Good Shepherd Services": "good_shepherd"
    }

    df_sent["Juvenile Detention Center Name"] = df_sent["Juvenile Detention Center Name"].apply(lambda x: facility_mapping.get(x, "other"))

    df_sent["What was their position at the facility?"] = df_sent["What was their position at the facility?"].str.lower().str.replace("not sure", "not-sure")

    df_sent["Were they ever physically abused?"] = df_sent["Were they ever physically abused?"].str.lower()

    df_sent["Minor underage at the time?"] = df_sent["Minor underage at the time?"].str.lower()

    df_sent["Do you know the name of the person?"] = df_sent["Do you know the name of the person?"].str.lower()

    df_sent["Do you have an attorney?"] = df_sent["Do you have an attorney?"].str.lower()

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — JUVENILE DETENTION CENTER T6
# ============================================
def obtener_datos_juvenile_detention_center_t6(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.Date_of_Abuse__c
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR00001BbsllYAB' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Juvenile Detention Center'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Date_of_Birth__c',
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.Address_Street__c', 'Lead__r.City__c',
                       'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.Date_of_Abuse__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Address_Street__c': 'Address',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip',
        "Lead__r.Date_of_Abuse__c":"Date of Abuse"
    })

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    # Smart views pide fechas mm/dd/yyyy
    df_sent['Retainer Signed Date'] = datetime.today().strftime('%m/%d/%Y')

    df_sent['Date of Birth'] = pd.to_datetime(df_sent['Date of Birth'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent['Date of Abuse'] = pd.to_datetime(df_sent['Date of Abuse'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — OLYMPUS T1
# ============================================
def obtener_datos_olympus_t1(case_number):

    global sf

    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.ip_address__c, 
            Lead__r.Trusted_Form__c,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Had_any_of_these_procedures__c,
            Lead__r.Did_the_infection_occur_within_a_year__c,
            Lead__r.Was_the_infection_after_2015__c,
            Lead__r.Did_you_have_any_of_these_infections__c,
            Lead__r.Hospitalized_with_IV_antibiotics__c,
            Lead__r.State_of_Incident__c,
            Lead__r.Medical_Records__c,
            Lead__r.Do_you_have_an_attorney__c
            FROM Lead_de_oportunidad__c
            WHERE Oportunidad__r.AccountId='001TR000000wRPiYAM' AND Lead__r.Status = 'Sent' AND Lead__r.Type='Olympus'
        """
    )

    records = accounts_sent.get("records", [])

    if not records:
        return pd.DataFrame()

    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])

    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent

    df_sent = df_sent[[
        'Lead__r.Id','Lead__r.CaseNumber','Lead__r.ip_address__c','Lead__r.Trusted_Form__c','Lead__r.FirstName__c','Lead__r.Last_Name__c',
        'Lead__r.Phone_Numbercontact__c','Lead__r.Email__c','Lead__r.Had_any_of_these_procedures__c','Lead__r.Did_the_infection_occur_within_a_year__c',
        'Lead__r.Was_the_infection_after_2015__c','Lead__r.Did_you_have_any_of_these_infections__c','Lead__r.Hospitalized_with_IV_antibiotics__c',
        'Lead__r.State_of_Incident__c','Lead__r.Medical_Records__c','Lead__r.Do_you_have_an_attorney__c'
    ]]

    df_sent = df_sent.rename(columns={
        "Lead__r.Id": "Current Date/Time",
        "Lead__r.CaseNumber": "Case Number",
        "Lead__r.ip_address__c": "IP Address",
        "Lead__r.Trusted_Form__c": "Trusted Form",
        "Lead__r.FirstName__c": "First Name",
        "Lead__r.Last_Name__c": "Last Name",
        "Lead__r.Phone_Numbercontact__c": "Phone Number",
        "Lead__r.Email__c": "Email",
        "Lead__r.Had_any_of_these_procedures__c": "Did you have a scope or endoscopic procedure from the list below?",
        "Lead__r.Did_the_infection_occur_within_a_year__c": "Did the infection occur within 1 year after the procedure?",
        "Lead__r.Was_the_infection_after_2015__c": "Was the infection after 2015?",
        "Lead__r.Did_you_have_any_of_these_infections__c": "Did you experience any of the following infections?",
        "Lead__r.Hospitalized_with_IV_antibiotics__c": "Were you hospitalized and given IV antibiotics?",
        "Lead__r.State_of_Incident__c": "What state did you get the procedure in?",
        "Lead__r.Medical_Records__c": "Are you able to obtain your medical records?",
        "Lead__r.Do_you_have_an_attorney__c": "Are you currently working with an attorney?"
    })


    df_sent["Current Date/Time"] = pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")

    df_sent = df_sent.fillna("NA")

    df_sent = df_sent.replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTENER DATOS — SEX TRAFFICKING T1
# ============================================

def obtener_datos_sex_trafficking_t1(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Area_Code__c,
            Lead__r.ip_address__c,
            Lead__r.Landing_Page_URL__c,
            Lead__r.Where_did_the_incident_occur__c,
            Lead__r.Minor_underage_at_the_time__c,
            Lead__r.Incident_Date__c,
            Lead__r.Do_you_know_the_name_of_the_person__c,
            Lead__r.Trusted_Form__c
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR00000LRBBNYA5' AND Lead__r.Substatus__c='Transferred' AND Lead__r.Type='Sex Trafficking'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id','Lead__r.FirstName__c','Lead__r.Last_Name__c','Lead__r.Email__c','Lead__r.Phone_Numbercontact__c','Lead__r.Area_Code__c',
                       'Lead__r.ip_address__c','Lead__r.Landing_Page_URL__c','Lead__r.Where_did_the_incident_occur__c','Lead__r.Minor_underage_at_the_time__c',
                       'Lead__r.Incident_Date__c','Lead__r.Do_you_know_the_trafficker_s_name__c','Lead__r.Trusted_Form__c']]
    
    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Area_Code__c': 'Zip Code',
        'Lead__r.ip_address__c': 'Ip Address',
        'Lead__r.Landing_Page_URL__c': 'Landing Page',
        'Lead__r.Where_did_the_incident_occur__c': 'Did the trafficking occur at a Motel 6, Studio 6, or Studio 6 Plus?',
        'Lead__r.Minor_underage_at_the_time__c': 'Were you a minor when the incident occurred?',
        'Lead__r.Incident_Date__c':'Did this happen in 2018 or earlier?',
        'Lead__r.Do_you_know_the_name_of_the_person__c':'Do you know the name of the trafficker or pimp involved?',
        'Lead__r.Trusted_Form__c':'Trusted Form'
    })

    df_sent['Zip Code'] = pd.to_numeric(df_sent['Zip Code'], errors='coerce').astype('Int64')

    df_sent["Did the trafficking occur at a Motel 6, Studio 6, or Studio 6 Plus?"] = df_sent["Did the trafficking occur at a Motel 6, Studio 6, or Studio 6 Plus?"].apply(lambda x: "yes" if pd.notna(x) and str(x).lower() != "na" else "no")

    df_sent['Do you know the name of the trafficker or pimp involved?'] = df_sent['Do you know the name of the trafficker or pimp involved?'].str.lower()

    df_sent['Were you a minor when the incident occurred?'] = df_sent['Were you a minor when the incident occurred?'].str.lower()

    df_sent["Did this happen in 2018 or earlier?"] = pd.to_datetime(df_sent["Did this happen in 2018 or earlier?"], errors="coerce").apply(lambda x: "yes" if pd.notna(x) and x.year <= 2018 else "no")

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent


# ============================================
# FUNCIÓN OBTE1NER DATOS — HERNIA MESH T1
# ============================================

def obtener_datos_hernia_mesh_t1(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Email__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Area_Code__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Signer_Last_4_SSN__c,
            Lead__r.State_of_Incident__c,
            Lead__r.Incident_Date__c,
            Lead__r.Additional_Notes__c,
            Lead__r.Hernia_Mesh_Harms__c
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR000015URsDYAW' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Hernia Mesh'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Email__c', 
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Area_Code__c', 'Lead__r.Address_Street__c', 'Lead__r.City__c', 
                       'Lead__r.StateUS__c', 'Lead__r.Date_of_Birth__c', 'Lead__r.Signer_Last_4_SSN__c', 'Lead__r.State_of_Incident__c', 
                       'Lead__r.Incident_Date__c', 'Lead__r.Additional_Notes__c','Lead__r.Hernia_Mesh_Harms__c']]
        
    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Area_Code__c': 'Zip',
        'Lead__r.Address_Street__c': 'Address',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Signer_Last_4_SSN__c': 'SSN Last Four',
        'Lead__r.State_of_Incident__c': 'State of Incident',
        'Lead__r.Incident_Date__c': 'Incident Date',
        'Lead__r.Additional_Notes__c': 'Additional Notes',
        'Lead__r.Hernia_Mesh_Harms__c':'Hernia Mesh Harms'
    })

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')
    # SSN llega como decimal (123.0): se pasa a entero y se completa con ceros a 4 dígitos
    ssn = pd.to_numeric(df_sent['SSN Last Four'], errors='coerce').astype('Int64')
    df_sent['SSN Last Four'] = ssn.astype(str).str.zfill(4).where(ssn.notna())

    df_sent['Retainer Signed Date'] = datetime.today().strftime('%Y-%m-%dT12:00:00Z')

    df_sent['Date of Birth'] = pd.to_datetime(df_sent['Date of Birth'], errors='coerce').dt.strftime('%Y-%m-%d')

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent



# ============================================
# FUNCIÓN OBTE1NER DATOS — HERNIA MESH T1 - SMART REVIEWS
# ============================================

def obtener_datos_hernia_mesh_t1_smart_reviews(case_number):
    global sf
    accounts_sent = sf.query_all(
        """
            SELECT
            Lead__r.Id,
            Lead__r.CaseNumber,
            Lead__r.FirstName__c,
            Lead__r.Last_Name__c,
            Lead__r.Date_of_Birth__c,
            Lead__r.Phone_Numbercontact__c,
            Lead__r.Email__c,
            Lead__r.Address_Street__c,
            Lead__r.City__c,
            Lead__r.StateUS__c,
            Lead__r.Area_Code__c,
            Lead__r.DiagnosisYear__c
            FROM Lead_de_oportunidad__c
	        WHERE Oportunidad__r.AccountId='001TR000015URsDYAW' AND Lead__r.Substatus__c='Signed' AND Lead__r.Type='Hernia Mesh'
        """
    )
    records = accounts_sent.get("records", [])
    if not records:
        return pd.DataFrame()
    df_sent = json_normalize(records)

    if "attributes" in df_sent.columns:
        df_sent = df_sent.drop(columns=["attributes"])
    df_sent = df_sent[df_sent['Lead__r.CaseNumber'].apply(normalizar_case_number) == normalizar_case_number(case_number)]

    if df_sent.empty:
        return df_sent
    
    df_sent = df_sent[['Lead__r.Id', 'Lead__r.CaseNumber', 'Lead__r.FirstName__c', 'Lead__r.Last_Name__c', 'Lead__r.Date_of_Birth__c',
                       'Lead__r.Phone_Numbercontact__c', 'Lead__r.Email__c', 'Lead__r.Address_Street__c', 'Lead__r.City__c',
                       'Lead__r.StateUS__c', 'Lead__r.Area_Code__c', 'Lead__r.DiagnosisYear__c']]

    df_sent = df_sent.rename(columns={
        'Lead__r.Id': 'Id',
        'Lead__r.CaseNumber': 'Case Number',
        'Lead__r.FirstName__c': 'First Name',
        'Lead__r.Last_Name__c': 'Last Name',
        'Lead__r.Date_of_Birth__c': 'Date of Birth',
        'Lead__r.Phone_Numbercontact__c': 'Phone Number',
        'Lead__r.Email__c': 'Email',
        'Lead__r.Address_Street__c': 'Address',
        'Lead__r.City__c': 'City',
        'Lead__r.StateUS__c': 'State',
        'Lead__r.Area_Code__c': 'Zip',
        "Lead__r.DiagnosisYear__c":"Date of Diagnosis"
    })

    df_sent['Zip'] = pd.to_numeric(df_sent['Zip'], errors='coerce').astype('Int64')

    # Smart Reviews pide fechas mm/dd/yyyy
    df_sent['Retainer Signed Date'] = datetime.today().strftime('%m/%d/%Y')

    df_sent['Date of Birth'] = pd.to_datetime(df_sent['Date of Birth'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent['Date of Diagnosis'] = pd.to_datetime(df_sent['Date of Diagnosis'], errors='coerce').dt.strftime('%m/%d/%Y')

    df_sent = df_sent.fillna("NA").replace("", "NA")

    return df_sent



# ============================================
# ENVIAR A SF EL RESPONSE CODE
# ============================================
# API_Message_Result__c es Text(255): se recorta para que Salesforce no rechace el update
def enviar_api_resultado(lead_id, api_response_text):
    global sf
    sf.Case.update(lead_id, {"API_Message_Result__c": str(api_response_text)[:255]})

# ============================================
# ENVIAR A SF EL RESPONSE CODE — TURNDOWN CASES
# ============================================
def enviar_api_resultado_turndowncases(lead_id, api_response_text):
    global sf
    sf.Case.update(lead_id, {"API_Message_Result__c": str(api_response_text)[:255], "TDC__c": True})

# ============================================
# MOSTRAR FORMULARIO
# ============================================
def mostrar_tabla(df, campaign=""):
    ventana = tk.Toplevel()
    ventana.title("Detalle del Lead")
    ventana.geometry("760x660")
    ventana.configure(bg=BG)

    # --- Header ---
    hdr = tk.Frame(ventana, bg="#1E293B")
    hdr.pack(fill="x")
    tk.Label(hdr, text="Detalle del Lead", font=("Segoe UI", 13, "bold"),
             bg="#1E293B", fg="white", padx=16, pady=12).pack(side="left")
    if campaign:
        tk.Label(hdr, text=f"Campaña: {campaign}", font=("Segoe UI", 9),
                 bg="#1E293B", fg="#94A3B8", padx=16).pack(side="right")

    # --- Botón Enviar fijo abajo ---
    btn_frame = tk.Frame(ventana, bg=BG, padx=16, pady=12)
    btn_frame.pack(fill="x", side="bottom")
    tk.Frame(btn_frame, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))

    def on_enviar():
        camp = opcion.get()

        # Bard Port T5: sin API, solo correo + asunto guardado en Salesforce
        if camp == "Bard Port T5":
            faltantes = [t for t, ruta in archivos_hernia.items() if not ruta]
            if faltantes:
                mostrar_error("Falta adjuntar: " + ", ".join(faltantes))
                return
            archivos = list(archivos_hernia.items())
            try:
                asunto = enviar_correo_adjuntos_bard_port_t5(row_data, archivos)
            except Exception as e:
                mostrar_error(f"Falló el envío del correo: {e}")
                return
            try:
                enviar_api_resultado(row_data.get("Id"), asunto)
            except Exception as e:
                mostrar_error(f"El correo se envió OK, pero falló la actualización en Salesforce: {e}")
                return
            mostrar_exito(f"Correo enviado y Salesforce actualizado.\n\nAsunto: {asunto}")
            return

        # Social Media Addiction T1: sin API, solo correo + asunto guardado en Salesforce
        if camp == "Social Media Addiction T1":
            # Adjuntos opcionales: se envía solo lo que se haya seleccionado
            archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
            try:
                asunto = enviar_correo_adjuntos_social_media_addiction_t1_full(row_data, archivos)
            except Exception as e:
                mostrar_error(f"Falló el envío del correo a Ventura Law: {e}\n\nNo se envió ningún correo.")
                return
            try:
                enviar_correo_adjuntos_social_media_addiction_t1_no_mp3(row_data, archivos)
            except Exception as e:
                mostrar_error(f"El correo a Ventura Law se envió OK, pero falló el correo a AWKO: {e}\n\nSalesforce no se actualizó.")
                return
            try:
                enviar_api_resultado(row_data.get("Id"), asunto)
            except Exception as e:
                mostrar_error(f"El correo se envió OK, pero falló la actualización en Salesforce: {e}")
                return
            mostrar_exito(f"Correo enviado y Salesforce actualizado.\n\nAsunto: {asunto}")
            return

        try:
            if camp == "Rideshare T11":
                response = enviar_api_rs11(row_data)
            elif camp == "Bard Port T2":
                response = enviar_api_bardport_t2(row_data)
            elif camp == "Bard Port T4":
                response = enviar_api_bard_port_t4(row_data)
            elif camp == "Depo Provera T8":
                response = enviar_api_depoprovera_t8(row_data)
            elif camp == "Talcum T15":
                response = enviar_api_talcum_t15(row_data)
            elif camp == "Rideshare T9":
                response = enviar_api_rideshare_t9(row_data, archivos_seleccionados or None)
            elif camp == "Depo Provera T7 Stinar":
                response = enviar_api_depoprovera_t7_stinar(row_data, archivos_seleccionados or None)
            elif camp == "Depo Provera T7 Hickory":
                response = enviar_api_depoprovera_t7_hickory(row_data, archivos_seleccionados or None)
            elif camp == "Rideshare T10":
                response = enviar_api_rideshare_t10(row_data)
            elif camp == "Rideshare T12 & T13 & T14":
                response = enviar_api_ridehsare_t12_t13_14(row_data)
            elif camp == "Womens Prisioner Abuse T1":
                response = enviar_api_womens_prisioner_abuse_t1(row_data, archivos_seleccionados or None)
            elif camp == "Womens Prisioner Abuse T2":
                response = enviar_api_womens_prisioner_abuse_t2(row_data)
            elif camp == "Womens Prisioner Abuse T3":
                # Adjuntos opcionales: se envía solo lo que se haya seleccionado
                archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
                response = enviar_api_womens_prisioner_abuse_t3(row_data, archivos or None)
            elif camp == "Chlorpyrifos T1":
                response = enviar_api_chlorpyrifos_t1(row_data, archivos_seleccionados or None)
            elif camp == "Chlorpyrifos T2":
                response = enviar_api_chlorpyrifos_t2(row_data)
            elif camp == "Asbestos T1":
                response = enviar_api_asbestos_t1(row_data)
            elif camp == "Asbestos T1 - Turndown Cases":
                response = enviar_api_asbestos_t1_turndowncases(row_data)
            elif camp == "Juvenile Detention Center T3":
                response = enviar_api_juvenile_detention_center_t3(row_data, archivos_seleccionados or None)
            elif camp == "Juvenile Detention Center T4":
                response = enviar_api_juvenile_detention_center_t4(row_data)
            elif camp == "Juvenile Detention Center T5":
                response = enviar_api_juvenile_detention_center_t5(row_data)
            elif camp == "Juvenile Detention Center T6":
                # Adjuntos opcionales: se envía solo lo que se haya seleccionado
                archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
                response = enviar_api_juvenile_detention_center_t6(row_data, archivos or None)
            elif camp == "Olympus T1":
                response = enviar_api_olympus_t1(row_data)
            elif camp == "Sex Trafficking T1":
                response = enviar_api_sex_trafficking_t1(row_data)
            elif camp == "Hernia Mesh T1":
                faltantes = [t for t in ("Retainer", "HIPAA", "Intake Questionnaire") if not archivos_hernia[t]]
                if faltantes:
                    mostrar_error("Falta adjuntar: " + ", ".join(faltantes))
                    return
                archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
                response = enviar_api_hernia_mesh_t1(row_data, archivos)
            elif camp == "Hernia Mesh T1 - Smart Reviews":
                faltantes = [t for t in ("Retainer", "HIPAA", "Intake Questionnaire") if not archivos_hernia[t]]
                if faltantes:
                    mostrar_error("Falta adjuntar: " + ", ".join(faltantes))
                    return
                archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
                response = enviar_api_hernia_mesh_t1_smart_reviews(row_data, archivos)
            elif camp == "Bard Port T3":
                faltantes = [t for t in ("Retainer", "HIPAA", "Intake Questionnaire") if not archivos_hernia[t]]
                if faltantes:
                    mostrar_error("Falta adjuntar: " + ", ".join(faltantes))
                    return
                archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
                response = enviar_api_bardport_t3(row_data, archivos)
            else:
                mostrar_error("Campaña no soportada aún")
                return
            mostrar_respuesta_api(response)
            if response.status_code in [200, 201]:
                lead_id = row_data.get("Id")
                if camp == "Asbestos T1 - Turndown Cases":
                    sf_status = enviar_api_resultado_turndowncases(lead_id, response.text)
                else:
                    sf_status = enviar_api_resultado(lead_id, response.text)
                print("Actualización Salesforce:", sf_status)

                if camp == "Bard Port T3":
                    try:
                        enviar_correo_adjuntos_bard_port_t3(row_data, camp, archivos)
                        print("Correo con adjuntos enviado.")
                    except Exception as e:
                        mostrar_error(f"El API se envió OK, pero falló el correo: {e}")

                if camp == "Rideshare T10":
                    try:
                        lp_lead_id = response.json().get("lead_id")
                    except Exception:
                        lp_lead_id = None
                    if lp_lead_id:
                        mostrar_ventana_documento_rideshare_t10(lp_lead_id, lead_id, response.text)
        except Exception as e:
            mostrar_error(str(e))

    # Bard Port T3: reenviar solo el correo con adjuntos, sin volver a llamar a la API
    def on_enviar_solo_correo():
        faltantes = [t for t in ("Retainer", "HIPAA", "Intake Questionnaire") if not archivos_hernia[t]]
        if faltantes:
            mostrar_error("Falta adjuntar: " + ", ".join(faltantes))
            return
        archivos = [(tipo, ruta) for tipo, ruta in archivos_hernia.items() if ruta]
        try:
            enviar_correo_adjuntos_bard_port_t3(row_data, opcion.get(), archivos)
        except Exception as e:
            mostrar_error(f"Falló el envío del correo: {e}")
            return
        mostrar_exito("Correo con adjuntos enviado (sin API).")

    if campaign == "Bard Port T3":
        tk.Button(
            btn_frame,
            text="Enviar solo correo",
            command=on_enviar_solo_correo,
            bg=DIS_BG,
            fg=TEXT_DARK,
            activebackground="#E2E8F0",
            activeforeground=TEXT_DARK,
            font=("Segoe UI", 11, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            pady=9,
        ).pack(fill="x", pady=(0, 8))

    tk.Button(
        btn_frame,
        text="Enviar",
        command=on_enviar,
        bg=BTN_ACCENT,
        fg="white",
        activebackground=BTN_ACCENT_HV,
        activeforeground="white",
        font=("Segoe UI", 12, "bold"),
        relief="flat",
        bd=0,
        cursor="hand2",
        pady=11,
    ).pack(fill="x")

    # --- Área scrollable ---
    main_frame = tk.Frame(ventana, bg=BG)
    main_frame.pack(fill="both", expand=True)

    canvas = tk.Canvas(main_frame, bg=BG, highlightthickness=0)
    scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")
    canvas.configure(yscrollcommand=scrollbar.set)

    scroll_frame = tk.Frame(canvas, bg=BG)
    window_id = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

    label_widgets = []
    value_widgets = []

    def on_resize(event):
        w = event.width
        canvas.coords(window_id, 0, 0)
        canvas.itemconfig(window_id, width=w)
        col0_wrap = max(80, w // 3 - 40)
        col1_wrap = max(150, w * 2 // 3 - 40)
        for lbl in label_widgets:
            lbl.config(wraplength=col0_wrap)
        for val in value_widgets:
            val.config(wraplength=col1_wrap)

    canvas.bind("<Configure>", on_resize)
    scroll_frame.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))

    if df.empty:
        tk.Label(scroll_frame, text="No hay datos", bg=BG, fg=TEXT_MUTED,
                 font=("Segoe UI", 11)).pack(pady=40)
        return

    row_data = df.iloc[0]
    archivos_seleccionados = []
    archivos_hernia = {"Retainer": None, "HIPAA": None, "Intake Questionnaire": None}
    if campaign == "Bard Port T5":
        archivos_hernia["Portal Patient Authorization"] = None
    elif campaign == "Womens Prisioner Abuse T3":
        archivos_hernia = {"Intake Questionnaire": None, "Retainer": None}
    elif campaign == "Social Media Addiction T1":
        archivos_hernia = {"ID": None, "Retainer": None, "Intake Questionnaire": None, "Audio": None}

    # Campañas cuyos documentos por tipo son opcionales (el resto los exige todos)
    adjuntos_opcionales = campaign in ("Womens Prisioner Abuse T3", "Social Media Addiction T1", "Juvenile Detention Center T6")

    # --- Tabla ---
    tk.Frame(scroll_frame, bg=BG, height=14).pack(fill="x")

    table_outer = tk.Frame(scroll_frame, bg=BORDER)
    table_outer.pack(fill="x", padx=16)
    table_inner = tk.Frame(table_outer, bg=BG)
    table_inner.pack(fill="both", expand=True, padx=1, pady=1)
    table_inner.columnconfigure(0, weight=1)
    table_inner.columnconfigure(1, weight=2)

    for i, col in enumerate([c for c in df.columns if c != "Id"]):
        key_bg = "#F8FAFC" if i % 2 == 0 else "#EFF6FF"
        val_bg = "white"   if i % 2 == 0 else "#F0F9FF"

        lbl = tk.Label(
            table_inner,
            text=col,
            anchor="nw",
            justify="left",
            bg=key_bg,
            fg=TEXT_DARK,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=10,
            relief="flat",
            wraplength=170,
        )
        lbl.grid(row=i * 2, column=0, sticky="nsew")
        label_widgets.append(lbl)

        val = tk.Label(
            table_inner,
            text=str(row_data[col]),
            anchor="nw",
            justify="left",
            wraplength=370,
            font=("Segoe UI", 10),
            padx=14,
            pady=10,
            relief="flat",
            bg=val_bg,
            fg=TEXT_DARK,
        )
        val.grid(row=i * 2, column=1, sticky="nsew")
        value_widgets.append(val)

        tk.Frame(table_inner, bg=BORDER, height=1).grid(
            row=i * 2 + 1, column=0, columnspan=2, sticky="ew"
        )

    # --- Archivos adjuntos (T9, T7, WPA, Chlorpyrifos) ---
    if campaign in ("Rideshare T9", "Depo Provera T7 Stinar", "Depo Provera T7 Hickory", "Womens Prisioner Abuse T1", "Chlorpyrifos T1", "Juvenile Detention Center T3"):
        tk.Frame(scroll_frame, bg=BG, height=14).pack(fill="x")

        arch_outer = tk.Frame(scroll_frame, bg=BORDER)
        arch_outer.pack(fill="x", padx=16)
        arch_inner = tk.Frame(arch_outer, bg=BG)
        arch_inner.pack(fill="both", expand=True, padx=1, pady=1)
        arch_inner.columnconfigure(0, weight=1)
        arch_inner.columnconfigure(1, weight=2)

        tk.Label(
            arch_inner,
            text="Archivos adjuntos",
            anchor="nw",
            bg="#F8FAFC",
            fg=TEXT_DARK,
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=10,
            relief="flat",
        ).grid(row=0, column=0, sticky="nsew")

        frame_file_val = tk.Frame(arch_inner, bg="white")
        frame_file_val.grid(row=0, column=1, sticky="nsew")

        frame_lista = tk.Frame(frame_file_val, bg="white")
        frame_lista.pack(fill="x", padx=10, pady=8)

        def actualizar_lista_archivos():
            for widget in frame_lista.winfo_children():
                widget.destroy()
            if not archivos_seleccionados:
                tk.Label(frame_lista, text="Sin archivos seleccionados",
                         fg=TEXT_MUTED, bg="white", font=("Segoe UI", 9)).pack(anchor="w")
            else:
                for i, ruta in enumerate(archivos_seleccionados):
                    fila = tk.Frame(frame_lista, bg="white")
                    fila.pack(fill="x", pady=1)
                    tk.Label(fila, text=os.path.basename(ruta), bg="white",
                             font=("Segoe UI", 9), fg=TEXT_DARK, anchor="w"
                             ).pack(side="left", fill="x", expand=True)
                    def eliminar(idx=i):
                        archivos_seleccionados.pop(idx)
                        actualizar_lista_archivos()
                    tk.Button(fila, text="✕", command=eliminar,
                              font=("Segoe UI", 8, "bold"), fg="#EF4444",
                              bg="white", bd=0, cursor="hand2", padx=4
                              ).pack(side="right")

        actualizar_lista_archivos()

        def seleccionar_archivos():
            rutas = filedialog.askopenfilenames(title="Seleccionar archivos")
            for r in rutas:
                if r not in archivos_seleccionados:
                    archivos_seleccionados.append(r)
            if rutas:
                actualizar_lista_archivos()

        tk.Button(
            frame_file_val,
            text="+ Adjuntar archivos",
            command=seleccionar_archivos,
            font=("Segoe UI", 9),
            bg=DIS_BG,
            fg=TEXT_DARK,
            activebackground="#E2E8F0",
            relief="flat",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=5,
        ).pack(anchor="w", padx=10, pady=(0, 8))

    # --- Archivos adjuntos por tipo (Hernia Mesh) ---
    if campaign in ("Hernia Mesh T1", "Hernia Mesh T1 - Smart Reviews", "Bard Port T3", "Bard Port T5", "Womens Prisioner Abuse T3", "Social Media Addiction T1", "Juvenile Detention Center T6"):
        tk.Frame(scroll_frame, bg=BG, height=14).pack(fill="x")

        arch_outer = tk.Frame(scroll_frame, bg=BORDER)
        arch_outer.pack(fill="x", padx=16)
        arch_inner = tk.Frame(arch_outer, bg=BG)
        arch_inner.pack(fill="both", expand=True, padx=1, pady=1)
        arch_inner.columnconfigure(0, weight=1)
        arch_inner.columnconfigure(1, weight=2)

        for i, tipo in enumerate(archivos_hernia):
            requerido = not adjuntos_opcionales  # el * marca los documentos obligatorios
            tk.Label(
                arch_inner,
                text=tipo + (" *" if requerido else ""),
                anchor="nw",
                bg="#F8FAFC",
                fg=TEXT_DARK,
                font=("Segoe UI", 10, "bold"),
                padx=14,
                pady=10,
                relief="flat",
            ).grid(row=i, column=0, sticky="nsew")

            celda = tk.Frame(arch_inner, bg="white")
            celda.grid(row=i, column=1, sticky="nsew")

            lbl_archivo = tk.Label(celda, text="Sin archivo", fg=TEXT_MUTED, bg="white",
                                   font=("Segoe UI", 9), anchor="w")
            lbl_archivo.pack(side="left", fill="x", expand=True, padx=10, pady=8)

            # ✕ para quitar el documento si se adjuntó uno equivocado (solo visible con archivo)
            btn_quitar = tk.Button(celda, text="✕", font=("Segoe UI", 8, "bold"), fg="#EF4444",
                                   bg="white", bd=0, cursor="hand2", padx=4)

            def quitar_pdf(tipo=tipo, lbl=lbl_archivo, btn=btn_quitar):
                archivos_hernia[tipo] = None
                lbl.config(text="Sin archivo", fg=TEXT_MUTED)
                btn.pack_forget()

            btn_quitar.config(command=quitar_pdf)

            def seleccionar_pdf(tipo=tipo, lbl=lbl_archivo, btn=btn_quitar):
                tipos_archivo = [("Audio MP3", "*.mp3")] if tipo == "Audio" else [("PDF", "*.pdf")]
                ruta = filedialog.askopenfilename(title=f"Seleccionar {tipo}",
                                                  filetypes=tipos_archivo)
                if ruta:
                    archivos_hernia[tipo] = ruta
                    lbl.config(text=os.path.basename(ruta), fg=TEXT_DARK)
                    if not btn.winfo_ismapped():
                        btn.pack(side="right", padx=(0, 4))

            tk.Button(
                celda,
                text="Seleccionar",
                command=seleccionar_pdf,
                font=("Segoe UI", 9),
                bg=DIS_BG,
                fg=TEXT_DARK,
                activebackground="#E2E8F0",
                relief="flat",
                bd=0,
                cursor="hand2",
                padx=10,
                pady=5,
            ).pack(side="right", padx=10, pady=6)

    tk.Frame(scroll_frame, bg=BG, height=14).pack(fill="x")


# ============================================
# CAMPAÑAS (agrupadas por categoría)
# ============================================
campaign_categories = {
    "Rideshare": ["Rideshare T9", "Rideshare T10", "Rideshare T11", "Rideshare T12 & T13 & T14"],
    "Depo Provera": ["Depo Provera T7 Stinar", "Depo Provera T7 Hickory", "Depo Provera T8"],
    "Chlorpyrifos": ["Chlorpyrifos T1", "Chlorpyrifos T2"],
    "Womens Prisioner Abuse": ["Womens Prisioner Abuse T1", "Womens Prisioner Abuse T2", "Womens Prisioner Abuse T3"],
    "Bard Port": ["Bard Port T2", "Bard Port T3", "Bard Port T4", "Bard Port T5"],
    "Talcum": ["Talcum T15"],
    "Asbestos": ["Asbestos T1", "Asbestos T1 - Turndown Cases"],
    "Juvenile Detention Center":["Juvenile Detention Center T3", "Juvenile Detention Center T4", "Juvenile Detention Center T5", "Juvenile Detention Center T6"],
    "Olympus": ["Olympus T1"],
    "Sex Trafficking": ["Sex Trafficking T1"],
    "Hernia Mesh": ["Hernia Mesh T1", "Hernia Mesh T1 - Smart Reviews"],
    "Social Media Addiction": ["Social Media Addiction T1"],
}


# ============================================
# VALIDACIÓN
# ============================================
def validar():
    campaign = opcion.get()
    case_number = obtener_case_number()

    if campaign == "":
        mostrar_error("Falta seleccionar la campaña")
        return

    if case_number == "":
        mostrar_error("Ingresa un Case Number")
        return

    if campaign == "Rideshare T11":
        df = obtener_datos_rs11(case_number)
    elif campaign == "Bard Port T2":
        df = obtener_datos_bardport_t2(case_number)
    elif campaign == "Bard Port T3":
        df = obtener_datos_bardport_t3(case_number)
    elif campaign == "Bard Port T4":
        df = obtener_datos_bard_port_t4(case_number)
    elif campaign == "Bard Port T5":
        df = obtener_datos_bard_port_t5(case_number)
    elif campaign == "Depo Provera T8":
        df = obtener_datos_depoprovera_t8(case_number)
    elif campaign == "Talcum T15":
        df = obtener_datos_talcum_t15(case_number)
    elif campaign == "Rideshare T9":
        df = obtener_datos_rideshare_t9(case_number)
    elif campaign == "Depo Provera T7 Stinar":
        df = obtener_datos_depo_provera_t7(case_number)
    elif campaign == "Depo Provera T7 Hickory":
        df = obtener_datos_depo_provera_t7(case_number)
    elif campaign == "Rideshare T10":
        df = obtener_datos_rideshare_t10(case_number)
    elif campaign == "Rideshare T12 & T13 & T14":
        df = obtener_datos_rideshare_t12_t13_t14(case_number)
    elif campaign == "Womens Prisioner Abuse T1":
        df = obtener_datos_womens_prisioner_abuse_t1(case_number)
    elif campaign == "Womens Prisioner Abuse T2":
        df = obtener_datos_womens_prisioner_abuse_t2(case_number)
    elif campaign == "Womens Prisioner Abuse T3":
        df = obtener_datos_womens_prisioner_abuse_t3(case_number)
    elif campaign == "Chlorpyrifos T1":
        df = obtener_datos_chlorpyrifos_t1(case_number)
    elif campaign == "Chlorpyrifos T2":
        df = obtener_datos_chlorpyrifos_t2(case_number)
    elif campaign == "Asbestos T1":
        df = obtener_datos_asbestos_t1(case_number)
    elif campaign == "Asbestos T1 - Turndown Cases":
        df = obtener_datos_asbestos_t1_turndowncases(case_number)
    elif campaign == "Juvenile Detention Center T3":
        df = obtener_datos_juvenile_detention_center_t3(case_number)
    elif campaign == "Juvenile Detention Center T4":
        df = obtener_datos_juvenile_detention_center_t4(case_number)
    elif campaign == "Juvenile Detention Center T5":
        df = obtener_datos_juvenile_detention_center_t5(case_number)
    elif campaign == "Juvenile Detention Center T6":
        df = obtener_datos_juvenile_detention_center_t6(case_number)
    elif campaign == "Olympus T1":
        df = obtener_datos_olympus_t1(case_number)
    elif campaign == "Sex Trafficking T1":
        df = obtener_datos_sex_trafficking_t1(case_number)
    elif campaign == "Hernia Mesh T1":
        df = obtener_datos_hernia_mesh_t1(case_number)
    elif campaign == "Hernia Mesh T1 - Smart Reviews":
        df = obtener_datos_hernia_mesh_t1_smart_reviews(case_number)
    elif campaign == "Social Media Addiction T1":
        df = obtener_datos_social_media_addiction_t1(case_number)
    else:
        mostrar_error("Campaña no soportada aún")
        return

    if df.empty:
        mostrar_sin_resultados()
    else:
        mostrar_tabla(df, campaign)


# ============================================
# UI
# ============================================
BG         = "#F1F5F9"
CARD_BG    = "#FFFFFF"
PRIMARY    = "#2ea043"
PRIMARY_HV = "#2c974b"
TEXT_DARK  = "#1E293B"
TEXT_MUTED = "#64748B"
BORDER     = "#CBD5E1"
DIS_BG     = "#F1F5F9"
DIS_FG     = "#94A3B8"
PLOMO_BG   = "#94A3B8"
PLOMO_FG   = "#FFFFFF"

# Botones de selección (tipo de campaña / campaña)
BTN_FONT      = ("Inter", -13, "normal") # ~13px, peso normal (Tk solo soporta normal/bold)
BTN_BORDER    = "#E4E7EC"                # gris claro, equivalente a oklch(90% 0.005 250)
BTN_ACCENT    = "#4F46E5"                # indigo
BTN_ACCENT_HV = "#4338CA"                # indigo, hover/active
BTN_BG_SEL    = "#EAE9FC"                # acento mezclado ~12% con blanco
BTN_TEXT_SEL  = BTN_ACCENT

def mostrar_error(mensaje, titulo="Error"):
    win = tk.Toplevel()
    win.title(titulo)
    win.geometry("420x230")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    hdr = tk.Frame(win, bg="#1E293B")
    hdr.pack(fill="x")
    tk.Label(hdr, text=f"  {titulo}", font=("Segoe UI", 12, "bold"),
             bg="#1E293B", fg="white", padx=16, pady=11, anchor="w").pack(side="left")

    tk.Frame(win, bg="#EF4444", height=3).pack(fill="x")

    body_f = tk.Frame(win, bg=BG, padx=24, pady=22)
    body_f.pack(fill="both", expand=True)
    tk.Label(body_f, text=mensaje, font=("Segoe UI", 11),
             bg=BG, fg=TEXT_DARK, wraplength=360, justify="left").pack(anchor="w")

    btn_frame = tk.Frame(win, bg=BG, padx=16, pady=12)
    btn_frame.pack(fill="x", side="bottom")
    tk.Frame(btn_frame, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
    tk.Button(
        btn_frame, text="Cerrar", command=win.destroy,
        bg="#EF4444", fg="white",
        activebackground="#DC2626", activeforeground="white",
        font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
        cursor="hand2", pady=9,
    ).pack(fill="x")


def mostrar_exito(mensaje, titulo="Envío exitoso"):
    win = tk.Toplevel()
    win.title(titulo)
    win.geometry("420x230")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    hdr = tk.Frame(win, bg="#1E293B")
    hdr.pack(fill="x")
    tk.Label(hdr, text=f"  {titulo}", font=("Segoe UI", 12, "bold"),
             bg="#1E293B", fg="white", padx=16, pady=11, anchor="w").pack(side="left")

    tk.Frame(win, bg="#22C55E", height=3).pack(fill="x")

    body_f = tk.Frame(win, bg=BG, padx=24, pady=22)
    body_f.pack(fill="both", expand=True)
    tk.Label(body_f, text=mensaje, font=("Segoe UI", 11),
             bg=BG, fg=TEXT_DARK, wraplength=360, justify="left").pack(anchor="w")

    btn_frame = tk.Frame(win, bg=BG, padx=16, pady=12)
    btn_frame.pack(fill="x", side="bottom")
    tk.Frame(btn_frame, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
    tk.Button(
        btn_frame, text="Cerrar", command=win.destroy,
        bg="#22C55E", fg="white",
        activebackground="#16A34A", activeforeground="white",
        font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
        cursor="hand2", pady=9,
    ).pack(fill="x")


def mostrar_sin_resultados():
    win = tk.Toplevel()
    win.title("Sin resultados")
    win.geometry("420x230")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()

    hdr = tk.Frame(win, bg="#1E293B")
    hdr.pack(fill="x")
    tk.Label(hdr, text="  Sin resultados", font=("Segoe UI", 12, "bold"),
             bg="#1E293B", fg="white", padx=16, pady=11, anchor="w").pack(side="left")

    tk.Frame(win, bg=BTN_ACCENT, height=3).pack(fill="x")

    body_f = tk.Frame(win, bg=BG, padx=24, pady=22)
    body_f.pack(fill="both", expand=True)
    tk.Label(body_f,
             text="No se encontraron resultados para el Case Number ingresado.",
             font=("Segoe UI", 11), bg=BG, fg=TEXT_DARK,
             wraplength=360, justify="left").pack(anchor="w")

    btn_frame = tk.Frame(win, bg=BG, padx=16, pady=12)
    btn_frame.pack(fill="x", side="bottom")
    tk.Frame(btn_frame, bg=BORDER, height=1).pack(fill="x", pady=(0, 10))
    tk.Button(
        btn_frame, text="Aceptar", command=win.destroy,
        bg=BTN_ACCENT, fg="white",
        activebackground=BTN_ACCENT_HV, activeforeground="white",
        font=("Segoe UI", 11, "bold"), relief="flat", bd=0,
        cursor="hand2", pady=9,
    ).pack(fill="x")


root = tk.Tk()
root.title("API Sender")
root.geometry("620x760")
root.configure(bg=BG)
root.resizable(True, True)

opcion = tk.StringVar(value="")

# --- Header ---
header = tk.Frame(root, bg="#1E293B")
header.pack(fill="x")
tk.Label(header, text="API Sender", font=("Segoe UI", 15, "bold"),
         bg="#1E293B", fg="white", pady=12).pack()
tk.Label(header, text="Gestión de Envío de Leads", font=("Segoe UI", 9),
         bg="#1E293B", fg="#94A3B8", pady=(0)).pack(pady=(0, 10))

# --- Footer ---
footer = tk.Frame(root, bg=BG)
footer.pack(fill="x", side="bottom")
tk.Frame(footer, bg=BORDER, height=1).pack(fill="x")
tk.Label(footer, text="© 2026 International Media Group. All Rights Reserved.",
         font=("Segoe UI", 7), bg=BG, fg=TEXT_MUTED).pack(pady=5)

# --- Body ---
body = tk.Frame(root, bg=BG, padx=24, pady=18)
body.pack(fill="both", expand=True)

# Sección categorías
tk.Label(body, text="Selecciona el tipo de campaña",
         font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT_DARK, anchor="w").pack(fill="x", pady=(0, 8))

grid_categorias = tk.Frame(body, bg=BG)

grid_categorias.pack(fill="x")
grid_categorias.columnconfigure(0, weight=1, uniform="cat")
grid_categorias.columnconfigure(1, weight=1, uniform="cat")
grid_categorias.columnconfigure(2, weight=1, uniform="cat")

categoria = tk.StringVar(value="")
category_buttons = {}

for idx, cat_name in enumerate(sorted(campaign_categories.keys(), key=str.lower)):
    row, col = divmod(idx, 3)
    wrapper = tk.Frame(grid_categorias, bg=BTN_BORDER, padx=1, pady=1)
    wrapper.grid(row=row, column=col, padx=5, pady=4, sticky="ew")
    btn = tk.Radiobutton(
        wrapper,
        text=cat_name,
        variable=categoria,
        value=cat_name,
        indicatoron=0,
        font=BTN_FONT,
        width=16,
        wraplength=140,
        justify="center",
        bg=CARD_BG,
        fg=TEXT_DARK,
        activebackground=BTN_BG_SEL,
        activeforeground=BTN_TEXT_SEL,
        selectcolor=BTN_BG_SEL,
        relief="flat",
        bd=0,
        padx=8,
        pady=10,
        cursor="hand2",
    )
    btn.pack(fill="both", expand=True)
    category_buttons[cat_name] = (btn, wrapper)

def actualizar_categorias(*_):
    val = categoria.get()
    for cat_val, (btn, wrapper) in category_buttons.items():
        if cat_val == val:
            btn.config(bg=BTN_BG_SEL, fg=BTN_TEXT_SEL)
            wrapper.config(bg=BTN_ACCENT)
        else:
            btn.config(bg=CARD_BG, fg=TEXT_DARK)
            wrapper.config(bg=BTN_BORDER)

categoria.trace_add("write", actualizar_categorias)

# Separador
tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=16)

# Sección campañas (depende de la categoría seleccionada)
tk.Label(body, text="Selecciona la campaña",
         font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT_DARK, anchor="w").pack(fill="x", pady=(0, 8))

grid_camp = tk.Frame(body, bg=BG)
grid_camp.pack(fill="x")
grid_camp.columnconfigure(0, weight=1, uniform="camp")
grid_camp.columnconfigure(1, weight=1, uniform="camp")
grid_camp.columnconfigure(2, weight=1, uniform="camp")

campaign_buttons = {}

def actualizar_botones(*_):
    val = opcion.get()
    for btn_val, (btn, wrapper) in campaign_buttons.items():
        if btn_val == val:
            btn.config(bg=BTN_BG_SEL, fg=BTN_TEXT_SEL)
            wrapper.config(bg=BTN_ACCENT)
        else:
            btn.config(bg=CARD_BG, fg=TEXT_DARK)
            wrapper.config(bg=BTN_BORDER)

def mostrar_campanas_de_categoria(*_):
    global campaign_buttons
    for widget in grid_camp.winfo_children():
        widget.destroy()
    campaign_buttons = {}
    opcion.set("")

    camp_list = campaign_categories.get(categoria.get(), [])

    if not camp_list:
        tk.Label(
            grid_camp,
            text="Elige un tipo de campaña arriba para ver sus opciones",
            font=("Segoe UI", 9, "italic"),
            bg=BG,
            fg=TEXT_MUTED,
        ).grid(row=0, column=0, columnspan=3, pady=6, sticky="w")
        return

    for idx, value in enumerate(camp_list):
        row, col = divmod(idx, 3)
        wrapper = tk.Frame(grid_camp, bg=BTN_BORDER, padx=1, pady=1)
        wrapper.grid(row=row, column=col, padx=5, pady=4, sticky="ew")
        btn = tk.Radiobutton(
            wrapper,
            text=value,
            variable=opcion,
            value=value,
            indicatoron=0,
            font=BTN_FONT,
            width=16,
            wraplength=140,
            anchor="center",
            justify="center",
            bg=CARD_BG,
            fg=TEXT_DARK,
            activebackground=BTN_BG_SEL,
            activeforeground=BTN_TEXT_SEL,
            selectcolor=BTN_BG_SEL,
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            cursor="hand2",
        )
        btn.pack(fill="both", expand=True)
        campaign_buttons[value] = (btn, wrapper)

categoria.trace_add("write", mostrar_campanas_de_categoria)
opcion.trace_add("write", actualizar_botones)
mostrar_campanas_de_categoria()

# Separador
tk.Frame(body, bg=BORDER, height=1).pack(fill="x", pady=16)

# Sección case number
PLACEHOLDER_CASE = "Ej: 00123456"

tk.Label(body, text="Case Number",
         font=("Segoe UI", 10, "bold"), bg=BG, fg=TEXT_DARK, anchor="w").pack(fill="x", pady=(0, 2))
tk.Label(body, text="Ingresa el case number:",
         font=("Segoe UI", 9), bg=BG, fg=TEXT_MUTED, anchor="w",
         wraplength=360, justify="left").pack(fill="x", pady=(0, 8))

entry_border = tk.Frame(body, bg=BORDER, padx=1, pady=1)
entry_border.pack(fill="x")
entry_case = tk.Entry(
    entry_border,
    font=("Segoe UI", 11),
    bg=CARD_BG,
    fg=TEXT_MUTED,
    relief="flat",
    bd=6,
    insertbackground=TEXT_DARK,
)
entry_case.pack(fill="x")
entry_case.insert(0, PLACEHOLDER_CASE)

def obtener_case_number():
    valor = entry_case.get().strip()
    return "" if valor == PLACEHOLDER_CASE else valor

def actualizar_estado_btn_validar(*_):
    if obtener_case_number():
        btn_validar.config(state="normal", bg=BTN_ACCENT, fg="white", cursor="hand2")
    else:
        btn_validar.config(state="disabled", bg=PLOMO_BG, fg=PLOMO_FG, cursor="arrow")

def on_focus_in_case(_):
    if entry_case.get() == PLACEHOLDER_CASE:
        entry_case.delete(0, "end")
        entry_case.config(fg=TEXT_DARK)

def on_focus_out_case(_):
    if not entry_case.get().strip():
        entry_case.insert(0, PLACEHOLDER_CASE)
        entry_case.config(fg=TEXT_MUTED)

entry_case.bind("<FocusIn>", on_focus_in_case)
entry_case.bind("<FocusOut>", on_focus_out_case)
entry_case.bind("<KeyRelease>", actualizar_estado_btn_validar)
entry_case.bind("<Return>", lambda _: validar())

# Botón validar
tk.Frame(body, bg=BG, height=4).pack()
btn_validar = tk.Button(
    body,
    text="Validar",
    command=validar,
    bg=PLOMO_BG,
    fg=PLOMO_FG,
    activebackground=BTN_ACCENT_HV,
    activeforeground="white",
    font=("Segoe UI", 12, "bold"),
    relief="flat",
    bd=0,
    state="disabled",
    cursor="arrow",
    pady=11,
)
btn_validar.pack(fill="x")

root.mainloop()