from datetime import date, datetime
import json
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pdfplumber
import streamlit as st


def parse_to_date(date_str):
  if not date_str:
    return date.today()
  date_str = str(date_str).strip()
  formats = (
      "%d/%m/%Y",
      "%d-%m-%Y",
      "%Y-%m-%d",
      "%d.%m.%Y",
      "%d %B %Y",
      "%d %b %Y",
      "%d%b%Y",
      "%d %b %y",
      "%d%b%y",
      "%d-%b-%Y",
      "%d-%b-%y",
      "%b %d, %Y",
      "%b %d %Y",
  )
  for fmt in formats:
    try:
      return datetime.strptime(date_str, fmt).date()
    except ValueError:
      pass

  found = re.search(
      r"(\d{1,2})[\s/-]*([A-Za-z]{3})[\s/-]*(\d{2,4})", date_str
  )
  if found:
    clean_str = f"{found.group(1)} {found.group(2)} {found.group(3)}"
    for fmt in ("%d %b %Y", "%d %b %y"):
      try:
        return datetime.strptime(clean_str, fmt).date()
      except ValueError:
        pass
  return date.today()


def push_to_google_sheet(data_dict, sheet_url):
  try:
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]

    # Secrets-ന് പകരം ഉപയോഗിക്കുന്ന ഡയറക്റ്റ് കോൺഫിഗറേഷൻ (Incorrect padding എറർ വരില്ല)
    key_dict = {
        "type": "service_account",
        "project_id": "ticket-extractor-app",
        "private_key_id": "07c81c074a6459dd5cb6bbb68818b4b957bb5206",
        "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQDA5PQtNWu4R9LV\ny8NoVjqviuosTG1R0cZWIZkSBKFJPRge+OnIxC6J7CH2gyEvvo1QCj41kHDMWtPJ\nxmMRM1B+89CHSgCMCb22AT9r2PZltII2THz739EnLcrd+HaCjgr0VUNoLLJUY7oR\nAQmC7R7LG/BG7BoEGG125H5BFiljmSeLGV376XKESELjqNZFcxWrQcf4Ma/VMt5y\n2sNhyMQKHUvcZY4VGGUDwpN4Eio7w5YsLUu2EgIEt6VPiTltGWGp0CFvIUIx4JGR\nmqAemjuSQlY0dxwT1TW3cMISdVkR3Nkz5wXcAfA1bHvj8KlNoPgFZ4ntmu0bUbp3\nI1OJc8XfAgMBAAECggEALsrbmOPun6N8t7RYUMUqM09Fgz1+/2wd6uL3mPFalsOl\nSE4lmDhO+dI4Yu5obIaTDSmO8bt6QXh/C+F+Qrvp+QH4QflnrJDoXnBrDCRzkTR6\nqeVgJFGlERYAslwFk6IVcjQEyA6fq+0NQ/a2cfZHlAnQ/cNkhD3QwBipr+xKWghu\n4yy6fZlmABquLIc2/zVp/IQm4orUgyy5+JmzCU4+VRSYbxdHl64LXPV/7XcngvSh\nMon2RXPCJR14EM5gIfysEkoAn5AdHwoCkgqfm3RWaN5qjXKTMLAjXY3Jm4bjGg2e\njs0s0NrPmO1wMU8W0FabDYpkqLkmOIBSaLq1oFhZQQKBgQDyJqdncV72501bYYCA\nBMxWB/efBlpGTBncRTrn3Jzdp2kF77UEEEBWoayhdeozVaIRsio74ar0uJDEawCz\nrzc3KNipVE/9xN0ASza0Dc6PGo9ZfHLgBcpN7aHdL6SGXLJo1wFxGDv2UtA3sSS0\n2KjDE7M6IKPY5RTFP+A4j2mAzwKBgQDL7SF0hee5Qx3HOCCdhB1n6WX+tlzi4pOI\nAIrVUhLA4JRuDrP5XpLlA++K1trRJw33Zgan4WF8pjyAXnSau9dw0x8I6CWJndGn\n0V6EbXu+CEFoi1ygvZKFZ/Mrt21c6u/hPFdu2830rBH1ccUHXuLVEQyNEcI/PmjW\nnnzBCaCrkN8QKBgFDzdSFSuDGIT8cNyFyDvh/AmBpUkFdR149YoYGjsdkzvxtZ8ETE\nfg24DLMJbVrt9Lk/u3i7T2ByVwsizmBDYg0RnaS15+vpJQyVGFuHBhe3BFchEHIt\n3VzB5UvBQpocYRRFVFkPhfQp6SvFD4VZrMlSS6dSBBRdON1cJkQiRV3nAoGAbLH0\nnhxtorALuOGXeXJcy5VQunVmuoPCMGo3PcmzQuiX6d782htC2E4PJhoOHFrxuYVPs\nnncEddowcocHPoSyGcb/LYM/MpLvUD7yNV8dg5gMz9sC+4K6VgF+OUZdTbYg+H1NJI+\nDoIyUV+PQlrL8aPuWng+sBgfT1SvEsA/lqA0MECgYBw0tPGC3nIoBaTWeg7ann2\nNGjj9MfLQV1s6wyyT8GIcSDTWxYBEha0It+Gkqtszjgt2S7hc224Cyl//YA113Fl/\nejtVeJnDXEg2m/zjernP/YhLiBuxTdn3jPnE3FvuB78Y6lRgFLPUeE6jYr8Ez/l\nnnjJrZituDdaZ395QXxecJiQ==\n-----END PRIVATE KEY-----",
        "client_email": (
            "ticket-sheet-bot@ticket-extractor-app.iam.gserviceaccount.com"
        ),
        "client_id": "106825017066171371189",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": (
            "https://www.googleapis.com/oauth2/v1/certs"
        ),
        "client_x509_cert_url": (
            "https://www.googleapis.com/robot/v1/metadata/x509/ticket-sheet-bot%40ticket-extractor-app.iam.gserviceaccount.com"
        ),
        "universe_domain": "googleapis.com",
    }

    creds = ServiceAccountCredentials.from_json_keyfile_dict(key_dict, scope)
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1

    row_values = [
        data_dict.get("booking_date_str", ""),
        data_dict.get("pax_name", ""),
        data_dict.get("company", ""),
        data_dict.get("due_amount", ""),
        data_dict.get("due_date", ""),
        data_dict.get("received_date", ""),
        data_dict.get("ref", ""),
        data_dict.get("payment", ""),
        data_dict.get("pnr", ""),
        data_dict.get("route", ""),
        data_dict.get("category", ""),
        data_dict.get("staff", ""),
        data_dict.get("airline", ""),
        data_dict.get("flight_no", ""),
        data_dict.get("booking_date_str", ""),
        data_dict.get("travel_date_str", ""),
        data_dict.get("vendor", ""),
        data_dict.get("net_vendor", ""),
        data_dict.get("amt_customer", ""),
        data_dict.get("profit", ""),
        data_dict.get("profit_15", ""),
        data_dict.get("amt_received_cash", ""),
        data_dict.get("amt_received_bank", ""),
        data_dict.get("pay_to_vendor", ""),
        data_dict.get("received_by", ""),
        data_dict.get("phone", ""),
        data_dict.get("remarks", ""),
    ]

    sheet.append_row(row_values)
    return True
  except Exception as e:
    st.error(f"Google Sheet Error: {e}")
    return False


st.set_page_config(
    page_title="Ticket Extractor & Google Sheet Integration", layout="wide"
)
st.title("🎫 Ticket Extractor with Google Sheet Direct Push")

if "ticket_data_store" not in st.session_state:
  st.session_state.ticket_data_store = {}

# --- 1. UPLOAD PDF TICKETS ---
st.subheader("1. Select Format Type & Upload PDF")
format_type = st.selectbox("Choose Ticket Format:", ["Lamsah", "Standard"])
uploaded_files = st.file_uploader(
    "Upload PDF Tickets", type="pdf", accept_multiple_files=True
)

if uploaded_files:
  file_names = [file.name for file in uploaded_files]

  for uploaded_file in uploaded_files:
    fname = uploaded_file.name

    if fname not in st.session_state.ticket_data_store:
      text_content = ""
      with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
          extracted = page.extract_text()
          if extracted:
            text_content += extracted + "\n"

      extracted_data = {}

      airline_map = {
          "Flyadeal": "F3",
          "Oman Air": "WY",
          "Gulf Air": "GF",
          "Emirates": "EK",
          "Air India Express": "IX",
          "Air Arabia": "G9",
          "Flynas": "XY",
          "Saudia": "SV",
          "Qatar Airways": "QR",
          "IndiGo": "6E",
          "Air India": "AI",
      }
      found_airline = "F3" if format_type == "Lamsah" else ""
      for name, code in airline_map.items():
        if name.lower() in text_content.lower():
          found_airline = code
          break
      extracted_data["airline"] = found_airline

      pnr_found = ""
      pnr_blacklist = {
          "ACCEPT",
          "TOTAL",
          "AMOUNT",
          "FLIGHT",
          "STATUS",
          "TICKET",
          "ADULT",
          "CABIN",
          "CLASS",
          "NUMBER",
          "COOKIE",
          "CONFIRM",
          "BOOKING",
          "DETAILS",
          "LAMSAH",
      }

      ref_patterns = [
          r"(?:Reference\s*Number|Airline\s*PNR|Booking\s*Reference|Booking\s*Ref|PNR|Confirmation\s*Number|Conf\.?\s*No\.?|Locator)\s*[:#\.\-]?\s*([A-Z0-9]{5,8})\b"
      ]
      for pat in ref_patterns:
        match = re.search(pat, text_content, re.IGNORECASE)
        if match:
          val = match.group(1).strip().upper()
          if val not in pnr_blacklist:
            pnr_found = val
            break

      if not pnr_found:
        potential_codes = re.findall(r"\b([A-Z0-9]{6})\b", text_content)
        for code in potential_codes:
          clean_code = code.strip().upper()
          if clean_code not in pnr_blacklist:
            pnr_found = clean_code
            break

      extracted_data["pnr"] = pnr_found

      # Passenger Name Finder (Fixed to ignore address lines)
      pax_name = ""
      address_blacklist = [
          "ROAD",
          "STREET",
          "NEAR",
          "KING",
          "SEIKO",
          "BUILDING",
          "BOX",
          "POSTAL",
          "CITY",
          "DISTRICT",
          "TRADING",
          "TRAVEL",
      ]

      lines = text_content.split("\n")
      for line in lines:
        clean_line = line.strip()
        match = re.search(
            r"(?:Passenger Name|Passenger|Name)\s*[:\-]?\s*([A-Z\s\/]{3,30})",
            clean_line,
            re.IGNORECASE,
        )
        if match:
          cand = match.group(1).strip()
          if not any(word in cand.upper() for word in address_blacklist):
            pax_name = cand
            break

      if not pax_name:
        for line in lines:
          clean_line = line.strip()
          if re.search(
              r"\b(Mr|Mrs|Ms|Miss|Master|Dr)\.?\s+[A-Za-z\s\/]{3,}",
              clean_line,
              re.IGNORECASE,
          ):
            if not any(
                word in clean_line.upper() for word in address_blacklist
            ):
              pax_name = clean_line
              break

      if pax_name:
        pax_name = re.sub(
            r"[-–—].*?(Checked|bag|kg|Seat).*$",
            "",
            pax_name,
            flags=re.IGNORECASE,
        ).strip()

      extracted_data["pax_name"] = pax_name

      # Route Finder
      route_found = ""
      bracket_airports = re.findall(r"\(([A-Z]{3})\)", text_content)
      bracket_airports = [a for a in bracket_airports if a != "UTC"]
      if len(bracket_airports) >= 2:
        route_found = f"{bracket_airports[0]}-{bracket_airports[1]}"

      extracted_data["route"] = route_found

      all_dates = re.findall(
          r"\b(\d{1,2}[\s/-]*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s/-]*\d{2,4}|\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4})\b",
          text_content,
          re.IGNORECASE,
      )
      extracted_data["booking_date"] = (
          all_dates[0] if len(all_dates) > 0 else ""
      )
      extracted_data["travel_date"] = (
          all_dates[1]
          if len(all_dates) > 1
          else (all_dates[0] if all_dates else "")
      )

      st.session_state.ticket_data_store[fname] = {
          "pnr": extracted_data["pnr"],
          "airline": extracted_data["airline"],
          "pax_name": extracted_data["pax_name"],
          "route": extracted_data["route"],
          "booking_date": parse_to_date(extracted_data["booking_date"]),
          "travel_date": parse_to_date(extracted_data["travel_date"]),
          "return_date": parse_to_date(""),
          "company": "NON",
          "ref": "NON",
          "category": "TICKET",
          "payment": "CASH",
          "vendor": "GO & GO",
          "staff": "MARSOOK",
          "due_amount": "",
          "due_date": "",
          "received_date": "",
          "flight_no": "",
          "net_vendor": "",
          "amt_customer": "",
          "profit": "",
          "profit_15": "",
          "amt_received_cash": "",
          "amt_received_bank": "",
          "pay_to_vendor": "",
          "received_by": "",
          "phone": "",
          "remarks": "",
      }

  # --- 2. SELECT FILE TO REVIEW & EDIT ---
  st.subheader("2. Select Ticket to Review & Edit Mistakes")
  selected_file_name = st.selectbox("Choose a file to edit:", file_names)

  if selected_file_name in st.session_state.ticket_data_store:
    t_data = st.session_state.ticket_data_store[selected_file_name]
    st.info(f"Currently Editing: **{selected_file_name}**")
    st.markdown("---")

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
      st.subheader("📝 Edit Details")

      t_data["booking_date"] = st.date_input(
          "Booking Date (Date)",
          value=t_data["booking_date"],
          format="DD/MM/YYYY",
          key=f"b_date_{selected_file_name}",
      )

      t_data["pax_name"] = st.text_input(
          "Passanger Name",
          value=t_data["pax_name"],
          key=f"pax_{selected_file_name}",
      )

      company_list = [
          "NON",
          "WLK",
          "INCO-PRECAST",
          "GULF GATE",
          "SCHOOL",
          "GBS",
          "MAWARID",
          "SINCHOLD",
          "BLUE VILLAGE",
          "IYON",
          "MHZ",
          "OBEID",
          "A1 SHAJI",
          "FLASH",
          "MIDDLE EAST",
          "ALAFKAR",
          "GEEPAS",
      ]
      t_data["company"] = st.selectbox(
          "Company Name",
          company_list,
          index=(
              company_list.index(t_data["company"])
              if t_data["company"] in company_list
              else 0
          ),
          key=f"comp_{selected_file_name}",
      )

      t_data["due_amount"] = st.text_input(
          "Due Amount",
          value=t_data["due_amount"],
          key=f"due_amt_{selected_file_name}",
      )
      t_data["due_date"] = st.text_input(
          "Due Date",
          value=t_data["due_date"],
          key=f"due_dt_{selected_file_name}",
      )
      t_data["received_date"] = st.text_input(
          "Received Date",
          value=t_data["received_date"],
          key=f"rec_dt_{selected_file_name}",
      )

      ref_list = [
          "NON",
          "WALKING",
          "MARSOOK",
          "1370 ANWAR",
          "2915 BABUKA",
          "250 ANWAR",
          "1645+360.15 BABUKA",
          "15845 ANWAR",
          "0 JABIR",
          "2083 BABUKA",
          "0 BABUKA",
          "0 ANWAR",
          "0 NISHAD",
          "56 BABUKA",
          "C/O ANWAR",
      ]
      t_data["ref"] = st.selectbox(
          "Reference / CO",
          ref_list,
          index=(
              ref_list.index(t_data["ref"]) if t_data["ref"] in ref_list else 0
          ),
          key=f"ref_{selected_file_name}",
      )

      t_data["payment"] = st.selectbox(
          "Mode of payment",
          ["CASH", "BANK", "CREDIT"],
          key=f"pay_{selected_file_name}",
      )
      t_data["pnr"] = st.text_input(
          "Ticket / Doc # (PNR)",
          value=t_data["pnr"],
          key=f"pnr_{selected_file_name}",
      )

      t_data["route"] = st.text_input(
          "Route (e.g. JED-RUH)",
          value=t_data["route"],
          key=f"route_{selected_file_name}",
      )

      category_options = ["TICKET", "DATE CHANGE", "REFUND", "VISA", "HOTEL"]
      cat_idx = (
          category_options.index(t_data["category"])
          if t_data["category"] in category_options
          else 0
      )
      t_data["category"] = st.selectbox(
          "Category",
          category_options,
          index=cat_idx,
          key=f"cat_{selected_file_name}",
      )

      t_data["staff"] = st.selectbox(
          "Staff",
          ["MARSOOK", "NISHAD"],
          key=f"staff_{selected_file_name}",
      )
      t_data["airline"] = st.text_input(
          "Airline",
          value=t_data["airline"],
          key=f"air_{selected_file_name}",
      )
      t_data["flight_no"] = st.text_input(
          "Flight No",
          value=t_data["flight_no"],
          key=f"flight_{selected_file_name}",
      )

      t_data["travel_date"] = st.date_input(
          "Departure Date",
          value=t_data["travel_date"],
          format="DD/MM/YYYY",
          key=f"t_{selected_file_name}",
      )
      t_data["return_date"] = st.date_input(
          "Return Date",
          value=t_data["return_date"],
          format="DD/MM/YYYY",
          key=f"r_{selected_file_name}",
      )

      t_data["vendor"] = st.selectbox(
          "Vendor Name & Code",
          ["GO & GO", "AKBAR SAUDI"],
          key=f"vend_{selected_file_name}",
      )
      t_data["net_vendor"] = st.text_input(
          "Net to Vendor",
          value=t_data["net_vendor"],
          key=f"net_{selected_file_name}",
      )
      t_data["amt_customer"] = st.text_input(
          "Amt to Customer",
          value=t_data["amt_customer"],
          key=f"amt_{selected_file_name}",
      )

      t_data["profit"] = st.text_input(
          "Profit",
          value=t_data["profit"],
          key=f"prof_{selected_file_name}",
      )
      t_data["profit_15"] = st.text_input(
          "PROFIT 15 %",
          value=t_data["profit_15"],
          key=f"p15_{selected_file_name}",
      )
      t_data["amt_received_cash"] = st.text_input(
          "Amount Received (CASH)",
          value=t_data["amt_received_cash"],
          key=f"rcash_{selected_file_name}",
      )
      t_data["amt_received_bank"] = st.text_input(
          "Amount Received (BANK)",
          value=t_data["amt_received_bank"],
          key=f"rbank_{selected_file_name}",
      )
      t_data["pay_to_vendor"] = st.text_input(
          "Mode of payment TO vendor",
          value=t_data["pay_to_vendor"],
          key=f"ptvend_{selected_file_name}",
      )
      t_data["received_by"] = st.text_input(
          "Received Amount by",
          value=t_data["received_by"],
          key=f"recby_{selected_file_name}",
      )
      t_data["phone"] = st.text_input(
          "PHONE NUMBER",
          value=t_data["phone"],
          key=f"phone_{selected_file_name}",
      )
      t_data["remarks"] = st.text_input(
          "REMARKES",
          value=t_data["remarks"],
          key=f"rem_{selected_file_name}",
      )

    with col_right:
      st.subheader("📋 Formatted Output & Google Sheet Push")

      booking_str = t_data["booking_date"].strftime("%d/%m/%Y")
      travel_str = t_data["travel_date"].strftime("%d/%m/%Y")
      return_str = t_data["return_date"].strftime("%d/%m/%Y")
      destination = t_data["route"]

      tab_normal, tab_excel, tab_gsheet = st.tabs(
          ["Normal Preview", "Excel Row Format", "Google Sheet Integration"]
      )

      with tab_normal:
        st.write(
            f"**Booking Date:** {booking_str}\n\n"
            f"**Passenger:** {t_data['pax_name']}\n\n"
            f"**Company:** {t_data['company']}\n\n"
            f"**Ref:** {t_data['ref']}\n\n"
            f"**Airline:** {t_data['airline']}\n\n"
            f"**PNR:** {t_data['pnr']}\n\n"
            f"**Route:** {destination}\n\n"
            f"**Departure / Return:** {travel_str} / {return_str}"
        )

      with tab_excel:
        st.info("ഇത് കോപ്പി ചെയ്ത് എക്സൽ ഷീറ്റിലേക്ക് പേസ്റ്റ് ചെയ്യാം:")
        excel_row_str = f"{booking_str}\t{t_data['pax_name']}\t{t_data['company']}\t{t_data['due_amount']}\t{t_data['due_date']}\t{t_data['received_date']}\t{t_data['ref']}\t{t_data['payment']}\t{t_data['pnr']}\t{destination}\t{t_data['category']}\t{t_data['staff']}\t{t_data['airline']}\t{t_data['flight_no']}\t{travel_str}\t{return_str}\t{t_data['vendor']}\t{t_data['net_vendor']}\t{t_data['amt_customer']}\t{t_data['profit']}\t{t_data['profit_15']}\t{t_data['amt_received_cash']}\t{t_data['amt_received_bank']}\t{t_data['pay_to_vendor']}\t{t_data['received_by']}\t{t_data['phone']}\t{t_data['remarks']}"
        st.code(excel_row_str, language="text")

      with tab_gsheet:
        st.subheader("Save Directly to Google Sheet")

        pinned_sheet_url = (
            "https://docs.google.com/spreadsheets/d/1eS7JWp46SCIbiG2yfUjC381zISOpp5O9cwujo5m3Nx8/edit?gid=0#gid=0"
        )
        st.markdown(
            f"🔗 **Pinned Google Sheet:** [Open Google Sheet]({pinned_sheet_url})"
        )
        st.markdown("---")

        sheet_url_input = st.text_input(
            "Google Sheet URL (Pinned):",
            value=pinned_sheet_url,
            key=f"g_sheet_url_{selected_file_name}",
        )

        if st.button(
            "🚀 Push Data to Google Sheet", key=f"btn_{selected_file_name}"
        ):
          if not sheet_url_input:
            st.warning("Please enter your Google Sheet URL first!")
          else:
            payload = {
                "booking_date_str": booking_str,
                "pax_name": t_data["pax_name"],
                "company": t_data["company"],
                "due_amount": t_data["due_amount"],
                "due_date": t_data["due_date"],
                "received_date": t_data["received_date"],
                "ref": t_data["ref"],
                "payment": t_data["payment"],
                "pnr": t_data["pnr"],
                "route": destination,
                "category": t_data["category"],
                "staff": t_data["staff"],
                "airline": t_data["airline"],
                "flight_no": t_data["flight_no"],
                "travel_date_str": travel_str,
                "return_date_str": return_str,
                "vendor": t_data["vendor"],
                "net_vendor": t_data["net_vendor"],
                "amt_customer": t_data["amt_customer"],
                "profit": t_data["profit"],
                "profit_15": t_data["profit_15"],
                "amt_received_cash": t_data["amt_received_cash"],
                "amt_received_bank": t_data["amt_received_bank"],
                "pay_to_vendor": t_data["pay_to_vendor"],
                "received_by": t_data["received_by"],
                "phone": t_data["phone"],
                "remarks": t_data["remarks"],
            }

            success = push_to_google_sheet(payload, sheet_url_input)
            if success:
              st.success("Successfully pushed data to Google Sheet! 🎉")