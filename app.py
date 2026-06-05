import hashlib
import json
import os
import re
from urllib.parse import urlencode
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import requests
import streamlit as st

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional runtime dependency
    OpenAI = None


APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
LOG_DIR = DATA_DIR / "logs"
CONFIG_PATH = DATA_DIR / "admin_config.json"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_MODEL = "gpt-5-mini"
DEFAULT_MFDS_ENDPOINT = "https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService07/getDrugPrdtPrmsnInq07"
DEFAULT_MFDS_TERMS = "cefazolin, cephalexin, cefuroxime, cefoxitin, ceftriaxone, cefotaxime, ceftazidime, cefepime"


st.set_page_config(
    page_title="항생제 처방 실무 가이드",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def inject_site_style() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #14161a;
            --muted: #5b6472;
            --line: #e6e8ec;
            --panel: #ffffff;
            --soft: #f6f7f9;
            --accent: #2563eb;
            --accent-2: #0f766e;
            --danger: #b91c1c;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(37, 99, 235, 0.08), transparent 32rem),
                linear-gradient(180deg, #fbfcfd 0%, #f4f6f8 100%);
            color: var(--ink);
        }

        [data-testid="stSidebar"] {
            background: #ffffff;
            border-right: 1px solid var(--line);
        }

        [data-testid="stSidebar"] h3 {
            font-size: 0.96rem;
            margin-top: 0.35rem;
        }

        .block-container {
            max-width: 1440px;
            padding-top: 1.35rem;
            padding-bottom: 3rem;
        }

        div[data-testid="stTabs"] button {
            border-radius: 999px;
            padding: 0.45rem 0.9rem;
            min-height: 2.5rem;
        }

        div[data-testid="stTabs"] [aria-selected="true"] {
            background: #111827;
            color: #ffffff;
        }

        div[data-testid="stTabs"] [aria-selected="true"] p {
            color: #ffffff;
        }

        .site-hero {
            display: grid;
            grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.75fr);
            gap: 1rem;
            align-items: stretch;
            margin-bottom: 1.1rem;
        }

        .hero-main,
        .hero-side,
        .metric-card {
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid var(--line);
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.07);
        }

        .hero-main {
            border-radius: 22px;
            padding: 1.4rem 1.55rem;
        }

        .hero-side {
            border-radius: 22px;
            padding: 1rem;
        }

        .eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            color: #0f766e;
            background: #e9f7f3;
            border: 1px solid #c9ebe2;
            border-radius: 999px;
            font-size: 0.78rem;
            font-weight: 700;
            padding: 0.28rem 0.65rem;
        }

        .hero-main h1 {
            font-size: clamp(1.85rem, 2.8vw, 2.85rem);
            line-height: 1.12;
            letter-spacing: 0;
            margin: 0.75rem 0 0.8rem;
            max-width: 18ch;
        }

        .hero-copy {
            color: var(--muted);
            max-width: 68rem;
            font-size: 1.02rem;
            line-height: 1.65;
        }

        .hero-actions {
            display: flex;
            gap: 0.65rem;
            flex-wrap: wrap;
            margin-top: 1rem;
        }

        .pill {
            border: 1px solid var(--line);
            background: var(--soft);
            color: #273142;
            border-radius: 999px;
            padding: 0.42rem 0.7rem;
            font-size: 0.82rem;
            font-weight: 650;
        }

        .side-title {
            color: var(--muted);
            font-size: 0.82rem;
            font-weight: 800;
            margin-bottom: 0.8rem;
            text-transform: uppercase;
        }

        .agent-step {
            display: grid;
            grid-template-columns: 1.7rem 1fr;
            gap: 0.65rem;
            padding: 0.72rem 0;
            border-top: 1px solid var(--line);
        }

        .agent-step:first-of-type {
            border-top: 0;
        }

        .step-dot {
            width: 1.7rem;
            height: 1.7rem;
            border-radius: 50%;
            background: #111827;
            color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.8rem;
            font-weight: 800;
        }

        .step-copy strong {
            display: block;
            font-size: 0.95rem;
        }

        .step-copy span {
            color: var(--muted);
            font-size: 0.84rem;
            line-height: 1.45;
        }

        .metric-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 0.75rem;
            margin: 0.5rem 0 1.1rem;
        }

        .metric-card {
            border-radius: 16px;
            padding: 0.9rem 1rem;
        }

        .metric-card span {
            color: var(--muted);
            font-size: 0.8rem;
            font-weight: 700;
        }

        .metric-card strong {
            display: block;
            font-size: 1.45rem;
            margin-top: 0.15rem;
        }

        .stDataFrame,
        [data-testid="stDataFrame"] {
            border-radius: 14px;
            overflow: hidden;
        }

        div.stButton > button,
        div.stDownloadButton > button {
            border-radius: 999px;
            border: 1px solid #d6dae1;
            font-weight: 750;
        }

        div.stButton > button[kind="primary"] {
            background: #111827;
            border-color: #111827;
        }

        @media (max-width: 900px) {
            .site-hero,
            .metric-grid {
                grid-template-columns: 1fr;
            }

            .hero-main h1 {
                font-size: 1.95rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_website_header(drug_count: int, is_admin: bool) -> None:
    admin_state = "관리자 활성" if is_admin else "일반 사용자"
    st.markdown(
        f"""
        <section class="site-hero">
            <div class="hero-main">
                <span class="eyebrow">AI Antibiotic Review Workspace</span>
                <h1>항생제 처방 가이드</h1>
                <p class="hero-copy">
                    원무·청구심사 부서가 자주 놓치는 세팔로스포린 세대, 병용 조합, 예방적 사용기간,
                    배양 후 축소 여부를 한 화면에서 확인하도록 구성한 병원 운영용 웹앱입니다.
                </p>
                <div class="hero-actions">
                    <span class="pill">처방 조합 판정</span>
                    <span class="pill">관리자 업로드</span>
                    <span class="pill">OpenAI API 질의</span>
                    <span class="pill">HIRA·DUR 확인 보조</span>
                </div>
            </div>
            <aside class="hero-side">
                <div class="side-title">Agent workflow</div>
                <div class="agent-step">
                    <div class="step-dot">1</div>
                    <div class="step-copy"><strong>약제 선택</strong><span>성분명과 세대, 감염 시나리오를 입력합니다.</span></div>
                </div>
                <div class="agent-step">
                    <div class="step-dot">2</div>
                    <div class="step-copy"><strong>규칙 검토</strong><span>가능·조건부·비권장 조합과 심사 포인트를 제시합니다.</span></div>
                </div>
                <div class="agent-step">
                    <div class="step-dot">3</div>
                    <div class="step-copy"><strong>AI 보조</strong><span>관리자가 설정한 API로 근거 제한형 답변을 생성합니다.</span></div>
                </div>
            </aside>
        </section>
        <section class="metric-grid">
            <div class="metric-card"><span>등록 약제</span><strong>{drug_count}</strong></div>
            <div class="metric-card"><span>조합 규칙</span><strong>{len(COMBINATION_RULES)}</strong></div>
            <div class="metric-card"><span>감염 흐름</span><strong>{len(INDICATION_FLOW)}</strong></div>
            <div class="metric-card"><span>현재 권한</span><strong>{admin_state}</strong></div>
        </section>
        """,
        unsafe_allow_html=True,
    )


REFERENCE_SOURCES = [
    {
        "name": "질병관리청·대한감염학회 전국 의료기관 항생제 사용량 분석 연보 보도자료",
        "url": "https://www.kdca.go.kr/board/board.es?act=view&bid=0015&list_no=723404&mid=a20501050000",
        "use": "세팔로스포린 세대별 사용 맥락, 항생제 스튜어드십 활동 항목",
    },
    {
        "name": "건강보험심사평가원 약제기준정보/요양기관 업무포털",
        "url": "https://www.hira.or.kr/main.do",
        "use": "급여기준, DUR, 병용금기·연령·임부금기 확인 업무 연결",
    },
    {
        "name": "OpenAI Responses API Reference",
        "url": "https://platform.openai.com/docs/api-reference/responses/create",
        "use": "관리자 설정 API 키로 근거 제한형 질의응답 구현",
    },
]


BASE_ANTIBIOTICS = [
    {
        "generation": "1세대",
        "ingredient": "cefazolin",
        "korean_name": "세파졸린",
        "route": "IV/IM",
        "spectrum": "MSSA, streptococci 중심. 일부 그람음성균 제한적.",
        "typical_use": "수술 예방적 항생제, 피부·연조직 감염, 감수성 확인된 경증 감염",
        "avoid_or_caution": "ESBL 의심, 중증 원내감염, 녹농균 의심, 중추신경계 감염 단독 사용",
        "billing_review_points": "예방적 항생제는 절개 전 투여 시점, 수술 후 지속기간, 불필요 병용 여부를 확인",
        "renal_adjustment": "신기능 저하 시 감량 또는 투여간격 조절 필요",
        "notes": "수술 예방 목적에서는 3세대 이상보다 1세대 선택이 원칙인 경우가 많음",
    },
    {
        "generation": "1세대",
        "ingredient": "cephalexin",
        "korean_name": "세팔렉신",
        "route": "PO",
        "spectrum": "MSSA, streptococci 중심. 경구 전환에 활용.",
        "typical_use": "경증 피부·연조직 감염, 감수성 확인 후 외래 경구 치료",
        "avoid_or_caution": "중증 감염 초기 경험요법, MRSA 의심, ESBL 의심",
        "billing_review_points": "주사제에서 경구 전환 시 임상 안정성, 배양 결과, 치료기간 근거 기록",
        "renal_adjustment": "신기능 저하 시 조절 필요",
        "notes": "중증도 낮고 경구 복용 가능한 환자에서 검토",
    },
    {
        "generation": "2세대",
        "ingredient": "cefuroxime",
        "korean_name": "세푸록심",
        "route": "IV/PO",
        "spectrum": "1세대보다 일부 그람음성균 보강, H. influenzae 등",
        "typical_use": "상·하기도 감염, 일부 수술 예방, 경증·중등도 감염",
        "avoid_or_caution": "녹농균, ESBL 의심, 중증 복강 내 감염 단독 사용",
        "billing_review_points": "동일 계열 중복 처방, 장기 사용, 배양검사 후 de-escalation 여부 확인",
        "renal_adjustment": "신기능 저하 시 조절 필요",
        "notes": "경구 제형이 있어 주사-경구 전환 경로 설계 가능",
    },
    {
        "generation": "2세대",
        "ingredient": "cefoxitin",
        "korean_name": "세폭시틴",
        "route": "IV",
        "spectrum": "일부 혐기성균 포함. cephamycin 계열.",
        "typical_use": "복부·골반 수술 예방, 혐기성 커버가 필요한 제한적 상황",
        "avoid_or_caution": "중증 ESBL 감염, 녹농균 의심, 불필요한 metronidazole 중복 병용",
        "billing_review_points": "혐기성 커버 중복, 예방적 사용기간 초과, 수술명과 적응증 일치 확인",
        "renal_adjustment": "신기능 저하 시 조절 필요",
        "notes": "혐기성 커버가 이미 포함되어 병용 필요성을 별도 검토",
    },
    {
        "generation": "3세대",
        "ingredient": "ceftriaxone",
        "korean_name": "세프트리악손",
        "route": "IV/IM",
        "spectrum": "광범위 그람음성균, 폐렴구균. 녹농균 커버 없음.",
        "typical_use": "중등도 지역사회획득 폐렴, 신우신염, 복강 내 감염 병용, 수막염 등",
        "avoid_or_caution": "녹농균 의심 감염 단독, 신생아 고빌리루빈혈증, 담즙정체 위험",
        "billing_review_points": "3세대 이상 사용 사유, 배양검사, 감량·축소, 장기 사용 사유 기록",
        "renal_adjustment": "대개 신장 단독 조절 부담은 낮지만 간담도 이상 주의",
        "notes": "담도 배설 특성 때문에 담낭 sludge 등 모니터링",
    },
    {
        "generation": "3세대",
        "ingredient": "cefotaxime",
        "korean_name": "세포탁심",
        "route": "IV",
        "spectrum": "ceftriaxone 유사. 소아·중추신경계 감염에서 선택 가능.",
        "typical_use": "중등도 감염, 수막염 병용, 패혈증 초기 경험요법 일부",
        "avoid_or_caution": "녹농균 의심 단독, ESBL 고위험에서 단독 유지",
        "billing_review_points": "중증도, 배양·감수성 결과, 병용 항생제 사유 확인",
        "renal_adjustment": "신기능 저하 시 조절 필요",
        "notes": "기관 지침의 ceftriaxone 대체 가능성을 확인",
    },
    {
        "generation": "3세대",
        "ingredient": "ceftazidime",
        "korean_name": "세프타지딤",
        "route": "IV",
        "spectrum": "녹농균 포함 그람음성균 중심. 그람양성 커버는 상대적으로 약함.",
        "typical_use": "녹농균 의심 요로·폐·원내감염, 호중구감소 발열 일부 병용",
        "avoid_or_caution": "그람양성균 단독 감염, 혐기성 감염 단독, ESBL 확정 감염 단독",
        "billing_review_points": "녹농균 위험인자, 배양검사, 병용 vancomycin/aminoglycoside 필요성 기록",
        "renal_adjustment": "신기능 저하 시 조절 필요",
        "notes": "녹농균 목적이면 ceftriaxone과 성격이 다르므로 대체 판단 주의",
    },
    {
        "generation": "4세대",
        "ingredient": "cefepime",
        "korean_name": "세페핌",
        "route": "IV",
        "spectrum": "광범위 그람음성균 및 녹농균, 일부 그람양성균.",
        "typical_use": "중증 원내감염, 호중구감소 발열, 녹농균 위험 중증 감염",
        "avoid_or_caution": "혐기성 복강 내 감염 단독, 신기능 저하 환자 신경독성, ESBL/CRE 의심 시 단독 유지",
        "billing_review_points": "4세대 사용 중증도, 신기능 기반 용량, 배양 후 축소, 사용기간 적정성",
        "renal_adjustment": "신기능 저하 시 반드시 용량·간격 조절. 혼돈/경련 등 신경독성 감시",
        "notes": "넓은 범위 항생제라 de-escalation 체크가 중요",
    },
]


COMBINATION_RULES = [
    {
        "combination": "ceftriaxone + metronidazole",
        "status": "가능",
        "rationale": "복강 내 감염처럼 혐기성 커버가 필요한 경우 3세대 세팔로스포린에 metronidazole을 추가할 수 있음",
        "checklist": "감염 부위, 수술/천공 여부, 혐기성균 위험, 치료기간, 배양검사",
    },
    {
        "combination": "cefepime + metronidazole",
        "status": "가능",
        "rationale": "녹농균 위험이 있으면서 복강 내 혐기성 커버가 필요한 중증 상황에서 검토",
        "checklist": "중증도, 녹농균 위험인자, 신기능 용량, 배양 후 축소",
    },
    {
        "combination": "ceftazidime + vancomycin",
        "status": "조건부 가능",
        "rationale": "녹농균/그람음성 커버에 MRSA 또는 중증 그람양성 커버가 필요한 경우",
        "checklist": "MRSA 위험인자, 혈중농도 모니터링, 신독성, 배양검사",
    },
    {
        "combination": "cefoxitin + metronidazole",
        "status": "주의/대체 검토",
        "rationale": "cefoxitin 자체가 일부 혐기성 커버를 가져 중복 가능성이 있음",
        "checklist": "혐기성 커버 중복, 기관 지침, 감염 부위, 중증도",
    },
    {
        "combination": "ceftriaxone + ceftazidime",
        "status": "불필요/비권장",
        "rationale": "동일 cephalosporin 계열 중복으로 치료 범위가 비합리적으로 겹칠 가능성이 큼",
        "checklist": "단일 항생제 또는 적절한 다른 계열 병용으로 정리",
    },
    {
        "combination": "cefazolin + cefuroxime",
        "status": "불필요/비권장",
        "rationale": "1·2세대 세팔로스포린 동시 사용은 대부분 중복 처방으로 판단",
        "checklist": "수술 예방 목적이면 표준 1제 선택, 치료 목적이면 감염 부위 기준 재평가",
    },
    {
        "combination": "cefepime + ceftriaxone",
        "status": "불필요/비권장",
        "rationale": "4세대 광범위 항생제와 3세대 항생제 중복으로 실익보다 내성·부작용 위험 증가",
        "checklist": "cefepime 단독 또는 목적별 병용 항생제로 재설계",
    },
    {
        "combination": "ceftriaxone + aminoglycoside",
        "status": "조건부 가능",
        "rationale": "중증 그람음성 감염 초기 경험요법에서 제한적으로 고려되나 신독성 위험 때문에 재평가 필요",
        "checklist": "신기능, 혈중농도, 배양 후 중단, 병용기간 최소화",
    },
]


INDICATION_FLOW = [
    {
        "scenario": "수술 예방적 항생제",
        "first_line": "cefazolin 등 1세대 우선 검토",
        "when_to_escalate": "오염 수술, 혐기성 필요, 기관 수술별 지침에 따른 경우",
        "review_focus": "절개 1시간 이내 투여, 수술 후 지속기간, 3세대 이상 사용 사유",
    },
    {
        "scenario": "피부·연조직 감염",
        "first_line": "MSSA/streptococci 의심 시 cefazolin 또는 cephalexin",
        "when_to_escalate": "중증, 면역저하, MRSA 위험, 괴사성 감염 의심",
        "review_focus": "MRSA 위험평가, 배농 여부, 경구 전환, 기간",
    },
    {
        "scenario": "지역사회획득 폐렴",
        "first_line": "중등도 이상에서 ceftriaxone/cefotaxime 기반 병용 검토",
        "when_to_escalate": "중환자실, 녹농균 위험, 최근 입원·항생제 노출",
        "review_focus": "중증도, 비정형균 커버 병용, 배양·항원검사, 축소",
    },
    {
        "scenario": "복강 내 감염",
        "first_line": "ceftriaxone + metronidazole 또는 cefoxitin 등 상황별 선택",
        "when_to_escalate": "원내감염, 패혈증, 녹농균 위험, ESBL 위험",
        "review_focus": "source control, 혐기성 커버, 중복 병용, 배양 후 조정",
    },
    {
        "scenario": "요로감염/신우신염",
        "first_line": "ceftriaxone 등 3세대 또는 배양 기반 경구 전환",
        "when_to_escalate": "패혈증, 도뇨관 관련, 녹농균 위험, ESBL 위험",
        "review_focus": "요배양, 혈액배양, 신기능 용량, 치료기간",
    },
    {
        "scenario": "녹농균 위험 중증 감염",
        "first_line": "cefepime 또는 ceftazidime 등 항녹농균 항생제",
        "when_to_escalate": "쇼크, CRE/ESBL 위험, 감수성 불량, 원내감염",
        "review_focus": "위험인자 기록, 배양 채취, 중복 커버, 감량·축소",
    },
]


ADMIN_HELP = """
관리자 기본 계정은 Streamlit secrets 또는 환경변수로 설정하세요.
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD_HASH`: SHA-256 해시
- `OPENAI_API_KEY`: 선택. 관리자 화면에서 세션 입력도 가능

개발 확인용 기본값은 `admin / admin1234`입니다. 운영 배포 전 반드시 변경하세요.
"""


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def get_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, os.getenv(name, default)))
    except Exception:
        return os.getenv(name, default)


def get_admin_username() -> str:
    return get_secret("ADMIN_USERNAME", "admin")


def get_admin_password_hash() -> str:
    return get_secret("ADMIN_PASSWORD_HASH", sha256_text("admin1234"))


def load_admin_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_admin_config(config: dict[str, Any]) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


@st.cache_data(show_spinner=False)
def base_antibiotics_df() -> pd.DataFrame:
    return pd.DataFrame(BASE_ANTIBIOTICS)


@st.cache_data(show_spinner=False)
def base_rules_df() -> pd.DataFrame:
    return pd.DataFrame(COMBINATION_RULES)


@st.cache_data(show_spinner=False)
def indication_df() -> pd.DataFrame:
    return pd.DataFrame(INDICATION_FLOW)


def read_uploaded_table(uploaded_file: Any) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in [".xlsx", ".xls"]:
        return pd.read_excel(uploaded_file)
    if suffix == ".csv":
        return pd.read_csv(uploaded_file)
    raise ValueError("CSV 또는 XLSX 파일만 업로드할 수 있습니다.")


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    column_map = {
        "세대": "generation",
        "성분명": "ingredient",
        "한글명": "korean_name",
        "투여경로": "route",
        "항균범위": "spectrum",
        "주요사용": "typical_use",
        "주의사항": "avoid_or_caution",
        "심사포인트": "billing_review_points",
        "신기능조절": "renal_adjustment",
        "비고": "notes",
    }
    renamed = df.rename(columns={k: v for k, v in column_map.items() if k in df.columns})
    required = list(base_antibiotics_df().columns)
    for col in required:
        if col not in renamed.columns:
            renamed[col] = ""
    return renamed[required].fillna("")


def find_value(record: dict[str, Any], *keys: str) -> str:
    lowered = {str(k).lower(): v for k, v in record.items()}
    for key in keys:
        value = lowered.get(key.lower())
        if value not in [None, ""]:
            return str(value)
    return ""


def strip_html(value: str) -> str:
    value = re.sub(r"<[^>]+>", " ", str(value))
    return re.sub(r"\s+", " ", value).strip()


def mask_secret(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:4]}...{value[-4:]}"


def sanitize_error_message(message: str, service_key: str) -> str:
    cleaned = str(message)
    if service_key:
        cleaned = cleaned.replace(service_key, mask_secret(service_key))
    cleaned = re.sub(r"(serviceKey=)[^&\s]+", r"\1****", cleaned, flags=re.IGNORECASE)
    return cleaned


def infer_generation_from_name(name: str) -> str:
    text = name.lower()
    mapping = {
        "cefazolin": "1세대",
        "cephalexin": "1세대",
        "cefuroxime": "2세대",
        "cefoxitin": "2세대",
        "ceftriaxone": "3세대",
        "cefotaxime": "3세대",
        "ceftazidime": "3세대",
        "cefepime": "4세대",
        "세파졸린": "1세대",
        "세팔렉신": "1세대",
        "세푸록심": "2세대",
        "세폭시틴": "2세대",
        "세프트리악손": "3세대",
        "세포탁심": "3세대",
        "세프타지딤": "3세대",
        "세페핌": "4세대",
    }
    for needle, generation in mapping.items():
        if needle in text:
            return generation
    return ""


def normalize_mfds_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []

    body = payload.get("body") or payload.get("Body") or payload
    items = body.get("items") if isinstance(body, dict) else None
    if isinstance(items, dict):
        item = items.get("item") or items.get("ITEM")
        if isinstance(item, list):
            return item
        if isinstance(item, dict):
            return [item]
    if isinstance(items, list):
        return items
    item = body.get("item") if isinstance(body, dict) else None
    if isinstance(item, list):
        return item
    if isinstance(item, dict):
        return [item]
    return []


def mfds_record_to_antibiotic(record: dict[str, Any], search_term: str) -> dict[str, str]:
    item_name = find_value(record, "ITEM_NAME", "itemName", "item_name", "품목명")
    entp_name = find_value(record, "ENTP_NAME", "entpName", "entp_name", "업체명")
    item_seq = find_value(record, "ITEM_SEQ", "itemSeq", "item_seq", "품목기준코드")
    class_name = find_value(record, "CLASS_NAME", "className", "CLASS_NO", "etcOtcName", "ETC_OTC_NAME")
    material = strip_html(find_value(record, "MATERIAL_NAME", "materialName", "주성분", "성분명"))
    efficacy = strip_html(find_value(record, "EE_DOC_DATA", "efcyQesitm", "efficacy", "효능효과"))
    use_method = strip_html(find_value(record, "UD_DOC_DATA", "useMethodQesitm", "용법용량"))
    caution = strip_html(find_value(record, "NB_DOC_DATA", "atpnQesitm", "주의사항"))
    storage = strip_html(find_value(record, "STORAGE_METHOD", "storageMethod", "저장방법"))

    display_name = item_name or search_term
    ingredient = search_term.lower().strip()
    return {
        "generation": infer_generation_from_name(f"{ingredient} {display_name} {material}"),
        "ingredient": ingredient,
        "korean_name": display_name,
        "route": "",
        "spectrum": material[:250],
        "typical_use": efficacy[:350],
        "avoid_or_caution": caution[:350],
        "billing_review_points": f"식약처 허가정보 동기화 항목. 품목기준코드: {item_seq or '확인 필요'}, 업체명: {entp_name or '확인 필요'}, 분류: {class_name or '확인 필요'}",
        "renal_adjustment": "허가사항, DUR, 환자 신기능 기준 별도 확인",
        "notes": f"식약처 API 동기화. 저장방법/용법: {(storage + ' ' + use_method).strip()[:250]}",
    }


def fetch_mfds_drugs(
    service_key: str,
    endpoint: str,
    search_terms: list[str],
    key_param: str,
    query_param: str,
    response_type_param: str,
    service_key_is_encoded: bool,
    rows_per_term: int,
) -> tuple[pd.DataFrame, list[str]]:
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    if not service_key:
        return pd.DataFrame(), ["식약처 API 인증키를 입력하세요."]
    if not endpoint:
        return pd.DataFrame(), ["식약처 API 엔드포인트를 입력하세요."]

    for term in search_terms:
        term = term.strip()
        if not term:
            continue
        params = {
            key_param: service_key,
            "pageNo": 1,
            "numOfRows": rows_per_term,
            response_type_param: "json",
            query_param: term,
        }
        try:
            if service_key_is_encoded:
                query = urlencode(params, safe="%")
                response = requests.get(f"{endpoint}?{query}", timeout=20)
            else:
                response = requests.get(endpoint, params=params, timeout=20)
            if response.status_code in [401, 403]:
                errors.append(
                    f"{term}: {response.status_code} 인증 실패. 인증키가 이 API에 승인되지 않았거나, Encoding/Decoding 키 사용 방식이 맞지 않을 수 있습니다. "
                    "공공데이터포털의 활용신청 승인 여부를 확인하고, Encoding 키를 쓰는 경우 'URL 인코딩된 인증키' 옵션을 켜거나 Decoding 키를 사용하세요."
                )
                continue
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError:
                errors.append(f"{term}: JSON 응답이 아닙니다. API의 type/json 지원 여부를 확인하세요.")
                continue
            items = normalize_mfds_items(payload)
            if not items:
                errors.append(f"{term}: 조회 결과 없음")
                continue
            for item in items:
                if isinstance(item, dict):
                    rows.append(mfds_record_to_antibiotic(item, term))
        except Exception as exc:
            errors.append(f"{term}: {sanitize_error_message(str(exc), service_key)}")

    if not rows:
        return pd.DataFrame(), errors
    df = pd.DataFrame(rows)
    return normalize_columns(df), errors


def save_custom_antibiotics(df: pd.DataFrame, source: str) -> Path:
    path = UPLOAD_DIR / f"antibiotics_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(path, index=False, encoding="utf-8-sig")
    st.cache_data.clear()
    return path


def load_custom_antibiotics() -> pd.DataFrame:
    files = sorted(UPLOAD_DIR.glob("antibiotics_*.csv"))
    if not files:
        return pd.DataFrame()
    return pd.read_csv(files[-1]).fillna("")


def get_antibiotics() -> pd.DataFrame:
    custom = load_custom_antibiotics()
    if custom.empty:
        return base_antibiotics_df()
    combined = pd.concat([base_antibiotics_df(), custom], ignore_index=True)
    combined["ingredient_key"] = combined["ingredient"].str.lower().str.strip()
    combined = combined.drop_duplicates("ingredient_key", keep="last").drop(columns=["ingredient_key"])
    return combined.fillna("")


def audit_log(event: str, payload: dict[str, Any]) -> None:
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "event": event,
        "payload": payload,
    }
    log_path = LOG_DIR / f"audit_{datetime.now().strftime('%Y%m')}.jsonl"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def login_panel() -> bool:
    with st.sidebar.expander("관리자 로그인", expanded=not st.session_state.get("is_admin", False)):
        username = st.text_input("아이디", value="", key="admin_username")
        password = st.text_input("비밀번호", type="password", key="admin_password")
        if st.button("로그인", use_container_width=True):
            ok = username == get_admin_username() and sha256_text(password) == get_admin_password_hash()
            st.session_state["is_admin"] = ok
            audit_log("admin_login", {"username": username, "success": ok})
            if ok:
                st.success("관리자 권한이 활성화되었습니다.")
            else:
                st.error("아이디 또는 비밀번호가 올바르지 않습니다.")
        if st.session_state.get("is_admin", False) and st.button("로그아웃", use_container_width=True):
            st.session_state["is_admin"] = False
            st.rerun()
    return bool(st.session_state.get("is_admin", False))


def find_drug(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if not query:
        return df
    key = query.lower().strip()
    mask = (
        df["ingredient"].str.lower().str.contains(key, na=False)
        | df["korean_name"].str.lower().str.contains(key, na=False)
        | df["generation"].str.lower().str.contains(key, na=False)
        | df["typical_use"].str.lower().str.contains(key, na=False)
    )
    return df[mask]


def evaluate_combination(selected: list[str], drug_df: pd.DataFrame) -> list[dict[str, str]]:
    selected_norm = [x.lower().strip() for x in selected]
    results: list[dict[str, str]] = []
    rule_df = base_rules_df()

    for _, rule in rule_df.iterrows():
        members = [x.strip().lower() for x in str(rule["combination"]).split("+")]
        if all(any(member in selected_item for selected_item in selected_norm) for member in members):
            results.append(rule.to_dict())

    cephalosporins = drug_df[drug_df["ingredient"].str.lower().isin(selected_norm)]
    if len(cephalosporins) >= 2:
        results.append(
            {
                "combination": " + ".join(selected),
                "status": "자동 경고",
                "rationale": "세팔로스포린 계열이 2개 이상 동시에 선택되었습니다. 대부분 중복 처방 가능성이 있어 적응증과 배양 결과를 재확인해야 합니다.",
                "checklist": "동일 계열 중복, spectrum 중복, 병용 사유, 중단 후보, 기관 항생제 지침",
            }
        )
    if not results:
        results.append(
            {
                "combination": " + ".join(selected) if selected else "선택 없음",
                "status": "규칙 없음",
                "rationale": "내장 규칙에서 명시 경고는 발견되지 않았습니다. 단, DUR·급여기준·환자별 금기는 별도 확인해야 합니다.",
                "checklist": "알레르기, 임신, 연령, 신기능, 간기능, 배양검사, 급여기준",
            }
        )
    return results


def render_status_badge(status: str) -> None:
    color = {
        "가능": "#0f766e",
        "조건부 가능": "#b45309",
        "주의/대체 검토": "#b45309",
        "불필요/비권장": "#b91c1c",
        "자동 경고": "#b91c1c",
        "규칙 없음": "#334155",
    }.get(status, "#334155")
    st.markdown(
        f"<span style='display:inline-block;padding:0.25rem 0.55rem;border-radius:999px;background:{color};color:white;font-size:0.85rem'>{status}</span>",
        unsafe_allow_html=True,
    )


def build_ai_context(drug_df: pd.DataFrame) -> str:
    drug_context = drug_df.to_markdown(index=False)
    rules_context = base_rules_df().to_markdown(index=False)
    flow_context = indication_df().to_markdown(index=False)
    sources = "\n".join([f"- {s['name']}: {s['url']} ({s['use']})" for s in REFERENCE_SOURCES])
    return f"""
이 앱의 내장 항생제 지식베이스입니다.

[항생제 목록]
{drug_context}

[조합 규칙]
{rules_context}

[처방 검토 흐름]
{flow_context}

[근거 출처]
{sources}
"""


def call_openai(question: str, drug_df: pd.DataFrame, api_key: str, model: str) -> str:
    if OpenAI is None:
        return "openai 패키지가 설치되어 있지 않습니다. `pip install -r requirements.txt` 후 다시 실행하세요."
    if not api_key:
        return "관리자 화면에서 OpenAI API 키를 설정하거나 OPENAI_API_KEY 환경변수를 지정하세요."
    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=(
            "당신은 한국 병원 원무·청구심사 실무자를 돕는 항생제 가이드 보조자입니다. "
            "제공된 지식베이스와 출처 안에서만 답하고, 환자 진료 최종 결정처럼 단정하지 마세요. "
            "답변은 1) 요약판정 2) 처방/심사 체크포인트 3) 불확실성/추가확인 4) 근거 출처 순서로 한국어로 작성하세요. "
            "DUR, 급여기준, 허가사항, 기관 지침 확인이 필요한 경우 명시하세요."
        ),
        input=f"{build_ai_context(drug_df)}\n\n[질문]\n{question}",
    )
    audit_log("ai_question", {"question": question, "model": model})
    return response.output_text


def admin_page(drug_df: pd.DataFrame) -> None:
    st.subheader("관리자 설정")
    st.info(ADMIN_HELP)

    uploaded = st.file_uploader("항생제 리스트 업로드", type=["csv", "xlsx", "xls"])
    if uploaded:
        try:
            raw_df = read_uploaded_table(uploaded)
            normalized = normalize_columns(raw_df)
            st.dataframe(normalized, use_container_width=True, hide_index=True)
            if st.button("업로드 자료 반영", type="primary"):
                save_custom_antibiotics(normalized, "upload")
                audit_log("upload_antibiotics", {"filename": uploaded.name, "rows": len(normalized)})
                st.success(f"{len(normalized):,}개 항목을 반영했습니다.")
                st.rerun()
        except Exception as exc:
            st.error(f"업로드 처리 실패: {exc}")

    st.divider()
    st.subheader("식약처 API 설정 및 약제 동기화")
    st.caption("공공데이터포털에서 발급받은 식품의약품안전처 의약품 API 인증키를 등록하면 약제 허가정보를 조회해 항생제 리스트에 반영할 수 있습니다.")
    config = load_admin_config()
    mfds_config = config.get("mfds", {})
    mfds_key = st.text_input(
        "식약처 API 인증키",
        value=mfds_config.get("service_key", get_secret("MFDS_API_KEY", "")),
        type="password",
        help="공공데이터포털(data.go.kr)에서 발급받은 일반 인증키를 입력하세요.",
    )
    mfds_endpoint = st.text_input(
        "식약처 API 엔드포인트",
        value=mfds_config.get("endpoint", DEFAULT_MFDS_ENDPOINT),
        help="기본값은 의약품 제품 허가정보 조회 API입니다.",
    )
    mfds_key_param = st.text_input(
        "인증키 파라미터명",
        value=mfds_config.get("key_param", "serviceKey"),
        help="공공데이터포털 API에 따라 serviceKey 또는 ServiceKey를 사용합니다.",
    )
    mfds_key_is_encoded = st.checkbox(
        "URL 인코딩된 인증키 사용",
        value=bool(mfds_config.get("service_key_is_encoded", False)),
        help="공공데이터포털의 Encoding 인증키를 붙여 넣은 경우 체크하세요. Decoding 인증키라면 체크하지 마세요.",
    )
    mfds_query_param = st.text_input(
        "검색 파라미터명",
        value=mfds_config.get("query_param", "item_name"),
        help="API 종류에 따라 item_name, itemName 등이 다를 수 있습니다.",
    )
    mfds_response_type_param = st.text_input(
        "JSON 응답 파라미터명",
        value=mfds_config.get("response_type_param", "type"),
        help="API에 따라 type=json 또는 _type=json을 사용합니다.",
    )
    mfds_terms = st.text_area(
        "동기화 검색어",
        value=mfds_config.get("search_terms", DEFAULT_MFDS_TERMS),
        help="쉼표로 구분합니다. 예: cefazolin, ceftriaxone, cefepime",
    )
    rows_per_term = st.number_input(
        "검색어별 최대 조회 건수",
        min_value=1,
        max_value=100,
        value=int(mfds_config.get("rows_per_term", 10)),
        step=1,
    )
    mfds_col1, mfds_col2 = st.columns([1, 1])
    with mfds_col1:
        if st.button("식약처 API 설정 저장", use_container_width=True):
            config["mfds"] = {
                "service_key": mfds_key,
                "endpoint": mfds_endpoint,
                "key_param": mfds_key_param,
                "service_key_is_encoded": bool(mfds_key_is_encoded),
                "query_param": mfds_query_param,
                "response_type_param": mfds_response_type_param,
                "search_terms": mfds_terms,
                "rows_per_term": int(rows_per_term),
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }
            save_admin_config(config)
            audit_log("mfds_config_update", {"endpoint": mfds_endpoint, "query_param": mfds_query_param, "has_key": bool(mfds_key)})
            st.success("식약처 API 설정을 저장했습니다.")
    with mfds_col2:
        if st.button("식약처 API 동기화", type="primary", use_container_width=True):
            terms = [x.strip() for x in mfds_terms.split(",") if x.strip()]
            with st.spinner("식약처 API에서 약제 허가정보를 조회하는 중입니다."):
                synced_df, errors = fetch_mfds_drugs(
                    mfds_key,
                    mfds_endpoint,
                    terms,
                    mfds_key_param,
                    mfds_query_param,
                    mfds_response_type_param,
                    bool(mfds_key_is_encoded),
                    int(rows_per_term),
                )
            if not synced_df.empty:
                current_custom = load_custom_antibiotics()
                merged = pd.concat([current_custom, synced_df], ignore_index=True) if not current_custom.empty else synced_df
                merged = normalize_columns(merged)
                merged["ingredient_key"] = merged["ingredient"].str.lower().str.strip()
                merged = merged.drop_duplicates("ingredient_key", keep="last").drop(columns=["ingredient_key"])
                save_custom_antibiotics(merged, "mfds")
                audit_log("mfds_sync", {"rows": len(synced_df), "terms": terms, "errors": errors[:10]})
                st.success(f"식약처 API에서 {len(synced_df):,}개 항목을 동기화했습니다.")
                st.dataframe(synced_df, use_container_width=True, hide_index=True)
                if errors:
                    st.warning("일부 검색어는 결과가 없거나 오류가 있었습니다.")
                    st.write(errors[:10])
            else:
                st.error("동기화된 항목이 없습니다.")
                if errors:
                    st.write(errors[:10])

    st.divider()
    st.subheader("AI API 설정")
    current_key = get_secret("OPENAI_API_KEY", "")
    api_key = st.text_input("OpenAI API Key", value=current_key, type="password")
    model = st.text_input("모델", value=st.session_state.get("openai_model", DEFAULT_MODEL))
    if st.button("세션에 API 설정 저장"):
        st.session_state["openai_api_key"] = api_key
        st.session_state["openai_model"] = model
        audit_log("api_config_update", {"model": model, "has_key": bool(api_key)})
        st.success("현재 세션에 API 설정을 저장했습니다.")

    st.divider()
    st.subheader("현재 항생제 데이터")
    st.download_button(
        "현재 데이터 CSV 다운로드",
        data=drug_df.to_csv(index=False, encoding="utf-8-sig"),
        file_name="antibiotics_current.csv",
        mime="text/csv",
        use_container_width=True,
    )


def main() -> None:
    inject_site_style()
    is_admin = login_panel()
    drug_df = get_antibiotics()

    render_website_header(len(drug_df), is_admin)

    with st.sidebar:
        st.markdown("### Antibiotic Guide")
        st.caption("병원 원무·청구심사 실무 웹앱")
        st.markdown("### 근거 자료")
        for source in REFERENCE_SOURCES:
            st.markdown(f"- [{source['name']}]({source['url']})")
        st.warning("진료 결정 자동화 도구가 아닙니다. 처방권자 판단과 최신 고시·허가사항 확인이 필요합니다.")

    tabs = ["처방 검토", "약제 검색", "감염별 처방 흐름", "AI 질의", "자료 출처"]
    if is_admin:
        tabs.append("관리자")
    selected_tabs = st.tabs(tabs)

    with selected_tabs[0]:
        st.subheader("처방 조합 검토")
        left, right = st.columns([1, 1])
        with left:
            selected = st.multiselect(
                "검토할 항생제 성분",
                options=drug_df["ingredient"].tolist(),
                format_func=lambda x: f"{x} ({drug_df.loc[drug_df['ingredient'] == x, 'korean_name'].iloc[0]})",
            )
            scenario = st.selectbox("감염/업무 시나리오", indication_df()["scenario"].tolist())
            patient_flags = st.multiselect(
                "환자·청구 체크 플래그",
                ["신기능 저하", "임신/수유", "소아/고령", "중증/패혈증", "원내감염", "녹농균 위험", "ESBL/CRE 위험", "베타락탐 알레르기", "수술 예방 목적"],
            )
        with right:
            flow = indication_df()[indication_df()["scenario"] == scenario].iloc[0]
            st.markdown("#### 시나리오 기본 흐름")
            st.write(f"**1차 검토:** {flow['first_line']}")
            st.write(f"**상향/변경 조건:** {flow['when_to_escalate']}")
            st.write(f"**심사 포인트:** {flow['review_focus']}")

        st.markdown("#### 조합 판정")
        for result in evaluate_combination(selected, drug_df):
            cols = st.columns([0.18, 0.82])
            with cols[0]:
                render_status_badge(result["status"])
            with cols[1]:
                st.write(f"**{result['combination']}**")
                st.write(result["rationale"])
                st.caption(f"체크리스트: {result['checklist']}")

        if selected:
            st.markdown("#### 선택 약제별 심사 체크")
            st.dataframe(
                drug_df[drug_df["ingredient"].isin(selected)][
                    ["generation", "ingredient", "korean_name", "route", "typical_use", "avoid_or_caution", "billing_review_points", "renal_adjustment"]
                ],
                use_container_width=True,
                hide_index=True,
            )

        if patient_flags:
            st.markdown("#### 플래그 기반 추가 확인")
            if "신기능 저하" in patient_flags:
                st.error("신기능 저하: cefepime 신경독성, ceftazidime/cefazolin/cefuroxime 등 신배설 약제 용량·간격 조절을 확인하세요.")
            if "ESBL/CRE 위험" in patient_flags:
                st.warning("ESBL/CRE 위험: 3·4세대 cephalosporin 단독 유지가 부적절할 수 있어 배양·감수성 및 기관 지침 확인이 필요합니다.")
            if "수술 예방 목적" in patient_flags:
                st.warning("수술 예방: 투여 시점, 수술 후 지속기간, 3세대 이상 사용 사유, 병용 투여 사유가 심사 포인트입니다.")
            if "베타락탐 알레르기" in patient_flags:
                st.error("베타락탐 알레르기: 알레르기 유형과 중증도를 확인하고 대체 계열 필요성을 처방권자와 검토하세요.")

    with selected_tabs[1]:
        st.subheader("약제 검색")
        keyword = st.text_input("성분명, 한글명, 세대, 적응증 검색")
        generation = st.multiselect("세대 필터", sorted(drug_df["generation"].unique()))
        filtered = find_drug(drug_df, keyword)
        if generation:
            filtered = filtered[filtered["generation"].isin(generation)]
        st.dataframe(filtered, use_container_width=True, hide_index=True)

    with selected_tabs[2]:
        st.subheader("감염별 처방 순서·심사 흐름")
        st.dataframe(indication_df(), use_container_width=True, hide_index=True)
        st.markdown("#### 실무 공통 순서")
        st.write("1. 감염 부위와 중증도 확인")
        st.write("2. 배양검사 필요 여부와 채취 시점 확인")
        st.write("3. 1차 경험요법 선택 후 환자 위험인자 반영")
        st.write("4. 48~72시간 내 배양·임상 반응으로 축소 또는 변경")
        st.write("5. 주사-경구 전환 가능성, 총 치료기간, 급여·DUR·허가사항 확인")

    with selected_tabs[3]:
        st.subheader("AI 근거 제한 질의")
        st.caption("AI 답변은 내장 지식베이스와 업로드 자료를 바탕으로 한 실무 보조입니다. 최신 고시·허가사항 최종 확인은 별도로 필요합니다.")
        question = st.text_area("질문", placeholder="예: ceftriaxone + metronidazole 처방 시 심사에서 확인해야 할 포인트는?")
        api_key = st.session_state.get("openai_api_key", get_secret("OPENAI_API_KEY", ""))
        model = st.session_state.get("openai_model", DEFAULT_MODEL)
        if not is_admin and not api_key:
            st.info("AI API는 관리자가 설정한 뒤 사용할 수 있습니다.")
        if st.button("AI 답변 생성", type="primary", disabled=not bool(question.strip())):
            with st.spinner("근거 자료를 기준으로 답변을 생성하는 중입니다."):
                answer = call_openai(question, drug_df, api_key, model)
            st.markdown(answer)

    with selected_tabs[4]:
        st.subheader("자료 출처와 운영 시 확인 항목")
        for source in REFERENCE_SOURCES:
            st.markdown(f"**[{source['name']}]({source['url']})**")
            st.write(source["use"])
        st.markdown("#### 운영 체크")
        st.write("- HIRA 고시·급여기준, DUR 병용금기, 허가사항 변경 시 관리자 업로드 자료를 갱신하세요.")
        st.write("- 병원별 항생제 위원회 또는 감염관리실 지침을 별도 컬럼으로 추가해 로컬 기준을 우선 적용하세요.")
        st.write("- 항생제 사용평가/적정성 평가 자료와 연동할 경우 처방일수, 예방적 사용기간, 배양검사 여부 컬럼을 추가하세요.")

    if is_admin:
        with selected_tabs[5]:
            admin_page(drug_df)


if __name__ == "__main__":
    main()
