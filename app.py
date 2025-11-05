import os
import re
import json
import httpx
import streamlit as st
from urllib.parse import urlparse, urljoin
from openai import OpenAI
from bs4 import BeautifulSoup

# -------------- App Config --------------
st.set_page_config(
    page_title="Career Redirector",
    page_icon="🎯",
)

# -------------- Sidebar --------------
st.sidebar.title("⚙️ Settings")
st.sidebar.caption("Use your OpenAI API key via environment variables or .env.")

model = st.sidebar.selectbox(
    "OpenAI model",
    [
        "gpt-4.1-mini",   # fast & capable
        "gpt-4.1",        # stronger
        "gpt-4o-mini",    # great $/speed balance
        "gpt-4o",         # flagship multimodal
    ],
    index=0,
)

openai_api_key = os.getenv("OPENAI_API_KEY", "")
if not openai_api_key:
    st.sidebar.error("OPENAI_API_KEY not found. Set it in your environment or .env.")
else:
    st.sidebar.success("OPENAI_API_KEY is set.")

open_in_new_tab = st.sidebar.toggle("Open links in a new tab", value=True)
auto_redirect = st.sidebar.toggle("Auto-redirect (same tab) on match", value=False)
show_debug = st.sidebar.toggle("Show debug info", value=False)

# -------------- OpenAI Client --------------
client = OpenAI(api_key=openai_api_key) if openai_api_key else None

# -------------- Helpers --------------
COMMON_CAREER_PATHS = [
    "careers",
    "jobs",
    "company/careers",
    "about/careers",
    "about-us/careers",
    "career",
    "join-us",
    "work-with-us",
]

POPULAR_DOMAINS = {
    "google": "https://about.google",
    "microsoft": "https://www.microsoft.com",
    "apple": "https://www.apple.com",
    "amazon": "https://www.amazon.com",
    "meta": "https://about.meta.com",
    "netflix": "https://www.netflix.com",
    "tesla": "https://www.tesla.com",
    "nvidia": "https://www.nvidia.com",
    "openai": "https://openai.com",
    "uber": "https://www.uber.com",
    "airbnb": "https://www.airbnb.com",
    "stripe": "https://stripe.com",
    "salesforce": "https://www.salesforce.com",
    "oracle": "https://www.oracle.com",
}

HEADERS = {"User-Agent": "CareerRedirector/1.0 (+https://streamlit.io)"}


def normalize_company(user_text: str) -> str:
    """Returns a cleaned 'company hint' (for heuristics + POPULAR_DOMAINS lookup)."""
    hint = user_text.strip().lower()
    hint = re.sub(r"\b(inc|inc\.|llc|corp|co\.|company|ltd)\b", "", hint)
    hint = re.sub(r"\s+", " ", hint).strip()
    return hint


def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def safe_head(url: str) -> bool:
    try:
        with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=10) as s:
            r = s.head(url)
            if r.status_code >= 400 or r.status_code == 405:
                r = s.get(url)
            return 200 <= r.status_code < 400
    except Exception:
        return False


def discover_careers_from_domain(domain_url: str) -> str | None:
    """Try common career paths under the domain, then scan homepage for 'career' links."""
    if not domain_url.endswith("/"):
        domain_url += "/"
    for path in COMMON_CAREER_PATHS:
        candidate = urljoin(domain_url, path)
        if safe_head(candidate):
            return candidate
    # Last resort: scan homepage for links
    try:
        with httpx.Client(follow_redirects=True, headers=HEADERS, timeout=12) as s:
            r = s.get(domain_url)
            if 200 <= r.status_code < 400:
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    text = (a.get_text() or "").lower()
                    if "career" in text or "job" in text or "join" in text:
                        candidate = urljoin(domain_url, href)
                        if safe_head(candidate):
                            return candidate
    except Exception:
        pass
    return None


def ddg_first_result(query: str) -> str | None:
    """Very lightweight DuckDuckGo HTML search to find an external careers link."""
    try:
        url = "https://duckduckgo.com/html/"
        params = {"q": query}
        with httpx.Client(headers=HEADERS, timeout=12) as s:
            r = s.get(url, params=params)
            if r.status_code != 200:
                return None
            soup = BeautifulSoup(r.text, "html.parser")
            for a in soup.select(".result__a"):
                href = a.get("href")
                if href and ("http://" in href or "https://" in href):
                    return href
    except Exception:
        return None
    return None


def openai_guess_company_and_urls(user_text: str) -> dict:
    """
    Ask OpenAI to normalize the company and propose official + careers URLs.
    SDK-version tolerant:
      1) Try Chat Completions with JSON mode (if available)
      2) Try Chat Completions without JSON mode and parse
      3) Try Responses API without response_format and parse
    """
    if not client:
        return {}

    system_instr = (
        "You are a precise URL resolver. "
        "Given a user string that likely names a company, respond ONLY with compact JSON containing:\n"
        '{"company": "<canonical company name>", '
        '"official_website": "<homepage URL or empty string>", '
        '"careers_url": "<careers/jobs URL or empty string>"}'
    )
    user_msg = f"Company input: {user_text}\nReturn ONLY JSON as specified."

    # ---- Attempt 1: Chat Completions with JSON mode ----
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
            response_format={"type": "json_object"},  # may not exist in older SDKs
        )
        content = resp.choices[0].message.content
        data = json.loads(content)
        return {
            "company": data.get("company"),
            "official_website": data.get("official_website"),
            "careers_url": data.get("careers_url"),
        }
    except TypeError:
        pass  # older SDK, continue
    except Exception:
        pass

    # ---- Attempt 2: Chat Completions without JSON mode; parse manually ----
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_instr},
                {"role": "user", "content": user_msg},
            ],
            temperature=0,
        )
        content = resp.choices[0].message.content
        try:
            data = json.loads(content)
        except Exception:
            m = re.search(
                r'\{.*"company"\s*:\s*".*?".*"official_website"\s*:\s*".*?".*"careers_url"\s*:\s*".*?".*\}',
                content,
                re.S,
            )
            data = json.loads(m.group(0)) if m else {}
        if isinstance(data, dict):
            return {
                "company": data.get("company"),
                "official_website": data.get("official_website"),
                "careers_url": data.get("careers_url"),
            }
    except Exception:
        pass

    # ---- Attempt 3: Responses API WITHOUT response_format; parse text ----
    try:
        resp = client.responses.create(
            model=model,
            instructions=system_instr,
            input=user_msg,
        )
        text_candidates = []
        if hasattr(resp, "output_text") and resp.output_text:
            text_candidates.append(resp.output_text)
        try:
            if hasattr(resp, "output") and resp.output:
                for block in resp.output:
                    if hasattr(block, "content"):
                        for c in getattr(block, "content", []):
                            t = getattr(getattr(c, "text", None), "value", None)
                            if t:
                                text_candidates.append(t)
        except Exception:
            pass

        text = next((t for t in text_candidates if t), "")
        if text:
            try:
                data = json.loads(text)
            except Exception:
                m = re.search(
                    r'\{.*"company"\s*:\s*".*?".*"official_website"\s*:\s*".*?".*"careers_url"\s*:\s*".*?".*\}',
                    text,
                    re.S,
                )
                data = json.loads(m.group(0)) if m else {}
            if isinstance(data, dict):
                return {
                    "company": data.get("company"),
                    "official_website": data.get("official_website"),
                    "careers_url": data.get("careers_url"),
                }
    except Exception:
        pass

    return {}


def best_urls_from_all_signals(user_text: str) -> tuple[str | None, str | None, dict]:
    """
    Returns (official_site, careers_url, debug_info).
    Combines URL paste, popular domain map, OpenAI suggestions,
    careers path discovery, and a lightweight web search fallback.
    """
    debug = {}

    if is_valid_url(user_text):
        parsed = urlparse(user_text)
        official = f"{parsed.scheme}://{parsed.netloc}"
        careers = user_text if any(x in parsed.path.lower() for x in ["career", "job"]) else None
        if not careers:
            maybe = discover_careers_from_domain(official)
            careers = maybe or user_text
        return official, careers, {"mode": "direct_url"}

    hint = normalize_company(user_text)
    debug["hint"] = hint

    # 1) Popular shortcut
    for key, dom in POPULAR_DOMAINS.items():
        if key in hint:
            official = dom
            careers = discover_careers_from_domain(official) or ddg_first_result(f"{key} careers site")
            return official, careers, {"mode": "popular_map"}

    # 2) Ask OpenAI
    ai = openai_guess_company_and_urls(user_text)
    debug["openai_raw"] = ai
    official = ai.get("official_website")
    careers = ai.get("careers_url")

    if official and not safe_head(official):
        official = None

    if official and (not careers or not safe_head(careers)):
        discovered = discover_careers_from_domain(official)
        if discovered:
            careers = discovered

    # 3) Search fallback
    if not official:
        homepage = ddg_first_result(f"{hint} official site")
        if homepage and safe_head(homepage):
            official = homepage
    if not careers:
        found = ddg_first_result(f"{hint} careers site")
        if found and safe_head(found):
            careers = found

    return official, careers, debug


def link_out(url: str, label: str, new_tab: bool):
    if new_tab:
        st.link_button(label, url)
    else:
        st.page_link(url, label=label, icon="🌐")


def js_redirect(url: str):
    """Force same-tab redirect using a small HTML/JS snippet."""
    from streamlit.components.v1 import html
    html(
        f"""
        <script>
            window.location.replace("{url}");
        </script>
        """,
        height=0,
    )


# -------------- UI --------------
st.title("🎯 Career Redirector")
st.write("Type a company name (or paste a URL). I’ll send you straight to the Careers page.")

with st.form("company_form", clear_on_submit=False):
    user_input = st.text_input(
        "Company or URL",
        placeholder="e.g., Nvidia, 'Goldman Sachs', https://openai.com/",
    )
    submitted = st.form_submit_button("Find Careers ▶")

if submitted and user_input.strip():
    with st.spinner("Resolving the best links..."):
        official, careers, dbg = best_urls_from_all_signals(user_input)

    st.divider()
    col1, col2 = st.columns(2)

    if official:
        with col1:
            st.subheader("Official Website")
            link_out(official, "Open Official Site", open_in_new_tab)
            st.caption(official)
    else:
        st.error("Couldn’t confidently find the official website.")

    if careers:
        with col2:
            st.subheader("Careers")
            link_out(careers, "Open Careers Page", open_in_new_tab)
            st.caption(careers)

            if auto_redirect:
                st.info("Auto-redirecting to Careers…")
                js_redirect(careers)
    else:
        st.warning("Couldn’t find a working Careers page. Try refining the company name.")

    if show_debug:
        with st.expander("Debug details"):
            st.write(dbg)

# -------------- Footer --------------
st.divider()
st.caption(
    "Tip: If a site blocks HEAD requests or unusual user-agents, switch off auto-redirect and click the link button."
)
