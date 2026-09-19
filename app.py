from datetime import date, datetime
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
    creds = ServiceAccountCredentials.from_json_keyfile_name(
        "credentials.json", scope
    )
    client = gspread.authorize(creds)
    sheet = client.open_by_url(sheet_url).sheet1

    row_values = [
        data_dict.get("booking_date_str", ""),  # 1. Date
        data_dict.get("pax_name", ""),  # 2. Passanger Name
        data_dict.get("company", ""),  # 3. company name
        data_dict.get("due_amount", ""),  # 4. Due Amount
        data_dict.get("due_date_str", ""),  # 5. Due Date
        data_dict.get("received_date_str", ""),  # 6. Received Date
        data_dict.get("ref", ""),  # 7. Reference/CO
        data_dict.get("payment", ""),  # 8. Mode of payment
        data_dict.get("pnr", ""),  # 9. Ticket/Doc #
        data_dict.get("route", ""),  # 10. Routing
        data_dict.get("category", ""),  # 11. Category
        data_dict.get("staff", ""),  # 12. Staff
        data_dict.get("airline", ""),  # 13. Airline
        data_dict.get("flight_no", ""),  # 14. Flight No
        data_dict.get("travel_date_str", ""),  # 15. Departure Date
        data_dict.get("return_date_str", ""),  # 16. Return Date
        data_dict.get("vendor", ""),  # 17. Vendor Name & Code
        data_dict.get("net_vendor", ""),  # 18. Net to Vendor
        data_dict.get("amt_customer", ""),  # 19. Amt to Customer
        data_dict.get("profit", ""),  # 20. Profit
        data_dict.get("profit_15", ""),  # 21. PROFIT 15 %
        data_dict.get("amt_received_cash", ""),  # 22. Amount Received (CASH)
        data_dict.get("amt_received_bank", ""),  # 23. Amount Received (BANK)
        data_dict.get("pay_to_vendor", ""),  # 24. Mode of payment TO vendor
        data_dict.get("received_by", ""),  # 25. Received Amount by
        data_dict.get("phone", ""),  # 26. PHONE NUMBER
        data_dict.get("remarks", ""),  # 27. REMARKES
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
          "Gulf Air": "GF",
          "Flyadeal": "F3",
          "Oman Air": "WY",
          "Emirates": "EK",
          "Air India Express": "IX",
          "Air Arabia": "G9",
          "Flynas": "XY",
          "Saudia": "SV",
          "Qatar Airways": "QR",
          "IndiGo": "6E",
          "Air India": "AI",
      }
      found_airline = "GF"
      for name, code in airline_map.items():
        if name.lower() in text_content.lower():
          found_airline = code
          break
      extracted_data["airline"] = found_airline

      pnr_found = ""
      pnr_match = re.search(
          r"(?:Airline Ref|CRS Ref)\s*:\s*([A-Z0-9]{5,8})",
          text_content,
          re.IGNORECASE,
      )
      if pnr_match:
        pnr_found = pnr_match.group(1).strip().upper()
      else:
        potential_codes = re.findall(r"\b([A-Z0-9]{6})\b", text_content)
        for code in potential_codes:
          if code.upper() not in [
              "TRAVEL",
              "STATUS",
              "AIRBUS",
              "DAMMAM",
              "BAHRAIN",
          ]:
            pnr_found = code.upper()
            break
      extracted_data["pnr"] = pnr_found

      pax_name = ""
      pax_match = re.search(
          r"Traveler\(s\)\s*Information.*?Code\s*Name.*?(?:Mr\.|Mrs\.|Ms\.|Miss\.|Dr\.)\s*([A-Z\s]+)",
          text_content,
          re.DOTALL | re.IGNORECASE,
      )
      if pax_match:
        full_title_match = re.search(
            r"((?:Mr\.|Mrs\.|Ms\.|Miss\.|Dr\.)\s+[A-Z\s]+)",
            pax_match.group(0),
            re.IGNORECASE,
        )
        if full_title_match:
          pax_name = full_title_match.group(1).strip()
          pax_name = pax_name.split("\n")[0].strip()

      if not pax_name:
        pax_match_alt = re.search(
            r"(?:Mr\.|Mrs\.|Ms\.|Miss\.|Dr\.)\s+[A-Za-z\s]+", text_content
        )
        if pax_match_alt:
          pax_name = pax_match_alt.group(0).strip()

      extracted_data["pax_name"] = pax_name

      route_found = ""
      onward_match = re.search(
          r"ONWARD\s+([A-Za-z\s]+)\s*→\s*([A-Za-z\s]+)", text_content, re.IGNORECASE
      )
      if onward_match:
        origin_city = onward_match.group(1).strip()
        all_arrows = re.findall(
            r"([A-Za-z\s]+)\s*→\s*([A-Za-z\s]+)", text_content
        )
        if all_arrows:
          final_dest = all_arrows[-1][1].strip().split("\n")[0].strip()
          city_to_code = {
              "Dammam": "DMM",
              "Bahrain": "BAH",
              "New Delhi": "DEL",
              "Riyadh": "RUH",
              "Jeddah": "JED",
          }
          orig_code = city_to_code.get(origin_city, origin_city[:3].upper())
          dest_code = city_to_code.get(final_dest, final_dest[:3].upper())
          route_found = f"{orig_code}-{dest_code}"

      if not route_found:
        bracket_airports = re.findall(r"\(([A-Z]{3})\)", text_content)
        bracket_airports = [a for a in bracket_airports if a != "UTC"]
        if len(bracket_airports) >= 2:
          route_found = f"{bracket_airports[0]}-{bracket_airports[-1]}"

      extracted_data["route"] = route_found

      booking_date_str = ""
      b_date_match = re.search(
          r"Date of Booking\s*:\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
          text_content,
          re.IGNORECASE,
      )
      if b_date_match:
        booking_date_str = b_date_match.group(1).strip()

      travel_date_str = ""
      t_date_match = re.search(
          r"(\d{1,2}\s+[A-Za-z]{3}\s+\d{4})\s*\|\s*Non\s*Stop", text_content
      )
      if t_date_match:
        travel_date_str = t_date_match.group(1).strip()

      st.session_state.ticket_data_store[fname] = {
          "pnr": extracted_data["pnr"],
          "airline": extracted_data["airline"],
          "pax_name": extracted_data["pax_name"],
          "route": extracted_data["route"],
          "booking_date": parse_to_date(
              booking_date_str if booking_date_str else "17 September 2026"
          ),
          "travel_date": parse_to_date(
              travel_date_str if travel_date_str else "13 Oct 2026"
          ),
          "return_date": None,
          "due_date": None,
          "received_date": None,
          "company": "NON",
          "ref": "NON",
          "category": "TICKET",
          "payment": "CASH",
          "vendor": "GO & GO",
          "staff": "MARSOOK",
          "due_amount": "",
          "flight_no": "GF104/134",
          "net_vendor": "",
          "amt_customer": "",
          "profit": "",
          "profit_15": "",
          "amt_received_cash": "",
          "amt_received_bank": "",
          "pay_to_vendor": "",
          "received_by": "",
          "phone": "558062636",
          "remarks": "",
      }

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

      # Calendar picker for Due Date
      t_data["due_date"] = st.date_input(
          "Due Date",
          value=t_data["due_date"],
          format="DD/MM/YYYY",
          key=f"due_dt_{selected_file_name}",
      )

      # Calendar picker for Received Date
      t_data["received_date"] = st.date_input(
          "Received Date",
          value=t_data["received_date"],
          format="DD/MM/YYYY",
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
          "Route (e.g. DMM-DEL)",
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

      booking_str = (
          t_data["booking_date"].strftime("%d/%m/%Y")
          if t_data["booking_date"]
          else ""
      )
      travel_str = (
          t_data["travel_date"].strftime("%d/%m/%Y")
          if t_data["travel_date"]
          else ""
      )
      return_str = (
          t_data["return_date"].strftime("%d/%m/%Y")
          if t_data["return_date"]
          else ""
      )
      due_date_str = (
          t_data["due_date"].strftime("%d/%m/%Y") if t_data["due_date"] else ""
      )
      received_date_str = (
          t_data["received_date"].strftime("%d/%m/%Y")
          if t_data["received_date"]
          else ""
      )
      destination = t_data["route"]

      tab_normal, tab_excel, tab_gsheet = st.tabs(
          ["Normal Preview", "Excel Row Format", "Google Sheet Integration"]
      )

      with tab_normal:
        st.write(
            f"**Booking Date (Date):** {booking_str}\n\n"
            f"**Passanger Name:** {t_data['pax_name']}\n\n"
            f"**Company Name:** {t_data['company']}\n\n"
            f"**Reference / CO:** {t_data['ref']}\n\n"
            f"**PNR:** {t_data['pnr']}\n\n"
            f"**Route:** {destination}\n\n"
            f"**Category:** {t_data['category']}\n\n"
            f"**Staff:** {t_data['staff']}\n\n"
            f"**Departure Date:** {travel_str}\n\n"
            f"**Vendor Name & Code:** {t_data['vendor']}\n\n"
            f"**Net to Vendor:** {t_data['net_vendor']}\n\n"
            f"**Profit:** {t_data['profit']}\n\n"
            f"**PROFIT 15 %:** {t_data['profit_15']}"
        )

      with tab_excel:
        st.info("ഇത് കോപ്പി ചെയ്ത് എക്സൽ ഷീറ്റിലേക്ക് പേസ്റ്റ് ചെയ്യാം:")
        excel_row_str = f"{booking_str}\t{t_data['pax_name']}\t{t_data['company']}\t{t_data['due_amount']}\t{due_date_str}\t{received_date_str}\t{t_data['ref']}\t{t_data['payment']}\t{t_data['pnr']}\t{destination}\t{t_data['category']}\t{t_data['staff']}\t{t_data['airline']}\t{t_data['flight_no']}\t{travel_str}\t{return_str}\t{t_data['vendor']}\t{t_data['net_vendor']}\t{t_data['amt_customer']}\t{t_data['profit']}\t{t_data['profit_15']}\t{t_data['amt_received_cash']}\t{t_data['amt_received_bank']}\t{t_data['pay_to_vendor']}\t{t_data['received_by']}\t{t_data['phone']}\t{t_data['remarks']}"
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
                "due_date_str": due_date_str,
                "received_date_str": received_date_str,
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
            else:
              st.error(
                  "Failed to push. Please check your credentials.json and"
                  " Google Sheet permissions."
              )