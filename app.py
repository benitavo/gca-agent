import streamlit as st
import anthropic
import json
import base64

st.set_page_config(page_title="GCA Extraction Agent", page_icon="⚡", layout="centered")

st.markdown("""
<style>
  .block-container { padding-top: 1.5rem; }
  .header { background:#1c2b3a; color:#e8dfc8; padding:20px 28px;
            border-bottom:3px solid #c9a84c; border-radius:8px; margin-bottom:24px;
            display:flex; align-items:center; gap:14px; }
  .icon { background:#c9a84c; color:#1c2b3a; font-size:18px; font-weight:bold;
          width:38px; height:38px; display:flex; align-items:center;
          justify-content:center; border-radius:4px; flex-shrink:0; }
  .field-label { font-size:11px; font-weight:700; text-transform:uppercase;
                 letter-spacing:0.6px; margin-bottom:2px; }
</style>
<div class="header">
  <div class="icon">⚡</div>
  <div>
    <div style="font-size:19px;font-weight:700;letter-spacing:1px;">GCA Extraction Agent</div>
    <div style="font-size:12px;color:#9aa8b4;margin-top:2px;">Grid Connection Agreement · Automated Data Extraction</div>
  </div>
</div>
""", unsafe_allow_html=True)

FIELDS = [
    ("project",                     "Project"),
    ("grid_operator",               "Grid operator"),
    ("company",                     "Company"),
    ("type",                        "Type"),
    ("reference",                   "Reference"),
    ("location",                    "Location"),
    ("date_of_signature",           "Date of signature"),
    ("date_initial_gco_request",    'Date of initial GCO ("PTF") request'),
    ("injection_capacity",          "Injection capacity"),
    ("consumption_capacity",        "Consumption capacity"),
    ("grid_voltage",                "Grid voltage"),
    ("inverters",                   "Inverters"),
    ("reactive_energy_requirements","Reactive energy requirements"),
    ("plant_substation",            "Plant substation"),
    ("grid_substation",             "Grid substation"),
    ("connection_works",            "Connection works"),
    ("equipment_plant_substation",  "Equipment in plant substation"),
    ("hv_protection_category",      "HV protection category"),
    ("hz_filter",                   "175 Hz filter"),
    ("downtime",                    "Downtime"),
    ("other",                       "Other"),
    ("total_costs_excl_vat",        "Total costs (excluding VAT)"),
    ("quote_part_excl_vat",         "Quote-part (excluding VAT)"),
    ("timing",                      "Timing"),
]

SYSTEM_PROMPT = """You are an expert at reading French grid connection agreements (Convention de raccordement / CRAC) from Enedis.
Respond ONLY with a valid JSON object — no markdown, no backticks.

CRITICAL: ALL values must be written in ENGLISH, even if the source document is in French.
Translate French terms, descriptions, and sentences into English. Never copy French text as-is.

Fields to extract (all values in English):
- project: Short project name (e.g. "Orion 45")
- grid_operator: Translate to English (e.g. "Enedis")
- company: Full legal company name of the applicant
- type: In English, e.g. "Grid connection agreement"
- reference: e.g. "CRAC dated 16/09/2022"
- location: City and postal code
- date_of_signature: DD/MM/YYYY
- date_initial_gco_request: DD/MM/YYYY
- injection_capacity: e.g. "10,330 kW"
- consumption_capacity: e.g. "30 kW"
- grid_voltage: e.g. "20 kV"
- inverters: English sentence, e.g. "46 Sungrow SG250HX inverters"
- reactive_energy_requirements: English sentence describing tan phi / reactive power requirements
- plant_substation: Name of the delivery substation (poste de livraison)
- grid_substation: Name of source substation and HTA feeder in English
- connection_works: English description of cable works (length, type, voltage)
- equipment_plant_substation: English description of equipment required at the plant substation
- hv_protection_category: English, e.g. "Category H.5 (by derogation)"
- hz_filter: English sentence on whether a 175 Hz filter is required
- downtime: English sentence on interruption zone and allowed downtime
- other: Any other notable requirements, in English
- total_costs_excl_vat: e.g. "€1,195,654.91 excl. VAT"
- quote_part_excl_vat: e.g. "€152,574.10 excl. VAT"
- timing: English sentence on expected connection or commissioning date

If a field cannot be found in the document, use exactly: "Info not found"."""

uploaded = st.file_uploader("Drop your GCA PDF here", type="pdf", label_visibility="collapsed")

if uploaded:
    st.info(f"📄 **{uploaded.name}** · {uploaded.size // 1024} KB")

    if "data" not in st.session_state:
        st.session_state.data = {}

    if st.button("⚡  Extract Data", use_container_width=True, type="primary"):
        with st.spinner("Reading document and extracting data…"):
            try:
                b64 = base64.standard_b64encode(uploaded.read()).decode()
                client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])
                resp = client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1500,
                    messages=[{"role": "user", "content": [
                        {"type": "text", "text": SYSTEM_PROMPT},
                        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": b64}},
                        {"type": "text", "text": "Extract all fields and return as JSON."}
                    ]}]
                )
                raw = resp.content[0].text.replace("```json","").replace("```","").strip()
                st.session_state.data = json.loads(raw)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Extraction failed: {e}")

    if st.session_state.get("data"):
        data = st.session_state.data
        not_found_count = sum(1 for k, _ in FIELDS if data.get(k) == "Info not found")

        st.markdown("---")
        st.markdown("✅ **Extracted — review and edit if needed**")
        if not_found_count:
            st.warning(f"⚠ {not_found_count} field{'s' if not_found_count > 1 else ''} not found in the document.")

        st.markdown("<br>", unsafe_allow_html=True)
        for key, label in FIELDS:
            val = data.get(key, "")
            is_nf = val == "Info not found"
            color = "#c0392b" if is_nf else "#444"
            st.markdown(f"<div class='field-label' style='color:{color}'>{label}</div>", unsafe_allow_html=True)
            data[key] = st.text_area(label, value=val,
                                     height=44 if len(val) < 80 else 80,
                                     label_visibility="collapsed", key=key)

        st.markdown("---")
        c1, c2 = st.columns(2)

        tsv = "\n".join(f"{lbl}\t{data.get(k,'')}" for k, lbl in FIELDS)
        c1.download_button("📋 Download TSV (paste into Excel)",
            data=tsv.encode("utf-8"),
            file_name=f"GCA_{data.get('project','output').replace(' ','_')}.tsv",
            mime="text/tab-separated-values", use_container_width=True)

        csv_rows = [f'"{lbl}","{data.get(k,"").replace(chr(34), chr(34)*2)}"' for k, lbl in FIELDS]
        c2.download_button("⬇ Download CSV",
            data=("\ufeff" + "\n".join(csv_rows)).encode("utf-8"),
            file_name=f"GCA_{data.get('project','output').replace(' ','_')}.csv",
            mime="text/csv", use_container_width=True, type="primary")

        if st.button("↩ Process another PDF"):
            del st.session_state["data"]
            st.rerun()
