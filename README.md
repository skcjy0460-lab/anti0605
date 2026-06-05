# 항생제 처방·청구심사 실무 가이드

병원 원무·청구심사 실무자를 위한 Streamlit 기반 항생제 검토 도구입니다. 1세대~4세대 세팔로스포린을 중심으로 약제 검색, 처방 조합 검토, 감염별 처방 흐름, 관리자 전용 항생제 리스트 업로드, OpenAI API 기반 근거 제한 질의 기능을 제공합니다.

## 실행

```powershell
pip install -r requirements.txt
streamlit run app.py
```

실행 후 브라우저에서 아래 주소로 접속합니다.

```text
http://localhost:8501
```

Streamlit Community Cloud, 사내 서버, 또는 클라우드 VM에 올리면 일반 웹사이트처럼 URL로 접속할 수 있습니다. `.streamlit/config.toml`에는 웹사이트형 밝은 테마와 서버 기본 설정을 포함했습니다.

## 관리자 계정

운영 환경에서는 Streamlit secrets 또는 환경변수로 아래 값을 설정하세요.

```toml
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "SHA256_HASH"
OPENAI_API_KEY = "sk-..."
```

개발 확인용 기본 계정은 `admin / admin1234`입니다. 배포 전 반드시 변경하세요.

비밀번호 해시는 아래 방식으로 만들 수 있습니다.

```python
import hashlib
print(hashlib.sha256("새비밀번호".encode("utf-8")).hexdigest())
```

## 업로드 컬럼

CSV 또는 XLSX를 업로드할 수 있습니다. 한글 컬럼과 영문 컬럼을 모두 지원합니다.

| 한글 컬럼 | 영문 컬럼 |
| --- | --- |
| 세대 | generation |
| 성분명 | ingredient |
| 한글명 | korean_name |
| 투여경로 | route |
| 항균범위 | spectrum |
| 주요사용 | typical_use |
| 주의사항 | avoid_or_caution |
| 심사포인트 | billing_review_points |
| 신기능조절 | renal_adjustment |
| 비고 | notes |

업로드 자료는 같은 성분명이 있을 경우 내장 기본 자료보다 우선 적용됩니다.

## 근거 자료

- 질병관리청·대한감염학회 전국 의료기관 항생제 사용량 분석 연보 보도자료
- 건강보험심사평가원 약제기준정보, DUR, 요양기관 업무포털
- OpenAI Responses API Reference

이 앱은 처방권자의 진료 판단을 대체하지 않습니다. 최신 고시, 허가사항, DUR, 병원 감염관리 지침 확인이 필요합니다.

## 웹사이트형 화면 구성

- 첫 화면: AI 작업공간형 헤더와 등록 약제/조합 규칙/감염 흐름 현황
- 처방 검토: 조합 판정, 감염 시나리오, 환자·청구 플래그
- 약제 검색: 성분명·한글명·세대·적응증 검색
- AI 질의: 관리자 API 설정 기반 근거 제한 답변
- 관리자: 리스트 업로드, API 설정, 현재 데이터 다운로드
