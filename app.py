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

SYSTEM_PROMPT = """You are an expert at reading French grid connection agreements (Convention de raccordement / CRAC) from Enedis and extracting structured data from them.
Respond ONLY with a valid JSON object — no markdown, no backticks.
Fields to extract: project, grid_operator, company, type, reference, location,
date_of_signature (DD/MM/YYYY), date_initial_gco_request (DD/MM/YYYY),
injection_capacity, consumption_capacity, grid_voltage, inverters,
reactive_energy_requirements, plant_substation, grid_substation, connection_works,
equipment_plant_substation, hv_protection_category, hz_filter, downtime, other,
total_costs_excl_vat, quote_part_excl_vat, timing.
Write all values in English. If a field is not found, use exactly: "Info not found"."""

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
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": [
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
