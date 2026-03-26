import os
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
import re
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlencode

import streamlit as st

import gspread
from google.auth.transport.requests import Request
from google.cloud import vision_v1
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.cloud.vision_v1 import types as vision_types


APP_TITLE = "Heat Exchanger Stock Manager"
LOCAL_REDIRECT_URI = st.secrets["google"]["redirect_uri"]


def _get_secret(path: List[str], default: Optional[str] = None) -> str:
    """
    Safe accessor for Streamlit secrets, handling Streamlit's Secrets object.

    Note: we intentionally do NOT print secret values anywhere.
    """
    cur: Any = st.secrets
    for key in path:
        try:
            cur = cur[key]
        except Exception:
            if default is None:
                raise KeyError(f"Missing secret: {'.'.join(path)}")
            return default
    if cur is None:
        if default is None:
            raise KeyError(f"Missing secret: {'.'.join(path)}")
        return default
    return str(cur)


def _debug_print_secret_keys() -> None:
    """
    Print which secrets exist (keys only), to help diagnose Streamlit secrets loading.
    """
    st.info("Secrets debug (keys only, values hidden).")
    try:
        top_keys = list(getattr(st.secrets, "keys", lambda: [])())
    except Exception:
        top_keys = []
    st.write("Top-level keys:", top_keys)

    if "google" in top_keys:
        try:
            google_obj = st.secrets["google"]
            google_keys = list(getattr(google_obj, "keys", lambda: [])())
        except Exception:
            google_keys = []
        st.write("`google` keys:", google_keys)
    else:
        # Some versions support direct membership, others don't.
        try:
            _ = st.secrets["google"]
            st.write("`google` keys:", list(getattr(st.secrets["google"], "keys", lambda: [])()))
        except Exception:
            st.write("`google` not present in st.secrets.")


def _get_query_params() -> Dict[str, List[str]]:
    # Streamlit compatibility across versions.
    try:
        qp = st.query_params  # type: ignore[attr-defined]
        # st.query_params is a dict-like; normalize to {k: [v]}
        out: Dict[str, List[str]] = {}
        for k, v in qp.items():
            if isinstance(v, list):
                out[k] = [str(x) for x in v]
            else:
                out[k] = [str(v)]
        return out
    except Exception:
        return st.experimental_get_query_params()


def _clear_query_params() -> None:
    try:
        st.experimental_set_query_params()
    except Exception:
        try:
            # Some versions allow clear on st.query_params.
            st.query_params.clear()  # type: ignore[attr-defined]
        except Exception:
            pass


def _build_oauth_flow(
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: List[str],
    disable_pkce: bool = True,
) -> Flow:
    client_config = {
        "web": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [redirect_uri],
        }
    }
    # PKCE can require a code_verifier during token exchange.
    # For Streamlit redirect/callback across sessions, disable PKCE to avoid
    # "InvalidGrantError: Missing code verifier".
    if disable_pkce:
        return Flow.from_client_config(
            client_config=client_config,
            scopes=scopes,
            redirect_uri=redirect_uri,
            code_verifier=None,
            autogenerate_code_verifier=False,
        )
    return Flow.from_client_config(
        client_config=client_config,
        scopes=scopes,
        redirect_uri=redirect_uri,
    )


def credentials_to_state(creds: Credentials) -> Dict[str, Any]:
    return {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
        "expiry": creds.expiry.isoformat() if creds.expiry else None,
    }


def credentials_from_state(state: Dict[str, Any]) -> Credentials:
    expiry_raw = state.get("expiry")
    expiry = datetime.fromisoformat(expiry_raw) if expiry_raw else None
    return Credentials(
        token=state.get("token"),
        refresh_token=state.get("refresh_token"),
        token_uri=state.get("token_uri"),
        client_id=state.get("client_id"),
        client_secret=state.get("client_secret"),
        scopes=state.get("scopes"),
        expiry=expiry,
    )


def ensure_fresh_credentials(creds: Credentials) -> Credentials:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    return creds


def get_logged_in_credentials() -> Optional[Credentials]:
    state = st.session_state.get("oauth_credentials")
    if not state:
        return None
    creds = credentials_from_state(state)
    return ensure_fresh_credentials(creds)


def extract_two_barcodes_and_reference_text(
    vision_client: vision_v1.ImageAnnotatorClient,
    image_bytes: bytes,
) -> Tuple[List[str], str]:
    image = vision_types.Image(content=image_bytes)

    # Barcodes
    barcode_resp = vision_client.barcode_detection(image=image)
    if barcode_resp.error and barcode_resp.error.message:
        raise RuntimeError(f"Vision barcode_detection error: {barcode_resp.error.message}")

    # De-dupe and prefer higher-confidence reads.
    # (Vision can return multiple detections for the same physical barcode.)
    best_conf_by_value: Dict[str, float] = {}
    for b in barcode_resp.barcode_annotations or []:
        if not b.raw_value:
            continue
        v = b.raw_value.strip()
        if not v:
            continue
        conf = float(getattr(b, "confidence", 0.0) or 0.0)
        best_conf_by_value[v] = max(best_conf_by_value.get(v, 0.0), conf)

    barcodes = sorted(best_conf_by_value.keys(), key=lambda v: best_conf_by_value.get(v, 0.0), reverse=True)[:2]

    # Full OCR text for reference extraction
    text_resp = vision_client.text_detection(image=image)
    if text_resp.error and text_resp.error.message:
        raise RuntimeError(f"Vision text_detection error: {text_resp.error.message}")

    ocr_text = text_resp.text_annotations[0].description if text_resp.text_annotations else ""
    reference = extract_reference_text(ocr_text, known_barcode_values=set(barcodes))
    return barcodes, reference


def extract_reference_text(ocr_text: str, known_barcode_values: set) -> str:
    """
    Heuristics to extract the single "reference text" from a label.

    If your label has a consistent pattern (e.g. "REF: ABC123"), update the regexes below.
    """
    if not ocr_text:
        return ""

    cleaned = ocr_text.replace("\u00a0", " ").strip()

    # 1) Prefer explicit reference markers if present.
    patterns = [
        # Examples: "REF: ABC123", "Ref-ABC123", "REFERENCE ABC123"
        r"(?:REF|Ref|REFS|REFERENCE|Ref(?:erence)?)[\s:\-]*([A-Za-z0-9][A-Za-z0-9\-_/]{2,})",
    ]
    for p in patterns:
        m = re.search(p, cleaned, flags=re.IGNORECASE)
        if m:
            candidate = m.group(1).strip()
            if candidate and candidate not in known_barcode_values:
                return candidate

    # 2) Otherwise, pick the best looking alphanumeric token that isn't a barcode.
    # Split into tokens and lines; Vision often adds extra whitespace/newlines.
    tokens = re.split(r"[\s\r\n]+", cleaned)
    candidates: List[str] = []
    for t in tokens:
        t_norm = t.strip()
        if not t_norm:
            continue
        if t_norm in known_barcode_values:
            continue
        # Require at least 3 chars and some alphanumerics.
        if len(t_norm) < 3:
            continue
        if not re.search(r"[A-Za-z0-9]", t_norm):
            continue
        # Prefer tokens with letters/digits (not just pure punctuation).
        if re.fullmatch(r"[\-_/]{2,}", t_norm):
            continue
        candidates.append(t_norm)

    # Heuristic: return the longest candidate (often the reference).
    if candidates:
        candidates.sort(key=lambda s: (len(s), s), reverse=True)
        return candidates[0]
    return ""


def append_row_to_google_sheet(
    creds: Credentials,
    sheet_id: str,
    worksheet_name: Optional[str],
    row_values: List[str],
) -> None:
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)

    if worksheet_name:
        ws = sh.worksheet(worksheet_name)
    else:
        ws = sh.sheet1

    # Append at the end.
    ws.append_row(row_values, value_input_option="RAW")


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="centered")
    st.title(APP_TITLE)

    show_debug = st.checkbox("Debug: show Streamlit secret keys (values hidden)")
    if show_debug:
        _debug_print_secret_keys()

    # ---- Secrets (configured in .streamlit/secrets.toml) ----
    client_id = _get_secret(["google", "client_id"])
    client_secret = _get_secret(["google", "client_secret"])
    # Google expects the exact redirect URI to be used in both the auth request and the token exchange.
    # For your local Streamlit usage, we force it to match exactly:
    #   http://localhost:8501
    # (Even if `.streamlit/secrets.toml` contains another value.)
    redirect_uri = LOCAL_REDIRECT_URI
    secrets_redirect_uri = _get_secret(["google", "redirect_uri"], default=redirect_uri)
    if str(secrets_redirect_uri).strip() != redirect_uri:
        st.warning(f"Using redirect_uri=`{redirect_uri}` (forced). Your secrets had `{secrets_redirect_uri}`.")

    sheet_id = _get_secret(["google", "sheet_id"])
    worksheet_name = st.secrets.get("google", {}).get("worksheet_name")  # type: ignore[attr-defined]

    scopes = [
        "openid",
        "https://www.googleapis.com/auth/userinfo.email",
        "https://www.googleapis.com/auth/spreadsheets",
        # Used for Vision API calls when using user OAuth credentials.
        "https://www.googleapis.com/auth/cloud-platform",
    ]

    # ---- OAuth sign-in / callback ----
    oauth_state = st.session_state.get("oauth_state")
    qp = _get_query_params()
    code = (qp.get("code") or [None])[0]
    returned_state = (qp.get("state") or [None])[0]

    if code and not get_logged_in_credentials():
        # If Streamlit session_state got reset between redirect + callback, we can recover it
        # from the returned `state` value for local use.
        if not oauth_state and returned_state:
            st.session_state["oauth_state"] = returned_state
            oauth_state = returned_state

        if not oauth_state or (returned_state and returned_state != oauth_state):
            st.error("OAuth state mismatch. Please sign in again.")
            _clear_query_params()
            st.stop()

        flow = _build_oauth_flow(client_id, client_secret, redirect_uri, scopes)
        # Ensure the flow knows the redirect URI for the token exchange step.
        try:
            flow.redirect_uri = redirect_uri  # type: ignore[attr-defined]
        except Exception:
            pass
        # Reconstruct the callback URL to satisfy google-auth-oauthlib.
        # This is safe because we control base redirect_uri via secrets.
        normalized_params: Dict[str, str] = {k: (v[0] if v else "") for k, v in qp.items()}
        authorization_response = f"{redirect_uri}?{urlencode(normalized_params)}"
        flow.fetch_token(authorization_response=authorization_response)

        creds = flow.credentials
        st.session_state["oauth_credentials"] = credentials_to_state(creds)
        _clear_query_params()
        st.rerun()

    creds = get_logged_in_credentials()

    col1, col2 = st.columns([1, 1])
    with col1:
        if creds:
            st.success("Signed in.")
        else:
            st.warning("Not signed in.")
    with col2:
        if creds and st.button("Sign out"):
            st.session_state.pop("oauth_credentials", None)
            st.session_state.pop("oauth_state", None)
            st.rerun()

    if not creds:
        flow = _build_oauth_flow(client_id, client_secret, redirect_uri, scopes)
        # Ensure the flow knows the redirect URI for the authorization request step.
        try:
            flow.redirect_uri = redirect_uri  # type: ignore[attr-defined]
        except Exception:
            pass
        # Some google-auth-oauthlib versions require explicit redirect_uri.
        try:
            auth_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
                redirect_uri=redirect_uri,
            )
        except TypeError:
            auth_url, state = flow.authorization_url(
                access_type="offline",
                include_granted_scopes="true",
                prompt="consent",
            )
        st.session_state["oauth_state"] = state
        st.markdown(f"[Sign in with Google]({auth_url})")
        st.stop()

    creds = ensure_fresh_credentials(creds)

    # ---- Vision client ----
    vision_client = vision_v1.ImageAnnotatorClient(credentials=creds)

    # ---- Capture photo ----
    st.subheader("Scan label")
    photo = st.camera_input("Take a photo of the entry label")

    if photo is None:
        st.caption("Take a clear photo containing the two barcodes and the reference text.")
        st.stop()

    image_bytes = photo.getvalue()
    st.image(BytesIO(image_bytes), caption="Captured label", use_column_width=True)

    if "extracted_values" not in st.session_state:
        st.session_state["extracted_values"] = None

    if st.button("Extract + append to sheet"):
        with st.spinner("Running Google Vision OCR/barcode extraction..."):
            barcodes, reference = extract_two_barcodes_and_reference_text(vision_client, image_bytes)
            st.session_state["extracted_values"] = {
                "barcode_1": barcodes[0] if len(barcodes) > 0 else "",
                "barcode_2": barcodes[1] if len(barcodes) > 1 else "",
                "reference": reference,
            }

    ev = st.session_state.get("extracted_values")
    if not ev:
        st.info("Click “Extract + append to sheet” to run Vision and fill the fields.")
        st.stop()

    barcode_1 = ev.get("barcode_1", "")
    barcode_2 = ev.get("barcode_2", "")
    reference = ev.get("reference", "")

    st.markdown("### Extracted values")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("Barcode 1", barcode_1 or "Not found")
    with c2:
        st.metric("Barcode 2", barcode_2 or "Not found")
    with c3:
        st.metric("Reference", reference or "Not found")

    if (not barcode_1) or (not barcode_2) or (not reference):
        st.error("Could not reliably extract all 3 required values. Please try another photo.")
        st.stop()

    if st.button("Confirm append"):
        with st.spinner("Appending row to Google Sheet..."):
            append_row_to_google_sheet(
                creds=creds,
                sheet_id=sheet_id,
                worksheet_name=worksheet_name,
                row_values=[barcode_1, barcode_2, reference],
            )
        st.success("Row appended successfully.")
        # Clear extracted values so the UI forces a re-extraction for the next photo.
        st.session_state["extracted_values"] = None


if __name__ == "__main__":
    main()
