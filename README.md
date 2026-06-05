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

개발 확인용 기본 관리자 계정:

```text
아이디: admin
비밀번호: admin1234
```

```toml
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD_HASH = "SHA256_HASH"
OPENAI_API_KEY = "sk-..."
```

배포 전 반드시 기본 비밀번호를 변경하세요.

## 식약처 API 동기화

관리자 화면에서 공공데이터포털 식품의약품안전처 API 인증키를 등록할 수 있습니다.

기본 설정값:

```text
엔드포인트: https://apis.data.go.kr/1471000/DrugPrdtPrmsnInfoService07/getDrugPrdtPrmsnInq07
인증키 파라미터명: serviceKey
검색 파라미터명: item_name
JSON 응답 파라미터명: type
```

API 종류나 승인 계정에 따라 파라미터명이 `ServiceKey`, `itemName`, `_type` 등으로 다를 수 있으므로 관리자 화면에서 수정할 수 있게 되어 있습니다. 공공데이터포털의 `Encoding` 인증키를 쓰는 경우 `URL 인코딩된 인증키 사용`을 체크하고, `Decoding` 인증키를 쓰는 경우 체크하지 마세요. 동기화 버튼을 누르면 검색어별 조회 결과가 항생제 리스트에 반영됩니다.

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
- 관리자: 리스트 업로드, 식약처 API 동기화, AI API 설정, 현재 데이터 다운로드
